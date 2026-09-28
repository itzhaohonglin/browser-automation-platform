from fastapi import APIRouter, Query, Depends
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.metrics import MetricsTimeSeries
from app.models.job import JobQueue, JobStatus

router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/query")
async def query_metrics(
    metric_name: str = Query(..., description="指标名称"),
    start_time: datetime = Query(..., description="开始时间（ISO 8601 格式）"),
    end_time: datetime = Query(..., description="结束时间（ISO 8601 格式）"),
    aggregation: Optional[str] = Query(None, description="聚合方式：avg/sum/max/min"),
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    查询指标数据

    返回指定时间范围内的指标数据点，支持聚合计算。
    """
    # 查询指标数据
    stmt = select(MetricsTimeSeries).where(
        MetricsTimeSeries.metric_name == metric_name,
        MetricsTimeSeries.timestamp >= start_time,
        MetricsTimeSeries.timestamp <= end_time
    ).order_by(MetricsTimeSeries.timestamp.asc())

    result = await db.execute(stmt)
    metrics = result.scalars().all()

    # 构建数据点
    data_points = [
        {
            "timestamp": m.timestamp.isoformat(),
            "value": m.metric_value,
            "labels": m.labels
        }
        for m in metrics
    ]

    # 聚合计算
    aggregated_value = None
    if aggregation and data_points:
        values = [dp["value"] for dp in data_points]
        if aggregation == "avg":
            aggregated_value = sum(values) / len(values)
        elif aggregation == "sum":
            aggregated_value = sum(values)
        elif aggregation == "max":
            aggregated_value = max(values)
        elif aggregation == "min":
            aggregated_value = min(values)

    return {
        "metric_name": metric_name,
        "start_time": start_time.isoformat(),
        "end_time": end_time.isoformat(),
        "data_points": data_points,
        "aggregated_value": aggregated_value,
        "aggregation": aggregation
    }


@router.get("/dashboard")
async def get_dashboard_stats(
    db: AsyncSession = Depends(get_db)
) -> Dict[str, Any]:
    """
    获取仪表板统计数据

    返回系统总体运行指标：任务总数、成功率、平均执行时间等。
    """
    # 统计任务总数
    total_stmt = select(func.count(JobQueue.id))
    total_result = await db.execute(total_stmt)
    total_jobs = total_result.scalar() or 0

    # 统计成功任务数
    success_stmt = select(func.count(JobQueue.id)).where(
        JobQueue.status == JobStatus.SUCCESS
    )
    success_result = await db.execute(success_stmt)
    success_jobs = success_result.scalar() or 0

    # 计算成功率
    success_rate = (success_jobs / total_jobs * 100) if total_jobs > 0 else 0.0

    # 查询最近 1 小时的平均执行时间指标
    one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
    avg_time_stmt = select(func.avg(MetricsTimeSeries.metric_value)).where(
        MetricsTimeSeries.metric_name == "job_execution_time",
        MetricsTimeSeries.timestamp >= one_hour_ago
    )
    avg_time_result = await db.execute(avg_time_stmt)
    avg_execution_time = avg_time_result.scalar() or 0.0

    return {
        "total_jobs": total_jobs,
        "success_jobs": success_jobs,
        "failed_jobs": total_jobs - success_jobs,
        "success_rate": round(success_rate, 2),
        "avg_execution_time": round(avg_execution_time, 2)
    }
