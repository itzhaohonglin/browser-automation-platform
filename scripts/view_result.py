"""
查看采集结果
"""

import asyncio
import sys
import json
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.result import CrawlerResult


async def view_result(job_id):
    """查看采集结果"""

    async with get_session() as session:
        result = await session.get(CrawlerResult, job_id)

        if not result:
            print(f"Result not found for job {job_id}")
            return

        print(f"Job ID: {result.job_id}")
        print(f"Config ID: {result.config_id}")
        print(f"Pages crawled: {result.page_count}")
        print(f"\nExtracted data:")
        print(json.dumps(result.extracted_data, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    job_id = int(sys.argv[1]) if len(sys.argv) > 1 else 3
    asyncio.run(view_result(job_id))
