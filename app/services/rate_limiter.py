"""
限流管理器

实现基于时间窗口的任务执行限流，防止对目标网站造成过大压力。
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional
from collections import deque

from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimiter:
    """限流管理器 - 控制任务执行速率"""

    def __init__(
        self,
        enabled: bool = None,
        window_minutes: int = None,
        max_tasks: int = None,
        per_config: bool = None
    ):
        """
        初始化限流管理器

        Args:
            enabled: 是否启用限流（None 则使用配置）
            window_minutes: 时间窗口（分钟）
            max_tasks: 窗口内最多执行的任务数
            per_config: 是否按配置ID分别限流
        """
        self.enabled = enabled if enabled is not None else settings.RATE_LIMIT_ENABLED
        self.window_minutes = window_minutes if window_minutes is not None else settings.RATE_LIMIT_WINDOW_MINUTES
        self.max_tasks = max_tasks if max_tasks is not None else settings.RATE_LIMIT_MAX_TASKS
        self.per_config = per_config if per_config is not None else settings.RATE_LIMIT_PER_CONFIG

        # 全局限流：记录所有任务的执行时间
        self._global_timestamps: deque = deque()

        # 按配置限流：记录每个配置ID的执行时间
        self._config_timestamps: Dict[int, deque] = {}

        # 锁，确保并发安全
        self._lock = asyncio.Lock()

        logger.info(
            f"限流管理器初始化: enabled={self.enabled}, "
            f"window={self.window_minutes}分钟, "
            f"max_tasks={self.max_tasks}, "
            f"per_config={self.per_config}"
        )

    async def can_execute(self, config_id: Optional[int] = None) -> bool:
        """
        检查是否可以执行任务

        Args:
            config_id: 配置ID（per_config=True 时需要）

        Returns:
            True 表示可以执行，False 表示达到限流上限
        """
        if not self.enabled:
            return True

        async with self._lock:
            now = datetime.now()
            window_start = now - timedelta(minutes=self.window_minutes)

            if self.per_config:
                # 按配置ID限流
                if config_id is None:
                    logger.warning("启用按配置限流但未提供 config_id，使用全局限流")
                    return await self._check_global_limit(now, window_start)

                # 获取或创建该配置的时间戳队列
                if config_id not in self._config_timestamps:
                    self._config_timestamps[config_id] = deque()

                timestamps = self._config_timestamps[config_id]

                # 清理过期的时间戳
                while timestamps and timestamps[0] < window_start:
                    timestamps.popleft()

                # 检查是否超过限制
                if len(timestamps) >= self.max_tasks:
                    logger.warning(
                        f"配置 {config_id} 达到限流上限: "
                        f"{len(timestamps)}/{self.max_tasks} 任务在 {self.window_minutes} 分钟内"
                    )
                    return False

                return True
            else:
                # 全局限流
                return await self._check_global_limit(now, window_start)

    async def _check_global_limit(self, now: datetime, window_start: datetime) -> bool:
        """
        检查全局限流

        Args:
            now: 当前时间
            window_start: 时间窗口起始时间

        Returns:
            True 表示可以执行，False 表示达到限流上限
        """
        # 清理过期的时间戳
        while self._global_timestamps and self._global_timestamps[0] < window_start:
            self._global_timestamps.popleft()

        # 检查是否超过限制
        if len(self._global_timestamps) >= self.max_tasks:
            logger.warning(
                f"达到全局限流上限: "
                f"{len(self._global_timestamps)}/{self.max_tasks} 任务在 {self.window_minutes} 分钟内"
            )
            return False

        return True

    async def record_execution(self, config_id: Optional[int] = None):
        """
        记录任务执行（在任务开始执行时调用）

        Args:
            config_id: 配置ID（per_config=True 时需要）
        """
        if not self.enabled:
            return

        async with self._lock:
            now = datetime.now()

            if self.per_config and config_id is not None:
                # 按配置ID记录
                if config_id not in self._config_timestamps:
                    self._config_timestamps[config_id] = deque()

                self._config_timestamps[config_id].append(now)
                logger.debug(
                    f"记录任务执行: config_id={config_id}, "
                    f"当前窗口内任务数={len(self._config_timestamps[config_id])}"
                )
            else:
                # 全局记录
                self._global_timestamps.append(now)
                logger.debug(
                    f"记录任务执行: 全局, "
                    f"当前窗口内任务数={len(self._global_timestamps)}"
                )

    async def get_wait_time(self, config_id: Optional[int] = None) -> int:
        """
        获取需要等待的时间（秒）

        Args:
            config_id: 配置ID（per_config=True 时需要）

        Returns:
            需要等待的秒数，0 表示可以立即执行
        """
        if not self.enabled:
            return 0

        async with self._lock:
            now = datetime.now()
            window_start = now - timedelta(minutes=self.window_minutes)

            if self.per_config and config_id is not None:
                if config_id not in self._config_timestamps:
                    return 0

                timestamps = self._config_timestamps[config_id]

                # 清理过期的时间戳
                while timestamps and timestamps[0] < window_start:
                    timestamps.popleft()

                # 如果未达到限制，可以立即执行
                if len(timestamps) < self.max_tasks:
                    return 0

                # 计算最早的时间戳距离窗口结束的时间
                oldest = timestamps[0]
                wait_until = oldest + timedelta(minutes=self.window_minutes)
                wait_seconds = (wait_until - now).total_seconds()

                return max(0, int(wait_seconds))
            else:
                # 全局限流
                # 清理过期的时间戳
                while self._global_timestamps and self._global_timestamps[0] < window_start:
                    self._global_timestamps.popleft()

                # 如果未达到限制，可以立即执行
                if len(self._global_timestamps) < self.max_tasks:
                    return 0

                # 计算最早的时间戳距离窗口结束的时间
                oldest = self._global_timestamps[0]
                wait_until = oldest + timedelta(minutes=self.window_minutes)
                wait_seconds = (wait_until - now).total_seconds()

                return max(0, int(wait_seconds))

    async def get_status(self, config_id: Optional[int] = None) -> Dict:
        """
        获取限流状态

        Args:
            config_id: 配置ID（可选，获取特定配置的状态）

        Returns:
            状态字典
        """
        async with self._lock:
            now = datetime.now()
            window_start = now - timedelta(minutes=self.window_minutes)

            if config_id is not None and config_id in self._config_timestamps:
                # 获取特定配置的状态
                timestamps = self._config_timestamps[config_id]

                # 清理过期的时间戳
                while timestamps and timestamps[0] < window_start:
                    timestamps.popleft()

                current_count = len(timestamps)
                remaining = max(0, self.max_tasks - current_count)

                return {
                    "enabled": self.enabled,
                    "config_id": config_id,
                    "window_minutes": self.window_minutes,
                    "max_tasks": self.max_tasks,
                    "current_count": current_count,
                    "remaining": remaining,
                    "utilization": f"{current_count}/{self.max_tasks} ({current_count/self.max_tasks*100:.1f}%)"
                }
            else:
                # 获取全局状态
                # 清理过期的时间戳
                while self._global_timestamps and self._global_timestamps[0] < window_start:
                    self._global_timestamps.popleft()

                current_count = len(self._global_timestamps)
                remaining = max(0, self.max_tasks - current_count)

                status = {
                    "enabled": self.enabled,
                    "window_minutes": self.window_minutes,
                    "max_tasks": self.max_tasks,
                    "current_count": current_count,
                    "remaining": remaining,
                    "utilization": f"{current_count}/{self.max_tasks} ({current_count/self.max_tasks*100:.1f}%)"
                }

                # 如果按配置限流，添加各配置的统计
                if self.per_config and self._config_timestamps:
                    config_stats = {}
                    for cid, timestamps in self._config_timestamps.items():
                        # 清理过期的时间戳
                        while timestamps and timestamps[0] < window_start:
                            timestamps.popleft()

                        if timestamps:  # 只显示有活动的配置
                            config_stats[cid] = {
                                "current_count": len(timestamps),
                                "remaining": max(0, self.max_tasks - len(timestamps))
                            }

                    status["per_config_stats"] = config_stats

                return status

    async def reset(self, config_id: Optional[int] = None):
        """
        重置限流计数器

        Args:
            config_id: 配置ID（可选，重置特定配置的计数器）
        """
        async with self._lock:
            if config_id is not None:
                if config_id in self._config_timestamps:
                    self._config_timestamps[config_id].clear()
                    logger.info(f"已重置配置 {config_id} 的限流计数器")
            else:
                self._global_timestamps.clear()
                self._config_timestamps.clear()
                logger.info("已重置所有限流计数器")


# 全局限流管理器实例
rate_limiter = RateLimiter()
