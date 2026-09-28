import logging
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.job import JobQueue, JobStatus
from app.services.alert_engine import alert_engine
from app.services.process_pool import ProcessPoolManager

logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器 - 负责定时补跑失败任务和评估告警规则"""

    # 调度配置常量
    RETRY_INTERVAL_MINUTES = 1  # 重试间隔（分钟）
    FIRST_RUN_DELAY_MINUTES = 1  # 首次运行延迟（分钟）
    MAX_RETRY_COUNT = 3  # 最大重试次数
    BATCH_SIZE = 100  # 每批处理的任务数量

    # 告警评估配置
    ALERT_EVAL_INTERVAL_MINUTES = 5  # 告警评估间隔（分钟）
    ALERT_FIRST_RUN_DELAY_MINUTES = 2  # 告警首次运行延迟（分钟）

    def __init__(self, ws_manager=None, pool_manager: Optional[ProcessPoolManager] = None):
        """
        初始化调度器

        Args:
            ws_manager: WebSocket 管理器（可选，用于状态推送）
            pool_manager: 进程池管理器（可选，用于任务分发）
        """
        self.scheduler = AsyncIOScheduler(
            timezone='Asia/Shanghai',
            job_defaults={
                'coalesce': True,  # 合并错过的执行
                'max_instances': 1  # 同时只运行一个补跑任务
            }
        )
        self.ws_manager = ws_manager
        self.pool_manager = pool_manager
        self.logger = logger

    async def start(self):
        """启动调度器"""
        self.logger.info("正在启动任务调度器...")

        # 添加定时任务：重试失败任务
        self.scheduler.add_job(
            func=self.retry_failed_jobs,
            trigger=IntervalTrigger(minutes=self.RETRY_INTERVAL_MINUTES),
            id='retry_failed_jobs',
            name='重试失败任务',
            next_run_time=datetime.now() + timedelta(minutes=self.FIRST_RUN_DELAY_MINUTES)
        )

        # 添加定时任务：评估告警规则
        self.scheduler.add_job(
            func=self.evaluate_alerts,
            trigger=IntervalTrigger(minutes=self.ALERT_EVAL_INTERVAL_MINUTES),
            id='evaluate_alerts',
            name='评估告警规则',
            next_run_time=datetime.now() + timedelta(minutes=self.ALERT_FIRST_RUN_DELAY_MINUTES)
        )

        # 添加定时任务：分发待处理任务
        self.scheduler.add_job(
            func=self.dispatch_pending_jobs,
            trigger=IntervalTrigger(seconds=10),
            id='dispatch_pending_jobs',
            name='分发待处理任务',
            next_run_time=datetime.now() + timedelta(seconds=5)
        )

        self.scheduler.start()
        self.logger.info("任务调度器启动成功")

    async def retry_failed_jobs(self):
        """
        扫描并重试失败的任务

        逻辑：
        1. 查询 status='failed' 且 retry_count < MAX_RETRY_COUNT 的任务
        2. 将状态重置为 'pending'，清空 error_msg
        3. 保留 retry_count（由执行器在失败时递增）
        """
        self.logger.info("开始扫描失败任务...")

        try:
            # 获取数据库会话
            async with get_session() as session:
                # 查询失败任务
                stmt = select(JobQueue).where(
                    JobQueue.status == JobStatus.FAILED,
                    JobQueue.retry_count < self.MAX_RETRY_COUNT
                ).order_by(JobQueue.updated_at.asc()).limit(self.BATCH_SIZE)

                result = await session.execute(stmt)
                failed_jobs = result.scalars().all()

                if not failed_jobs:
                    self.logger.info("没有需要重试的失败任务")
                    return

                self.logger.info(f"发现 {len(failed_jobs)} 个失败任务，开始重置状态")

                # 逐个重置任务状态（内存中）
                for job in failed_jobs:
                    job.status = JobStatus.PENDING
                    job.error_msg = None

                    self.logger.info(
                        f"任务 #{job.id} 已重置为 pending "
                        f"(重试次数: {job.retry_count}/{self.MAX_RETRY_COUNT})"
                    )

                # 批量提交所有更改
                try:
                    await session.commit()
                    self.logger.info(f"成功重置 {len(failed_jobs)} 个失败任务")

                    # 广播所有重置消息
                    if self.ws_manager:
                        for job in failed_jobs:
                            await self.ws_manager.broadcast({
                                "type": "log",
                                "level": "info",
                                "msg": f"任务 #{job.id} 已重置为 pending 状态进行重试"
                            })
                except Exception as e:
                    self.logger.error(f"批量重置任务失败: {e}")
                    await session.rollback()

        except Exception as e:
            self.logger.error(f"扫描失败任务时出错: {e}", exc_info=True)

    async def evaluate_alerts(self):
        """
        评估告警规则

        定期调用告警引擎评估所有启用的告警规则。
        """
        self.logger.info("开始评估告警规则...")

        try:
            await alert_engine.evaluate_rules()
            self.logger.info("告警规则评估完成")

        except Exception as e:
            self.logger.error(f"告警规则评估失败: {e}", exc_info=True)

    async def dispatch_pending_jobs(self):
        """
        扫描并分发待处理任务到进程池

        逻辑：
        1. 检查进程池是否可用
        2. 查询 status='pending' 的任务（按 priority DESC, created_at ASC 排序）
        3. 获取进程池可用插槽数（max_workers - active_workers）
        4. 提交任务到进程池（不超过可用插槽数）
        5. 更新任务状态为 'processing'
        6. 通过 WebSocket 广播任务状态
        """
        # 检查进程池是否可用
        if self.pool_manager is None:
            self.logger.warning("进程池管理器未初始化，跳过任务分发")
            return

        pool_status = self.pool_manager.get_pool_status()
        if not pool_status.get('is_running', False):
            self.logger.warning("进程池未运行，跳过任务分发")
            return

        try:
            # 计算可用插槽数
            active_workers = self.pool_manager.get_active_workers()
            available_slots = self.pool_manager.max_workers - active_workers

            if available_slots <= 0:
                self.logger.debug(f"进程池已满（{active_workers}/{self.pool_manager.max_workers}），跳过任务分发")
                return

            self.logger.info(f"开始扫描待处理任务（可用插槽: {available_slots}）...")

            # 获取数据库会话
            async with get_session() as session:
                # 查询待处理任务（按优先级和创建时间排序）
                stmt = select(JobQueue).where(
                    JobQueue.status == JobStatus.PENDING
                ).order_by(
                    JobQueue.priority.desc(),
                    JobQueue.created_at.asc()
                ).limit(available_slots)

                result = await session.execute(stmt)
                pending_jobs = result.scalars().all()

                if not pending_jobs:
                    self.logger.debug("没有待处理任务")
                    return

                self.logger.info(f"发现 {len(pending_jobs)} 个待处理任务，开始分发")

                # 逐个提交任务到进程池
                dispatched_count = 0
                for job in pending_jobs:
                    try:
                        # 更新任务状态为 processing
                        job.status = JobStatus.PROCESSING
                        await session.commit()

                        # 提交任务到进程池
                        await self.pool_manager.submit_job(job.id)

                        # 广播任务状态
                        if self.ws_manager:
                            await self.ws_manager.broadcast({
                                "type": "status",
                                "job_id": job.id,
                                "status": "processing",
                                "message": f"任务 #{job.id} 已分发到进程池（优先级: {job.priority}）"
                            })

                        dispatched_count += 1
                        self.logger.info(
                            f"任务 #{job.id} 已分发到进程池（优先级: {job.priority}, "
                            f"{dispatched_count}/{len(pending_jobs)}）"
                        )

                    except Exception as e:
                        self.logger.error(f"分发任务 #{job.id} 失败: {e}", exc_info=True)
                        # 回滚该任务的状态更新
                        await session.rollback()
                        # 重新获取会话以继续处理下一个任务
                        continue

                self.logger.info(
                    f"任务分发完成: 成功 {dispatched_count}/{len(pending_jobs)} "
                    f"(活跃工作进程: {self.pool_manager.get_active_workers()}/{self.pool_manager.max_workers})"
                )

        except Exception as e:
            self.logger.error(f"扫描和分发待处理任务时出错: {e}", exc_info=True)

    async def shutdown(self):
        """优雅停止调度器"""
        self.logger.info("正在停止任务调度器...")
        self.scheduler.shutdown(wait=True)
        self.logger.info("任务调度器已停止")
