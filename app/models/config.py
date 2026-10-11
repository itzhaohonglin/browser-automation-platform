# app/models/config.py
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import String, Integer, Boolean, JSON, DateTime, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base
from app.core.database import ChineseJSON


class CrawlerConfig(Base):
    """采集配置表 - 存储爬虫规则和目标页面配置"""

    __tablename__ = "crawler_configs"

    # 主键
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)

    # 基本配置
    config_name: Mapped[str] = mapped_column(String(100), nullable=False, comment="任务名称")
    target_url: Mapped[str] = mapped_column(String(500), nullable=False, comment="目标页面URL")

    # 登录配置
    need_login: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False, comment="是否需要登录")
    auth_profile: Mapped[Optional[str]] = mapped_column(String(50), nullable=True, comment="登录态标识")
    login_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True, comment="登录页地址")

    # 页面交互配置
    input_configs: Mapped[Any] = mapped_column(ChineseJSON, nullable=False, comment="多输入框配置")
    submit_selector: Mapped[str] = mapped_column(String(200), nullable=False, comment="查询按钮选择器")
    wait_selector: Mapped[str] = mapped_column(String(200), nullable=False, comment="等待加载完成的选择器")
    fields_mapping: Mapped[dict] = mapped_column(ChineseJSON, nullable=False, comment="数据提取规则")

    # 分页配置
    pagination_selector: Mapped[Optional[str]] = mapped_column(String(200), nullable=True, comment="下一页按钮选择器")
    max_pages: Mapped[int] = mapped_column(Integer, default=1, nullable=False, comment="最大翻页数")

    # 超时配置（新增）
    timeout_config: Mapped[Optional[dict]] = mapped_column(
        ChineseJSON,
        nullable=True,
        comment="超时配置 {page_load: 30000, wait_selector: 15000, ...}"
    )

    # 提取规则配置（新增）
    extraction_config: Mapped[Optional[dict]] = mapped_column(
        ChineseJSON,
        nullable=True,
        comment="提取规则 {filters: [...], wait_times: {...}, retry: {...}}"
    )

    # 优先级（新增）
    priority: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
        comment="任务优先级 1-10，数字越大优先级越高"
    )

    # 状态字段
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False, comment="是否启用")
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=func.now(),
        nullable=False,
        comment="创建时间"
    )
    deleted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        default=None,
        comment="删除时间（逻辑删除）"
    )

    # 关系定义（一对多：一个配置对应多个任务，仅用于 ORM）
    jobs: Mapped[list["JobQueue"]] = relationship(
        "JobQueue",
        back_populates="config",
        cascade="all, delete-orphan",
        foreign_keys="JobQueue.config_id",
        primaryjoin="CrawlerConfig.id == JobQueue.config_id"
    )

    # 索引
    __table_args__ = (
        Index("idx_auth_profile", "auth_profile"),
        Index("idx_deleted_at", "deleted_at"),
    )

    def __repr__(self) -> str:
        return f"<CrawlerConfig(id={self.id}, name={self.config_name})>"
