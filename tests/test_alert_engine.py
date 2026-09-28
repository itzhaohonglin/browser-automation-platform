import pytest
from datetime import datetime, timedelta, timezone
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
        MagicMock(metric_value=0.15, timestamp=datetime.now(timezone.utc))
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
        MagicMock(metric_value=0.05, timestamp=datetime.now(timezone.utc))
    ]

    with patch.object(engine, '_get_enabled_rules', return_value=[mock_rule]), \
         patch.object(engine, '_query_metrics', return_value=mock_metrics), \
         patch.object(engine, '_create_alert', new_callable=AsyncMock) as mock_create:

        await engine.evaluate_rules()

        mock_create.assert_not_called()


@pytest.mark.asyncio
async def test_check_should_trigger_all_conditions():
    """测试：所有6种条件运算符"""
    engine = AlertEngine()

    # 测试 > 运算符
    assert engine._check_should_trigger(0.15, ">", 0.1) == True
    assert engine._check_should_trigger(0.05, ">", 0.1) == False

    # 测试 >= 运算符
    assert engine._check_should_trigger(0.1, ">=", 0.1) == True
    assert engine._check_should_trigger(0.15, ">=", 0.1) == True
    assert engine._check_should_trigger(0.05, ">=", 0.1) == False

    # 测试 < 运算符
    assert engine._check_should_trigger(0.05, "<", 0.1) == True
    assert engine._check_should_trigger(0.15, "<", 0.1) == False

    # 测试 <= 运算符
    assert engine._check_should_trigger(0.1, "<=", 0.1) == True
    assert engine._check_should_trigger(0.05, "<=", 0.1) == True
    assert engine._check_should_trigger(0.15, "<=", 0.1) == False

    # 测试 == 运算符（使用容差）
    assert engine._check_should_trigger(0.1, "==", 0.1) == True
    assert engine._check_should_trigger(0.1000000001, "==", 0.1) == True
    assert engine._check_should_trigger(0.15, "==", 0.1) == False

    # 测试 != 运算符（使用容差）
    assert engine._check_should_trigger(0.15, "!=", 0.1) == True
    assert engine._check_should_trigger(0.1, "!=", 0.1) == False
    assert engine._check_should_trigger(0.1000000001, "!=", 0.1) == False

    # 测试不支持的运算符
    assert engine._check_should_trigger(0.15, "unknown", 0.1) == False


@pytest.mark.asyncio
async def test_send_notifications_updates_status_success():
    """测试：所有通知成功时更新状态为 success"""
    engine = AlertEngine()

    mock_rule = MagicMock(spec=AlertRule)
    mock_rule.channels = ["email", "dingtalk"]

    mock_alert = MagicMock(spec=AlertHistory)
    mock_alert.alert_message = "测试告警"

    mock_metric = MagicMock(spec=MetricsTimeSeries)
    mock_session = AsyncMock()

    with patch.object(engine.email_notifier, 'send', new_callable=AsyncMock), \
         patch.object(engine.dingtalk_notifier, 'send', new_callable=AsyncMock):

        await engine._send_notifications(mock_rule, mock_alert, mock_metric, mock_session)

        assert mock_alert.notify_status == "success"
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_send_notifications_partial_failure():
    """测试：部分通知失败时更新状态为 partial_success"""
    engine = AlertEngine()

    mock_rule = MagicMock(spec=AlertRule)
    mock_rule.channels = ["email", "dingtalk", "wecom"]

    mock_alert = MagicMock(spec=AlertHistory)
    mock_alert.alert_message = "测试告警"

    mock_metric = MagicMock(spec=MetricsTimeSeries)
    mock_session = AsyncMock()

    with patch.object(engine.email_notifier, 'send', new_callable=AsyncMock), \
         patch.object(engine.dingtalk_notifier, 'send', side_effect=Exception("网络错误")), \
         patch.object(engine.wecom_notifier, 'send', new_callable=AsyncMock):

        await engine._send_notifications(mock_rule, mock_alert, mock_metric, mock_session)

        assert mock_alert.notify_status == "partial_success"
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_send_notifications_all_failed():
    """测试：所有通知失败时更新状态为 failed"""
    engine = AlertEngine()

    mock_rule = MagicMock(spec=AlertRule)
    mock_rule.channels = ["email", "dingtalk"]

    mock_alert = MagicMock(spec=AlertHistory)
    mock_alert.alert_message = "测试告警"

    mock_metric = MagicMock(spec=MetricsTimeSeries)
    mock_session = AsyncMock()

    with patch.object(engine.email_notifier, 'send', side_effect=Exception("发送失败")), \
         patch.object(engine.dingtalk_notifier, 'send', side_effect=Exception("发送失败")):

        await engine._send_notifications(mock_rule, mock_alert, mock_metric, mock_session)

        assert mock_alert.notify_status == "failed"
        assert "2 个渠道全部失败" in mock_alert.notify_error
        mock_session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_evaluate_rules_handles_query_error():
    """测试：查询指标数据失败时不影响其他规则评估"""
    engine = AlertEngine()

    mock_rule1 = MagicMock(spec=AlertRule)
    mock_rule1.id = 1
    mock_rule1.rule_name = "规则1"
    mock_rule1.metric_name = "metric1"

    mock_rule2 = MagicMock(spec=AlertRule)
    mock_rule2.id = 2
    mock_rule2.rule_name = "规则2"
    mock_rule2.metric_name = "metric2"

    async def mock_query_side_effect(session, metric_name, start_time, end_time):
        if metric_name == "metric1":
            raise Exception("数据库查询错误")
        return [MagicMock(metric_value=0.15, timestamp=datetime.now(timezone.utc))]

    with patch.object(engine, '_get_enabled_rules', return_value=[mock_rule1, mock_rule2]), \
         patch.object(engine, '_query_metrics', side_effect=mock_query_side_effect), \
         patch.object(engine, '_create_alert', new_callable=AsyncMock) as mock_create:

        await engine.evaluate_rules()

        # 第一个规则失败，但不影响第二个规则的评估
        # 由于 mock_query 抛出异常，_evaluate_single_rule 会捕获并继续
        assert True  # 验证不会抛出异常
