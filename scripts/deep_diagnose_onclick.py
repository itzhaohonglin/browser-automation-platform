"""
深入诊断：检查onclick函数和执行环境
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright


async def deep_diagnose():
    """深入诊断onclick"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        await page.goto("https://code.nhsa.gov.cn/toSearch.html?sysflag=1004")
        print("[1] 页面加载完成")
        await asyncio.sleep(2)

        iframe1 = page.frame_locator("iframe#dataInfo")
        iframe2 = iframe1.frame_locator("iframe.els-iframe.active")

        await iframe2.locator("input[name='regcardNm']").fill("滇械注准20192140008")
        await iframe2.locator("#search").click()
        await asyncio.sleep(5)
        print("[2] 查询完成\n")

        rows = iframe2.locator("tbody tr.jqgrow")
        count = await rows.count()

        if count > 0:
            first_row = rows.nth(0)
            detail_btn = first_row.locator("a[onclick*='goodsDetail']")

            # 获取实际的frame对象（不是locator）
            iframe1_element = await page.wait_for_selector("iframe#dataInfo")
            iframe1_frame = await iframe1_element.content_frame()

            iframe2_element = await iframe1_frame.wait_for_selector("iframe.els-iframe.active")
            iframe2_frame = await iframe2_element.content_frame()

            print("[诊断1] 检查goodsDetail函数是否存在:")

            # 在iframe2中检查goodsDetail函数
            goods_detail_exists = await iframe2_frame.evaluate("""
                () => {
                    return typeof goodsDetail !== 'undefined';
                }
            """)

            print(f"  iframe2中goodsDetail函数存在: {goods_detail_exists}")

            if not goods_detail_exists:
                # 检查父窗口
                parent_exists = await page.evaluate("""
                    () => {
                        return typeof goodsDetail !== 'undefined';
                    }
                """)
                print(f"  主窗口中goodsDetail函数存在: {parent_exists}")

            print("\n[诊断2] 获取onclick完整代码:")

            # 获取按钮元素
            btn_element = await iframe2_frame.wait_for_selector("a[onclick*='goodsDetail']")
            onclick_attr = await btn_element.get_attribute("onclick")
            print(f"  onclick: {onclick_attr}")

            print("\n[诊断3] 手动执行goodsDetail函数:")

            try:
                # 解析onclick中的参数
                import re
                match = re.search(r'goodsDetail\((.*?)\)', onclick_attr)
                if match:
                    params = match.group(1)
                    print(f"  参数: {params}")

                    # 尝试在iframe2中执行
                    result = await iframe2_frame.evaluate(f"""
                        () => {{
                            try {{
                                goodsDetail({params});
                                return 'success';
                            }} catch(e) {{
                                return 'error: ' + e.message;
                            }}
                        }}
                    """)
                    print(f"  执行结果: {result}")

                    await asyncio.sleep(3)

                    iframe_count = await page.locator("iframe.artDialog-iframe").count()
                    print(f"  artDialog-iframe数量: {iframe_count}")

            except Exception as e:
                print(f"  执行失败: {e}")

            print("\n[诊断4] 尝试Playwright原生click:")

            try:
                # 使用原生frame的click
                await btn_element.click(force=True)
                print("  强制点击已执行")
                await asyncio.sleep(3)

                iframe_count = await page.locator("iframe.artDialog-iframe").count()
                print(f"  artDialog-iframe数量: {iframe_count}")

            except Exception as e:
                print(f"  点击失败: {e}")

        print("\n\n[诊断完成] 浏览器将保持打开60秒...")
        print("请手动点击详情按钮，观察弹窗是否出现")
        await asyncio.sleep(60)

        await browser.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(deep_diagnose())
