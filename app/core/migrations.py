"""数据库迁移运行器

通过 alembic Python API 执行迁移，兼容 PyInstaller 打包环境
（打包后 alembic 资源位于 sys._MEIPASS，客户端无 Python 环境，
无法使用 alembic 命令行工具）。
"""
import logging
import sys
from pathlib import Path

from alembic import command
from alembic.config import Config

# env.py 的 fileConfig 会修改这些 logger（root 级别降为 WARN 等）
_AFFECTED_LOGGERS = ("", "sqlalchemy.engine", "alembic")


def get_bundle_base_path() -> Path:
    """应用资源根目录：开发环境为项目根目录，打包后为 sys._MEIPASS"""
    if getattr(sys, "frozen", False):
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent.parent


def build_alembic_config(base_path: Path) -> Config:
    """构建 alembic 配置，script_location 覆盖为 base_path 下的绝对路径"""
    config = Config(str(base_path / "alembic.ini"))
    config.set_main_option("script_location", str(base_path / "alembic"))
    return config


def run_migrations(base_path: Path | None = None) -> None:
    """执行数据库迁移到最新版本"""
    config = build_alembic_config(base_path or get_bundle_base_path())
    # alembic env.py 的 fileConfig 会重配日志（root 降为 WARN、替换 handlers），
    # 迁移后必须恢复，否则应用启动后的 INFO 日志会全部丢失
    saved = [
        (lg, lg.level, lg.handlers[:], lg.disabled, lg.propagate)
        for name in _AFFECTED_LOGGERS
        for lg in [logging.getLogger(name)]
    ]
    try:
        command.upgrade(config, "head")
    finally:
        for lg, level, handlers, disabled, propagate in saved:
            lg.setLevel(level)
            lg.handlers = handlers
            lg.disabled = disabled
            lg.propagate = propagate
