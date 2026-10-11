"""
测试不同的详情按钮点击方式
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright


async def test_click_methods():
    """测试不同点击方式"""

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
        print("[2] 查询完成")

        rows = iframe2.locator("tbody tr.jqgrow")
        count = await rows.count()

        if count > 0:
            first_row = rows.nth(0)
            detail_btn = first_row.locator("a[onclick*='goodsDetail']")

            print("\n测试不同的点击方式:")
            print("="*60)

            # 方法1: 普通click
            print("\n[方法1] 普通click()")
            try:
                await detail_btn.click(timeout=5000)
                print("  [OK] 点击成功")
                await asyncio.sleep(3)

                iframe_count = await page.locator("iframe.artDialog-iframe").count()
                print(f"  artDialog-iframe数量: {iframe_count}")

                if iframe_count == 0:
                    print("  [FAIL] 详情弹窗未出现")
                else:
                    print("  [SUCCESS] 详情弹窗已出现!")
            except Exception as e:
                print(f"  [FAIL] 点击失败: {str(e)[:100]}")

            # 等待并关闭可能的弹窗
            await asyncio.sleep(2)

            # 方法2: JavaScript element.click()
            print("\n[方法2] JavaScript element.click()")
            try:
                await detail_btn.evaluate("element => element.click()")
                print("  [OK] JavaScript执行成功")
                await asyncio.sleep(3)

                iframe_count = await page.locator("iframe.artDialog-iframe").count()
                print(f"  artDialog-iframe数量: {iframe_count}")

                if iframe_count == 0:
                    print("  [FAIL] 详情弹窗未出现")
                else:
                    print("  [SUCCESS] 详情弹窗已出现!")
            except Exception as e:
                print(f"  [FAIL] 执行失败: {e}")

            await asyncio.sleep(2)

            # 方法3: 直接调用onclick函数
            print("\n[方法3] 直接调用onclick函数")
            try:
                # 获取onclick属性值
                onclick_value = await detail_btn.get_attribute("onclick")
                print(f"  onclick属性: {onclick_value[:100]}...")

                # 在iframe2的context中执行onclick函数
                result = await iframe2.evaluate(f"""
                    () => {{
                        {onclick_value}
                    }}
                """)

                print("  [OK] onclick函数执行")
                await asyncio.sleep(3)

                iframe_count = await page.locator("iframe.artDialog-iframe").count()
                print(f"  artDialog-iframe数量: {iframe_count}")

                if iframe_count > 0:
                    print("  [SUCCESS!!!] 成功！详情弹窗已出现！")
                else:
                    print("  [FAIL] 详情弹窗未出现")

            except Exception as e:
                print(f"  [FAIL] 执行失败: {e}")

            await asyncio.sleep(2)

            # 方法4: dispatchEvent模拟鼠标点击
            print("\n[方法4] dispatchEvent模拟鼠标点击")
            try:
                await detail_btn.evaluate("""
                    element => {
                        const event = new MouseEvent('click', {
                            bubbles: true,
                            cancelable: true,
                            view: window
                        });
                        element.dispatchEvent(event);
                    }
                """)
                print("  [OK] MouseEvent触发成功")
                await asyncio.sleep(3)

                iframe_count = await page.locator("iframe.artDialog-iframe").count()
                print(f"  artDialog-iframe数量: {iframe_count}")

                if iframe_count > 0:
                    print("  [SUCCESS!!!] 成功！详情弹窗已出现！")
                else:
                    print("  [FAIL] 详情弹窗未出现")

            except Exception as e:
                print(f"  [FAIL] 执行失败: {e}")

        print("\n\n[测试完成] 浏览器将保持打开30秒供观察...")
        await asyncio.sleep(30)

        await browser.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(test_click_methods())
