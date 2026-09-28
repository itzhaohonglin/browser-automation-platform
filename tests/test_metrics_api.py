import pytest
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="module")
def client():
    """Create a test client for the entire module"""
    with TestClient(app) as test_client:
        yield test_client


def test_query_metrics(client):
    """测试：查询指标数据"""
    response = client.get(
        "/api/metrics/",
        params={
            "metric_name": "job_success_rate",
            "start_time": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat()
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # 验证列表中的每个元素包含 timestamp, value, labels 字段
    for item in data:
        assert "timestamp" in item
        assert "value" in item
        assert "labels" in item or item.get("labels") is None


def test_get_dashboard_stats(client):
    """测试：获取仪表板统计数据"""
    response = client.get("/api/metrics/dashboard")
    assert response.status_code == 200
    data = response.json()
    # 验证 DashboardData 模型字段
    assert "job_success_rate" in data
    assert "avg_execution_time" in data
    assert "browser_pool_utilization" in data
    assert "queue_size" in data
    # 验证字段类型
    assert isinstance(data["job_success_rate"], (int, float))
    assert isinstance(data["avg_execution_time"], (int, float))
    assert isinstance(data["browser_pool_utilization"], (int, float))
    assert isinstance(data["queue_size"], (int, float))
