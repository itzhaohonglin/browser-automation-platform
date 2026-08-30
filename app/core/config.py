from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """应用配置类"""

    # 数据库配置
    DATABASE_URL: str = "mysql+aiomysql://root:password@localhost:3306/browser_automation"

    # 应用配置
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    DEBUG: bool = True

    # Playwright 配置
    HEADLESS_MODE: bool = True

    # 文件路径配置
    AUTH_FILES_DIR: str = "auth_files"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局配置实例
settings = Settings()
