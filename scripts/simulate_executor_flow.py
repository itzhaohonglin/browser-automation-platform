"""
模拟执行器完整流程测试详情采集
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright


async def simulate_executor_flow():
    """模拟执行器流程"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto("https://code.nhsa.gov.cn/toSearch.html?sysflag=1004")
        print("[1] 页面加载完成")
        await asyncio.sleep(2)

        # 获取iframe2（模拟executor的target_frame）
        iframe1_element = await page.wait_for_selector("iframe#dataInfo")
        iframe1_frame = await iframe1_element.content_frame()

        iframe2_element = await iframe1_frame.wait_for_selector("iframe.els-iframe.active")
        target_frame = await iframe2_element.content_frame()

        await target_frame.fill("input[name='regcardNm']", "滇械注准20192140008")
        await target_frame.click("#search")
        await asyncio.sleep(5)
        print("[2] 查询完成\n")

        # 获取第一行
        rows = target_frame.locator("tbody tr.jqgrow")
        first_row = rows.nth(0)

        # 获取详情按钮
        detail_button = first_row.locator("a[onclick*='goodsDetail']")
        print("[3] 模拟点击详情按钮...")

        # 使用JavaScript点击（配置中的click_method: 'javascript'）
        await detail_button.evaluate("element => element.click()")
        print("  JavaScript点击已执行")

        # 等待iframe加载（模拟executor的wait_for_selector）
        print("\n[4] 在target_frame(iframe2)中查找detail_iframe...")

        try:
            # 等待时间更长一些
            await asyncio.sleep(3)

            # 在iframe2中查找artDialog-iframe
            detail_iframe_element = await target_frame.wait_for_selector(
                "iframe.artDialog-iframe",
                timeout=10000
            )
            print("  [SUCCESS] 找到detail_iframe!")

            detail_frame = await detail_iframe_element.content_frame()

            if not detail_frame:
                print("  [FAIL] 无法获取detail_frame content")
            else:
                print("  [SUCCESS] 获取detail_frame成功")

                # 等待表格加载
                await asyncio.sleep(2)

                print("\n[5] 提取详情数据...")

                # 检查表格
                table_count = await detail_frame.locator("table").count()
                print(f"  表格数量: {table_count}")

                if table_count > 0:
                    # 获取所有tr
                    rows = detail_frame.locator("tr")
                    row_count = await rows.count()
                    print(f"  行数: {row_count}")

                    # 提取前3行数据
                    print("\n  前3行数据:")
                    for i in range(min(row_count, 3)):
                        row = rows.nth(i)
                        cells = row.locator("td")
                        cell_count = await cells.count()

                        if cell_count >= 2:
                            # 假设第一列是标签，第二列是值
                            label = await cells.nth(0).inner_text()
                            value = await cells.nth(1).inner_text()
                            print(f"    行{i+1}: {label.strip()[:20]} = {value.strip()[:50]}")

                    print("\n  [SUCCESS] 详情数据提取成功!")

        except Exception as e:
            print(f"  [FAIL] 等待detail_iframe失败: {e}")

        print("\n\n浏览器将保持打开30秒...")
        await asyncio.sleep(30)

        await browser.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(simulate_executor_flow())
