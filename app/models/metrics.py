# app/models/metrics.py
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, Float, JSON, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.models.base import Base


class MetricsTimeSeries(Base):
    """指标时序数据表"""

    __tablename__ = "metrics_timeseries"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 指标字段
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, index=True, comment="指标名称")
    metric_value: Mapped[float] = mapped_column(Float, nullable=False, comment="指标值")
    labels: Mapped[Optional[dict]] = mapped_column(JSON, nullable=True, comment="标签信息")

    # 时间戳
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        index=True,
        default=func.now(),
        comment="记录时间"
    )

    # 复合索引
    __table_args__ = (
        Index('idx_metric_time', 'metric_name', 'timestamp'),
    )

    def __repr__(self) -> str:
        return f"<MetricsTimeSeries(id={self.id}, metric={self.metric_name}, value={self.metric_value})>"

