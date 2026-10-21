"""
简化的事件循环关闭测试

直接测试核心修复：在关闭事件循环前调用 engine.dispose()
"""
import asyncio
import sys
import os
import io

# 设置 stdout 为 UTF-8 编码
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_with_dispose():
    """测试：使用 engine.dispose() 的版本（修复后）"""
    print("\n[测试 A] 使用 engine.dispose() 的版本（修复后）")
    print("-" * 50)

    import asyncio
    from app.core.database import async_engine, get_session
    from sqlalchemy import text

    async def run_query():
        """执行一个简单的数据库查询"""
        async with get_session() as session:
            result = await session.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"  ✓ 查询成功: {row}")
            return True

    async def cleanup():
        """清理资源"""
        print("  → 正在关闭数据库引擎...")
        await async_engine.dispose()
        print("  ✓ 数据库引擎已关闭")

    # 创建新事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        print("  → 执行数据库查询...")
        result = loop.run_until_complete(run_query())
        print("  ✓ 任务完成")
        return True
    except Exception as e:
        print(f"  ❌ 执行失败: {e}")
        return False
    finally:
        try:
            # 关键：在关闭事件循环前清理资源
            print("  → 开始清理...")
            loop.run_until_complete(cleanup())

            # 取消待处理任务
            pending = asyncio.all_tasks(loop)
            if pending:
                print(f"  → 取消 {len(pending)} 个待处理任务...")
                for task in pending:
                    task.cancel()
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception as e:
            print(f"  ⚠ 清理时出现异常: {e}")
        finally:
            print("  → 关闭事件循环...")
            loop.close()
            print("  ✓ 事件循环已关闭")


def test_without_dispose():
    """测试：不使用 engine.dispose() 的版本（修复前）"""
    print("\n[测试 B] 不使用 engine.dispose() 的版本（修复前）")
    print("-" * 50)

    import asyncio
    from app.core.database import get_session
    from sqlalchemy import text

    async def run_query():
        """执行一个简单的数据库查询"""
        async with get_session() as session:
            result = await session.execute(text("SELECT 1 as test"))
            row = result.fetchone()
            print(f"  ✓ 查询成功: {row}")
            return True

    # 创建新事件循环
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        print("  → 执行数据库查询...")
        result = loop.run_until_complete(run_query())
        print("  ✓ 任务完成")
        return True
    except Exception as e:
        print(f"  ❌ 执行失败: {e}")
        return False
    finally:
        try:
            # 注意：这里没有调用 engine.dispose()
            # 取消待处理任务
            pending = asyncio.all_tasks(loop)
            if pending:
                print(f"  → 取消 {len(pending)} 个待处理任务...")
                for task in pending:
                    task.cancel()
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception as e:
            print(f"  ⚠ 清理时出现异常: {e}")
        finally:
            print("  → 关闭事件循环...")
            loop.close()
            print("  ✓ 事件循环已关闭")
            # 可能会在这之后看到 "Event loop is closed" 错误


def main():
    """主测试流程"""
    print("=" * 60)
    print("事件循环关闭修复对比测试")
    print("=" * 60)

    # Windows 平台设置事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    # 测试 A：使用 dispose（修复后）
    success_a = test_with_dispose()

    # 等待一下，观察是否有延迟的错误
    import time
    time.sleep(1)

    # 测试 B：不使用 dispose（修复前）
    print("\n⚠ 注意：测试 B 可能会产生 'Event loop is closed' 错误")
    success_b = test_without_dispose()

    # 等待一下，观察错误
    time.sleep(1)

    print("\n" + "=" * 60)
    print("测试结果总结")
    print("=" * 60)
    print(f"测试 A (使用 dispose): {'✓ 通过' if success_a else '❌ 失败'}")
    print(f"测试 B (不使用 dispose): {'✓ 通过' if success_b else '❌ 失败'}")
    print("\n期望结果：")
    print("- 测试 A 应该干净地完成，没有错误")
    print("- 测试 B 可能会在结束后输出 'Event loop is closed' 错误")
    print("\n如果测试 A 没有错误，说明修复成功！")


if __name__ == "__main__":
    main()
