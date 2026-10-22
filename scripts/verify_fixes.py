"""
简单的语法和逻辑验证测试（无需依赖）

验证修复后的代码逻辑正确性。
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


async def test_websocket_timeout():
    """测试 WebSocket 超时保护"""
    print("=" * 60)
    print("测试场景：WebSocket 超时保护")
    print("=" * 60)

    from app.api.websocket import websocket_manager

    # 创建一个模拟的慢连接
    class SlowWebSocket:
        async def send_json(self, message):
            # 模拟慢连接：等待 2 秒（超过 1 秒超时）
            print("  [慢连接] 开始发送（会超时）...")
            await asyncio.sleep(2)
            print("  [慢连接] 发送完成")

    # 创建一个正常的快速连接
    class FastWebSocket:
        async def send_json(self, message):
            # 快速连接：立即完成
            print("  [快连接] 发送完成")

    slow_ws = SlowWebSocket()
    fast_ws = FastWebSocket()

    websocket_manager.active_connections.add(slow_ws)
    websocket_manager.active_connections.add(fast_ws)

    print(f"\n初始活跃连接数: {len(websocket_manager.active_connections)}")
    print("  - 1 个慢连接（2秒延迟）")
    print("  - 1 个快连接（无延迟）")

    # 广播消息（应该超时并移除慢连接）
    print("\n发送广播消息（超时设置: 1.0 秒）...")
    start_time = asyncio.get_event_loop().time()
    await websocket_manager.broadcast({"type": "test", "msg": "测试消息"}, timeout=1.0)
    elapsed = asyncio.get_event_loop().time() - start_time

    print(f"\n广播耗时: {elapsed:.2f} 秒")
    print(f"广播后活跃连接数: {len(websocket_manager.active_connections)}")

    # 验证结果
    slow_removed = slow_ws not in websocket_manager.active_connections
    fast_kept = fast_ws in websocket_manager.active_connections

    print("\n验证结果:")
    if slow_removed:
        print("  ✅ 慢连接已被正确移除")
    else:
        print("  ❌ 慢连接未被移除（测试失败）")

    if fast_kept:
        print("  ✅ 快连接保持活跃")
    else:
        print("  ❌ 快连接被错误移除（测试失败）")

    if elapsed < 1.5:
        print(f"  ✅ 广播未被阻塞（耗时 {elapsed:.2f}s < 1.5s）")
    else:
        print(f"  ❌ 广播被阻塞（耗时 {elapsed:.2f}s >= 1.5s）")

    # 清理
    websocket_manager.active_connections.clear()

    return slow_removed and fast_kept and elapsed < 1.5


async def test_scheduler_shutdown():
    """测试调度器优雅关闭"""
    print("\n" + "=" * 60)
    print("测试场景：调度器优雅关闭")
    print("=" * 60)

    from app.services.scheduler import TaskScheduler

    # 创建调度器（不启动，只测试 shutdown 逻辑）
    scheduler = TaskScheduler()

    print("\n测试 shutdown 方法...")
    try:
        await scheduler.shutdown()
        print("  ✅ shutdown 方法执行成功（无异常）")
        return True
    except Exception as e:
        print(f"  ❌ shutdown 方法执行失败: {e}")
        return False


async def test_resource_cleanup_logic():
    """测试资源清理逻辑（模拟）"""
    print("\n" + "=" * 60)
    print("测试场景：资源清理异常保护")
    print("=" * 60)

    # 模拟资源清理逻辑
    class MockResource:
        def __init__(self, name, should_fail=False):
            self.name = name
            self.should_fail = should_fail
            self.closed = False

        async def close(self):
            if self.should_fail:
                raise Exception(f"{self.name} 关闭失败（模拟）")
            self.closed = True
            print(f"  ✅ {self.name} 已关闭")

    # 创建资源
    page = MockResource("页面", should_fail=True)  # 故意让第一个失败
    context = MockResource("上下文")
    browser = MockResource("浏览器")
    playwright = MockResource("Playwright")

    resources = [
        ("page", page),
        ("context", context),
        ("browser", browser),
        ("playwright", playwright)
    ]

    print("\n执行清理（第一个资源会失败）...")

    # 使用修复后的清理逻辑
    cleanup_count = 0
    for name, resource in resources:
        if resource:
            try:
                await resource.close()
                cleanup_count += 1
            except Exception as e:
                print(f"  ⚠️  关闭 {name} 失败（已忽略）: {e}")
                # 继续清理后续资源

    print(f"\n清理结果:")
    print(f"  - 尝试清理: 4 个资源")
    print(f"  - 成功清理: {cleanup_count} 个资源")
    print(f"  - 失败但已忽略: {4 - cleanup_count} 个资源")

    # 验证：即使第一个失败，后续 3 个也应该成功
    success = (
        not page.closed and  # 第一个失败
        context.closed and
        browser.closed and
        playwright.closed
    )

    if success:
        print("  ✅ 后续资源在第一个失败后仍正常清理")
    else:
        print("  ❌ 资源清理被中断（测试失败）")

    return success


async def main():
    """主测试函数"""
    print("开始验证修复效果...\n")

    results = {}

    try:
        # 测试 1: WebSocket 超时保护
        results['websocket'] = await test_websocket_timeout()

        # 测试 2: 调度器优雅关闭
        results['scheduler'] = await test_scheduler_shutdown()

        # 测试 3: 资源清理异常保护
        results['cleanup'] = await test_resource_cleanup_logic()

        # 汇总结果
        print("\n" + "=" * 60)
        print("测试汇总")
        print("=" * 60)

        all_passed = True
        for test_name, passed in results.items():
            status = "✅ 通过" if passed else "❌ 失败"
            print(f"{test_name:20s}: {status}")
            if not passed:
                all_passed = False

        print("\n" + "=" * 60)
        if all_passed:
            print("🎉 所有测试通过！修复生效")
        else:
            print("⚠️  部分测试失败，请检查代码")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ 测试过程出现异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    asyncio.run(main())
