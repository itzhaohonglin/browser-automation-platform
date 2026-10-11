"""
直接执行任务（绕过API）
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.services.executor import PlaywrightExecutor
from app.api.websocket import websocket_manager


async def execute_job_direct(job_id):
    """直接执行任务"""

    print(f"Executing job {job_id}...")

    async with get_session() as session:
        executor = PlaywrightExecutor(ws_manager=None)  # 不使用WebSocket

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

    job_id = int(sys.argv[1]) if len(sys.argv) > 1 else 9
    asyncio.run(execute_job_direct(job_id))
