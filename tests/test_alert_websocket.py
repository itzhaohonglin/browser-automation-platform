import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.alert_engine import AlertEngine


@pytest.mark.asyncio
async def test_alert_engine_broadcasts_via_websocket():
    """测试：告警引擎通过 WebSocket 广播告警"""
    engine = AlertEngine()

    # Mock WebSocket 管理器
    mock_ws_manager = MagicMock()
    mock_ws_manager.broadcast = AsyncMock()
    engine.ws_manager = mock_ws_manager

    # Mock 告警触发
    mock_rule = MagicMock()
    mock_rule.id = 1
    mock_rule.rule_name = "测试规则"
    mock_rule.metric_name = "job_failure_rate"

    mock_alert = MagicMock()
    mock_alert.id = 1
    mock_alert.alert_message = "告警消息"

    mock_metric = MagicMock()
    mock_metric.metric_value = 0.5

    # 调用广播方法
    await engine._broadcast_alert(mock_rule, mock_alert, mock_metric)

    # 验证 WebSocket 广播被调用
    mock_ws_manager.broadcast.assert_called_once()
    call_args = mock_ws_manager.broadcast.call_args[0][0]
    assert call_args["type"] == "alert"
    assert "rule_name" in call_args


@pytest.mark.asyncio
async def test_alert_engine_handles_websocket_failure():
    """测试：WebSocket 广播失败不影响告警流程"""
    engine = AlertEngine()

    # Mock WebSocket 管理器失败
    mock_ws_manager = MagicMock()
    mock_ws_manager.broadcast = AsyncMock(side_effect=Exception("WS error"))
    engine.ws_manager = mock_ws_manager

    mock_rule = MagicMock()
    mock_rule.id = 1
    mock_rule.rule_name = "测试规则"

    mock_alert = MagicMock()
    mock_alert.id = 1

    mock_metric = MagicMock()
    mock_metric.metric_value = 0.5

    # 广播失败不应该抛出异常
    await engine._broadcast_alert(mock_rule, mock_alert, mock_metric)
