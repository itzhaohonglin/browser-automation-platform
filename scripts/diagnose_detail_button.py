"""
诊断脚本：查看列表第一行的详情按钮HTML结构
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright
from app.core.database import get_session
from app.models.config import CrawlerConfig
from app.models.job import JobQueue


async def diagnose_detail_button(job_id):
    """诊断详情按钮"""

    async with get_session() as session:
        # 获取任务和配置
        job = await session.get(JobQueue, job_id)
        config = await session.get(CrawlerConfig, job.config_id)

        print(f"Job {job_id}: {job.query_params}")
        print(f"Config: {config.config_name}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            # 访问页面
            await page.goto(config.target_url, wait_until="networkidle")
            print(f"\n访问URL: {config.target_url}")

            # 进入iframe
            iframe1 = page.frame_locator("iframe#dataInfo")
            iframe2 = iframe1.frame_locator("iframe.els-iframe.active")

            # 填写并提交
            input_selector = config.input_configs[0]['selector']
            reg_no = job.query_params['registration_no']

            await iframe2.locator(input_selector).fill(reg_no)
            await iframe2.locator("#search").click()

            # 等待结果
            await iframe2.locator(".ui-jqgrid-btable").wait_for(timeout=15000)
            await asyncio.sleep(2)

            # 获取第一行
            rows = iframe2.locator("tbody tr.jqgrow")
            count = await rows.count()
            print(f"\n找到 {count} 行数据")

            if count > 0:
                first_row = rows.nth(0)

                # 获取第一行的HTML
                html = await first_row.inner_html()
                print(f"\n第一行HTML:\n{html[:500]}...")

                # 测试不同的选择器
                selectors = [
                    "a[onclick*='goodsDetail']",
                    "a[onclick]",
                    "a",
                    "td a",
                    "a[aria-describedby]"
                ]

                print(f"\n测试选择器:")
                for selector in selectors:
                    button = first_row.locator(selector)
                    btn_count = await button.count()
                    print(f"  {selector}: {btn_count} 个")

                    if btn_count > 0:
                        # 获取第一个匹配元素的属性
                        onclick = await button.first.get_attribute("onclick")
                        text = await button.first.inner_text()
                        print(f"    -> text: '{text}', onclick: '{onclick[:50] if onclick else None}...'")

            await browser.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    job_id = int(sys.argv[1]) if len(sys.argv) > 1 else 18
    asyncio.run(diagnose_detail_button(job_id))
