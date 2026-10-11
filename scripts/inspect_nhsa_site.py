"""
检查国家医保局网站结构

用途：
1. 验证页面结构（iframe、输入框、按钮）
2. 检查列表结果的字段
3. 检查详情按钮和详情页面结构
"""
import asyncio
import sys
import os
import json

# 设置UTF-8输出
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from playwright.async_api import async_playwright


async def inspect_nhsa_site():
    """检查NHSA网站结构"""

    async with async_playwright() as p:
        print("启动浏览器...")
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        # 访问目标页面
        url = "https://code.nhsa.gov.cn/toSearch.html?sysflag=1004"
        print(f"\n访问URL: {url}")
        await page.goto(url, wait_until='networkidle')
        await asyncio.sleep(5)

        # 检查iframe结构
        print("\n=== iframe 结构检查 ===")
        frames = page.frames
        print(f"总共有 {len(frames)} 个frame")
        for idx, frame in enumerate(frames):
            print(f"Frame {idx}: {frame.url[:100]}")

        # 尝试进入第一层iframe
        print("\n=== 进入第1层iframe ===")
        try:
            iframe1_element = await page.wait_for_selector("iframe#dataInfo", timeout=10000)
            iframe1 = await iframe1_element.content_frame()
            if iframe1:
                print("[OK] 成功进入第1层iframe")
                print(f"  URL: {iframe1.url[:100]}")
                await asyncio.sleep(2)

                # 尝试进入第二层iframe
                print("\n=== 进入第2层iframe ===")
                iframe2_element = await iframe1.wait_for_selector("iframe.els-iframe", timeout=10000)
                iframe2 = await iframe2_element.content_frame()

                if iframe2:
                    print("[OK] 成功进入第2层iframe")
                    print(f"  URL: {iframe2.url[:100]}")
                    await asyncio.sleep(2)

                    # 检查输入框
                    print("\n=== 输入框检查 ===")
                    # 查找所有输入框
                    inputs = await iframe2.query_selector_all("input")
                    print(f"找到 {len(inputs)} 个输入框")

                    for idx, inp in enumerate(inputs[:5]):  # 只检查前5个
                        name = await inp.get_attribute("name")
                        placeholder = await inp.get_attribute("placeholder")
                        inp_type = await inp.get_attribute("type")
                        print(f"  输入框 {idx}: name='{name}', type='{inp_type}', placeholder='{placeholder}'")

                    # 填写注册证号
                    print("\n=== 填写表单 ===")
                    registration_no = "滇械注准20192140008"

                    # 尝试不同的选择器
                    selectors = [
                        "input[name='zczbh']",
                        "input[name='regcardNm']",
                        "input[placeholder*='注册证号']"
                    ]

                    input_found = False
                    for selector in selectors:
                        try:
                            count = await iframe2.locator(selector).count()
                            if count > 0:
                                print(f"[OK] 找到输入框: {selector}")
                                await iframe2.fill(selector, registration_no)
                                print(f"  已填入: {registration_no}")
                                input_found = True
                                break
                        except:
                            print(f"[NO] 未找到: {selector}")

                    if not input_found:
                        print("[NO] 所有选择器都未找到输入框")
                        return

                    # 查找提交按钮
                    print("\n=== 提交按钮检查 ===")
                    buttons = await iframe2.query_selector_all("button")
                    print(f"找到 {len(buttons)} 个按钮")

                    for idx, btn in enumerate(buttons[:3]):
                        text = await btn.inner_text()
                        print(f"  按钮 {idx}: '{text}'")

                    # 点击查询按钮
                    print("\n=== 点击查询按钮 ===")
                    try:
                        await iframe2.click("button:has-text('查询')", timeout=5000)
                        print("[OK] 查询按钮已点击")
                    except Exception as e:
                        print(f"[NO] 点击失败: {e}")
                        return

                    # 等待结果加载
                    print("\n=== 等待结果加载 ===")
                    await asyncio.sleep(5)

                    # 检查结果表格
                    print("\n=== 检查结果表格 ===")
                    try:
                        rows = await iframe2.query_selector_all("tbody tr.jqgrow")
                        print(f"找到 {len(rows)} 行数据")

                        if len(rows) > 0:
                            # 检查第一行的结构
                            first_row = rows[0]
                            cells = await first_row.query_selector_all("td")
                            print(f"\n第一行有 {len(cells)} 个单元格:")
                            for idx, cell in enumerate(cells[:12]):  # 检查前12个
                                text = await cell.inner_text()
                                print(f"  列 {idx+1}: '{text[:50]}'")

                            # 检查详情按钮
                            print("\n=== 检查详情按钮 ===")
                            detail_links = await first_row.query_selector_all("a")
                            print(f"找到 {len(detail_links)} 个链接")

                            for idx, link in enumerate(detail_links):
                                text = await link.inner_text()
                                print(f"  链接 {idx}: '{text}'")

                            # 尝试点击详情按钮
                            if len(detail_links) > 0:
                                print("\n=== 点击详情按钮 ===")
                                try:
                                    # 使用JavaScript点击避免遮挡问题
                                    await detail_links[0].evaluate("element => element.click()")
                                    print("[OK] 详情按钮已点击")
                                    await asyncio.sleep(3)

                                    # 检查详情iframe
                                    print("\n=== 检查详情iframe ===")
                                    detail_iframe_selectors = [
                                        "iframe.artDialog-iframe",
                                        "iframe[src*='detail']",
                                        ".artDialog iframe"
                                    ]

                                    detail_frame = None
                                    for selector in detail_iframe_selectors:
                                        try:
                                            detail_iframe_elem = await iframe2.wait_for_selector(selector, timeout=5000)
                                            detail_frame = await detail_iframe_elem.content_frame()
                                            if detail_frame:
                                                print(f"[OK] 找到详情iframe: {selector}")
                                                print(f"  URL: {detail_frame.url[:100]}")
                                                break
                                        except:
                                            print(f"[NO] 未找到: {selector}")

                                    if detail_frame:
                                        await asyncio.sleep(2)

                                        # 检查详情页面内容
                                        print("\n=== 检查详情页面 ===")
                                        detail_html = await detail_frame.content()
                                        print(f"详情页面HTML长度: {len(detail_html)} 字符")

                                        # 查找所有div元素（详情字段通常在div中）
                                        divs = await detail_frame.query_selector_all("div")
                                        print(f"找到 {len(divs)} 个div元素")

                                        # 显示前20个div的文本
                                        print("\n前20个div的内容:")
                                        for idx, div in enumerate(divs[:20]):
                                            text = await div.inner_text()
                                            if text and len(text.strip()) > 0:
                                                print(f"  div {idx}: '{text[:60]}'")

                                except Exception as e:
                                    print(f"[NO] 详情操作失败: {e}")

                    except Exception as e:
                        print(f"[NO] 表格检查失败: {e}")
            else:
                print("[NO] 无法获取第1层iframe")
        except Exception as e:
            print(f"[NO] iframe检查失败: {e}")

        # 保持浏览器打开以便手动检查
        print("\n\n浏览器将保持打开30秒，请手动检查...")
        await asyncio.sleep(30)

        await browser.close()
        print("\n检查完成")


if __name__ == "__main__":
    # Windows平台设置事件循环策略
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(inspect_nhsa_site())
