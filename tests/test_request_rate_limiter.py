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
