"""
测试 API 配置端点
"""
import requests
import json

API_BASE = "http://127.0.0.1:8000"

def test_get_configs():
    """测试获取配置列表"""
    print("\n" + "="*60)
    print("  测试 GET /api/configs")
    print("="*60 + "\n")

    try:
        response = requests.get(f"{API_BASE}/api/configs", timeout=5)
        print(f"HTTP 状态码: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print(f"\n返回数据:")
            print(f"  总数: {data.get('total')}")
            print(f"  当前页: {data.get('page')}")
            print(f"  每页大小: {data.get('page_size')}")
            print(f"  配置数量: {len(data.get('items', []))}")

            if data.get('items'):
                print(f"\n配置详情:")
                for item in data['items']:
                    print(f"\n  [配置 ID: {item.get('id')}]")
                    print(f"    名称: {item.get('config_name')}")
                    print(f"    启用: {item.get('is_active')}")
                    print(f"    创建时间: {item.get('created_at')}")
        else:
            print(f"\n错误响应: {response.text}")

    except requests.exceptions.ConnectionError:
        print("[错误] 无法连接到服务器，请确认服务是否运行在 http://127.0.0.1:8000")
    except Exception as e:
        print(f"[错误] 请求失败: {e}")

    print("\n" + "="*60)
    print()


if __name__ == "__main__":
    test_get_configs()
