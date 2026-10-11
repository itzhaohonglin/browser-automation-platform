"""
诊断详情iframe的存在时机和状态
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright


async def diagnose_detail_iframe():
    """诊断详情iframe"""

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)  # 使用有头模式方便观察
        page = await browser.new_page()

        # 访问页面
        await page.goto("https://code.nhsa.gov.cn/toSearch.html?sysflag=1004")
        print("[1] 页面加载完成")
        await asyncio.sleep(2)

        # 进入iframe
        iframe1 = page.frame_locator("iframe#dataInfo")
        iframe2 = iframe1.frame_locator("iframe.els-iframe.active")

        # 填写并查询
        await iframe2.locator("input[name='regcardNm']").fill("滇械注准20192140008")
        await iframe2.locator("#search").click()
        await asyncio.sleep(5)
        print("[2] 查询完成")

        # 检查点1：点击详情按钮之前
        print("\n[检查点1] 点击详情按钮之前:")

        # 检查页面上所有iframe
        all_iframes = await page.evaluate("""
            () => {
                const iframes = document.querySelectorAll('iframe');
                return Array.from(iframes).map((iframe, index) => ({
                    index: index,
                    id: iframe.id,
                    class: iframe.className,
                    name: iframe.name,
                    src: iframe.src,
                    visible: iframe.offsetParent !== null,
                    width: iframe.offsetWidth,
                    height: iframe.offsetHeight
                }));
            }
        """)

        print(f"  页面顶层iframe数量: {len(all_iframes)}")
        for iframe in all_iframes:
            print(f"    - iframe#{iframe['index']}: id='{iframe['id']}', class='{iframe['class']}', visible={iframe['visible']}")

        # 检查artDialog-iframe是否存在
        art_dialog_exists = await page.locator("iframe.artDialog-iframe").count()
        print(f"  artDialog-iframe存在: {art_dialog_exists > 0} (数量: {art_dialog_exists})")

        # 检查详情按钮
        rows = iframe2.locator("tbody tr.jqgrow")
        count = await rows.count()
        print(f"  列表行数: {count}")

        if count > 0:
            first_row = rows.nth(0)
            detail_btn = first_row.locator("a[onclick*='goodsDetail']")
            btn_count = await detail_btn.count()
            print(f"  详情按钮找到: {btn_count > 0}")

            # 检查点2：尝试JavaScript点击
            print("\n[检查点2] 尝试JavaScript点击详情按钮:")

            try:
                # 使用JavaScript点击
                await detail_btn.evaluate("element => element.click()")
                print("  JavaScript点击已执行")
                await asyncio.sleep(3)

                # 检查点3：点击后iframe状态
                print("\n[检查点3] 点击后iframe状态:")

                all_iframes_after = await page.evaluate("""
                    () => {
                        const iframes = document.querySelectorAll('iframe');
                        return Array.from(iframes).map((iframe, index) => ({
                            index: index,
                            id: iframe.id,
                            class: iframe.className,
                            name: iframe.name,
                            src: iframe.src,
                            visible: iframe.offsetParent !== null,
                            width: iframe.offsetWidth,
                            height: iframe.offsetHeight
                        }));
                    }
                """)

                print(f"  页面顶层iframe数量: {len(all_iframes_after)}")
                for iframe in all_iframes_after:
                    if 'artDialog' in iframe['class'] or 'artDialog' in iframe.get('name', ''):
                        print(f"    [新增] iframe#{iframe['index']}: class='{iframe['class']}', name='{iframe['name'][:50]}...', visible={iframe['visible']}, src='{iframe['src'][:80]}...'")

                art_dialog_after = await page.locator("iframe.artDialog-iframe").count()
                print(f"  artDialog-iframe数量: {art_dialog_after}")

                # 尝试定位详情iframe并读取内容
                if art_dialog_after > 0:
                    print("\n[检查点4] 尝试读取详情iframe内容:")

                    detail_iframe_locator = page.frame_locator("iframe.artDialog-iframe")

                    # 等待iframe加载
                    await asyncio.sleep(2)

                    # 检查表格
                    table_count = await detail_iframe_locator.locator("table").count()
                    print(f"  表格数量: {table_count}")

                    if table_count > 0:
                        # 获取表格HTML
                        table_html = await detail_iframe_locator.locator("table").first.inner_html()
                        print(f"  表格HTML (前500字符):")
                        print(f"  {table_html[:500]}")

            except Exception as e:
                print(f"  JavaScript点击失败: {e}")

        print("\n[诊断完成] 浏览器将保持打开30秒供观察...")
        await asyncio.sleep(30)

        await browser.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(diagnose_detail_iframe())
