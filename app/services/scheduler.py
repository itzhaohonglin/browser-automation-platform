import asyncio
import logging
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_session
from app.models.job import JobQueue, JobStatus
from app.models.config import CrawlerConfig
from app.services.process_pool import ProcessPoolManager

logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器 - 负责定时补跑失败任务和周期性任务调度"""

    FIRST_RUN_DELAY_MINUTES = 1  # 首次运行延迟（分钟）

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
            trigger=IntervalTrigger(minutes=settings.RETRY_INTERVAL_MINUTES),
            id='retry_failed_jobs',
            name='重试失败任务',
            next_run_time=datetime.now() + timedelta(minutes=self.FIRST_RUN_DELAY_MINUTES)
        )

        # 添加定时任务：分发待处理任务
        self.scheduler.add_job(
            func=self.dispatch_pending_jobs,
            trigger=IntervalTrigger(minutes=settings.DISPATCH_INTERVAL_MINUTES),
            id='dispatch_pending_jobs',
            name='分发待处理任务',
            next_run_time=datetime.now() + timedelta(seconds=5)
        )

        # 添加定时任务：重新创建周期性任务
        self.scheduler.add_job(
            func=self.recreate_scheduled_jobs,
            trigger=IntervalTrigger(minutes=settings.SCHEDULE_CHECK_INTERVAL_MINUTES),
            id='recreate_scheduled_jobs',
            name='重新创建周期性任务',
            next_run_time=datetime.now() + timedelta(minutes=settings.SCHEDULE_FIRST_RUN_DELAY_MINUTES)
        )

        # 添加定时任务：检测并处理超时任务
        if settings.TASK_TIMEOUT_CHECK_ENABLED:
            self.scheduler.add_job(
                func=self.check_timeout_jobs,
                trigger=IntervalTrigger(minutes=settings.TASK_TIMEOUT_CHECK_INTERVAL_MINUTES),
                id='check_timeout_jobs',
                name='检测超时任务',
                next_run_time=datetime.now() + timedelta(minutes=2)
            )
            self.logger.info(
                f"任务超时检测已启用（阈值: {settings.TASK_TIMEOUT_MINUTES} 分钟，"
                f"检测间隔: {settings.TASK_TIMEOUT_CHECK_INTERVAL_MINUTES} 分钟）"
            )

        self.scheduler.start()
        self.logger.info("任务调度器启动成功")

    async def retry_failed_jobs(self):
        """
        扫描并重试失败的任务（智能重试）

        逻辑：
        1. 检查是否有大量 pending 任务未处理，如果有则跳过重试
        2. 查询失败时间超过最小等待时间的任务
        3. 将状态重置为 'pending'，清空 error_msg
        4. 保留 retry_count（由执行器在失败时递增）
        """
        self.logger.info("开始扫描失败任务...")

        try:
            # 获取数据库会话
            async with get_session() as session:
                # 步骤1：检查 pending 任务数量
                pending_count_stmt = select(func.count(JobQueue.id)).where(
                    JobQueue.status == JobStatus.PENDING
                )
                pending_count_result = await session.execute(pending_count_stmt)
                pending_count = pending_count_result.scalar()

                if pending_count > settings.RETRY_SKIP_IF_PENDING_OVER:
                    self.logger.warning(
                        f"当前有 {pending_count} 个 pending 任务（超过阈值 {settings.RETRY_SKIP_IF_PENDING_OVER}），"
                        f"跳过失败任务重试，优先处理现有任务"
                    )
                    return

                self.logger.info(f"当前 pending 任务数: {pending_count}，继续重试流程")

                # 步骤2：查询符合条件的失败任务
                min_wait_time = datetime.now() - timedelta(minutes=settings.RETRY_MIN_WAIT_MINUTES)

                stmt = select(JobQueue).where(
                    JobQueue.status == JobStatus.FAILED,
                    JobQueue.retry_count < settings.MAX_RETRY_COUNT,
                    JobQueue.updated_at < min_wait_time  # 失败时间超过最小等待时间
                ).order_by(JobQueue.updated_at.asc()).limit(settings.RETRY_BATCH_SIZE)

                result = await session.execute(stmt)
                failed_jobs = result.scalars().all()

                if not failed_jobs:
                    self.logger.info("没有需要重试的失败任务")
                    return

                self.logger.info(
                    f"发现 {len(failed_jobs)} 个失败任务（失败时间超过 {settings.RETRY_MIN_WAIT_MINUTES} 分钟），"
                    f"开始重置状态"
                )

                # 步骤3：逐个重置任务状态
                for job in failed_jobs:
                    job.status = JobStatus.PENDING
                    job.error_msg = None

                    self.logger.info(
                        f"任务 #{job.id} 已重置为 pending "
                        f"(重试次数: {job.retry_count}/{settings.MAX_RETRY_COUNT}, "
                        f"失败时间: {job.updated_at})"
                    )

                # 步骤4：批量提交所有更改
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

    async def dispatch_pending_jobs(self):
        """
        扫描并分发待处理任务到进程池

        逻辑：
        1. 检查进程池是否可用
        2. **从数据库查询真实的PROCESSING任务数（不依赖内存计数器）**
        3. 查询 status='pending' 的任务（按 priority DESC, created_at ASC 排序）
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
            # ===关键修复：直接从数据库查询PROCESSING任务数，不依赖内存计数器===
            # 这解决了进程池回调失败导致的计数器漂移问题
            async with get_session() as session:
                stmt = select(func.count()).where(JobQueue.status == JobStatus.PROCESSING)
                result = await session.execute(stmt)
                db_processing_count = result.scalar() or 0

            # 使用数据库的真实值计算可用插槽
            available_slots = self.pool_manager.max_workers - db_processing_count

            # 同时更新内存计数器（保持一致性）
            memory_count = self.pool_manager.get_active_workers()
            if memory_count != db_processing_count:
                self.logger.warning(
                    f"进程池计数器不一致：内存={memory_count}, 数据库={db_processing_count}，"
                    f"以数据库为准"
                )
                # 强制同步
                await self.pool_manager.sync_worker_count_from_db()

            if available_slots <= 0:
                self.logger.info(
                    f"进程池已满（数据库PROCESSING: {db_processing_count}/{self.pool_manager.max_workers}），"
                    f"跳过任务分发"
                )
                return

            self.logger.info(
                f"开始扫描待处理任务（数据库PROCESSING: {db_processing_count}, "
                f"可用插槽: {available_slots}）..."
            )

            # 获取数据库会话
            async with get_session() as session:
                # 关键修复：刷新会话以确保能看到最新数据
                # 解决数据库事务隔离导致的查询返回空结果问题
                await session.execute(select(1))  # 预热查询，刷新连接

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
                    # 修改为INFO级别，方便诊断
                    self.logger.info(f"没有待处理任务（可用插槽: {available_slots}）")
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

    async def check_timeout_jobs(self):
        """
        检测并处理超时任务

        逻辑：
        1. 查询所有 status='processing' 且 updated_at 超过阈值的任务
        2. 将这些任务标记为 'failed'，设置错误信息
        3. 递增 retry_count
        4. 这些任务会被后续的重试机制重新执行
        """
        self.logger.info(
            f"开始检测超时任务（阈值: {settings.TASK_TIMEOUT_MINUTES} 分钟）..."
        )

        try:
            async with get_session() as session:
                # 计算超时阈值：当前时间 - 超时分钟数
                timeout_threshold = datetime.now() - timedelta(
                    minutes=settings.TASK_TIMEOUT_MINUTES
                )

                # 查询所有超时的 processing 任务
                stmt = select(JobQueue).where(
                    JobQueue.status == JobStatus.PROCESSING,
                    JobQueue.updated_at < timeout_threshold
                )

                result = await session.execute(stmt)
                timeout_jobs = result.scalars().all()

                if not timeout_jobs:
                    self.logger.debug("没有超时任务")
                    return

                self.logger.warning(
                    f"发现 {len(timeout_jobs)} 个超时任务（超过 {settings.TASK_TIMEOUT_MINUTES} 分钟未完成）"
                )

                # 逐个处理超时任务
                for job in timeout_jobs:
                    # 计算任务已运行时长
                    runtime_minutes = (datetime.now() - job.updated_at).total_seconds() / 60

                    # 标记为失败
                    job.status = JobStatus.FAILED
                    job.error_msg = (
                        f"任务执行超时（运行时长: {runtime_minutes:.1f} 分钟，"
                        f"阈值: {settings.TASK_TIMEOUT_MINUTES} 分钟）"
                    )
                    job.retry_count += 1  # 递增重试次数
                    job.updated_at = datetime.now()

                    self.logger.warning(
                        f"任务 #{job.id} 已标记为超时失败 "
                        f"(运行时长: {runtime_minutes:.1f}分钟, "
                        f"重试次数: {job.retry_count}/{settings.MAX_RETRY_COUNT})"
                    )

                # 批量提交所有更改
                await session.commit()
                self.logger.info(f"成功处理 {len(timeout_jobs)} 个超时任务")

                # 广播消息
                if self.ws_manager:
                    for job in timeout_jobs:
                        await self.ws_manager.broadcast({
                            "type": "log",
                            "level": "warning",
                            "msg": f"任务 #{job.id} 执行超时，已自动标记为失败并等待重试"
                        })

        except Exception as e:
            self.logger.error(f"检测超时任务时出错: {e}", exc_info=True)

    async def recreate_scheduled_jobs(self):
        """
        扫描并重新创建已完成的任务（全局机制）

        逻辑：
        1. 检查是否启用自动重新执行（AUTO_RECREATE_SUCCESS_JOBS）
        2. 查询所有 status='success' 且完成时间超过指定间隔的任务
        3. 为这些任务创建新的任务（复用相同的 config_id 和 query_params）
        4. 新任务自动进入队列等待执行
        """
        # 检查是否启用自动重新执行
        if not settings.AUTO_RECREATE_SUCCESS_JOBS:
            self.logger.debug("自动重新执行功能未启用（AUTO_RECREATE_SUCCESS_JOBS=False）")
            return

        self.logger.info(
            f"开始扫描已完成任务（间隔: {settings.AUTO_RECREATE_INTERVAL_MINUTES} 分钟）..."
        )

        try:
            async with get_session() as session:
                # 计算时间阈值：当前时间 - 间隔时间
                threshold_time = datetime.now() - timedelta(
                    minutes=settings.AUTO_RECREATE_INTERVAL_MINUTES
                )

                # 查询所有满足条件的 success 任务
                # 条件：status='success' 且 updated_at < threshold_time
                stmt = select(JobQueue).where(
                    JobQueue.status == JobStatus.SUCCESS,
                    JobQueue.updated_at < threshold_time
                ).order_by(JobQueue.updated_at.asc())

                result = await session.execute(stmt)
                success_jobs = result.scalars().all()

                if not success_jobs:
                    self.logger.debug("没有需要重新执行的任务")
                    return

                self.logger.info(
                    f"发现 {len(success_jobs)} 个任务需要重新执行 "
                    f"(完成时间超过 {settings.AUTO_RECREATE_INTERVAL_MINUTES} 分钟)"
                )

                recreated_count = 0
                for job in success_jobs:
                    try:
                        # 创建新任务（复用相同的配置和参数）
                        new_job = JobQueue(
                            config_id=job.config_id,
                            query_params=job.query_params,
                            priority=job.priority,
                            status=JobStatus.PENDING
                        )
                        session.add(new_job)

                        # 更新原任务的 updated_at，避免重复创建
                        job.updated_at = datetime.now()

                        self.logger.info(
                            f"为任务 #{job.id} (config_id={job.config_id}) 创建新任务 "
                            f"(原任务完成于 {job.updated_at})"
                        )
                        recreated_count += 1

                    except Exception as e:
                        self.logger.error(f"创建新任务失败（原任务 #{job.id}）: {e}")
                        continue

                await session.commit()

                if recreated_count > 0:
                    self.logger.info(f"成功创建 {recreated_count} 个新任务")

                    # 广播消息
                    if self.ws_manager:
                        await self.ws_manager.broadcast({
                            "type": "log",
                            "level": "info",
                            "msg": f"自动重新执行：创建了 {recreated_count} 个新任务"
                        })

        except Exception as e:
            self.logger.error(f"重新创建任务时出错: {e}", exc_info=True)

    async def shutdown(self):
        """
        优雅停止调度器

        停止流程：
        1. 暂停调度器（不再接受新任务）
        2. 等待运行中的任务完成（最多 30 秒）
        3. 关闭调度器
        """
        self.logger.info("正在停止任务调度器...")

        try:
            # 1. 暂停调度器（不再接受新任务）
            self.scheduler.pause()
            self.logger.info("调度器已暂停，等待运行中任务完成...")

            # 2. 等待运行中的任务完成（最多等待 30 秒）
            max_wait = 30
            for i in range(max_wait):
                running_jobs = self.scheduler.get_jobs()
                if not running_jobs:
                    self.logger.info("所有调度任务已完成")
                    break
                if i % 5 == 0:  # 每 5 秒日志一次
                    self.logger.info(f"等待 {len(running_jobs)} 个调度任务完成...")
                await asyncio.sleep(1)
            else:
                # 超时后强制继续
                running_jobs = self.scheduler.get_jobs()
                if running_jobs:
                    self.logger.warning(
                        f"等待超时（{max_wait}s），仍有 {len(running_jobs)} 个任务运行中，强制关闭"
                    )

            # 3. 关闭调度器（使用 wait=False 避免阻塞）
            self.scheduler.shutdown(wait=False)
            self.logger.info("任务调度器已停止")

        except Exception as e:
            self.logger.error(f"停止调度器时出错: {e}", exc_info=True)
            # 强制关闭
            try:
                self.scheduler.shutdown(wait=False)
                self.logger.info("任务调度器已强制关闭")
            except Exception as e2:
                self.logger.error(f"强制关闭调度器失败: {e2}")
