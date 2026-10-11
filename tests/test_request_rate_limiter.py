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
    config = {"enabled": True, "interval_seconds": 2}
    limiter = PlaywrightExecutor.RequestRateLimiter(config)

    start = datetime.now()
    await limiter.wait_if_needed()
    elapsed = (datetime.now() - start).total_seconds()

    assert elapsed < 0.1, "首次请求应立即通过"
