"""main.py 调度器与进程池接线测试"""
from app.main import create_scheduler


def test_create_scheduler_wires_pool_manager():
    """应用启动时必须为调度器提供进程池管理器，否则 pending 任务永远不会被执行"""
    scheduler, pool_manager = create_scheduler()

    assert pool_manager is not None
    assert scheduler.pool_manager is pool_manager
