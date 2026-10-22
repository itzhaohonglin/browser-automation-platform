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
    from app.core.database import get_session, async_engine

    # Windows 平台设置事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    async def run_job():
        """异步执行任务（带会话管理保护）"""
        session = None
        try:
            async with get_session() as session:
                executor = PlaywrightExecutor()
                result = await executor.execute_job(job_id, session)
                return result
        except asyncio.CancelledError:
            # 任务被取消时，确保会话正确关闭
            logger.warning(f"任务 {job_id} 被取消，正在清理会话")
            if session:
                try:
                    await session.rollback()
                    await session.close()
                except Exception as e:
                    logger.error(f"取消任务时关闭会话失败: {e}")
            raise
        except Exception as e:
            logger.error(f"任务 {job_id} 执行失败: {e}")
            raise

    async def cleanup_resources():
        """清理所有异步资源"""
        try:
            # 关键修复：在关闭事件循环前，显式关闭数据库引擎
            # 这会确保所有连接池中的连接都被正确关闭，避免 "Event loop is closed" 错误
            logger.debug(f"任务 {job_id}: 正在关闭数据库引擎...")
            await async_engine.dispose()
            logger.debug(f"任务 {job_id}: 数据库引擎已关闭")
        except Exception as e:
            logger.warning(f"任务 {job_id}: 关闭数据库引擎时出错: {e}")

    # 创建新的事件循环并在执行完成后正确清理
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(run_job())
        return result
    except Exception as e:
        logger.error(f"任务 {job_id} 在进程中执行失败: {e}")
        return {"status": "failed", "error": str(e)}
    finally:
        # 清理顺序很重要：
        # 1. 先关闭数据库引擎（释放连接池资源）
        # 2. 再取消待处理任务
        # 3. 最后关闭事件循环
        try:
            # 步骤 1: 关闭数据库引擎
            loop.run_until_complete(cleanup_resources())

            # 步骤 2: 取消所有待处理的任务
            pending = asyncio.all_tasks(loop)
            if pending:
                logger.debug(f"任务 {job_id}: 正在取消 {len(pending)} 个待处理任务")
                for task in pending:
                    task.cancel()
                # 等待所有任务完成取消
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
                logger.debug(f"任务 {job_id}: 已取消所有待处理任务")
        except Exception as e:
            logger.warning(f"任务 {job_id}: 清理事件循环时出错: {e}")
        finally:
            # 步骤 3: 关闭事件循环
            try:
                # 给一点时间让所有回调完成
                loop.run_until_complete(asyncio.sleep(0.1))
            except Exception:
                pass
            finally:
                logger.debug(f"任务 {job_id}: 正在关闭事件循环")
                loop.close()
                logger.debug(f"任务 {job_id}: 事件循环已关闭")


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
            # 关键修复：保存事件循环引用，避免回调中获取到错误的loop
            current_loop = loop

            def on_complete(f):
                try:
                    # 使用保存的事件循环引用，而不是重新获取
                    asyncio.run_coroutine_threadsafe(
                        self._decrement_active_workers(job_id, f),
                        current_loop
                    )
                except Exception as e:
                    # 如果回调失败，记录错误并手动递减计数器
                    logger.error(f"任务 {job_id} 回调执行失败: {e}", exc_info=True)
                    # 使用线程安全的方式递减计数器
                    asyncio.run_coroutine_threadsafe(
                        self._force_decrement_worker(job_id),
                        current_loop
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

    async def _force_decrement_worker(self, job_id: int):
        """
        强制递减活跃工作进程计数（回调失败时的保险措施）

        Args:
            job_id: 任务 ID
        """
        async with self._lock:
            if self._active_workers > 0:
                self._active_workers -= 1
                logger.warning(
                    f"任务 {job_id} 回调失败，强制递减计数器（活跃工作进程: {self._active_workers}/{self.max_workers}）"
                )
            else:
                logger.error(f"任务 {job_id} 回调失败，但计数器已经为0，无法递减")

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

    async def sync_worker_count_from_db(self):
        """
        从数据库同步活跃工作进程计数（防止计数器漂移）

        通过查询数据库中 PROCESSING 状态的任务数来校正内存中的计数器。
        这是一个保险机制，用于修复回调失败导致的计数器不同步问题。
        """
        from app.core.database import get_session
        from app.models.job import JobQueue, JobStatus
        from sqlalchemy import select, func

        try:
            async with get_session() as session:
                # 查询数据库中 PROCESSING 状态的任务数
                stmt = select(func.count()).where(JobQueue.status == JobStatus.PROCESSING)
                result = await session.execute(stmt)
                db_processing_count = result.scalar() or 0

                async with self._lock:
                    old_count = self._active_workers
                    # 数据库中的 PROCESSING 任务数才是真实的活跃工作进程数
                    self._active_workers = min(db_processing_count, self.max_workers)

                    if old_count != self._active_workers:
                        logger.warning(
                            f"进程池计数器已同步：{old_count} → {self._active_workers} "
                            f"（数据库 PROCESSING 任务数: {db_processing_count}）"
                        )
                    else:
                        logger.debug(f"进程池计数器同步检查通过: {self._active_workers}/{self.max_workers}")

        except Exception as e:
            logger.error(f"同步进程池计数器失败: {e}", exc_info=True)

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
