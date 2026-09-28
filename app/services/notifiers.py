import logging
import aiohttp
import smtplib
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailNotifier:
    """邮件通知"""

    async def send(self, message: str):
        """发送邮件"""
        if not settings.ALERT_EMAIL_FROM or not settings.ALERT_EMAIL_TO:
            logger.warning("邮件配置未设置，跳过发送")
            return

        msg = MIMEText(message, 'plain', 'utf-8')
        msg['Subject'] = '【告警】浏览器自动化平台'
        msg['From'] = settings.ALERT_EMAIL_FROM
        msg['To'] = settings.ALERT_EMAIL_TO

        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            logger.info("邮件通知发送成功")
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            raise

class DingTalkNotifier:
    """钉钉机器人通知"""

    async def send(self, message: str):
        """发送钉钉消息"""
        if not settings.DINGTALK_WEBHOOK_URL:
            logger.warning("钉钉 Webhook 未配置，跳过发送")
            return

        payload = {
            "msgtype": "text",
            "text": {
                "content": f"【告警】\n{message}"
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.DINGTALK_WEBHOOK_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"钉钉通知发送失败: {error_text}")
            logger.info("钉钉通知发送成功")
        except Exception as e:
            logger.error(f"钉钉通知失败: {e}")
            raise

class WeComNotifier:
    """企业微信机器人通知"""

    async def send(self, message: str):
        """发送企业微信消息"""
        if not settings.WECOM_WEBHOOK_URL:
            logger.warning("企业微信 Webhook 未配置，跳过发送")
            return

        payload = {
            "msgtype": "text",
            "text": {
                "content": f"【告警】\n{message}"
            }
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.WECOM_WEBHOOK_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"企业微信通知发送失败: {error_text}")
            logger.info("企业微信通知发送成功")
        except Exception as e:
            logger.error(f"企业微信通知失败: {e}")
            raise
