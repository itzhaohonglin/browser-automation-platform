import pytest
from datetime import datetime, timedelta
from app.services.metrics_collector import metrics_collector

@pytest.mark.asyncio
async def test_record_metric():
    """测试记录指标"""
    await metrics_collector.record(
        "test_metric",
        100.5,
        labels={"test": "true"}
    )

    # 验证缓冲区有数据
    assert len(metrics_collector.buffer) > 0

@pytest.mark.asyncio
async def test_query_metric():
    """测试查询指标"""
    # 先定义时间范围
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)

    # 记录测试数据
    await metrics_collector.record("test_query", 50.0)
    await metrics_collector._flush()

    # 查询数据时使用更宽松的结束时间
    now = datetime.utcnow() + timedelta(seconds=1)

    results = await metrics_collector.query(
        "test_query",
        one_hour_ago,
        now
    )

    assert len(results) > 0
    assert results[0]["value"] == 50.0
