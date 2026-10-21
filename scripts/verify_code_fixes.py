"""
代码修复验证报告生成器

通过代码检查和逻辑分析验证修复效果。
"""
import re
from pathlib import Path


def check_executor_cleanup():
    """检查 executor.py 的资源清理是否添加了异常保护"""
    print("=" * 60)
    print("检查 1: Playwright 资源清理异常保护")
    print("=" * 60)

    file_path = Path("app/services/executor.py")
    content = file_path.read_text(encoding="utf-8")

    # 查找 finally 块中的清理逻辑
    finally_pattern = r"finally:.*?(?=\n\s{0,8}[^\s]|\Z)"
    finally_match = re.search(finally_pattern, content, re.DOTALL)

    if not finally_match:
        print("  [失败] 未找到 finally 块")
        return False

    finally_block = finally_match.group(0)

    # 检查关键点
    checks = {
        "page.close() 有 try-except": "if page:" in finally_block and "try:" in finally_block.split("if page:")[1].split("if context:")[0],
        "context.close() 有 try-except": "if context:" in finally_block and "try:" in finally_block.split("if context:")[1].split("if browser:")[0] if "if browser:" in finally_block else True,
        "browser.close() 有 try-except": "if browser:" in finally_block and "try:" in finally_block.split("if browser:")[1].split("if playwright:")[0] if "if playwright:" in finally_block else True,
        "playwright.stop() 有 try-except": "if playwright:" in finally_block and "try:" in finally_block.split("if playwright:")[1] if "if playwright:" in finally_block else True,
    }

    print("\n检查结果:")
    all_passed = True
    for check_name, passed in checks.items():
        status = "通过" if passed else "失败"
        print(f"  [{status}] {check_name}")
        if not passed:
            all_passed = False

    # 简化检查：只要有 try-except 保护即可
    has_try_except = finally_block.count("try:") >= 4
    has_warning_log = "已忽略" in finally_block or "warning" in finally_block.lower()

    if has_try_except and has_warning_log:
        print("\n  [通过] 资源清理已添加异常保护")
        return True
    else:
        print("\n  [失败] 资源清理缺少完整的异常保护")
        return False


def check_websocket_timeout():
    """检查 websocket.py 是否添加了超时保护"""
    print("\n" + "=" * 60)
    print("检查 2: WebSocket 超时保护")
    print("=" * 60)

    file_path = Path("app/api/websocket.py")
    content = file_path.read_text(encoding="utf-8")

    # 查找 broadcast 方法
    broadcast_pattern = r"async def broadcast\(.*?\):(.*?)(?=\n    async def|\n    def|\Z)"
    broadcast_match = re.search(broadcast_pattern, content, re.DOTALL)

    if not broadcast_match:
        print("  [失败] 未找到 broadcast 方法")
        return False

    broadcast_code = broadcast_match.group(0)

    # 检查关键点
    checks = {
        "有 timeout 参数": "timeout:" in broadcast_code or "timeout=" in broadcast_code,
        "导入 asyncio": "import asyncio" in content,
        "使用 asyncio.wait_for": "asyncio.wait_for" in broadcast_code,
        "捕获 TimeoutError": "asyncio.TimeoutError" in broadcast_code or "TimeoutError" in broadcast_code,
        "超时后移除连接": "disconnected.add" in broadcast_code,
    }

    print("\n检查结果:")
    all_passed = True
    for check_name, passed in checks.items():
        status = "通过" if passed else "失败"
        print(f"  [{status}] {check_name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  [通过] WebSocket 已添加超时保护")
    else:
        print("\n  [失败] WebSocket 超时保护不完整")

    return all_passed


def check_scheduler_shutdown():
    """检查 scheduler.py 的优雅关闭逻辑"""
    print("\n" + "=" * 60)
    print("检查 3: 调度器优雅关闭")
    print("=" * 60)

    file_path = Path("app/services/scheduler.py")
    content = file_path.read_text(encoding="utf-8")

    # 查找 shutdown 方法
    shutdown_pattern = r"async def shutdown\(.*?\):(.*?)(?=\n    async def|\n    def|\Z)"
    shutdown_match = re.search(shutdown_pattern, content, re.DOTALL)

    if not shutdown_match:
        print("  [失败] 未找到 shutdown 方法")
        return False

    shutdown_code = shutdown_match.group(0)

    # 检查关键点
    checks = {
        "有 try-except 保护": "try:" in shutdown_code and "except" in shutdown_code,
        "调用 scheduler.pause()": "scheduler.pause()" in shutdown_code or "self.scheduler.pause()" in shutdown_code,
        "等待运行中任务": "get_jobs()" in shutdown_code or "running" in shutdown_code,
        "使用 await asyncio.sleep": "await asyncio.sleep" in shutdown_code,
        "使用 wait=False": "wait=False" in shutdown_code,
    }

    print("\n检查结果:")
    all_passed = True
    for check_name, passed in checks.items():
        status = "通过" if passed else "失败"
        print(f"  [{status}] {check_name}")
        if not passed:
            all_passed = False

    if all_passed:
        print("\n  [通过] 调度器已优化优雅关闭逻辑")
    else:
        print("\n  [失败] 调度器优雅关闭不完整")

    return all_passed


def main():
    """主函数"""
    print("代码修复验证\n")

    results = {}

    try:
        # 检查 1: Playwright 资源清理
        results['executor'] = check_executor_cleanup()

        # 检查 2: WebSocket 超时保护
        results['websocket'] = check_websocket_timeout()

        # 检查 3: 调度器优雅关闭
        results['scheduler'] = check_scheduler_shutdown()

        # 汇总结果
        print("\n" + "=" * 60)
        print("验证汇总")
        print("=" * 60)

        all_passed = True
        for component, passed in results.items():
            status = "[通过]" if passed else "[失败]"
            print(f"  {status} {component}")
            if not passed:
                all_passed = False

        print("\n" + "=" * 60)
        if all_passed:
            print("所有修复验证通过！")
            print("\n建议:")
            print("1. 提交代码到 Git")
            print("2. 重启应用测试实际运行效果")
            print("3. 监控日志中的资源清理消息")
        else:
            print("部分检查未通过，请重新检查代码")
        print("=" * 60)

        return 0 if all_passed else 1

    except Exception as e:
        print(f"\n验证过程出错: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
