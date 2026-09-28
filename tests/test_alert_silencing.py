import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone, timedelta
from app.services.alert_engine import AlertEngine
from app.models.metrics import AlertRule


@pytest.mark.asyncio
async def test_alert_engine_silences_repeated_alerts():
    """测试：告警引擎静默重复告警"""
    engine = AlertEngine()

    # Mock 规则，最近刚触发过告警
    mock_rule = MagicMock(spec=AlertRule)
    mock_rule.id = 1
    mock_rule.rule_name = "测试规则"
    mock_rule.last_alert_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    mock_rule.silence_duration = 3600  # 静默 1 小时

    # 检查是否在静默期
    is_silenced = engine._is_in_silence_period(mock_rule)

    assert is_silenced is True


@pytest.mark.asyncio
async def test_alert_engine_allows_alerts_after_silence():
    """测试：静默期过后允许告警"""
    engine = AlertEngine()

    # Mock 规则，上次告警是 2 小时前
    mock_rule = MagicMock(spec=AlertRule)
    mock_rule.id = 1
    mock_rule.rule_name = "测试规则"
    mock_rule.last_alert_at = datetime.now(timezone.utc) - timedelta(hours=2)
    mock_rule.silence_duration = 3600  # 静默 1 小时

    # 检查是否在静默期
    is_silenced = engine._is_in_silence_period(mock_rule)

    assert is_silenced is False


@pytest.mark.asyncio
async def test_alert_engine_allows_first_alert():
    """测试：首次告警不受静默限制"""
    engine = AlertEngine()

    # Mock 规则，从未触发过告警
    mock_rule = MagicMock(spec=AlertRule)
    mock_rule.id = 1
    mock_rule.rule_name = "测试规则"
    mock_rule.last_alert_at = None
    mock_rule.silence_duration = 3600

    # 检查是否在静默期
    is_silenced = engine._is_in_silence_period(mock_rule)

    assert is_silenced is False
