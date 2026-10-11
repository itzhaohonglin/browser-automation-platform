"""
限流管理 API

提供限流配置和状态查询接口。
"""

from typing import Optional
from fastapi import APIRouter, Query

from app.services.rate_limiter import rate_limiter

router = APIRouter(prefix="/api/rate-limit", tags=["限流管理"])


@router.get("/status")
async def get_rate_limit_status(
    config_id: Optional[int] = Query(None, description="配置ID（可选，获取特定配置的限流状态）")
):
    """
    获取限流状态

    Args:
        config_id: 配置ID（可选）

    Returns:
        限流状态信息
    """
    status = await rate_limiter.get_status(config_id)
    return {
        "success": True,
        "data": status
    }


@router.post("/reset")
async def reset_rate_limit(
    config_id: Optional[int] = Query(None, description="配置ID（可选，重置特定配置的限流计数器）")
):
    """
    重置限流计数器

    Args:
        config_id: 配置ID（可选，不传则重置所有）

    Returns:
        操作结果
    """
    await rate_limiter.reset(config_id)

    message = f"已重置配置 {config_id} 的限流计数器" if config_id else "已重置所有限流计数器"

    return {
        "success": True,
        "message": message
    }


@router.get("/wait-time")
async def get_wait_time(
    config_id: Optional[int] = Query(None, description="配置ID（可选）")
):
    """
    获取需要等待的时间

    Args:
        config_id: 配置ID（可选）

    Returns:
        需要等待的秒数
    """
    wait_seconds = await rate_limiter.get_wait_time(config_id)

    return {
        "success": True,
        "data": {
            "wait_seconds": wait_seconds,
            "wait_minutes": round(wait_seconds / 60, 2),
            "can_execute_now": wait_seconds == 0
        }
    }


@router.get("/config")
async def get_rate_limit_config():
    """
    获取限流配置

    Returns:
        限流配置信息
    """
    return {
        "success": True,
        "data": {
            "enabled": rate_limiter.enabled,
            "window_minutes": rate_limiter.window_minutes,
            "max_tasks": rate_limiter.max_tasks,
            "per_config": rate_limiter.per_config,
            "description": {
                "enabled": "是否启用限流",
                "window_minutes": "时间窗口（分钟）",
                "max_tasks": f"在 {rate_limiter.window_minutes} 分钟内最多执行 {rate_limiter.max_tasks} 个任务",
                "per_config": "是否按配置ID分别限流（True=每个配置独立计数，False=全局统一计数）"
            }
        }
    }
