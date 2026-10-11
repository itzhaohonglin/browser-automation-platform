"""
进程池管理器

管理多个工作进程并发执行采集任务，提高系统吞吐量。
"""

import asyncio
import logging
from concurrent.futures import ProcessPoolExecutor
from typing import Optional

logger = logging.getLogger(__name__)


def _execute_job_in_process(job_id: int) -> dict:
    """
    在独立进程中执行任务

    Args:
        job_id: 任务 ID

    Returns:
        执行结果字典
    """
    # Import here to avoid circular dependencies
    import asyncio
    import sys
    from app.services.executor import PlaywrightExecutor
    from app.core.database import get_session

    # Windows 平台设置事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    async def run_job():
        """异步执行任务"""
        async with get_session() as session:
            executor = PlaywrightExecutor()
            result = await executor.execute_job(job_id, session)
            return result

    # 创建新的事件循环并在执行完成后正确清理
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_job())
        return result
    finally:
        # 清理所有待处理的任务
        try:
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        finally:
            loop.close()


class ProcessPoolManager:
    """进程池管理器"""

    def __init__(self, max_workers: int = 3, memory_limit_mb: int = 512):
        """
        初始化进程池管理器

        Args:
            max_workers: 最大工作进程数
            memory_limit_mb: 内存限制（MB，预留用于未来增强）
        """
        self.max_workers = max_workers
        self.memory_limit_mb = memory_limit_mb
        self.executor: Optional[ProcessPoolExecutor] = None
        self._active_workers = 0
        self._lock = asyncio.Lock()

        logger.info(f"初始化进程池管理器: max_workers={max_workers}, memory_limit={memory_limit_mb}MB")

    async def start(self) -> None:
        """启动进程池"""
        if self.executor is not None:
            logger.warning("进程池已启动，跳过重复启动")
            return

        self.executor = ProcessPoolExecutor(max_workers=self.max_workers)
        logger.info(f"进程池已启动，工作进程数: {self.max_workers}")

    async def submit_job(self, job_id: int) -> asyncio.Future:
        """
        提交任务到进程池

        Args:
            job_id: 任务 ID

        Returns:
            异步 Future 对象
        """
        if self.executor is None:
            raise RuntimeError("进程池未启动，请先调用 start() 方法")

        async with self._lock:
            self._active_workers += 1

        logger.info(f"提交任务 {job_id} 到进程池（当前活跃: {self._active_workers}/{self.max_workers}）")

        try:
            # 使用 run_in_executor 桥接同步的 ProcessPoolExecutor 和异步代码
            loop = asyncio.get_event_loop()
            future = loop.run_in_executor(
                self.executor,
                _execute_job_in_process,
                job_id
            )

            # 添加回调来更新活跃工作进程计数
            def on_complete(f):
                loop = asyncio.get_event_loop()
                asyncio.run_coroutine_threadsafe(
                    self._decrement_active_workers(job_id, f),
                    loop
                )

            future.add_done_callback(on_complete)

            return future

        except Exception as e:
            logger.error(f"提交任务 {job_id} 失败: {e}", exc_info=True)
            async with self._lock:
                self._active_workers -= 1
            raise

    async def _decrement_active_workers(self, job_id: int, future: asyncio.Future):
        """
        递减活跃工作进程计数（任务完成后的回调）

        Args:
            job_id: 任务 ID
            future: 完成的 Future 对象
        """
        async with self._lock:
            self._active_workers -= 1

        try:
            result = future.result()
            status = result.get('status', 'unknown')
            logger.info(
                f"任务 {job_id} 执行完成，状态: {status}（活跃工作进程: {self._active_workers}/{self.max_workers}）"
            )
        except Exception as e:
            logger.error(f"任务 {job_id} 执行失败: {e}", exc_info=True)

    async def shutdown(self, wait: bool = True) -> None:
        """
        关闭进程池

        Args:
            wait: 是否等待所有任务完成
        """
        if self.executor is None:
            logger.info("进程池未启动或已关闭")
            return

        logger.info(f"正在关闭进程池（wait={wait}）...")

        try:
            self.executor.shutdown(wait=wait)
            self.executor = None
            self._active_workers = 0
            logger.info("进程池已关闭")
        except Exception as e:
            logger.error(f"关闭进程池时出错: {e}", exc_info=True)

    def get_active_workers(self) -> int:
        """
        获取当前活跃的工作进程数

        Returns:
            活跃工作进程数
        """
        return self._active_workers

    def get_pool_status(self) -> dict:
        """
        获取进程池状态

        Returns:
            状态字典，包含 max_workers、active、pending
        """
        return {
            "max_workers": self.max_workers,
            "active": self._active_workers,
            "pending": max(0, self._active_workers),  # 简化版：pending = active
            "is_running": self.executor is not None
        }
