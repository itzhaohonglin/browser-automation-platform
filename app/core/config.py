from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """应用配置类

    企业级配置管理：
    1. 不在代码中硬编码敏感信息
    2. 必须通过环境变量或 .env 文件提供
    3. 生产环境禁止使用默认值
    """

    # 数据库配置 - 必须通过环境变量提供
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

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 确保必要目录存在
        os.makedirs(self.AUTH_FILES_DIR, exist_ok=True)
        if self.LOG_FILE:
            os.makedirs(os.path.dirname(self.LOG_FILE), exist_ok=True)


# 全局配置实例
settings = Settings()
