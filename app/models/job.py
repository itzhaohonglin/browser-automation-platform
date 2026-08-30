# app/models/job.py
from datetime import datetime
from enum import Enum as PyEnum
from typing import Optional
from sqlalchemy import Integer, JSON, Text, DateTime, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base


class JobStatus(str, PyEnum):
    """任务状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"


class JobQueue(Base):
    """任务队列表 - 存储待执行的采集任务"""

    __tablename__ = "job_queue"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 外键
    config_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("crawler_configs.id"),
        nullable=False,
        comment="关联crawler_configs.id"
    )

    # 任务参数
    query_params: Mapped[dict] = mapped_column(JSON, nullable=False, comment="查询参数")

    # 状态字段
    status: Mapped[str] = mapped_column(
        SQLEnum(JobStatus),
        default=JobStatus.PENDING,
        nullable=False,
        comment="任务状态"
    )
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="重试次数")
    error_msg: Mapped[Optional[str]] = mapped_column(Text, nullable=True, comment="错误信息")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="更新时间"
    )

    # 关系定义
    config: Mapped["CrawlerConfig"] = relationship("CrawlerConfig", back_populates="jobs")
    results: Mapped[list["CrawlerResult"]] = relationship(
        "CrawlerResult",
        back_populates="job",
        cascade="all, delete-orphan"
    )

    # 索引
    __table_args__ = (
        Index("idx_config_status", "config_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<JobQueue(id={self.id}, status={self.status})>"
