import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.notifiers import EmailNotifier, DingTalkNotifier, WeComNotifier

@pytest.mark.asyncio
async def test_email_notifier_success():
    """测试邮件发送成功"""
    with patch('app.services.notifiers.settings') as mock_settings:
        mock_settings.ALERT_EMAIL_FROM = "alert@example.com"
        mock_settings.ALERT_EMAIL_TO = "admin@example.com"
        mock_settings.SMTP_HOST = "smtp.example.com"
        mock_settings.SMTP_PORT = 587
        mock_settings.SMTP_USE_TLS = True
        mock_settings.SMTP_USER = "user"
        mock_settings.SMTP_PASSWORD = "password"

        with patch('smtplib.SMTP') as mock_smtp:
            mock_server = MagicMock()
            mock_smtp.return_value.__enter__.return_value = mock_server

            notifier = EmailNotifier()
            await notifier.send("Test message")

            mock_server.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_dingtalk_notifier_success():
    """测试钉钉通知成功"""
    with patch('app.services.notifiers.settings') as mock_settings:
        mock_settings.DINGTALK_WEBHOOK_URL = "https://oapi.dingtalk.com/robot/send?access_token=test"

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="OK")

            mock_post = MagicMock()
            mock_post.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_post)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            notifier = DingTalkNotifier()
            await notifier.send("Test message")

            mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_wecom_notifier_success():
    """测试企业微信通知成功"""
    with patch('app.services.notifiers.settings') as mock_settings:
        mock_settings.WECOM_WEBHOOK_URL = "https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=test"

        with patch('aiohttp.ClientSession') as mock_session_class:
            mock_response = AsyncMock()
            mock_response.status = 200
            mock_response.text = AsyncMock(return_value="OK")

            mock_post = MagicMock()
            mock_post.__aenter__ = AsyncMock(return_value=mock_response)
            mock_post.__aexit__ = AsyncMock(return_value=None)

            mock_session = MagicMock()
            mock_session.post = MagicMock(return_value=mock_post)
            mock_session.__aenter__ = AsyncMock(return_value=mock_session)
            mock_session.__aexit__ = AsyncMock(return_value=None)

            mock_session_class.return_value = mock_session

            notifier = WeComNotifier()
            await notifier.send("Test message")

            mock_session.post.assert_called_once()

@pytest.mark.asyncio
async def test_email_notifier_skip_when_not_configured():
    """测试未配置时跳过发送"""
    with patch('app.services.notifiers.settings') as mock_settings:
        mock_settings.ALERT_EMAIL_FROM = None
        mock_settings.ALERT_EMAIL_TO = None

        notifier = EmailNotifier()
        # 应该不会抛出异常，只是跳过发送
        await notifier.send("Test message")

@pytest.mark.asyncio
async def test_dingtalk_notifier_skip_when_not_configured():
    """测试未配置钉钉时跳过发送"""
    with patch('app.services.notifiers.settings') as mock_settings:
        mock_settings.DINGTALK_WEBHOOK_URL = None

        notifier = DingTalkNotifier()
        # 应该不会抛出异常，只是跳过发送
        await notifier.send("Test message")

@pytest.mark.asyncio
async def test_wecom_notifier_skip_when_not_configured():
    """测试未配置企业微信时跳过发送"""
    with patch('app.services.notifiers.settings') as mock_settings:
        mock_settings.WECOM_WEBHOOK_URL = None

        notifier = WeComNotifier()
        # 应该不会抛出异常，只是跳过发送
        await notifier.send("Test message")
