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
