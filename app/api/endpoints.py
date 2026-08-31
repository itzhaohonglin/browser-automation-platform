from fastapi import APIRouter, HTTPException, Query
from app.services.auth_manager import auth_manager
from pathlib import Path
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["登录态管理"])


@router.post("/start")
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


@router.post("/save")
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


@router.get("/status")
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


@router.delete("/session/{profile}")
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


@router.delete("/file/{profile}")
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
