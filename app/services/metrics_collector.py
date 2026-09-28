import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_session
from app.models.metrics import MetricsTimeSeries

logger = logging.getLogger(__name__)

class MetricsCollector:
    """指标收集器 - 单例模式"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.buffer: List[MetricsTimeSeries] = []
        self.buffer_lock = asyncio.Lock()
        self.flush_interval = 10  # 每 10 秒刷新一次
        self.buffer_size = 100  # 批量写入阈值
        self.hit_count = 0
        self.miss_count = 0

    async def record(
        self,
        metric_name: str,
        value: float,
        labels: Optional[Dict] = None,
        timestamp: Optional[datetime] = None
    ):
        """记录指标（异步缓冲）"""
        metric = MetricsTimeSeries(
            metric_name=metric_name,
            metric_value=value,
            labels=labels or {},
            timestamp=timestamp or datetime.utcnow()
        )

        async with self.buffer_lock:
            self.buffer.append(metric)

            # 缓冲区满则触发刷新
            if len(self.buffer) >= self.buffer_size:
                await self._flush()

    async def _flush(self):
        """刷新缓冲区到数据库"""
        if not self.buffer:
            return

        async with self.buffer_lock:
            metrics_to_save = self.buffer[:]
            self.buffer.clear()

        try:
            async with get_session() as session:
                session.add_all(metrics_to_save)
                await session.commit()
            logger.debug(f"已刷新 {len(metrics_to_save)} 条指标到数据库")
        except Exception as e:
            logger.error(f"指标刷新失败: {e}")

    async def start_background_flush(self):
        """启动后台定时刷新"""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self._flush()

    async def query(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        labels: Optional[Dict] = None,
        aggregation: Optional[str] = None  # "avg", "sum", "max", "min"
    ) -> List[Dict]:
        """查询指标数据"""
        async with get_session() as session:
            stmt = select(MetricsTimeSeries).where(
                MetricsTimeSeries.metric_name == metric_name,
                MetricsTimeSeries.timestamp >= start_time,
                MetricsTimeSeries.timestamp <= end_time
            )

            # 标签过滤
            if labels:
                for key, value in labels.items():
                    stmt = stmt.where(
                        MetricsTimeSeries.labels[key].astext == str(value)
                    )

            result = await session.execute(stmt)
            metrics = result.scalars().all()

            # 聚合处理
            if aggregation and metrics:
                if aggregation == "avg":
                    return [{"value": sum(m.metric_value for m in metrics) / len(metrics)}]
                elif aggregation == "sum":
                    return [{"value": sum(m.metric_value for m in metrics)}]
                elif aggregation == "max":
                    return [{"value": max(m.metric_value for m in metrics)}]
                elif aggregation == "min":
                    return [{"value": min(m.metric_value for m in metrics)}]

            return [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "value": m.metric_value,
                    "labels": m.labels
                }
                for m in metrics
            ]

# 全局单例
metrics_collector = MetricsCollector()
