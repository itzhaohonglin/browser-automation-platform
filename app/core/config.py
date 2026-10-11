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

    # 告警邮件配置
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USE_TLS: bool = True
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    ALERT_EMAIL_FROM: Optional[str] = None
    ALERT_EMAIL_TO: Optional[str] = None

    # 钉钉机器人
    DINGTALK_WEBHOOK_URL: Optional[str] = None

    # 企业微信机器人
    WECOM_WEBHOOK_URL: Optional[str] = None

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
