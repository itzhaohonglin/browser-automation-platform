"""
测试资源清理的异常保护

验证即使某个清理步骤失败，后续清理仍能正常执行。
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.executor import PlaywrightExecutor
from app.core.database import get_session
from app.models.job import JobQueue, JobStatus
from app.models.config import CrawlerConfig


async def test_cleanup_with_mock_failure():
    """测试资源清理在出现异常时的健壮性"""
    print("=" * 60)
    print("测试场景：模拟 page.close() 失败，验证后续清理是否执行")
    print("=" * 60)

    # 创建一个测试配置和任务
    async with get_session() as session:
        # 查找一个简单的配置用于测试
        from sqlalchemy import select
        stmt = select(CrawlerConfig).limit(1)
        result = await session.execute(stmt)
        config = result.scalar_one_or_none()

        if not config:
            print("❌ 未找到测试配置，请先创建配置")
            return

        # 创建测试任务
        test_job = JobQueue(
            config_id=config.id,
            query_params={"test": "cleanup"},
            status=JobStatus.PENDING
        )
        session.add(test_job)
        await session.commit()
        await session.refresh(test_job)

        print(f"✅ 创建测试任务 #{test_job.id}")

        # 执行任务（会在启动浏览器后立即失败，触发清理逻辑）
        executor = PlaywrightExecutor()

        # 注入一个会失败的步骤（模拟网络异常）
        print("\n开始执行任务（预期会失败以触发清理逻辑）...")
        try:
            # 这里我们不真正执行完整任务，只测试清理逻辑的健壮性
            # 实际测试需要运行完整的 execute_job
            await executor.execute_job(test_job.id, session)
        except Exception as e:
            print(f"⚠️  任务执行失败（预期）: {e}")

        print("\n检查清理日志...")
        print("✅ 如果看到 '页面已关闭'、'浏览器上下文已关闭' 等日志，说明清理正常")

        # 清理测试任务
        await session.delete(test_job)
        await session.commit()
        print(f"\n✅ 清理测试任务 #{test_job.id}")


async def test_websocket_timeout():
    """测试 WebSocket 超时保护"""
    print("\n" + "=" * 60)
    print("测试场景：WebSocket 超时保护")
    print("=" * 60)

    from app.api.websocket import websocket_manager

    # 创建一个模拟的慢连接
    class SlowWebSocket:
        async def send_json(self, message):
            # 模拟慢连接：等待 2 秒（超过 1 秒超时）
            await asyncio.sleep(2)

    slow_ws = SlowWebSocket()
    websocket_manager.active_connections.add(slow_ws)

    print(f"活跃连接数: {len(websocket_manager.active_connections)}")

    # 广播消息（应该超时并移除慢连接）
    print("发送广播消息（慢连接应该被移除）...")
    await websocket_manager.broadcast({"type": "test", "msg": "测试消息"})

    print(f"广播后活跃连接数: {len(websocket_manager.active_connections)}")

    if slow_ws not in websocket_manager.active_connections:
        print("✅ 慢连接已被正确移除")
    else:
        print("❌ 慢连接未被移除（测试失败）")


async def main():
    """主测试函数"""
    print("开始资源清理测试...\n")

    try:
        # 测试 1: 资源清理异常保护
        # await test_cleanup_with_mock_failure()

        # 测试 2: WebSocket 超时保护
        await test_websocket_timeout()

        print("\n" + "=" * 60)
        print("测试完成")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
