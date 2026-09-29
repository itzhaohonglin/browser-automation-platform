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


@pytest.mark.asyncio
async def test_extract_list_with_details():
    """测试列表+详情联合提取"""
    executor = PlaywrightExecutor()

    page = AsyncMock()

    fields_mapping = {
        "list_selector": "#gridlist tbody tr",
        "fields": [
            {"name": "产品名称", "selector": "td:nth-child(1)", "attr": "text"},
            {"name": "注册证号", "selector": "td:nth-child(2)", "attr": "text"}
        ]
    }

    detail_config = {
        "enabled": True,
        "detail_button_selector": "td:nth-child(3) a",
        "wait_selector": ".detail-content",
        "close_method": "escape",
        "fields": [
            {"name": "详细规格", "selector": "#spec", "attr": "text"}
        ],
        "retry": {
            "max_attempts": 2,
            "delay_seconds": 0.1
        }
    }

    # Mock列表数据提取
    async def mock_extract_page_data(p, fm):
        return [
            {"产品名称": "产品A", "注册证号": "ABC123"},
            {"产品名称": "产品B", "注册证号": "DEF456"}
        ]

    executor._extract_page_data = mock_extract_page_data

    # Mock行定位器
    row_locator = AsyncMock()
    row_locator.count = AsyncMock(return_value=2)

    # Mock第1行
    row1 = AsyncMock()
    button1 = AsyncMock()
    button1.count = AsyncMock(return_value=1)
    row1.locator = MagicMock(return_value=button1)

    # Mock第2行
    row2 = AsyncMock()
    button2 = AsyncMock()
    button2.count = AsyncMock(return_value=1)
    row2.locator = MagicMock(return_value=button2)

    # Mock nth方法
    def mock_nth(index):
        return row1 if index == 0 else row2

    row_locator.nth = mock_nth
    page.locator = MagicMock(return_value=row_locator)

    # Mock详情提取
    call_count = 0
    async def mock_extract_detail_with_retry(mp, btn, cfg, idx):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return {"详细规格": "规格A"}, "success", None
        else:
            return {"详细规格": "规格B"}, "success", None

    executor._extract_detail_with_retry = mock_extract_detail_with_retry

    # Mock WebSocket
    executor.ws_manager = None

    # 执行测试
    result = await executor._extract_list_with_details(
        page, fields_mapping, detail_config, job_id=1
    )

    # 验证
    assert len(result) == 2
    assert result[0]["list_data"]["产品名称"] == "产品A"
    assert result[0]["detail_data"]["详细规格"] == "规格A"
    assert result[0]["detail_status"] == "success"
    assert result[1]["list_data"]["产品名称"] == "产品B"
    assert result[1]["detail_data"]["详细规格"] == "规格B"


@pytest.mark.asyncio
async def test_extract_list_with_details_paginated():
    """测试分页+详情提取"""
    executor = PlaywrightExecutor()

    page = AsyncMock()

    config = MagicMock()
    config.fields_mapping = {
        "list_selector": "#gridlist tbody tr",
        "fields": [{"name": "name", "selector": "td", "attr": "text"}],
        "detail_config": {
            "enabled": True,
            "detail_button_selector": "a",
            "wait_selector": ".detail",
            "fields": [{"name": "detail", "selector": "div", "attr": "text"}],
            "retry": {"max_attempts": 2, "delay_seconds": 0.1}
        }
    }
    config.pagination_selector = "#next"
    config.max_pages = 2
    config.wait_selector = "#gridlist"

    # Mock单页提取（每页返回2条数据）
    page_call_count = 0
    async def mock_extract_list_with_details(p, fm, dc, jid):
        nonlocal page_call_count
        page_call_count += 1
        return [
            {"list_data": {"name": f"Page{page_call_count}-Item1"},
             "detail_data": {"detail": "D1"}, "detail_status": "success"},
            {"list_data": {"name": f"Page{page_call_count}-Item2"},
             "detail_data": {"detail": "D2"}, "detail_status": "success"}
        ]

    executor._extract_list_with_details = mock_extract_list_with_details

    # Mock _load_timeouts
    executor._load_timeouts = lambda cfg: {
        'click': 10000,
        'wait_selector': 15000
    }

    # Mock翻页按钮
    next_button = AsyncMock()
    next_button.count = AsyncMock(side_effect=[1, 0])  # 第1页有下一页，第2页没有
    next_button.is_disabled = AsyncMock(return_value=False)
    next_button.click = AsyncMock()
    page.locator = MagicMock(return_value=next_button)
    page.wait_for_selector = AsyncMock()

    # Mock WebSocket
    executor.ws_manager = None

    # 执行测试
    all_items, page_count, summary = await executor._extract_list_with_details_paginated(
        page, config, job_id=1
    )

    # 验证
    assert len(all_items) == 4  # 2页 x 2条
    assert page_count == 2
    assert summary["total_items"] == 4
    assert summary["detail_success"] == 4
    assert summary["detail_failed"] == 0
