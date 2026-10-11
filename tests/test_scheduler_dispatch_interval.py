"""任务分发调度间隔配置测试"""
from datetime import timedelta

from apscheduler.triggers.interval import IntervalTrigger

from app.core.config import Settings, settings
from app.services.scheduler import TaskScheduler


def test_default_dispatch_interval_is_30_minutes():
    """未配置时，任务分发间隔默认应为 30 分钟"""
    s = Settings(DATABASE_URL="driver://u:p@h/db", _env_file=None)
    assert s.DISPATCH_INTERVAL_MINUTES == 30


def test_dispatch_interval_reads_from_env(monkeypatch):
    """DISPATCH_INTERVAL_MINUTES 应能从环境变量（.env）读取"""
    monkeypatch.setenv("DISPATCH_INTERVAL_MINUTES", "5")
    s = Settings(DATABASE_URL="driver://u:p@h/db", _env_file=None)
    assert s.DISPATCH_INTERVAL_MINUTES == 5


async def test_scheduler_uses_configured_dispatch_interval(monkeypatch):
    """调度器分发任务应使用 settings 中配置的间隔，而不是硬编码 10 秒"""
    monkeypatch.setattr(settings, "DISPATCH_INTERVAL_MINUTES", 7)
    triggers = {}

    class FakeScheduler:
        def __init__(self, *args, **kwargs):
            pass

        def add_job(self, func, trigger, id, name, next_run_time):
            triggers[id] = trigger

        def start(self):
            pass

    monkeypatch.setattr("app.services.scheduler.AsyncIOScheduler", FakeScheduler)

    sched = TaskScheduler()
    await sched.start()

    trigger = triggers["dispatch_pending_jobs"]
    assert isinstance(trigger, IntervalTrigger)
    assert trigger.interval == timedelta(minutes=7)
