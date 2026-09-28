import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.scheduler import TaskScheduler


@pytest.mark.asyncio
async def test_scheduler_evaluates_alert_rules():
    """测试：调度器定期评估告警规则"""
    scheduler = TaskScheduler()

    with patch('app.services.scheduler.alert_engine') as mock_engine:
        mock_engine.evaluate_rules = AsyncMock()

        # 手动触发一次告警评估
        await scheduler.evaluate_alerts()

        # 验证调用了告警引擎
        mock_engine.evaluate_rules.assert_called_once()


@pytest.mark.asyncio
async def test_scheduler_handles_alert_evaluation_errors():
    """测试：调度器处理告警评估错误"""
    scheduler = TaskScheduler()

    with patch('app.services.scheduler.alert_engine') as mock_engine:
        mock_engine.evaluate_rules = AsyncMock(side_effect=Exception("Test error"))

        # 告警评估失败不应该导致调度器崩溃
        await scheduler.evaluate_alerts()

        # 验证调用了告警引擎（尽管失败了）
        mock_engine.evaluate_rules.assert_called_once()
