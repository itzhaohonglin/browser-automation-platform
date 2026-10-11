"""
使用headful模式执行，可以手动观察浏览器
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.services.executor import PlaywrightExecutor


async def execute_job_headful(job_id):
    """使用headful模式执行任务（可以看到浏览器）"""

    print(f"Executing job {job_id} in HEADFUL mode...")
    print("You will see the browser window open.")

    async with get_session() as session:
        # 创建执行器，设置为headful模式
        executor = PlaywrightExecutor(ws_manager=None, headless=False)

        try:
            result = await executor.execute_job(job_id, session)
            print(f"\nExecution result:")
            print(f"  Job ID: {result.get('job_id')}")
            print(f"  Status: {result.get('status')}")
            print(f"  Extracted count: {result.get('extracted_count', 0)}")
            print(f"  Pages crawled: {result.get('pages_crawled', 0)}")
            if result.get('error'):
                print(f"  Error: {result.get('error')}")
        except Exception as e:
            print(f"\nExecution failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    job_id = int(sys.argv[1]) if len(sys.argv) > 1 else 18
    asyncio.run(execute_job_headful(job_id))
