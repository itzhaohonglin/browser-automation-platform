"""导出Job 49的样本数据用于验证"""
import asyncio
import json
import sys
from pathlib import Path
import io

# Set UTF-8 encoding for console output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_session
from app.models.result import CrawlerResult
from sqlalchemy import select


async def export():
    """导出样本数据"""
    try:
        async with get_session() as session:
            # Query for job_id = 49
            stmt = select(CrawlerResult).where(CrawlerResult.job_id == 49)
            result = await session.execute(stmt)
            crawler_result = result.scalar_one_or_none()

            if crawler_result:
                data = {
                    "job_id": crawler_result.job_id,
                    "config_id": crawler_result.config_id,
                    "extracted_data": crawler_result.extracted_data,
                    "page_count": crawler_result.page_count,
                    "created_at": crawler_result.created_at.isoformat() if crawler_result.created_at else None
                }

                # Create docs directory if it doesn't exist
                docs_dir = Path(__file__).parent.parent / "docs"
                docs_dir.mkdir(exist_ok=True)

                output_path = docs_dir / "sample_data_job49.json"
                with open(output_path, "w", encoding="utf-8") as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)

                print(f"✓ 样本数据已导出到 {output_path}")

                # Extract and analyze data
                extracted = data['extracted_data']

                # Navigate nested structure: extracted_data -> items -> items (list)
                items_wrapper = extracted.get('items', {})
                items_list = items_wrapper.get('items', []) if isinstance(items_wrapper, dict) else []

                if items_list:
                    print(f"  列表记录数: {len(items_list)}")

                    if len(items_list) > 0:
                        item = items_list[0]
                        if isinstance(item, dict):
                            list_data = item.get('list_data', {})
                            detail_data = item.get('detail_data', {})

                            print(f"  列表字段数: {len(list_data)}")
                            print(f"  详情字段数: {len(detail_data)}")

                            # Count non-empty detail fields
                            non_empty = sum(1 for v in detail_data.values() if v)
                            print(f"  非空详情字段: {non_empty}/{len(detail_data)}")

                            print("\n  列表字段名:")
                            for key in list_data.keys():
                                print(f"    - {key}")

                            print("\n  详情字段名:")
                            for key in detail_data.keys():
                                print(f"    - {key}")
                        else:
                            print(f"  第一项类型: {type(item)}")

                    # Print summary if available
                    summary = items_wrapper.get('summary', {}) if isinstance(items_wrapper, dict) else {}
                    if summary:
                        print(f"\n  数据汇总:")
                        print(f"    - 总项数: {summary.get('total_items', 0)}")
                        print(f"    - 详情成功: {summary.get('detail_success', 0)}")
                        print(f"    - 详情失败: {summary.get('detail_failed', 0)}")
                        print(f"    - 页数: {summary.get('pages_crawled', 0)}")
                else:
                    print(f"  未找到items数据")
            else:
                print("✗ 未找到Job 49的结果")
                print("  尝试查询所有结果...")

                # List all jobs
                stmt = select(CrawlerResult).limit(5)
                result = await session.execute(stmt)
                results = result.scalars().all()

                if results:
                    print(f"  找到 {len(results)} 条记录:")
                    for r in results:
                        print(f"    - Job ID: {r.job_id}, Config ID: {r.config_id}")
                else:
                    print("  数据库中没有结果记录")

    except Exception as e:
        print(f"✗ 导出失败: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(export())
