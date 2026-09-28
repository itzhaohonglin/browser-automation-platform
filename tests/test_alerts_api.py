import pytest
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="function")
def client():
    """Create a test client for each test function"""
    with TestClient(app) as test_client:
        yield test_client


def test_create_alert_rule(client):
    """测试：创建告警规则"""
    response = client.post(
        "/api/alerts/rules",
        json={
            "rule_name": "测试规则",
            "metric_name": "job_failure_rate",
            "condition": ">",
            "threshold": 0.1,
            "duration_seconds": 60,
            "channels": ["email", "dingtalk"],
            "enabled": True
        }
    )
    assert response.status_code == 201
    data = response.json()
    assert data["rule_name"] == "测试规则"
    assert "id" in data


def test_list_alert_rules(client):
    """测试：列出告警规则"""
    response = client.get("/api/alerts/rules")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)


def test_get_alert_history(client):
    """测试：获取告警历史"""
    response = client.get("/api/alerts/history")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
