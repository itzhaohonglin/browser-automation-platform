import logging
from typing import Dict, List

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.job import JobQueue, JobStatus
from app.services.executor import PlaywrightExecutor

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter(tags=["任务执行"])


@router.post("/task/run")
async def run_tasks(
    config_id: int = Query(..., description="配置 ID"),
    limit: int = Query(1, description="执行任务数量", ge=1, le=10),
    db: AsyncSession = Depends(get_db)
) -> Dict:
    """
    手动触发执行指定配置的待处理任务

    用于测试和手动触发任务执行。

    Args:
        config_id: 配置 ID
        limit: 执行任务数量（1-10）
        db: 数据库 session

    Returns:
        执行结果摘要
    """
    logger.info(f"接收任务执行请求：config_id={config_id}, limit={limit}")

    # 1. 查询待处理任务
    stmt = select(JobQueue).where(
        JobQueue.config_id == config_id,
        JobQueue.status == JobStatus.PENDING
    ).limit(limit)

    result = await db.execute(stmt)
    jobs = result.scalars().all()

    if not jobs:
        raise HTTPException(status_code=404, detail="未找到待处理的任务")

    logger.info(f"找到 {len(jobs)} 个待处理任务")

    # 2. 创建执行器
    executor = PlaywrightExecutor()

    # 3. 串行执行任务
    results: List[Dict] = []
    for job in jobs:
        logger.info(f"开始执行任务 {job.id}")
        try:
            result = await executor.execute_job(job.id, db)
            results.append(result)
        except Exception as e:
            logger.error(f"任务 {job.id} 执行异常: {e}", exc_info=True)
            results.append({
                "job_id": job.id,
                "status": "error",
                "error": str(e)
            })

    # 4. 统计结果
    success_count = sum(1 for r in results if r.get("status") == "success")
    failed_count = len(results) - success_count

    logger.info(f"任务执行完成：成功 {success_count}，失败 {failed_count}")

    return {
        "status": "completed",
        "config_id": config_id,
        "total_jobs": len(results),
        "success_count": success_count,
        "failed_count": failed_count,
        "results": results
    }
