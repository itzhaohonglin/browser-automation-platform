"""
全面搜索：查找手动点击后出现的所有dialog和iframe
"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from playwright.async_api import async_playwright


async def search_all_dialogs():
    """搜索所有dialog和iframe"""

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

        print("="*60)
        print("请手动点击详情按钮！")
        print("等待15秒让您有时间点击...")
        print("="*60)
        await asyncio.sleep(15)

        print("\n[搜索1] 顶层page中所有iframe:")
        all_iframes = await page.evaluate("""
            () => {
                const iframes = document.querySelectorAll('iframe');
                return Array.from(iframes).map((iframe, idx) => ({
                    index: idx,
                    id: iframe.id,
                    className: iframe.className,
                    name: iframe.name,
                    src: iframe.src,
                    visible: iframe.offsetParent !== null
                }));
            }
        """)

        for iframe in all_iframes:
            if iframe['visible']:
                print(f"  iframe[{iframe['index']}]:")
                print(f"    id: {iframe['id']}")
                print(f"    class: {iframe['className']}")
                print(f"    name: {iframe['name'][:60] if iframe['name'] else ''}")
                print(f"    src: {iframe['src'][:80]}")

        print("\n[搜索2] 包含'dialog'或'popup'类名的元素:")
        dialog_classes = await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('[class*="dialog"], [class*="Dialog"], [class*="popup"], [class*="modal"]');
                return Array.from(elements).map((el, idx) => ({
                    index: idx,
                    tag: el.tagName,
                    className: el.className,
                    visible: el.offsetParent !== null,
                    hasIframe: el.querySelector('iframe') !== null
                }));
            }
        """)

        for el in dialog_classes:
            if el['visible']:
                print(f"  元素[{el['index']}]:")
                print(f"    标签: {el['tag']}")
                print(f"    class: {el['className']}")
                print(f"    包含iframe: {el['hasIframe']}")

        print("\n[搜索3] 所有包含'artDialog'的元素:")
        art_dialogs = await page.evaluate("""
            () => {
                const elements = document.querySelectorAll('[class*="artDialog"]');
                return Array.from(elements).map((el, idx) => ({
                    index: idx,
                    tag: el.tagName,
                    className: el.className,
                    visible: el.offsetParent !== null
                }));
            }
        """)

        if len(art_dialogs) > 0:
            for el in art_dialogs:
                print(f"  元素[{el['index']}]:")
                print(f"    标签: {el['tag']}")
                print(f"    class: {el['className']}")
                print(f"    可见: {el['visible']}")
        else:
            print("  未找到包含'artDialog'的元素")

        print("\n[搜索4] iframe2内部的所有iframe:")
        iframes_in_iframe2 = await iframe2_frame.evaluate("""
            () => {
                const iframes = document.querySelectorAll('iframe');
                return Array.from(iframes).map((iframe, idx) => ({
                    index: idx,
                    id: iframe.id,
                    className: iframe.className,
                    name: iframe.name,
                    src: iframe.src,
                    visible: iframe.offsetParent !== null
                }));
            }
        """)

        if len(iframes_in_iframe2) > 0:
            print(f"  iframe2内部iframe数量: {len(iframes_in_iframe2)}")
            for iframe in iframes_in_iframe2:
                if iframe['visible']:
                    print(f"    iframe[{iframe['index']}]:")
                    print(f"      class: {iframe['className']}")
                    print(f"      src: {iframe['src'][:80]}")
        else:
            print("  iframe2内部没有iframe")

        print("\n[搜索5] iframe2内部包含dialog的元素:")
        dialogs_in_iframe2 = await iframe2_frame.evaluate("""
            () => {
                const elements = document.querySelectorAll('[class*="dialog"], [class*="Dialog"], [class*="popup"]');
                return Array.from(elements).map((el, idx) => ({
                    index: idx,
                    tag: el.tagName,
                    className: el.className,
                    visible: el.offsetParent !== null,
                    hasIframe: el.querySelector('iframe') !== null
                }));
            }
        """)

        if len(dialogs_in_iframe2) > 0:
            print(f"  iframe2内部dialog数量: {len(dialogs_in_iframe2)}")
            for el in dialogs_in_iframe2:
                if el['visible']:
                    print(f"    元素[{el['index']}]:")
                    print(f"      标签: {el['tag']}")
                    print(f"      class: {el['className']}")
                    print(f"      包含iframe: {el['hasIframe']}")
        else:
            print("  iframe2内部没有dialog元素")

        print("\n\n浏览器将保持打开30秒供检查...")
        await asyncio.sleep(30)

        await browser.close()


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    asyncio.run(search_all_dialogs())
