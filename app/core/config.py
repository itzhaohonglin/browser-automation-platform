from pydantic_settings import BaseSettings
from typing import Optional
import os
import sys


class Settings(BaseSettings):
    """应用配置类

    企业级配置管理：
    1. 不在代码中硬编码敏感信息
    2. 必须通过环境变量或 .env 文件提供
    3. 生产环境禁止使用默认值
    """

    # 数据库配置 - 必须通过环境变量提供
    # MySQL 示例: mysql+aiomysql://user:password@host:3306/database?charset=utf8mb4
    # SQL Server 示例 (异步): mssql+aioodbc://user:password@host:1433/database?driver=ODBC+Driver+17+for+SQL+Server
    DATABASE_URL: str

    # 应用配置
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = False  # 生产环境默认关闭 DEBUG

    # Playwright 配置
    HEADLESS_MODE: bool = True  # 生产环境默认无头模式

    # 文件路径配置
    AUTH_FILES_DIR: str = "auth_files"

    # 日志配置
    LOG_LEVEL: str = "INFO"
    LOG_FILE: Optional[str] = None

    # 任务调度配置
    DISPATCH_INTERVAL_MINUTES: int = 30  # 待处理任务分发间隔（分钟）
    RETRY_INTERVAL_MINUTES: int = 30  # 失败任务重试间隔（分钟）
    MAX_RETRY_COUNT: int = 3  # 最大重试次数
    RETRY_BATCH_SIZE: int = 100  # 每批重试的任务数量

    # 智能重试配置
    RETRY_MIN_WAIT_MINUTES: int = 60  # 失败后至少等待多久才重试（分钟）
    RETRY_SKIP_IF_PENDING_OVER: int = 100  # 如果pending任务超过此数量，跳过重试

    # 进程池配置
    MAX_WORKERS: int = 3  # 最大工作进程数（并发任务数）
    WORKER_MEMORY_LIMIT_MB: int = 512  # 工作进程内存限制（MB）

    # 请求级限流配置（全局默认）
    REQUEST_RATE_LIMIT_ENABLED: bool = False  # 是否启用请求级限流
    REQUEST_RATE_LIMIT_INTERVAL_SECONDS: float = 5.0  # 请求间隔（秒）

    # 周期性任务调度配置
    SCHEDULE_CHECK_INTERVAL_MINUTES: int = 5  # 周期性任务检查间隔（分钟）
    SCHEDULE_FIRST_RUN_DELAY_MINUTES: int = 2  # 首次检查延迟（分钟）

    # 全局重新执行配置
    AUTO_RECREATE_SUCCESS_JOBS: bool = False  # 是否自动重新执行 success 任务
    AUTO_RECREATE_INTERVAL_MINUTES: int = 1440  # success 任务多久后重新执行（分钟，默认24小时）

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保必要目录存在
        os.makedirs(self.AUTH_FILES_DIR, exist_ok=True)
        if self.LOG_FILE:
            log_dir = os.path.dirname(self.LOG_FILE)
            if log_dir:
                os.makedirs(log_dir, exist_ok=True)


# 全局配置实例 - 带友好的错误提示
try:
    settings = Settings()
except Exception as e:
    error_msg = str(e)

    # 检查是否是缺少 .env 文件的错误
    if "DATABASE_URL" in error_msg and "required" in error_msg:
        print("\n" + "="*60)
        print("  Configuration Error")
        print("="*60)
        print("\n[ERROR] Configuration file .env not found or incomplete")
        print("\nPlease follow these steps:")
        print("  1. Run install.bat for first-time setup")
        print("  2. Or manually create .env file from .env.example")
        print("  3. Configure DATABASE_URL in .env file")
        print("\nExample configuration:")
        print("  DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server")
        print("\n" + "="*60)
        print("\nPress Enter to exit...")
        input()
        sys.exit(1)
    else:
        # 其他配置错误
        print("\n" + "="*60)
        print("  Configuration Error")
        print("="*60)
        print(f"\n[ERROR] {error_msg}")
        print("\nPlease check your .env file for errors.")
        print("\n" + "="*60)
        print("\nPress Enter to exit...")
        input()
        sys.exit(1)
