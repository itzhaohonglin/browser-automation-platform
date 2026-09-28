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
        "/api/metrics/query",
        params={
            "metric_name": "job_success_rate",
            "start_time": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat()
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert "metric_name" in data
    assert "data_points" in data
    assert isinstance(data["data_points"], list)


def test_get_dashboard_stats(client):
    """测试：获取仪表板统计数据"""
    response = client.get("/api/metrics/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "total_jobs" in data
    assert "success_rate" in data
    assert "avg_execution_time" in data
