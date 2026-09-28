import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from app.services.alert_engine import AlertEngine
from app.models.metrics import AlertRule, AlertHistory


@pytest.mark.asyncio
async def test_alert_engine_detects_recovery():
    """测试：告警引擎检测指标恢复"""
    engine = AlertEngine()

    # Mock 规则和最近的活跃告警
    mock_rule = MagicMock(spec=AlertRule)
    mock_rule.id = 1
    mock_rule.rule_name = "测试规则"
    mock_rule.metric_name = "job_failure_rate"
    mock_rule.condition = ">"
    mock_rule.threshold = 0.8

    mock_alert = MagicMock(spec=AlertHistory)
    mock_alert.id = 1
    mock_alert.is_active = True

    mock_metric = MagicMock()
    mock_metric.metric_value = 0.5  # 低于阈值，已恢复

    # 检查是否应该发送恢复通知
    should_recover = engine._should_send_recovery(
        mock_rule,
        mock_alert,
        mock_metric.metric_value
    )

    assert should_recover is True


@pytest.mark.asyncio
async def test_alert_engine_skips_recovery_when_still_triggered():
    """测试：指标仍超阈值时不发送恢复通知"""
    engine = AlertEngine()

    mock_rule = MagicMock(spec=AlertRule)
    mock_rule.condition = ">"
    mock_rule.threshold = 0.8

    mock_alert = MagicMock(spec=AlertHistory)
    mock_alert.is_active = True

    mock_metric_value = 0.9  # 仍然超过阈值

    should_recover = engine._should_send_recovery(
        mock_rule,
        mock_alert,
        mock_metric_value
    )

    assert should_recover is False


@pytest.mark.asyncio
async def test_alert_engine_sends_recovery_notification():
    """测试：发送恢复通知"""
    engine = AlertEngine()

    mock_rule = MagicMock()
    mock_rule.id = 1
    mock_rule.rule_name = "测试规则"
    mock_rule.channels = ["email"]

    mock_alert = MagicMock()
    mock_alert.id = 1

    with patch.object(engine.email_notifier, 'send', new_callable=AsyncMock) as mock_send:
        await engine._send_recovery_notification(mock_rule, mock_alert, 0.5)

        # 验证发送了恢复通知
        mock_send.assert_called_once()
        call_args = mock_send.call_args[0][0]
        assert "恢复" in call_args or "Recovered" in call_args
