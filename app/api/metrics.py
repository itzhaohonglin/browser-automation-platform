from fastapi import APIRouter, Query, Depends
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.metrics import MetricsTimeSeries
from app.models.job import JobQueue, JobStatus
from app.schemas.metrics import MetricResponse, DashboardData
from app.services.metrics_collector import metrics_collector

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/", response_model=List[MetricResponse])
async def query_metrics(
    metric_name: str = Query(..., description="指标名称"),
    start_time: datetime = Query(..., description="开始时间（ISO 8601 格式）"),
    end_time: datetime = Query(..., description="结束时间（ISO 8601 格式）"),
    aggregation: Optional[str] = Query(None, description="聚合方式：avg/sum/max/min")
) -> List[MetricResponse]:
    """
    查询指标数据

    返回指定时间范围内的指标数据点列表。
    """
    # 使用 metrics_collector 查询
    data_points = await metrics_collector.query(
        metric_name=metric_name,
        start_time=start_time,
        end_time=end_time,
        aggregation=aggregation
    )

    # 转换为 MetricResponse 列表
    return [
        MetricResponse(
            timestamp=dp.get("timestamp", datetime.now(timezone.utc).isoformat()),
            value=dp.get("value", 0.0),
            labels=dp.get("labels")
        )
        for dp in data_points
    ]


@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db)
) -> DashboardData:
    """
    获取仪表板统计数据

    返回系统总体运行指标：任务成功率、平均执行时间、浏览器池利用率、队列大小。
    """
    # 时间范围：最近 1 小时
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    now = datetime.now(timezone.utc)

    # 查询任务成功率
    total_stmt = select(func.count(JobQueue.id)).where(
        JobQueue.created_at >= one_hour_ago
    )
    total_result = await db.execute(total_stmt)
    total_jobs = total_result.scalar() or 0

    success_stmt = select(func.count(JobQueue.id)).where(
        JobQueue.status == JobStatus.SUCCESS,
        JobQueue.created_at >= one_hour_ago
    )
    success_result = await db.execute(success_stmt)
    success_jobs = success_result.scalar() or 0

    job_success_rate = (success_jobs / total_jobs * 100) if total_jobs > 0 else 0.0

    # 查询平均执行时间（使用 metrics_collector）
    exec_time_data = await metrics_collector.query(
        metric_name="job_execution_time",
        start_time=one_hour_ago,
        end_time=now,
        aggregation="avg"
    )
    avg_execution_time = exec_time_data[0].get("value", 0.0) if exec_time_data else 0.0

    # 查询浏览器池利用率（使用 metrics_collector）
    pool_data = await metrics_collector.query(
        metric_name="browser_pool_utilization",
        start_time=one_hour_ago,
        end_time=now,
        aggregation="avg"
    )
    browser_pool_utilization = pool_data[0].get("value", 0.0) if pool_data else 0.0

    # 查询队列大小（当前待处理任务数）
    queue_stmt = select(func.count(JobQueue.id)).where(
        JobQueue.status == JobStatus.PENDING
    )
    queue_result = await db.execute(queue_stmt)
    queue_size = float(queue_result.scalar() or 0)

    return DashboardData(
        job_success_rate=round(job_success_rate, 2),
        avg_execution_time=round(avg_execution_time, 2),
        browser_pool_utilization=round(browser_pool_utilization, 2),
        queue_size=round(queue_size, 2)
    )
