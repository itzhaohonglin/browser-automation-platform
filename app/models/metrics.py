# app/models/metrics.py
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import String, Integer, Float, Boolean, JSON, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
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


class AlertRule(Base):
    """告警规则表"""

    __tablename__ = "alert_rules"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 规则配置
    rule_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="规则名称")
    metric_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="监控指标")
    condition: Mapped[str] = mapped_column(String(10), nullable=False, comment="条件：gt/lt/eq/gte/lte")
    threshold: Mapped[float] = mapped_column(Float, nullable=False, comment="阈值")
    duration_seconds: Mapped[int] = mapped_column(Integer, default=60, nullable=False, comment="持续时长")
    channels: Mapped[dict] = mapped_column(JSON, nullable=False, comment="通知渠道")

    # 状态字段
    enabled: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")

    # 告警静默相关字段
    silence_duration: Mapped[int] = mapped_column(Integer, default=3600, nullable=False, comment="静默时长（秒），默认1小时")
    last_alert_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True, comment="上次告警时间")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
        comment="更新时间"
    )

    # 关系定义
    history: Mapped[list["AlertHistory"]] = relationship(
        "AlertHistory",
        back_populates="rule",
        cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<AlertRule(id={self.id}, name={self.rule_name}, enabled={self.enabled})>"


class AlertHistory(Base):
    """告警历史表"""

    __tablename__ = "alert_history"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 外键
    rule_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey('alert_rules.id'),
        nullable=False,
        comment="关联alert_rules.id"
    )

    # 告警信息
    triggered_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="触发时间")
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True, comment="恢复时间")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="告警是否仍然活跃")
    alert_message: Mapped[str] = mapped_column(Text, nullable=False, comment="告警消息")
    metric_value: Mapped[float] = mapped_column(Float, nullable=False, comment="触发时指标值")

    # 通知状态
    notify_status: Mapped[str] = mapped_column(String(20), default="pending", nullable=False, comment="通知状态")
    notify_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="通知错误信息")

    # 关系定义
    rule: Mapped["AlertRule"] = relationship("AlertRule", back_populates="history")

    def __repr__(self) -> str:
        return f"<AlertHistory(id={self.id}, rule_id={self.rule_id}, status={self.notify_status})>"
