"""验证数据结构的完整性"""
import json
from pathlib import Path
import sys
import io

# Set UTF-8 encoding for console output on Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def validate():
    """验证导出的样本数据"""
    json_file = Path(__file__).parent.parent / "docs" / "sample_data_job49.json"

    with open(json_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Navigate nested structure
    items_wrapper = data['extracted_data'].get('items', {})
    items_list = items_wrapper.get('items', []) if isinstance(items_wrapper, dict) else []
    summary = items_wrapper.get('summary', {}) if isinstance(items_wrapper, dict) else {}

    print("数据验证报告")
    print("=" * 60)

    # 验证基本结构
    print("\n1. 基本信息:")
    print(f"  Job ID: {data['job_id']}")
    print(f"  Config ID: {data['config_id']}")
    print(f"  页数: {data['page_count']}")
    print(f"  创建时间: {data['created_at']}")

    # 验证数据数量
    print("\n2. 数据数量统计:")
    print(f"  列表记录总数: {len(items_list)}")
    print(f"  详情成功: {summary.get('detail_success', 0)}")
    print(f"  详情失败: {summary.get('detail_failed', 0)}")

    # 验证字段结构
    if items_list:
        item = items_list[0]
        list_data = item.get('list_data', {})
        detail_data = item.get('detail_data', {})

        print("\n3. 字段结构验证:")
        print(f"  列表字段数: {len(list_data)} 个")
        print(f"  详情字段数: {len(detail_data)} 个")

        # 统计非空字段
        non_empty_list = sum(1 for v in list_data.values() if v)
        non_empty_detail = sum(1 for v in detail_data.values() if v)

        print(f"  列表非空字段: {non_empty_list}/{len(list_data)}")
        print(f"  详情非空字段: {non_empty_detail}/{len(detail_data)}")

        # 详情字段完整性
        print("\n4. 详情字段完整性检查:")
        expected_fields = [
            "型号", "序号", "规格", "产品名称", "医保编码",
            "注册证号", "生产企业", "原注册证号", "注册人企业",
            "单件产品名称", "完整医保编码"
        ]
        missing = [f for f in expected_fields if f not in detail_data]
        if missing:
            print(f"  缺失字段: {', '.join(missing)}")
        else:
            print("  所有期望字段均存在 [OK]")

        # 验证所有记录
        print("\n5. 数据一致性检查:")
        all_have_list = all('list_data' in item for item in items_list)
        all_have_detail = all('detail_data' in item for item in items_list)
        all_success = all(item.get('detail_status') == 'success' for item in items_list)

        print(f"  所有记录都有list_data: {'[OK]' if all_have_list else '[FAIL]'}")
        print(f"  所有记录都有detail_data: {'[OK]' if all_have_detail else '[FAIL]'}")
        print(f"  所有记录detail_status为success: {'[OK]' if all_success else '[FAIL]'}")

    print("\n" + "=" * 60)
    print("数据验证完成")

if __name__ == "__main__":
    validate()
