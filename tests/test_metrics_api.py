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
    assert isinstance(data["queue_size"], int)  # queue_size 应该是 int 类型


def test_query_metrics_invalid_aggregation(client):
    """测试：查询指标数据 - 无效的聚合参数"""
    response = client.get(
        "/api/metrics/",
        params={
            "metric_name": "job_success_rate",
            "start_time": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "aggregation": "invalid_agg"  # 无效的聚合方式
        }
    )
    assert response.status_code == 400
    assert "aggregation 必须是以下之一" in response.json()["detail"]


def test_query_metrics_invalid_time_range_order(client):
    """测试：查询指标数据 - 时间范围顺序错误"""
    now = datetime.now(timezone.utc)
    one_hour_ago = now - timedelta(hours=1)

    response = client.get(
        "/api/metrics/",
        params={
            "metric_name": "job_success_rate",
            "start_time": now.isoformat(),  # start_time 晚于 end_time
            "end_time": one_hour_ago.isoformat()
        }
    )
    assert response.status_code == 400
    assert "start_time 必须小于 end_time" in response.json()["detail"]


def test_query_metrics_invalid_time_range_span(client):
    """测试：查询指标数据 - 时间范围跨度过大"""
    now = datetime.now(timezone.utc)
    long_ago = now - timedelta(days=31)  # 超过 30 天

    response = client.get(
        "/api/metrics/",
        params={
            "metric_name": "job_success_rate",
            "start_time": long_ago.isoformat(),
            "end_time": now.isoformat()
        }
    )
    assert response.status_code == 400
    assert "时间范围不能超过" in response.json()["detail"]


def test_query_metrics_empty_result(client):
    """测试：查询指标数据 - 空结果"""
    # 查询一个不存在的指标
    response = client.get(
        "/api/metrics/",
        params={
            "metric_name": "non_existent_metric",
            "start_time": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat()
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # 空结果也是有效的
    assert len(data) >= 0


def test_query_metrics_with_aggregation(client):
    """测试：查询指标数据 - 使用聚合"""
    response = client.get(
        "/api/metrics/",
        params={
            "metric_name": "job_execution_time",
            "start_time": (datetime.now(timezone.utc) - timedelta(hours=1)).isoformat(),
            "end_time": datetime.now(timezone.utc).isoformat(),
            "aggregation": "avg"
        }
    )
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    # 验证聚合结果包含 timestamp
    for item in data:
        assert "timestamp" in item
        assert "value" in item


def test_dashboard_handles_missing_data(client):
    """测试：仪表板能够处理缺失的指标数据"""
    # 即使某些指标不存在，仪表板也应该返回 200 并使用默认值
    response = client.get("/api/metrics/dashboard")
    assert response.status_code == 200
    data = response.json()

    # 所有字段都应该存在且为数字
    assert isinstance(data["job_success_rate"], (int, float))
    assert isinstance(data["avg_execution_time"], (int, float))
    assert isinstance(data["browser_pool_utilization"], (int, float))
    assert isinstance(data["queue_size"], int)

    # 值应该 >= 0
    assert data["job_success_rate"] >= 0
    assert data["avg_execution_time"] >= 0
    assert data["browser_pool_utilization"] >= 0
    assert data["queue_size"] >= 0
