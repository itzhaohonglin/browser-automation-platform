from pydantic import BaseModel
from typing import Optional, List


class MetricQuery(BaseModel):
    """指标查询请求"""
    metric_name: str
    start_time: str  # ISO 8601 格式
    end_time: str
    aggregation: Optional[str] = None


class MetricResponse(BaseModel):
    """指标查询响应（单个数据点）"""
    timestamp: str
    value: float
    labels: Optional[dict] = None


class DashboardData(BaseModel):
    """仪表板数据响应"""
    job_success_rate: float
    avg_execution_time: float
    browser_pool_utilization: float
    queue_size: float
