import logging
from datetime import datetime, timedelta
from typing import Optional
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.job import JobQueue, JobStatus

logger = logging.getLogger(__name__)


class TaskScheduler:
    """任务调度器 - 负责定时补跑失败任务"""

    def __init__(self, ws_manager=None):
        """
        初始化调度器

        Args:
            ws_manager: WebSocket 管理器（可选，用于状态推送）
        """
        self.scheduler = AsyncIOScheduler(
            timezone='Asia/Shanghai',
            job_defaults={
                'coalesce': True,  # 合并错过的执行
                'max_instances': 1  # 同时只运行一个补跑任务
            }
        )
        self.ws_manager = ws_manager
        self.logger = logger

    async def start(self):
        """启动调度器"""
        self.logger.info("正在启动任务调度器...")

        # 添加定时任务：每 30 分钟扫描并重试失败任务
        self.scheduler.add_job(
            func=self.retry_failed_jobs,
            trigger=IntervalTrigger(minutes=30),
            id='retry_failed_jobs',
            name='重试失败任务',
            next_run_time=datetime.now() + timedelta(minutes=1)  # 首次执行延迟 1 分钟
        )

        self.scheduler.start()
        self.logger.info("任务调度器启动成功")

    async def retry_failed_jobs(self):
        """
        扫描并重试失败的任务

        逻辑：
        1. 查询 status='failed' 且 retry_count < 3 的任务
        2. 将状态重置为 'pending'，清空 error_msg
        3. 保留 retry_count（由执行器在失败时递增）
        """
        self.logger.info("开始扫描失败任务...")

        try:
            async for session in get_session():
                # 查询失败任务
                stmt = select(JobQueue).where(
                    JobQueue.status == JobStatus.FAILED,
                    JobQueue.retry_count < 3
                ).order_by(JobQueue.updated_at.asc()).limit(100)

                result = await session.execute(stmt)
                failed_jobs = result.scalars().all()

                if not failed_jobs:
                    self.logger.info("没有需要重试的失败任务")
                    return

                self.logger.info(f"发现 {len(failed_jobs)} 个失败任务，开始重置状态")

                # 逐个重置任务状态（不提交）
                reset_count = 0
                for job in failed_jobs:
                    job.status = JobStatus.PENDING
                    job.error_msg = None
                    reset_count += 1

                    self.logger.info(
                        f"任务 #{job.id} 已重置为 pending "
                        f"(重试次数: {job.retry_count}/3)"
                    )

                # 批量提交所有更改
                try:
                    await session.commit()
                    self.logger.info(f"成功重置 {reset_count} 个失败任务")

                    # 广播所有重置消息
                    if self.ws_manager:
                        for job in failed_jobs:
                            await self.ws_manager.broadcast({
                                "type": "log",
                                "level": "info",
                                "message": f"任务 #{job.id} 已重置为 pending 状态进行重试",
                                "timestamp": datetime.now().isoformat()
                            })
                except Exception as e:
                    self.logger.error(f"批量重置任务失败: {e}")
                    await session.rollback()

        except Exception as e:
            self.logger.error(f"扫描失败任务时出错: {e}", exc_info=True)

    async def shutdown(self):
        """优雅停止调度器"""
        self.logger.info("正在停止任务调度器...")
        self.scheduler.shutdown(wait=True)
        self.logger.info("任务调度器已停止")
