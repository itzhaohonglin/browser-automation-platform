import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.executor import PlaywrightExecutor


@pytest.mark.asyncio
async def test_executor_accepts_ws_manager():
    """测试执行器接受 ws_manager 参数"""
    mock_ws_manager = MagicMock()
    executor = PlaywrightExecutor(ws_manager=mock_ws_manager)

    assert executor.ws_manager is mock_ws_manager


@pytest.mark.asyncio
async def test_executor_works_without_ws_manager():
    """测试执行器在没有 ws_manager 时正常工作"""
    executor = PlaywrightExecutor()

    assert executor.ws_manager is None


@pytest.mark.asyncio
async def test_broadcast_progress_with_manager():
    """测试 _broadcast_progress 调用 ws_manager"""
    mock_ws_manager = MagicMock()
    mock_ws_manager.broadcast = AsyncMock()
    executor = PlaywrightExecutor(ws_manager=mock_ws_manager)

    await executor._broadcast_progress(123, "测试消息", current=3, total=10)

    mock_ws_manager.broadcast.assert_called_once()
    call_args = mock_ws_manager.broadcast.call_args[0][0]
    assert call_args["type"] == "progress"
    assert call_args["job_id"] == 123
    assert call_args["message"] == "测试消息"
    assert call_args["progress"]["current"] == 3
    assert call_args["progress"]["total"] == 10
    assert "timestamp" in call_args


@pytest.mark.asyncio
async def test_broadcast_progress_without_manager():
    """测试 _broadcast_progress 在没有 manager 时不报错"""
    executor = PlaywrightExecutor()

    # 不应该抛出异常
    await executor._broadcast_progress(123, "测试消息")


@pytest.mark.asyncio
async def test_broadcast_log_with_manager():
    """测试 _broadcast_log 调用 ws_manager"""
    mock_ws_manager = MagicMock()
    mock_ws_manager.broadcast = AsyncMock()
    executor = PlaywrightExecutor(ws_manager=mock_ws_manager)

    await executor._broadcast_log("info", "测试日志", job_id=456)

    mock_ws_manager.broadcast.assert_called_once()
    call_args = mock_ws_manager.broadcast.call_args[0][0]
    assert call_args["type"] == "log"
    assert call_args["level"] == "info"
    assert call_args["message"] == "测试日志"
    assert call_args["job_id"] == 456
    assert "timestamp" in call_args


@pytest.mark.asyncio
async def test_broadcast_log_without_job_id():
    """测试 _broadcast_log 可以不传 job_id"""
    mock_ws_manager = MagicMock()
    mock_ws_manager.broadcast = AsyncMock()
    executor = PlaywrightExecutor(ws_manager=mock_ws_manager)

    await executor._broadcast_log("error", "系统错误")

    call_args = mock_ws_manager.broadcast.call_args[0][0]
    assert "job_id" not in call_args
