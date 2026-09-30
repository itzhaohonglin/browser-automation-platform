"""
Final End-to-End Test
验证整个采集流程的完整性
"""
import pymysql
import json
import sys
import time
from datetime import datetime

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

# Database connection
conn = pymysql.connect(host='localhost', user='root', password='root', database='bap')
cursor = conn.cursor()

print("=" * 80)
print("最终端到端测试 - 2026/09/30")
print("=" * 80)

# Step 1: Verify Config 44 exists
print("\n[Step 1] 验证配置 44 存在")
cursor.execute('SELECT id, config_name, is_active FROM crawler_configs WHERE id = 44')
config = cursor.fetchone()

if not config:
    print("✗ 配置 44 不存在")
    conn.close()
    exit(1)

print(f"✓ 配置已找到: {config[1]}")
print(f"✓ 启用状态: {'是' if config[2] else '否'}")

# Step 2: Create test job
print("\n[Step 2] 创建测试任务")
try:
    cursor.execute("""
        INSERT INTO job_queue (config_id, query_params, status, retry_count, priority, created_at, updated_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (
        44,
        json.dumps({"registration_no": "滇械注准20192140008"}),
        "pending",
        0,
        5,
        datetime.now(),
        datetime.now()
    ))
    conn.commit()
    job_id = cursor.lastrowid
    print(f"✓ 测试任务创建成功，Job ID: {job_id}")
except Exception as e:
    print(f"✗ 创建任务失败: {e}")
    conn.close()
    exit(1)

# Step 3: Check if task was created
print("\n[Step 3] 验证任务信息")
cursor.execute('SELECT id, config_id, status FROM job_queue WHERE id = %s', (job_id,))
job = cursor.fetchone()

if not job:
    print(f"✗ 无法找到创建的任务")
    conn.close()
    exit(1)

print(f"✓ Job ID: {job[0]}")
print(f"✓ Config ID: {job[1]}")
print(f"✓ 初始状态: {job[2]}")

# Step 4: Wait and check if executor would pick it up
print("\n[Step 4] 任务排队完成，等待执行引擎处理...")
print("  (注: 实际执行需要启动 FastAPI 服务)")
print(f"  任务将通过以下接口执行:")
print(f"  POST /api/jobs/{job_id}/execute")

# Step 5: Verify configuration details
print("\n[Step 5] 验证配置详情")
cursor.execute('SELECT fields_mapping FROM crawler_configs WHERE id = 44')
config_data = cursor.fetchone()

if config_data:
    fields_mapping = json.loads(config_data[0]) if config_data[0] else {}

    # List fields
    list_fields = fields_mapping.get('fields', [])
    print(f"✓ 列表字段数: {len(list_fields)}")

    # Detail fields
    detail_config = fields_mapping.get('detail_config', {})
    if detail_config.get('enabled'):
        detail_fields = detail_config.get('fields', [])
        print(f"✓ 详情字段数: {len(detail_fields)}")
        print(f"✓ 详情采集已启用")
        print(f"✓ 详情按钮选择器: {detail_config.get('detail_button_selector', 'N/A')}")
        print(f"✓ 详情iframe选择器: {detail_config.get('detail_iframe_selector', 'N/A')}")
        print(f"✓ 点击方式: {detail_config.get('click_method', 'N/A')}")
    else:
        print("✗ 详情采集未启用")

# Step 6: Summary
print("\n" + "=" * 80)
print("验收清单检查")
print("=" * 80)

checklist = {
    "配置存在且启用": config[2] if config else False,
    "测试任务创建成功": job_id > 0,
    "任务状态初始化正确": job[2].lower() == "pending" if job else False,
    "列表字段配置完整": len(list_fields) > 0 if 'list_fields' in locals() else False,
    "详情采集已启用": detail_config.get('enabled', False) if 'detail_config' in locals() else False,
    "详情字段配置完整": len(detail_fields) > 0 if 'detail_fields' in locals() else False,
}

all_pass = True
for check_name, result in checklist.items():
    status = "✓" if result else "✗"
    print(f"{status} {check_name}")
    if not result:
        all_pass = False

# Final report
print("\n" + "=" * 80)
if all_pass:
    print("✅ 系统就绪，可以执行端到端测试")
    print(f"\n下一步操作:")
    print(f"1. 启动 FastAPI 服务: uvicorn app.main:app --reload")
    print(f"2. 执行任务: POST /api/jobs/{job_id}/execute")
    print(f"3. 监控进度: WebSocket ws://127.0.0.1:8000/ws")
    print(f"4. 查看结果: GET /api/jobs/{job_id}/result")
    conn.close()
    exit(0)
else:
    print("❌ 部分检查项未通过，请检查配置")
    conn.close()
    exit(1)
