# app/models/__init__.py
from app.models.base import Base
from app.models.config import CrawlerConfig
from app.models.job import JobQueue, JobStatus
from app.models.result import CrawlerResult

__all__ = [
    "Base",
    "CrawlerConfig",
    "JobQueue",
    "JobStatus",
    "CrawlerResult",
]
