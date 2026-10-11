"""
通过Web方式查看结果（避免控制台编码问题）
"""
import asyncio
import sys
from pathlib import Path
import webbrowser

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.result import CrawlerResult
from sqlalchemy import select
import json


async def export_result_to_html():
    """导出结果为HTML文件"""

    async with get_session() as session:
        # 获取最新结果
        result = await session.execute(
            select(CrawlerResult).order_by(CrawlerResult.id.desc()).limit(1)
        )
        latest = result.scalar_one_or_none()

        if not latest:
            print("No results found")
            return

        # 生成HTML
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>采集结果 - Job {latest.job_id}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h1 {{ color: #333; }}
        .info {{ background: #f0f0f0; padding: 10px; margin: 10px 0; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .json {{ background: #f5f5f5; padding: 10px; overflow: auto; }}
        pre {{ white-space: pre-wrap; word-wrap: break-word; }}
    </style>
</head>
<body>
    <h1>采集结果查看器</h1>

    <div class="info">
        <p><strong>Job ID:</strong> {latest.job_id}</p>
        <p><strong>Config ID:</strong> {latest.config_id}</p>
        <p><strong>创建时间:</strong> {latest.created_at}</p>
        <p><strong>页数:</strong> {latest.page_count}</p>
    </div>

    <h2>提取的数据</h2>
"""

        data = latest.extracted_data
        if data and 'items' in data:
            items = data['items']
            if isinstance(items, dict) and 'items' in items:
                items = items['items']
                summary = data['items'].get('summary', {})
                html_content += f"""
    <div class="info">
        <p><strong>总记录数:</strong> {summary.get('total_items', 0)}</p>
        <p><strong>详情成功:</strong> {summary.get('detail_success', 0)}</p>
        <p><strong>详情失败:</strong> {summary.get('detail_failed', 0)}</p>
    </div>
"""

            if items and len(items) > 0:
                html_content += "<h3>列表数据（第1条）</h3><table>"
                first_item = items[0]
                list_data = first_item.get('list_data', {})

                html_content += "<tr><th>字段名</th><th>值</th></tr>"
                for key, value in list_data.items():
                    html_content += f"<tr><td>{key}</td><td>{value}</td></tr>"
                html_content += "</table>"

                if first_item.get('detail_data'):
                    html_content += "<h3>详情数据</h3><table>"
                    html_content += "<tr><th>字段名</th><th>值</th></tr>"
                    for key, value in first_item['detail_data'].items():
                        html_content += f"<tr><td>{key}</td><td>{value}</td></tr>"
                    html_content += "</table>"

        html_content += """
    <h2>完整JSON数据</h2>
    <div class="json">
        <pre>""" + json.dumps(data, ensure_ascii=False, indent=2) + """</pre>
    </div>
</body>
</html>
"""

        # 保存到临时文件
        output_file = project_root / "temp_result.html"
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(html_content)

        print(f"结果已导出到: {output_file}")
        print("正在打开浏览器...")
        webbrowser.open(str(output_file))


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(export_result_to_html())
