"""
测试提取详情列表的所有行
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright


async def test_extract_detail_list():
    """测试提取详情列表"""

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
        print("[1] 查询完成\n")

        # 点击详情
        rows = target_frame.locator("tbody tr.jqgrow")
        first_row = rows.nth(0)
        detail_button = first_row.locator("a[onclick*='goodsDetail']")

        await detail_button.evaluate("element => element.click()")
        await asyncio.sleep(3)
        print("[2] 详情弹窗已打开\n")

        # 获取detail iframe
        detail_iframe_element = await target_frame.wait_for_selector(
            "iframe.artDialog-iframe",
            timeout=10000
        )
        detail_frame = await detail_iframe_element.content_frame()
        await asyncio.sleep(2)

        # 定位详情列表表格
        print("[3] 提取详情列表数据:\n")

        # 详情表格的行选择器
        detail_rows = detail_frame.locator("tbody tr.jqgrow")
        detail_row_count = await detail_rows.count()

        print(f"详情列表行数: {detail_row_count}\n")

        # 定义字段映射（根据截图中的列）
        detail_fields = [
            {"name": "注册备案号", "index": 1},
            {"name": "医保耗材分类编码", "index": 2},
            {"name": "注册备案人", "index": 3},
            {"name": "单件产品名称", "index": 4},
            {"name": "企业名称", "index": 5},
            {"name": "规格", "index": 6},
            {"name": "型号", "index": 7},
            {"name": "UDI-DI", "index": 8}
        ]

        all_detail_items = []

        for i in range(detail_row_count):
            row = detail_rows.nth(i)
            detail_item = {}

            print(f"详情行 {i+1}:")

            for field in detail_fields:
                # td索引从0开始，但第0个是序号列，所以实际数据从第1列开始
                selector = f"td:nth-child({field['index'] + 1})"
                cell = row.locator(selector)

                try:
                    text = await cell.inner_text()
                    detail_item[field['name']] = text.strip()
                    print(f"  {field['name']}: {text.strip()[:50]}")
                except Exception as e:
                    detail_item[field['name']] = ""
                    print(f"  {field['name']}: [提取失败: {e}]")

            all_detail_items.append(detail_item)
            print()

        print(f"\n[成功] 共提取 {len(all_detail_items)} 条详情数据")

        # 显示JSON结构
        import json
        print("\nJSON结构:")
        print(json.dumps(all_detail_items, ensure_ascii=False, indent=2))

        print("\n\n浏览器将保持打开30秒...")
        await asyncio.sleep(30)

        await browser.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(test_extract_detail_list())
