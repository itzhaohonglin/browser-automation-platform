"""
Integration tests for WebSocket endpoint
"""
import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)


def test_websocket_endpoint_exists(client):
    """Test that /ws endpoint exists and supports WebSocket connections"""
    with client.websocket_connect("/ws") as websocket:
        # Test ping/pong heartbeat
        websocket.send_text("ping")
        data = websocket.receive_text()
        assert data == "pong"


def test_websocket_multiple_messages(client):
    """Test that WebSocket can handle multiple ping/pong exchanges"""
    with client.websocket_connect("/ws") as websocket:
        # Send multiple pings
        for _ in range(3):
            websocket.send_text("ping")
            data = websocket.receive_text()
            assert data == "pong"
