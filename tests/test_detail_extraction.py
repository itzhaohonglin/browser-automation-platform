import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.executor import PlaywrightExecutor


@pytest.mark.asyncio
async def test_extract_detail_data_with_iframe():
    """测试详情提取 - iframe场景"""
    executor = PlaywrightExecutor()

    # Mock页面和定位器
    main_page = MagicMock()
    detail_button = AsyncMock()
    detail_iframe_element = AsyncMock()
    detail_frame = MagicMock()

    # 模拟点击详情按钮
    detail_button.click = AsyncMock()

    # 模拟等待iframe出现 - 使用MagicMock的spec可以避免链式调用问题
    main_page.wait_for_selector = AsyncMock(return_value=detail_iframe_element)

    # 模拟获取iframe的content_frame
    detail_iframe_element.content_frame = AsyncMock(return_value=detail_frame)

    # 模拟等待详情内容加载
    detail_frame.wait_for_selector = AsyncMock()

    # 模拟提取详情字段 - 关键：这里必须返回字典
    detail_frame.evaluate = AsyncMock(return_value={
        "产品名称": "测试产品", "型号规格": "10ml"
    })

    # 模拟keyboard对象
    mock_keyboard = MagicMock()
    mock_keyboard.press = AsyncMock()
    detail_frame.keyboard = mock_keyboard

    detail_config = {
        "detail_iframe_selector": "iframe#detailFrame",
        "wait_selector": ".detail-table",
        "close_method": "escape",
        "fields": [
            {"name": "产品名称", "selector": "#productName", "attr": "text"},
            {"name": "型号规格", "selector": "#spec", "attr": "text"}
        ],
        "timeout": {
            "iframe_load": 10000,
            "wait_selector": 5000
        }
    }

    # 执行测试
    detail_data, status, error = await executor._extract_detail_data(
        main_page, detail_button, detail_config, 0
    )

    # 验证
    assert status == "success"
    assert error is None
    assert "产品名称" in detail_data
    assert detail_data["产品名称"] == "测试产品"
    detail_button.click.assert_called_once()


@pytest.mark.asyncio
async def test_extract_detail_with_retry_success_on_second_attempt():
    """测试详情提取重试 - 第2次成功"""
    executor = PlaywrightExecutor()

    main_page = AsyncMock()
    detail_button = AsyncMock()

    detail_config = {
        "detail_iframe_selector": None,
        "wait_selector": ".detail-content",
        "close_method": "escape",
        "fields": [{"name": "field1", "selector": "#f1", "attr": "text"}],
        "retry": {
            "max_attempts": 3,
            "delay_seconds": 0.1
        }
    }

    # 模拟第1次失败，第2次成功
    call_count = 0
    async def mock_extract(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise Exception("临时错误")
        return {"field1": "value1"}, "success", None

    executor._extract_detail_data = mock_extract

    # 执行测试
    detail_data, status, error = await executor._extract_detail_with_retry(
        main_page, detail_button, detail_config, 0
    )

    # 验证
    assert status == "success"
    assert call_count == 2
    assert detail_data["field1"] == "value1"


@pytest.mark.asyncio
async def test_extract_detail_with_retry_all_failed():
    """测试详情提取重试 - 全部失败"""
    executor = PlaywrightExecutor()

    main_page = AsyncMock()
    detail_button = AsyncMock()

    detail_config = {
        "retry": {
            "max_attempts": 3,
            "delay_seconds": 0.1
        },
        "fields": []
    }

    # 模拟始终失败
    async def mock_extract(*args, **kwargs):
        raise Exception("持续错误")

    executor._extract_detail_data = mock_extract

    # 执行测试
    detail_data, status, error = await executor._extract_detail_with_retry(
        main_page, detail_button, detail_config, 0
    )

    # 验证
    assert status == "failed"
    assert "持续错误" in error
    assert "已重试3次" in error
