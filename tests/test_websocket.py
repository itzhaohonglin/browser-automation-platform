"""
Tests for WebSocket connection manager
"""
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from app.api.websocket import WebSocketManager


@pytest.fixture
def ws_manager():
    """Create a fresh WebSocketManager instance for each test"""
    return WebSocketManager()


@pytest.fixture
def mock_websocket():
    """Create a mock WebSocket instance"""
    ws = MagicMock(spec=WebSocket)
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock()
    return ws


@pytest.mark.asyncio
async def test_websocket_manager_connect(ws_manager, mock_websocket):
    """Test that connect() adds a websocket to active connections"""
    # Initially empty
    assert len(ws_manager.active_connections) == 0

    # Connect a websocket
    await ws_manager.connect(mock_websocket)

    # Should be in active connections
    assert len(ws_manager.active_connections) == 1
    assert mock_websocket in ws_manager.active_connections

    # accept() should have been called
    mock_websocket.accept.assert_called_once()


@pytest.mark.asyncio
async def test_websocket_manager_disconnect(ws_manager, mock_websocket):
    """Test that disconnect() removes a websocket from active connections"""
    # Add a websocket first
    await ws_manager.connect(mock_websocket)
    assert len(ws_manager.active_connections) == 1

    # Disconnect it
    await ws_manager.disconnect(mock_websocket)

    # Should be removed
    assert len(ws_manager.active_connections) == 0
    assert mock_websocket not in ws_manager.active_connections


@pytest.mark.asyncio
async def test_websocket_manager_broadcast(ws_manager):
    """Test that broadcast() sends messages to all connected clients"""
    # Create 3 mock websockets
    ws1 = MagicMock(spec=WebSocket)
    ws1.accept = AsyncMock()
    ws1.send_json = AsyncMock()

    ws2 = MagicMock(spec=WebSocket)
    ws2.accept = AsyncMock()
    ws2.send_json = AsyncMock()

    ws3 = MagicMock(spec=WebSocket)
    ws3.accept = AsyncMock()
    ws3.send_json = AsyncMock()

    # Connect all three
    await ws_manager.connect(ws1)
    await ws_manager.connect(ws2)
    await ws_manager.connect(ws3)

    assert len(ws_manager.active_connections) == 3

    # Broadcast a message
    test_message = {
        "type": "progress",
        "job_id": 123,
        "message": "Test message"
    }
    await ws_manager.broadcast(test_message)

    # All three should have received the message
    ws1.send_json.assert_called_once_with(test_message)
    ws2.send_json.assert_called_once_with(test_message)
    ws3.send_json.assert_called_once_with(test_message)


@pytest.mark.asyncio
async def test_websocket_manager_broadcast_handles_disconnected(ws_manager):
    """Test that broadcast() automatically cleans up disconnected clients"""
    # Create 3 websockets: 2 working, 1 that will fail
    ws1 = MagicMock(spec=WebSocket)
    ws1.accept = AsyncMock()
    ws1.send_json = AsyncMock()

    ws2_disconnected = MagicMock(spec=WebSocket)
    ws2_disconnected.accept = AsyncMock()
    ws2_disconnected.send_json = AsyncMock(side_effect=WebSocketDisconnect())

    ws3 = MagicMock(spec=WebSocket)
    ws3.accept = AsyncMock()
    ws3.send_json = AsyncMock()

    # Connect all three
    await ws_manager.connect(ws1)
    await ws_manager.connect(ws2_disconnected)
    await ws_manager.connect(ws3)

    assert len(ws_manager.active_connections) == 3

    # Broadcast a message
    test_message = {"type": "log", "message": "Test"}
    await ws_manager.broadcast(test_message)

    # Disconnected websocket should be removed
    assert len(ws_manager.active_connections) == 2
    assert ws2_disconnected not in ws_manager.active_connections

    # Other two should still be there and have received the message
    assert ws1 in ws_manager.active_connections
    assert ws3 in ws_manager.active_connections
    ws1.send_json.assert_called_once_with(test_message)
    ws3.send_json.assert_called_once_with(test_message)


@pytest.mark.asyncio
async def test_websocket_endpoint_ping_pong():
    """Test websocket_endpoint ping/pong heartbeat mechanism"""
    manager = WebSocketManager()
    mock_ws = MagicMock(spec=WebSocket)
    mock_ws.accept = AsyncMock()
    mock_ws.receive_text = AsyncMock(side_effect=["ping", WebSocketDisconnect()])
    mock_ws.send_text = AsyncMock()

    await manager.websocket_endpoint(mock_ws)

    # Verify connection was accepted
    mock_ws.accept.assert_called_once()
    # Verify pong was sent
    mock_ws.send_text.assert_called_once_with("pong")
    # Verify connection was cleaned up
    assert mock_ws not in manager.active_connections


@pytest.mark.asyncio
async def test_websocket_endpoint_handles_disconnect():
    """Test websocket_endpoint handles client disconnect"""
    manager = WebSocketManager()
    mock_ws = MagicMock(spec=WebSocket)
    mock_ws.accept = AsyncMock()
    mock_ws.receive_text = AsyncMock(side_effect=WebSocketDisconnect())

    await manager.websocket_endpoint(mock_ws)

    # Verify connection was cleaned up
    assert mock_ws not in manager.active_connections


@pytest.mark.asyncio
async def test_websocket_endpoint_handles_exception():
    """Test websocket_endpoint handles exceptions"""
    manager = WebSocketManager()
    mock_ws = MagicMock(spec=WebSocket)
    mock_ws.accept = AsyncMock()
    mock_ws.receive_text = AsyncMock(side_effect=Exception("Connection error"))

    await manager.websocket_endpoint(mock_ws)

    # Verify connection was cleaned up
    assert mock_ws not in manager.active_connections
