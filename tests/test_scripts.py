"""独立脚本（scripts/ 目录）行为测试"""
import asyncio
import runpy
import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def test_batch_import_script_accepts_file_arg_noninteractive(monkeypatch):
    """传入文件路径参数时应直接执行 import_from_file，而不是交互式 main()"""
    script = PROJECT_ROOT / "scripts" / "batch_import_registration_jobs.py"

    captured = {}

    def fake_run(coro):
        captured["coro"] = coro
        return [1, 2, 3]

    monkeypatch.setattr(asyncio, "run", fake_run)
    old_argv = sys.argv[:]
    try:
        sys.argv = [str(script), "import_data/jobs.csv"]
        runpy.run_path(str(script), run_name="__main__")
    finally:
        sys.argv = old_argv

    assert "coro" in captured, "脚本应通过 asyncio.run 启动导入逻辑"
    assert captured["coro"].__qualname__ == "import_from_file"


def test_batch_import_script_exits_nonzero_when_no_jobs_imported(monkeypatch):
    """非交互模式导入结果为空时应以非零状态退出（供 bat 判断失败）"""
    script = PROJECT_ROOT / "scripts" / "batch_import_registration_jobs.py"

    monkeypatch.setattr(asyncio, "run", lambda coro: [])
    old_argv = sys.argv[:]
    try:
        sys.argv = [str(script), "import_data/empty.csv"]
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_path(str(script), run_name="__main__")
    finally:
        sys.argv = old_argv

    assert exc_info.value.code == 1


def test_init_config_script_runs_async_init(monkeypatch):
    """初始化脚本应通过 asyncio.run 执行 init_nhsa_registration_config"""
    script = PROJECT_ROOT / "scripts" / "init_nhsa_registration_config.py"

    captured = {}

    def fake_run(coro):
        captured["coro"] = coro
        return (None, None)

    monkeypatch.setattr(asyncio, "run", fake_run)

    runpy.run_path(str(script), run_name="__main__")

    assert "coro" in captured, "脚本应通过 asyncio.run 启动初始化逻辑"
    assert captured["coro"].__qualname__ == "init_nhsa_registration_config"
