import logging
from typing import Dict, List
from pathlib import Path

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.core.config import settings
from app.models.job import JobQueue, JobStatus
from app.services.executor import PlaywrightExecutor
from app.services.auth_manager import auth_manager
from app.api.websocket import websocket_manager

# 配置日志
logger = logging.getLogger(__name__)

# 创建路由器
router = APIRouter()

# ============ 登录态管理接口 ============

@router.post("/auth/start", tags=["登录态管理"])
async def start_auth_update(
    profile: str = Query(..., description="登录态标识，如 taobao、jd、test"),
    login_url: str = Query(
        "https://www.baidu.com",
        description="登录页面URL（测试时可使用默认值）"
    )
):
    """
    拉起有头浏览器，跳转到登录页面

    管理员在看板点击"更新登录态"时调用此接口。
    浏览器会自动打开并跳转到指定的登录页面。

    **使用流程：**
    1. 调用此接口，浏览器自动打开
    2. 手动在浏览器中完成登录（包括验证码）
    3. 登录成功后，调用 /auth/save 保存登录态
    """
    result = await auth_manager.start_login_session(profile, login_url)

    if result["status"] == "error":
        raise HTTPException(status_code=500, detail=result["message"])

    return result


@router.post("/auth/save", tags=["登录态管理"])
async def save_auth_state(
    profile: str = Query(..., description="登录态标识，如 taobao、jd、test")
):
    """
    保存当前浏览器的登录态到文件

    管理员在浏览器中完成登录后，在看板点击"确认已登录并保存"时调用此接口。
    登录态会保存到 `auth_files/auth_{profile}.json` 文件中。

    **注意：** 调用此接口前必须先调用 /auth/start 打开浏览器
    """
    result = await auth_manager.save_auth_state(profile)

    if result["status"] == "error":
        raise HTTPException(status_code=400, detail=result["message"])

    return result


@router.get("/auth/status", tags=["登录态管理"])
async def get_auth_status():
    """
    获取所有登录态的状态

    返回每个 profile 的登录态文件是否存在，以及当前活跃的登录会话。
    """
    auth_dir = Path(settings.AUTH_FILES_DIR)
    auth_files = []

    # 扫描 auth_files 目录
    if auth_dir.exists():
        for file in auth_dir.glob("auth_*.json"):
            profile_name = file.stem.replace("auth_", "")
            auth_files.append({
                "profile": profile_name,
                "file_path": str(file),
                "status": "saved"
            })

    # 获取活跃会话
    active_profiles = await auth_manager.get_active_profiles()

    return {
        "saved_profiles": auth_files,
        "active_sessions": active_profiles,
        "total_saved": len(auth_files),
        "total_active": len(active_profiles)
    }


@router.delete("/auth/session/{profile}", tags=["登录态管理"])
async def close_auth_session(profile: str):
    """
    关闭指定 profile 的活跃浏览器会话

    如果管理员不小心打开了浏览器但不想保存，可以调用此接口关闭。
    """
    if profile not in await auth_manager.get_active_profiles():
        raise HTTPException(status_code=404, detail=f"未找到 {profile} 的活跃会话")

    await auth_manager.close_session(profile)

    return {
        "status": "success",
        "message": f"{profile} 的浏览器会话已关闭",
        "profile": profile
    }


@router.delete("/auth/file/{profile}", tags=["登录态管理"])
async def delete_auth_file(profile: str):
    """
    删除指定 profile 的登录态文件

    用于清理过期或不需要的登录态。
    """
    auth_file = Path(settings.AUTH_FILES_DIR) / f"auth_{profile}.json"

    if not auth_file.exists():
        raise HTTPException(status_code=404, detail=f"未找到 {profile} 的登录态文件")

    try:
        auth_file.unlink()
        return {
            "status": "success",
            "message": f"{profile} 的登录态文件已删除",
            "profile": profile
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"删除文件失败: {str(e)}")


# ============ 任务执行接口 ============

@router.post("/task/run", tags=["任务执行"])
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
    executor = PlaywrightExecutor(ws_manager=websocket_manager)

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
