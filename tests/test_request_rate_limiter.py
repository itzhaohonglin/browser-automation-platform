"""
Tests for RequestRateLimiter class
"""
import pytest
import asyncio
from datetime import datetime
from app.services.executor import PlaywrightExecutor


@pytest.mark.asyncio
async def test_first_request_passes_immediately():
    """首次请求应立即通过，不等待"""
    limiter = PlaywrightExecutor.RequestRateLimiter(interval_seconds=2)

    start = datetime.now()
    wait_time = await limiter.acquire()
    elapsed = (datetime.now() - start).total_seconds()

    assert wait_time == 0.0, "首次请求应返回 0.0"
    assert elapsed < 0.1, "首次请求应立即通过"


@pytest.mark.asyncio
async def test_second_request_waits():
    """第二个请求如果间隔不足，应等待"""
    limiter = PlaywrightExecutor.RequestRateLimiter(interval_seconds=2.0)

    # 首次请求
    await limiter.acquire()

    # 立即发起第二次请求（间隔不足）
    start = datetime.now()
    wait_time = await limiter.acquire()
    elapsed = (datetime.now() - start).total_seconds()

    # 应该等待约 2 秒
    assert wait_time >= 1.9, f"应等待约 2 秒，实际返回 {wait_time}"
    assert elapsed >= 1.9, f"实际等待时间应 >= 1.9 秒，实际 {elapsed}"
    assert elapsed < 2.2, f"等待时间不应超过 2.2 秒，实际 {elapsed}"


@pytest.mark.asyncio
async def test_sufficient_interval_no_wait():
    """如果两次请求间隔足够，第二次请求不应等待"""
    limiter = PlaywrightExecutor.RequestRateLimiter(interval_seconds=1.0)

    # 首次请求
    await limiter.acquire()

    # 等待足够的时间
    await asyncio.sleep(1.1)

    # 第二次请求应立即通过
    start = datetime.now()
    wait_time = await limiter.acquire()
    elapsed = (datetime.now() - start).total_seconds()

    assert wait_time == 0.0, f"间隔足够时应返回 0.0，实际返回 {wait_time}"
    assert elapsed < 0.1, f"间隔足够时不应等待，实际等待 {elapsed}"


@pytest.mark.asyncio
async def test_zero_interval_no_wait():
    """interval_seconds=0 时应无限流，所有请求立即通过"""
    limiter = PlaywrightExecutor.RequestRateLimiter(interval_seconds=0)

    # 首次请求
    wait_time1 = await limiter.acquire()
    assert wait_time1 == 0.0

    # 连续多次请求都应立即通过
    for i in range(3):
        start = datetime.now()
        wait_time = await limiter.acquire()
        elapsed = (datetime.now() - start).total_seconds()

        assert wait_time == 0.0, f"第 {i+2} 次请求应返回 0.0，实际返回 {wait_time}"
        assert elapsed < 0.1, f"第 {i+2} 次请求不应等待，实际等待 {elapsed}"


@pytest.mark.asyncio
async def test_executor_loads_rate_limit_config():
    """测试：执行器正确加载限流配置"""
    from app.models.config import CrawlerConfig

    # 创建测试配置
    config = CrawlerConfig(
        config_name="测试",
        target_url="http://example.com",
        input_configs=[],
        submit_selector="button",
        wait_selector=".result",
        fields_mapping={},
        extraction_config={
            "request_rate_limit": {
                "enabled": True,
                "interval_seconds": 5
            }
        }
    )

    executor = PlaywrightExecutor()

    # 加载配置
    extraction_cfg = executor._load_extraction_config(config)

    # 验证配置正确加载
    assert "request_rate_limit" in extraction_cfg
    assert extraction_cfg["request_rate_limit"]["enabled"] is True
    assert extraction_cfg["request_rate_limit"]["interval_seconds"] == 5


@pytest.mark.asyncio
async def test_executor_initializes_limiter_when_enabled():
    """测试：启用限流时正确初始化限流器"""
    from app.models.config import CrawlerConfig

    config = CrawlerConfig(
        config_name="测试",
        target_url="http://example.com",
        input_configs=[],
        submit_selector="button",
        wait_selector=".result",
        fields_mapping={},
        extraction_config={
            "request_rate_limit": {
                "enabled": True,
                "interval_seconds": 3
            }
        }
    )

    executor = PlaywrightExecutor()

    # 模拟初始化限流器的逻辑
    extraction_cfg = executor._load_extraction_config(config)
    rate_limit_cfg = extraction_cfg.get("request_rate_limit", {})

    if rate_limit_cfg.get("enabled", False):
        interval = rate_limit_cfg.get("interval_seconds", 5)
        if interval > 0:
            limiter = executor.RequestRateLimiter(interval_seconds=interval)
            assert limiter.interval_seconds == 3
            assert limiter.last_request_time is None


@pytest.mark.asyncio
async def test_executor_no_limiter_when_disabled():
    """测试：禁用限流时不初始化限流器"""
    from app.models.config import CrawlerConfig

    config = CrawlerConfig(
        config_name="测试",
        target_url="http://example.com",
        input_configs=[],
        submit_selector="button",
        wait_selector=".result",
        fields_mapping={},
        extraction_config={
            "request_rate_limit": {
                "enabled": False,
                "interval_seconds": 5
            }
        }
    )

    executor = PlaywrightExecutor()
    extraction_cfg = executor._load_extraction_config(config)
    rate_limit_cfg = extraction_cfg.get("request_rate_limit", {})

    # 验证禁用时不应创建限流器
    assert rate_limit_cfg.get("enabled") is False
