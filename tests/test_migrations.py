"""数据库迁移运行器测试"""
import sys
from pathlib import Path

import pytest

from app.core.migrations import build_alembic_config, get_bundle_base_path, run_migrations


@pytest.fixture
def bundle_dir(tmp_path):
    """模拟应用资源目录（包含 alembic.ini 和 alembic/）"""
    versions_dir = tmp_path / "alembic" / "versions"
    versions_dir.mkdir(parents=True)
    (tmp_path / "alembic.ini").write_text(
        "[alembic]\nscript_location = alembic\n"
        "sqlalchemy.url = driver://user:pass@localhost/dbname\n",
        encoding="utf-8",
    )
    return tmp_path


def test_build_alembic_config_uses_absolute_script_location(bundle_dir):
    """打包后 alembic 资源位于 _MEIPASS，script_location 必须被覆盖为绝对路径"""
    cfg = build_alembic_config(bundle_dir)

    assert Path(cfg.config_file_name) == bundle_dir / "alembic.ini"
    assert cfg.get_main_option("script_location") == str(bundle_dir / "alembic")


def test_get_bundle_base_path_frozen_uses_meipass(monkeypatch, bundle_dir):
    """打包环境（sys.frozen=True）应返回 sys._MEIPASS 目录"""
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(bundle_dir), raising=False)

    assert get_bundle_base_path() == bundle_dir


def test_get_bundle_base_path_dev_returns_project_root():
    """开发环境应返回项目根目录（包含 alembic.ini 和 app/）"""
    base = get_bundle_base_path()

    assert (base / "alembic.ini").exists()
    assert (base / "app").is_dir()


def test_run_migrations_runs_upgrade_to_head(monkeypatch, bundle_dir):
    """run_migrations 应使用传入目录构建配置并执行 upgrade head"""
    calls = []

    def fake_upgrade(cfg, target):
        calls.append((cfg, target))

    monkeypatch.setattr("alembic.command.upgrade", fake_upgrade)

    run_migrations(bundle_dir)

    assert len(calls) == 1
    assert calls[0][1] == "head"
    assert Path(calls[0][0].config_file_name) == bundle_dir / "alembic.ini"


def test_run_migrations_restores_logging_config(monkeypatch, bundle_dir):
    """迁移后应恢复应用日志配置：alembic 的 fileConfig 会把 root 级别降为 WARN、
    替换 handlers 并禁用相关 logger，导致迁移后应用 INFO 日志全部丢失"""
    import logging

    root = logging.getLogger()
    engine_logger = logging.getLogger("sqlalchemy.engine")
    alembic_logger = logging.getLogger("alembic")
    loggers = (root, engine_logger, alembic_logger)
    saved = {
        lg: (lg.level, lg.handlers[:], lg.disabled, lg.propagate)
        for lg in loggers
    }

    def fake_upgrade(cfg, target):
        # 模拟 alembic fileConfig 的副作用
        root.setLevel(logging.WARNING)
        root.handlers = []
        engine_logger.setLevel(logging.WARNING)
        engine_logger.disabled = True
        alembic_logger.disabled = True

    monkeypatch.setattr("alembic.command.upgrade", fake_upgrade)

    run_migrations(bundle_dir)

    for lg, state in saved.items():
        assert (lg.level, lg.handlers[:], lg.disabled, lg.propagate) == state
