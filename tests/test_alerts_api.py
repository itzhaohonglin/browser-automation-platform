import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient
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


def test_create_alert_rule_invalid_condition(client):
    """测试：创建告警规则 - 无效条件"""
    response = client.post(
        "/api/alerts/rules",
        json={
            "rule_name": "测试规则",
            "metric_name": "job_failure_rate",
            "condition": "invalid",  # 无效条件
            "threshold": 0.1,
            "duration_seconds": 60,
            "channels": ["email"],
            "enabled": True
        }
    )
    assert response.status_code == 422  # Validation error


def test_create_alert_rule_invalid_channels(client):
    """测试：创建告警规则 - 无效通知渠道"""
    response = client.post(
        "/api/alerts/rules",
        json={
            "rule_name": "测试规则",
            "metric_name": "job_failure_rate",
            "condition": ">",
            "threshold": 0.1,
            "duration_seconds": 60,
            "channels": ["invalid_channel"],
            "enabled": True
        }
    )
    assert response.status_code == 400


def test_create_alert_rule_duration_too_small(client):
    """测试：创建告警规则 - 持续时间过小"""
    response = client.post(
        "/api/alerts/rules",
        json={
            "rule_name": "测试规则",
            "metric_name": "job_failure_rate",
            "condition": ">",
            "threshold": 0.1,
            "duration_seconds": 5,  # 小于最小值 10
            "channels": ["email"],
            "enabled": True
        }
    )
    assert response.status_code == 422


def test_get_alert_rule_not_found(client):
    """测试：获取不存在的告警规则"""
    response = client.get("/api/alerts/rules/99999")
    assert response.status_code == 404


def test_update_alert_rule_not_found(client):
    """测试：更新不存在的告警规则"""
    response = client.put(
        "/api/alerts/rules/99999",
        json={"enabled": False}
    )
    assert response.status_code == 404


def test_delete_alert_rule_not_found(client):
    """测试：删除不存在的告警规则"""
    response = client.delete("/api/alerts/rules/99999")
    assert response.status_code == 404


def test_get_alert_history_with_limit(client):
    """测试：获取告警历史 - 带 limit 参数"""
    response = client.get("/api/alerts/history?limit=10")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 10


def test_list_alert_rules_with_pagination(client):
    """测试：列出告警规则 - 带分页参数"""
    response = client.get("/api/alerts/rules?page=1&page_size=5")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) <= 5

