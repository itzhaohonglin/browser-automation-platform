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
    """测试 _broadcast_progress 调用 ws_manager（PRD V2.0 格式）"""
    mock_ws_manager = MagicMock()
    mock_ws_manager.broadcast = AsyncMock()
    executor = PlaywrightExecutor(ws_manager=mock_ws_manager)

    await executor._broadcast_progress(
        job_id=123,
        data={
            "job_id": 123,
            "status": "running",
            "current": 3,
            "total": 10
        }
    )

    mock_ws_manager.broadcast.assert_called_once()
    call_args = mock_ws_manager.broadcast.call_args[0][0]
    assert call_args["type"] == "progress"
    assert call_args["data"]["job_id"] == 123
    assert call_args["data"]["status"] == "running"
    assert call_args["data"]["current"] == 3
    assert call_args["data"]["total"] == 10
    # PRD V2.0 格式不包含 timestamp
    assert "timestamp" not in call_args


@pytest.mark.asyncio
async def test_broadcast_progress_without_manager():
    """测试 _broadcast_progress 在没有 manager 时不报错"""
    executor = PlaywrightExecutor()

    # 不应该抛出异常
    await executor._broadcast_progress(job_id=123, data={"status": "running"})


@pytest.mark.asyncio
async def test_broadcast_log_with_manager():
    """测试 _broadcast_log 调用 ws_manager（PRD V2.0 格式）"""
    mock_ws_manager = MagicMock()
    mock_ws_manager.broadcast = AsyncMock()
    executor = PlaywrightExecutor(ws_manager=mock_ws_manager)

    await executor._broadcast_log("info", "测试日志")

    mock_ws_manager.broadcast.assert_called_once()
    call_args = mock_ws_manager.broadcast.call_args[0][0]
    assert call_args["type"] == "log"
    assert call_args["level"] == "info"
    assert call_args["msg"] == "测试日志"
    # PRD V2.0 格式不包含 job_id 和 timestamp
    assert "job_id" not in call_args
    assert "timestamp" not in call_args
    assert "message" not in call_args  # 使用 msg 而不是 message


@pytest.mark.asyncio
async def test_broadcast_log_without_job_id():
    """测试 _broadcast_log 支持 success 级别（PRD V2.0）"""
    mock_ws_manager = MagicMock()
    mock_ws_manager.broadcast = AsyncMock()
    executor = PlaywrightExecutor(ws_manager=mock_ws_manager)

    await executor._broadcast_log("success", "任务执行成功")

    call_args = mock_ws_manager.broadcast.call_args[0][0]
    assert call_args["type"] == "log"
    assert call_args["level"] == "success"
    assert call_args["msg"] == "任务执行成功"
    assert "job_id" not in call_args


@pytest.mark.asyncio
async def test_broadcast_progress_without_progress_params():
    """测试 _broadcast_progress 使用 data 字段（PRD V2.0）"""
    mock_ws_manager = MagicMock()
    mock_ws_manager.broadcast = AsyncMock()
    executor = PlaywrightExecutor(ws_manager=mock_ws_manager)

    await executor._broadcast_progress(job_id=123, data={"status": "pending"})

    mock_ws_manager.broadcast.assert_called_once()
    call_args = mock_ws_manager.broadcast.call_args[0][0]
    assert call_args["type"] == "progress"
    assert call_args["data"]["status"] == "pending"
    # 验证使用 data 字段而不是顶层字段
    assert "job_id" not in call_args  # job_id 应在 data 内
    assert "message" not in call_args
    assert "timestamp" not in call_args


@pytest.mark.asyncio
async def test_broadcast_progress_handles_exception():
    """测试 _broadcast_progress 在广播失败时正确处理异常"""
    mock_ws_manager = MagicMock()
    mock_ws_manager.broadcast = AsyncMock(side_effect=Exception("Connection lost"))
    executor = PlaywrightExecutor(ws_manager=mock_ws_manager)

    # 不应该抛出异常
    await executor._broadcast_progress(job_id=123, data={"status": "running"})


@pytest.mark.asyncio
async def test_broadcast_log_handles_exception():
    """测试 _broadcast_log 在广播失败时正确处理异常"""
    mock_ws_manager = MagicMock()
    mock_ws_manager.broadcast = AsyncMock(side_effect=Exception("Connection lost"))
    executor = PlaywrightExecutor(ws_manager=mock_ws_manager)

    # 不应该抛出异常
    await executor._broadcast_log("error", "测试日志")
