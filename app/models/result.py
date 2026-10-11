# app/models/result.py
from datetime import datetime
from sqlalchemy import Integer, JSON, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base
from app.core.database import ChineseJSON


class CrawlerResult(Base):
    """采集结果表 - 存储提取的业务数据"""

    __tablename__ = "crawler_results"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 关联字段（不使用外键约束）
    job_id: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        comment="关联job_queue.id"
    )
    config_id: Mapped[int] = mapped_column(Integer, nullable=False, comment="冗余字段便于查询")

    # 数据字段
    query_params: Mapped[dict] = mapped_column(ChineseJSON, nullable=False, comment="查询参数快照")
    extracted_data: Mapped[dict] = mapped_column(ChineseJSON, nullable=False, comment="提取的业务数据")
    page_count: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="实际抓取页数")

    # 时间戳
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
        comment="创建时间"
    )

    # 关系定义（仅用于 ORM，指定外键字段）
    job: Mapped["JobQueue"] = relationship(
        "JobQueue",
        back_populates="results",
        foreign_keys=[job_id],
        primaryjoin="CrawlerResult.job_id == JobQueue.id"
    )

    # 索引
    __table_args__ = (
        Index("idx_job", "job_id"),
        Index("idx_config", "config_id"),
    )

    def __repr__(self) -> str:
        return f"<CrawlerResult(id={self.id}, job_id={self.job_id})>"
