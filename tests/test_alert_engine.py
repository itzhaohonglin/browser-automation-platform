import pytest
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.alert_engine import AlertEngine
from app.models.metrics import AlertRule, AlertHistory, MetricsTimeSeries
from app.core.database import get_session


@pytest.mark.asyncio
async def test_evaluate_rules_triggers_alert():
    """测试：当指标超过阈值时触发告警"""
    engine = AlertEngine()

    # Mock 数据库查询
    mock_rule = MagicMock(spec=AlertRule)
    mock_rule.id = 1
    mock_rule.rule_name = "高失败率告警"
    mock_rule.metric_name = "job_failure_rate"
    mock_rule.condition = ">"
    mock_rule.threshold = 0.1
    mock_rule.duration_seconds = 60
    mock_rule.channels = ["email", "dingtalk"]
    mock_rule.enabled = True

    mock_metrics = [
        MagicMock(metric_value=0.15, timestamp=datetime.utcnow())
    ]

    with patch.object(engine, '_get_enabled_rules', return_value=[mock_rule]), \
         patch.object(engine, '_query_metrics', return_value=mock_metrics), \
         patch.object(engine, '_check_should_trigger', return_value=True), \
         patch.object(engine, '_create_alert', new_callable=AsyncMock) as mock_create, \
         patch.object(engine, '_send_notifications', new_callable=AsyncMock):

        await engine.evaluate_rules()

        mock_create.assert_called_once()


@pytest.mark.asyncio
async def test_evaluate_rules_no_trigger_below_threshold():
    """测试：当指标低于阈值时不触发告警"""
    engine = AlertEngine()

    mock_rule = MagicMock(spec=AlertRule)
    mock_rule.id = 1
    mock_rule.metric_name = "job_failure_rate"
    mock_rule.condition = ">"
    mock_rule.threshold = 0.1

    mock_metrics = [
        MagicMock(metric_value=0.05, timestamp=datetime.utcnow())
    ]

    with patch.object(engine, '_get_enabled_rules', return_value=[mock_rule]), \
         patch.object(engine, '_query_metrics', return_value=mock_metrics), \
         patch.object(engine, '_create_alert', new_callable=AsyncMock) as mock_create:

        await engine.evaluate_rules()

        mock_create.assert_not_called()
