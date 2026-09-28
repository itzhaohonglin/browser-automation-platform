# app/models/system_config.py
from datetime import datetime
from typing import Optional
from sqlalchemy import String, Integer, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.models.base import Base


class SystemConfig(Base):
    """系统配置表 - 存储运行时参数"""

    __tablename__ = "system_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    config_key: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
        comment="配置键"
    )
    config_value: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
        comment="配置值"
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
        comment="配置说明"
    )
    updated_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime,
        nullable=True,
        default=func.now(),
        onupdate=func.now(),
        comment="更新时间"
    )

    def __repr__(self):
        return f"<SystemConfig(key={self.config_key}, value={self.config_value})>"
