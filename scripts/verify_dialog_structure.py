"""
验证artDialog-iframe的位置和详情表格结构
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright


async def verify_dialog_structure():
    """验证dialog结构"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto("https://code.nhsa.gov.cn/toSearch.html?sysflag=1004")
        print("[1] 页面加载完成")
        await asyncio.sleep(2)

        iframe1_element = await page.wait_for_selector("iframe#dataInfo")
        iframe1_frame = await iframe1_element.content_frame()

        iframe2_element = await iframe1_frame.wait_for_selector("iframe.els-iframe.active")
        iframe2_frame = await iframe2_element.content_frame()

        await iframe2_frame.fill("input[name='regcardNm']", "滇械注准20192140008")
        await iframe2_frame.click("#search")
        await asyncio.sleep(5)
        print("[2] 查询完成\n")

        print("请手动点击详情按钮...")
        print("等待10秒让您有时间点击...\n")
        await asyncio.sleep(10)

        print("[验证1] 检查.ui-dialog元素:")
        ui_dialog_count = await page.locator(".ui-dialog").count()
        print(f"  .ui-dialog数量: {ui_dialog_count}")

        if ui_dialog_count > 0:
            print("\n[验证2] 检查.ui-dialog下的iframe:")

            # 检查所有.ui-dialog
            for i in range(ui_dialog_count):
                dialog = page.locator(".ui-dialog").nth(i)

                # 检查是否可见
                is_visible = await dialog.is_visible()
                print(f"\n  Dialog #{i}:")
                print(f"    可见: {is_visible}")

                if is_visible:
                    # 检查内部的iframe
                    iframe_in_dialog = dialog.locator("iframe.artDialog-iframe")
                    iframe_count = await iframe_in_dialog.count()
                    print(f"    包含artDialog-iframe: {iframe_count > 0}")

                    if iframe_count > 0:
                        print("\n[SUCCESS] 找到详情iframe!")

                        # 获取iframe的src
                        iframe_src = await iframe_in_dialog.get_attribute("src")
                        print(f"    iframe src: {iframe_src[:100]}...")

                        # 尝试读取iframe内容
                        print("\n[验证3] 读取详情iframe内容:")

                        detail_iframe_locator = dialog.frame_locator("iframe.artDialog-iframe")

                        # 等待加载
                        await asyncio.sleep(2)

                        # 检查表格
                        table_count = await detail_iframe_locator.locator("table").count()
                        print(f"    表格数量: {table_count}")

                        if table_count > 0:
                            # 检查tr和td
                            tr_count = await detail_iframe_locator.locator("tr").count()
                            td_count = await detail_iframe_locator.locator("td").count()
                            print(f"    行数(tr): {tr_count}")
                            print(f"    单元格数(td): {td_count}")

                            # 获取表格HTML
                            print("\n[验证4] 表格HTML结构:")
                            table_html = await detail_iframe_locator.locator("table").first.inner_html()
                            print(f"    {table_html[:800]}")

                            # 尝试提取第一行数据
                            print("\n[验证5] 提取第一行数据:")

                            first_row = detail_iframe_locator.locator("tr").nth(0)
                            cells = first_row.locator("td")
                            cell_count = await cells.count()

                            print(f"    第一行单元格数: {cell_count}")

                            for j in range(min(cell_count, 4)):  # 只显示前4个
                                text = await cells.nth(j).inner_text()
                                print(f"      td[{j}]: {text.strip()[:50]}")

        else:
            print("  [FAIL] 未找到.ui-dialog元素")
            print("  请确认是否已点击详情按钮")

        print("\n\n浏览器将保持打开30秒...")
        await asyncio.sleep(30)

        await browser.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(verify_dialog_structure())
