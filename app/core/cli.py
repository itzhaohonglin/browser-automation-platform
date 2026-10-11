"""命令行入口辅助

打包后的 exe 通过命令行参数提供数据库迁移、浏览器驱动安装、
配置初始化和数据导入能力，替代客户端无法使用的
alembic / playwright / python 命令行工具。
"""
import runpy
import sys

from app.core.migrations import get_bundle_base_path

ACTION_MIGRATE = "migrate"
ACTION_INSTALL_BROWSER = "install_browser"
ACTION_INIT_CONFIG = "init_config"
ACTION_IMPORT_JOBS = "import_jobs"

_MIGRATE_FLAG = "--migrate"
_INSTALL_BROWSER_FLAG = "--install-browser"
_INIT_CONFIG_FLAG = "--init-config"
_IMPORT_JOBS_FLAG = "--import-jobs"


def parse_cli_args(argv: list[str]) -> tuple[str | None, list[str]]:
    """解析命令行参数，返回 (动作, 附加参数)；无匹配动作时返回 (None, [])"""
    for i, arg in enumerate(argv):
        if arg == _IMPORT_JOBS_FLAG:
            if i + 1 < len(argv):
                return ACTION_IMPORT_JOBS, [argv[i + 1]]
            return ACTION_IMPORT_JOBS, []
        if arg.startswith(_IMPORT_JOBS_FLAG + "=") and len(arg) > len(_IMPORT_JOBS_FLAG) + 1:
            return ACTION_IMPORT_JOBS, [arg[len(_IMPORT_JOBS_FLAG) + 1 :]]
    if _MIGRATE_FLAG in argv:
        return ACTION_MIGRATE, []
    if _INSTALL_BROWSER_FLAG in argv:
        return ACTION_INSTALL_BROWSER, []
    if _INIT_CONFIG_FLAG in argv:
        return ACTION_INIT_CONFIG, []
    return None, []


def run_bundled_script(script_name: str, args: list[str] | None = None) -> None:
    """以 __main__ 身份执行打包资源目录 scripts/ 下的独立脚本"""
    path = get_bundle_base_path() / "scripts" / script_name
    if not path.exists():
        raise FileNotFoundError(f"脚本不存在: {path}")

    old_argv = sys.argv
    sys.argv = [str(path)] + (args or [])
    try:
        runpy.run_path(str(path), run_name="__main__")
    finally:
        sys.argv = old_argv


def run_init_config() -> None:
    """初始化示例配置（--init-config）"""
    run_bundled_script("init_nhsa_registration_config.py")


def run_import_jobs(file_path: str) -> None:
    """从文件批量导入任务（--import-jobs <file>）"""
    run_bundled_script("batch_import_registration_jobs.py", [file_path])


def install_browser() -> None:
    """调用 Playwright 内置 CLI 安装 Chromium 浏览器"""
    from playwright.__main__ import main as playwright_main

    sys.argv = ["playwright", "install", "chromium"]
    playwright_main()
