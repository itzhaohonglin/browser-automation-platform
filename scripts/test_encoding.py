"""
测试 Playwright 提取中文字符
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright


async def test_encoding():
    """测试中文字符提取"""

    print("测试 Playwright 中文提取")
    print("="*60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        # 访问国家医保局页面
        await page.goto("https://code.nhsa.gov.cn/toSearch.html?sysflag=1004")
        print("[OK] 页面加载完成")

        # 进入iframe
        iframe1 = page.frame_locator("iframe#dataInfo")
        iframe2 = iframe1.frame_locator("iframe.els-iframe.active")

        # 填写注册证号
        await iframe2.locator("input[name='regcardNm']").fill("滇械注准20192140008")
        print("[OK] 填写注册证号")

        # 点击查询
        await iframe2.locator("#search").click()
        await asyncio.sleep(5)
        print("[OK] 查询完成")

        # 提取第一行数据
        rows = iframe2.locator("tbody tr.jqgrow")
        count = await rows.count()
        print(f"[OK] 找到 {count} 行")

        if count > 0:
            first_row = rows.nth(0)

            # 提取第3列（一级分类）
            cell = first_row.locator("td:nth-child(3)")
            text = await cell.inner_text()

            print(f"\n提取的文本:")
            print(f"  原始: {repr(text)}")
            print(f"  显示: {text}")
            print(f"  编码: {text.encode('utf-8')}")
            print(f"  长度: {len(text)} 字符")

            # 检查是否包含中文
            contains_chinese = any('一' <= char <= '鿿' for char in text)
            print(f"  包含中文: {contains_chinese}")

        await browser.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(test_encoding())
