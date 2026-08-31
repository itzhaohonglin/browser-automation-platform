from playwright.async_api import async_playwright, Browser, BrowserContext, Playwright
from pathlib import Path
from typing import Optional, Dict
import asyncio
import sys
from app.core.config import settings

# Windows 平台事件循环策略修复
if sys.platform == "win32":
    # 确保使用 ProactorEventLoop
    if not isinstance(asyncio.get_event_loop_policy(), asyncio.WindowsProactorEventLoopPolicy):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())


class AuthManager:
    """登录态管理器 - 负责拉起浏览器和保存登录态"""

    def __init__(self):
        # 存储活跃的浏览器会话 {profile: {"playwright": p, "browser": b, "context": ctx}}
        self.active_sessions: Dict[str, Dict] = {}

    async def start_login_session(self, profile: str, login_url: str) -> dict:
        """
        拉起有头浏览器，跳转到登录页面

        Args:
            profile: 登录态标识（如 taobao, jd, test）
            login_url: 登录页面URL

        Returns:
            {"status": "success", "message": "浏览器已打开"}
        """
        # 如果该 profile 已有活跃会话，先关闭旧的
        if profile in self.active_sessions:
            await self.close_session(profile)

        try:
            # 启动 Playwright
            playwright = await async_playwright().start()

            # 启动有头浏览器（headless=False）
            browser = await playwright.chromium.launch(
                headless=False,
                args=['--start-maximized']  # 最大化窗口
            )

            # 创建新的浏览器上下文
            context = await browser.new_context(
                viewport=None  # 使用窗口默认大小
            )

            # 打开新页面并导航到登录URL
            page = await context.new_page()
            await page.goto(login_url, wait_until="domcontentloaded", timeout=30000)

            # 保存会话信息
            self.active_sessions[profile] = {
                "playwright": playwright,
                "browser": browser,
                "context": context,
                "page": page,
                "login_url": login_url
            }

            return {
                "status": "success",
                "message": f"浏览器已打开，请在窗口中完成登录操作",
                "profile": profile,
                "login_url": login_url
            }

        except Exception as e:
            # 如果启动失败，清理资源
            if profile in self.active_sessions:
                await self.close_session(profile)

            return {
                "status": "error",
                "message": f"启动浏览器失败: {str(e)}",
                "profile": profile
            }

    async def save_auth_state(self, profile: str) -> dict:
        """
        保存当前浏览器的登录态到文件

        Args:
            profile: 登录态标识

        Returns:
            {"status": "success", "file_path": "auth_files/auth_xxx.json"}
        """
        if profile not in self.active_sessions:
            return {
                "status": "error",
                "message": f"未找到 {profile} 的活跃登录会话，请先调用 /auth/start"
            }

        try:
            session = self.active_sessions[profile]
            context: BrowserContext = session["context"]

            # 确保 auth_files 目录存在
            auth_dir = Path(settings.AUTH_FILES_DIR)
            auth_dir.mkdir(exist_ok=True)

            # 保存登录态到文件
            auth_file_path = auth_dir / f"auth_{profile}.json"
            await context.storage_state(path=str(auth_file_path))

            # 保存成功后关闭浏览器
            await self.close_session(profile)

            return {
                "status": "success",
                "message": f"{profile} 登录态已成功保存",
                "file_path": str(auth_file_path),
                "profile": profile
            }

        except Exception as e:
            return {
                "status": "error",
                "message": f"保存登录态失败: {str(e)}",
                "profile": profile
            }

    async def close_session(self, profile: str):
        """关闭指定 profile 的浏览器会话"""
        if profile in self.active_sessions:
            session = self.active_sessions[profile]

            try:
                # 依次关闭浏览器和 Playwright
                if "browser" in session:
                    await session["browser"].close()
                if "playwright" in session:
                    await session["playwright"].stop()
            except Exception as e:
                print(f"关闭会话时出错: {e}")
            finally:
                # 从活跃会话中移除
                del self.active_sessions[profile]

    async def get_active_profiles(self) -> list:
        """获取当前所有活跃的登录会话"""
        return list(self.active_sessions.keys())

    async def close_all_sessions(self):
        """关闭所有活跃会话"""
        profiles = list(self.active_sessions.keys())
        for profile in profiles:
            await self.close_session(profile)


# 全局单例
auth_manager = AuthManager()
