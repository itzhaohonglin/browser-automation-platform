"""
获取详情表格的完整HTML结构
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright


async def get_detail_table_html():
    """获取详情表格HTML"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto("https://code.nhsa.gov.cn/toSearch.html?sysflag=1004")
        await asyncio.sleep(2)

        iframe1_element = await page.wait_for_selector("iframe#dataInfo")
        iframe1_frame = await iframe1_element.content_frame()

        iframe2_element = await iframe1_frame.wait_for_selector("iframe.els-iframe.active")
        target_frame = await iframe2_element.content_frame()

        await target_frame.fill("input[name='regcardNm']", "滇械注准20192140008")
        await target_frame.click("#search")
        await asyncio.sleep(5)

        # 点击详情
        rows = target_frame.locator("tbody tr.jqgrow")
        first_row = rows.nth(0)
        detail_button = first_row.locator("a[onclick*='goodsDetail']")

        await detail_button.evaluate("element => element.click()")
        await asyncio.sleep(3)

        # 获取detail iframe
        detail_iframe_element = await target_frame.wait_for_selector(
            "iframe.artDialog-iframe",
            timeout=10000
        )
        detail_frame = await detail_iframe_element.content_frame()

        await asyncio.sleep(2)

        # 获取所有表格的HTML
        tables = detail_frame.locator("table")
        table_count = await tables.count()

        print(f"详情iframe中表格数量: {table_count}\n")
        print("="*80)

        for i in range(table_count):
            table = tables.nth(i)
            table_html = await table.inner_html()

            print(f"\n表格 #{i+1}:")
            print("-"*80)
            print(table_html[:2000])  # 前2000字符
            print("...")
            print()

        # 也尝试获取所有tr的文本内容
        print("\n" + "="*80)
        print("所有行的文本内容:")
        print("="*80)

        all_rows = detail_frame.locator("tr")
        row_count = await all_rows.count()

        for i in range(min(row_count, 10)):  # 只显示前10行
            row = all_rows.nth(i)
            text = await row.inner_text()
            print(f"行 {i+1}: {text[:200]}")

        print("\n\n浏览器将保持打开30秒...")
        await asyncio.sleep(30)

        await browser.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(get_detail_table_html())
