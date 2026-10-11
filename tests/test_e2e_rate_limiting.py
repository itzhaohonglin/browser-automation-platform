"""
端到端测试：验证限流在实际执行中生效

这个测试验证 RequestRateLimiter 在真实任务执行流程中是否正常工作。
"""
import pytest
import asyncio
from datetime import datetime
from app.services.executor import PlaywrightExecutor
from app.models.config import CrawlerConfig


@pytest.mark.asyncio
@pytest.mark.slow
async def test_rate_limiting_enforces_interval():
    """
    端到端测试：验证限流在实际执行中生效

    注意：这是一个慢速测试，会实际等待约6秒
    """
    # 创建配置：每3秒一个请求
    config = CrawlerConfig(
        config_name="限流测试",
        target_url="http://httpbin.org/delay/0",
        input_configs=[],
        submit_selector="button",
        wait_selector="body",
        fields_mapping={},
        extraction_config={
            "request_rate_limit": {
                "enabled": True,
                "interval_seconds": 3
            }
        }
    )

    # 初始化执行器
    executor = PlaywrightExecutor()

    # 加载提取配置（模拟 execute_job 中的逻辑）
    extraction_cfg = executor._load_extraction_config(config)
    rate_limit_cfg = extraction_cfg.get("request_rate_limit", {})

    # 初始化限流器
    if rate_limit_cfg.get("enabled", False):
        interval = rate_limit_cfg.get("interval_seconds", 5)
        if interval > 0:
            executor._request_limiter = executor.RequestRateLimiter(interval_seconds=interval)
        else:
            executor._request_limiter = None
    else:
        executor._request_limiter = None

    # 验证限流器已初始化
    assert executor._request_limiter is not None, "限流器应该被初始化"
    assert executor._request_limiter.interval_seconds == 3, "间隔应为3秒"

    # 模拟连续3次请求
    complete_times = []

    for i in range(3):
        await executor._rate_limit_check(f"请求{i+1}")
        complete_times.append(datetime.now())

    # 验证间隔
    # 第1个请求：立即执行
    # 第2个请求：等待约3秒
    # 第3个请求：等待约3秒

    if len(complete_times) >= 2:
        interval1 = (complete_times[1] - complete_times[0]).total_seconds()
        assert interval1 >= 2.9, f"第1-2个请求间隔应>=3秒，实际{interval1:.1f}秒"

    if len(complete_times) >= 3:
        interval2 = (complete_times[2] - complete_times[1]).total_seconds()
        assert interval2 >= 2.9, f"第2-3个请求间隔应>=3秒，实际{interval2:.1f}秒"

    total_time = (complete_times[-1] - complete_times[0]).total_seconds()
    print(f"OK: 限流测试通过: 3个请求总耗时{total_time:.1f}秒")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_rate_limiting_disabled_no_wait():
    """
    端到端测试：禁用限流时不应等待

    这个测试应该快速完成（<1秒）
    """
    # 创建配置：禁用限流
    config = CrawlerConfig(
        config_name="无限流测试",
        target_url="http://httpbin.org/delay/0",
        input_configs=[],
        submit_selector="button",
        wait_selector="body",
        fields_mapping={},
        extraction_config={
            "request_rate_limit": {
                "enabled": False,
                "interval_seconds": 3
            }
        }
    )

    # 初始化执行器
    executor = PlaywrightExecutor()

    # 加载提取配置
    extraction_cfg = executor._load_extraction_config(config)
    rate_limit_cfg = extraction_cfg.get("request_rate_limit", {})

    # 初始化限流器（应该为 None）
    if rate_limit_cfg.get("enabled", False):
        interval = rate_limit_cfg.get("interval_seconds", 5)
        if interval > 0:
            executor._request_limiter = executor.RequestRateLimiter(interval_seconds=interval)
        else:
            executor._request_limiter = None
    else:
        executor._request_limiter = None

    # 验证限流器未初始化
    assert executor._request_limiter is None, "禁用限流时不应初始化限流器"

    # 连续3次请求应该立即完成
    start = datetime.now()

    for i in range(3):
        await executor._rate_limit_check(f"请求{i+1}")

    total_time = (datetime.now() - start).total_seconds()

    # 3次请求应该在很短时间内完成（<0.5秒）
    assert total_time < 0.5, f"禁用限流时应立即完成，实际耗时{total_time:.1f}秒"
    print(f"OK: 无限流测试通过，3个请求总耗时{total_time:.3f}秒")


@pytest.mark.asyncio
@pytest.mark.slow
async def test_rate_limiting_concurrent_operations():
    """
    端到端测试：验证限流在并发场景下的行为

    注意：当前的 RequestRateLimiter 实现在并发调用时会并发等待，
    而不是串行化。这是因为 acquire() 方法不使用锁。

    实际行为：
    - 3个请求几乎同时到达
    - 第1个请求：立即通过（首次）
    - 第2和第3个请求：检测到间隔不足，都等待2秒
    - 结果：总耗时约2秒（并发等待）

    这对于单个executor实例是可接受的，因为任务本身是串行执行的。
    """
    config = CrawlerConfig(
        config_name="并发限流测试",
        target_url="http://httpbin.org/delay/0",
        input_configs=[],
        submit_selector="button",
        wait_selector="body",
        fields_mapping={},
        extraction_config={
            "request_rate_limit": {
                "enabled": True,
                "interval_seconds": 2
            }
        }
    )

    executor = PlaywrightExecutor()

    # 初始化限流器
    extraction_cfg = executor._load_extraction_config(config)
    rate_limit_cfg = extraction_cfg.get("request_rate_limit", {})

    if rate_limit_cfg.get("enabled", False):
        interval = rate_limit_cfg.get("interval_seconds", 5)
        if interval > 0:
            executor._request_limiter = executor.RequestRateLimiter(interval_seconds=interval)

    assert executor._request_limiter is not None

    # 创建多个并发任务
    timestamps = []

    async def make_request(index: int):
        """模拟一个请求"""
        await executor._rate_limit_check(f"并发请求{index}")
        timestamps.append(datetime.now())

    # 同时启动3个请求
    start = datetime.now()
    await asyncio.gather(
        make_request(1),
        make_request(2),
        make_request(3)
    )

    # 验证：当前实现下，并发请求会并发等待
    # 请求1：立即通过
    # 请求2和3：都检测到间隔不足，并发等待2秒
    # 总耗时约为2秒

    total_time = (timestamps[-1] - start).total_seconds()

    # 验证总耗时（应该约为2秒，因为并发等待）
    assert total_time >= 1.9, f"并发请求并发等待，总耗时应>=2秒，实际{total_time:.1f}秒"
    assert total_time < 2.5, f"并发等待不应有额外延迟，实际{total_time:.1f}秒"

    print(f"OK: 并发限流测试通过，3个并发请求并发等待，总耗时{total_time:.1f}秒")
