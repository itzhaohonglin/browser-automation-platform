"""命令行参数解析与脚本执行测试"""
import sys

import pytest

from app.core import cli
from app.core.cli import (
    ACTION_INIT_CONFIG,
    ACTION_INSTALL_BROWSER,
    ACTION_IMPORT_JOBS,
    ACTION_MIGRATE,
    parse_cli_args,
    run_bundled_script,
)


def test_parse_cli_args_no_flags_returns_none():
    assert parse_cli_args([]) == (None, [])
    assert parse_cli_args(["some", "args"]) == (None, [])


def test_parse_cli_args_detects_migrate():
    assert parse_cli_args(["--migrate"]) == (ACTION_MIGRATE, [])


def test_parse_cli_args_detects_install_browser():
    assert parse_cli_args(["--install-browser"]) == (ACTION_INSTALL_BROWSER, [])


def test_parse_cli_args_detects_init_config():
    assert parse_cli_args(["--init-config"]) == (ACTION_INIT_CONFIG, [])


def test_parse_cli_args_import_jobs_with_space():
    assert parse_cli_args(["--import-jobs", "import_data/jobs.csv"]) == (
        ACTION_IMPORT_JOBS,
        ["import_data/jobs.csv"],
    )


def test_parse_cli_args_import_jobs_with_equals():
    assert parse_cli_args(["--import-jobs=import_data/jobs.csv"]) == (
        ACTION_IMPORT_JOBS,
        ["import_data/jobs.csv"],
    )


def test_parse_cli_args_import_jobs_without_value():
    assert parse_cli_args(["--import-jobs"]) == (ACTION_IMPORT_JOBS, [])


def test_parse_cli_args_migrate_takes_priority():
    assert parse_cli_args(["--install-browser", "--migrate"]) == (ACTION_MIGRATE, [])


def test_run_bundled_script_executes_with_main_and_argv(tmp_path, monkeypatch):
    """打包脚本应以 __main__ 身份执行，且能通过 sys.argv 接收参数"""
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    out_file = tmp_path / "argv.txt"
    (scripts_dir / "fake_script.py").write_text(
        "import sys\n"
        f"with open({str(out_file)!r}, 'w', encoding='utf-8') as f:\n"
        "    f.write(repr(sys.argv))\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(cli, "get_bundle_base_path", lambda: tmp_path)

    run_bundled_script("fake_script.py", ["arg1", "arg2"])

    assert out_file.read_text(encoding="utf-8") == repr(
        [str(scripts_dir / "fake_script.py"), "arg1", "arg2"]
    )


def test_run_bundled_script_restores_argv(tmp_path, monkeypatch):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    (scripts_dir / "noop.py").write_text("", encoding="utf-8")

    monkeypatch.setattr(cli, "get_bundle_base_path", lambda: tmp_path)
    old_argv = sys.argv[:]
    try:
        run_bundled_script("noop.py")
        assert sys.argv == old_argv
    finally:
        sys.argv = old_argv


def test_run_bundled_script_missing_script_raises(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, "get_bundle_base_path", lambda: tmp_path)

    with pytest.raises(FileNotFoundError):
        run_bundled_script("not_exist.py")


def test_run_init_config_executes_init_script(monkeypatch, tmp_path):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    out_file = tmp_path / "ran.txt"
    (scripts_dir / "init_nhsa_registration_config.py").write_text(
        f"with open({str(out_file)!r}, 'w', encoding='utf-8') as f:\n"
        "    f.write('ran')\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(cli, "get_bundle_base_path", lambda: tmp_path)

    cli.run_init_config()

    assert out_file.read_text(encoding="utf-8") == "ran"


def test_run_import_jobs_passes_file_arg(monkeypatch, tmp_path):
    scripts_dir = tmp_path / "scripts"
    scripts_dir.mkdir()
    out_file = tmp_path / "argv.txt"
    (scripts_dir / "batch_import_registration_jobs.py").write_text(
        "import sys\n"
        f"with open({str(out_file)!r}, 'w', encoding='utf-8') as f:\n"
        "    f.write(repr(sys.argv))\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(cli, "get_bundle_base_path", lambda: tmp_path)

    cli.run_import_jobs("import_data/jobs.csv")

    assert out_file.read_text(encoding="utf-8") == repr(
        [str(scripts_dir / "batch_import_registration_jobs.py"), "import_data/jobs.csv"]
    )
