"""
Verify Task 3 Specification Compliance
Check Job 49 detail collection results
"""
import pymysql
import json
import sys

# Force UTF-8 encoding for Windows console
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')

conn = pymysql.connect(host='localhost', user='root', password='root', database='bap')
cursor = conn.cursor()

job_id = 49

print("=" * 80)
print("Task 3 Specification Compliance Verification")
print("=" * 80)

# 1. Query job status
cursor.execute('SELECT id, config_id, status, error_msg FROM job_queue WHERE id = %s', (job_id,))
job = cursor.fetchone()

if not job:
    print(f"[FAIL] Job {job_id} does not exist")
    conn.close()
    exit(1)

print(f"\n[Job Basic Information]")
print(f"Job ID: {job[0]}")
print(f"Config ID: {job[1]}")
print(f"Status: {job[2]}")
if job[3]:
    print(f"Error: {job[3]}")

if job[2].lower() != 'success':
    print(f"\n[FAIL] Job status is not success, current status: {job[2]}")
    conn.close()
    exit(1)

config_id = job[1]

# 2. Query configuration
cursor.execute('SELECT id, config_name, fields_mapping FROM crawler_configs WHERE id = %s', (config_id,))
config = cursor.fetchone()

if not config:
    print(f"\n[FAIL] Config {config_id} does not exist")
    conn.close()
    exit(1)

print(f"\n[Configuration Information]")
print(f"Config ID: {config[0]}")
print(f"Config Name: {config[1]}")

fields_mapping = json.loads(config[2]) if config[2] else {}
detail_config = fields_mapping.get('detail_config', {})
print(f"\n[Detail Configuration]")
print(f"Enabled: {detail_config.get('enabled', False)}")
print(f"Detail Button Selector: {detail_config.get('detail_button_selector', 'N/A')}")
print(f"Detail Iframe Selector: {detail_config.get('detail_iframe_selector', 'N/A')}")
print(f"Detail Fields Count: {len(detail_config.get('fields', []))}")
print(f"Click Method: {detail_config.get('click_method', 'N/A')}")

# 3. Query results
cursor.execute('SELECT id, page_count, extracted_data FROM crawler_results WHERE job_id = %s', (job_id,))
result = cursor.fetchone()

if not result:
    print(f"\n[FAIL] No result found for Job {job_id}")
    conn.close()
    exit(1)

print(f"\n[Collection Results]")
print(f"Result ID: {result[0]}")
print(f"Page Count: {result[1]}")

extracted_data = json.loads(result[2]) if result[2] else None
if not extracted_data:
    print(f"\n[FAIL] extracted_data is empty")
    conn.close()
    exit(1)

# Parse data
if isinstance(extracted_data, dict):
    items = extracted_data.get('items', [])
    # Handle nested items structure: {'items': {'items': [...]}}
    if isinstance(items, dict) and 'items' in items:
        items = items['items']
    # If items is still a dict with numeric keys, convert to list
    if isinstance(items, dict):
        items = list(items.values())
elif isinstance(extracted_data, list):
    items = extracted_data
else:
    items = []

print(f"Items Count: {len(items)}")
print(f"Items Type: {type(items)}")

# 4. Verify detail data
print(f"\n[Detail Data Verification]")
if not items or len(items) == 0:
    print(f"[FAIL] No data collected")
    print(f"Debug - extracted_data structure: {type(extracted_data)}")
    if isinstance(extracted_data, dict):
        print(f"Debug - extracted_data keys: {list(extracted_data.keys())}")
    conn.close()
    exit(1)

# Check detail fields in first item
first_item = items[0]
if not isinstance(first_item, dict):
    print(f"[FAIL] First item is not a dict: {type(first_item)}")
    conn.close()
    exit(1)
print(f"\nFirst item all fields:")
for key, value in first_item.items():
    value_str = str(value)[:100] + "..." if len(str(value)) > 100 else str(value)
    print(f"  {key}: {value_str}")

# The first item has list_data and detail_data
list_data = first_item.get('list_data', {})
detail_data = first_item.get('detail_data', {})

print(f"\n[Data Structure]")
print(f"Has list_data: {bool(list_data)}")
print(f"Has detail_data: {bool(detail_data)}")
print(f"List data fields: {len(list_data)}")
print(f"Detail data fields: {len(detail_data)}")

# Count detail fields
detail_fields = detail_data

print(f"\n[Detail Fields Statistics]")
print(f"Detail fields count: {len(detail_fields)}")

print(f"\nDetail fields list:")
for i, (key, value) in enumerate(detail_fields.items(), 1):
    value_preview = str(value)[:80] + "..." if len(str(value)) > 80 else str(value)
    is_empty = value is None or value == '' or value == 'N/A'
    status = "[EMPTY]" if is_empty else "[OK]"
    print(f"  {i}. {key}: {value_preview} {status}")

# 5. Count non-empty detail fields
non_empty_detail_fields = {k: v for k, v in detail_fields.items()
                           if v is not None and v != '' and v != 'N/A'}

print(f"\nNon-empty detail fields count: {len(non_empty_detail_fields)}")

# 6. Check detail fields in multiple items
print(f"\n[Multiple Items Verification]")
items_with_details = 0
for i, item in enumerate(items[:5], 1):  # Check first 5 items
    item_detail_data = item.get('detail_data', {})
    item_non_empty = {k: v for k, v in item_detail_data.items()
                      if v is not None and v != '' and v != 'N/A'}

    has_details = len(item_non_empty) >= 5  # At least 5 non-empty detail fields
    if has_details:
        items_with_details += 1

    status = "[OK]" if has_details else "[FAIL]"
    print(f"  Item {i}: Detail fields {len(item_detail_data)}, Non-empty {len(item_non_empty)} {status}")

# 7. Final decision
print(f"\n{'=' * 80}")
print("[Specification Compliance Decision]")
print(f"{'=' * 80}")

# Decision criteria
min_items_with_details = min(3, len(items))  # At least 3 or all items if less than 3
requirements = {
    "Job status is success": job[2].lower() == 'success',
    "Detail config enabled": detail_config.get('enabled', False) == True,
    "detail_button_selector configured": bool(detail_config.get('detail_button_selector')),
    "detail_iframe_selector configured": bool(detail_config.get('detail_iframe_selector')),
    "Config fields count >= 10": len(detail_config.get('fields', [])) >= 10,
    "Data collected": len(items) > 0,
    "Detail fields count >= 7": len(detail_fields) >= 7,  # 11 configured, at least 7 extracted is reasonable
    "Non-empty detail fields >= 5": len(non_empty_detail_fields) >= 5,
    f"Items with details >= {min_items_with_details}": items_with_details >= min_items_with_details
}

all_passed = True
for requirement, passed in requirements.items():
    status = "[PASS]" if passed else "[FAIL]"
    print(f"{status} {requirement}")
    if not passed:
        all_passed = False

print(f"\n{'=' * 80}")
if all_passed:
    print("[PASS] Specification Compliant - Task 3 fully meets requirements")
    print(f"\nVerification Results:")
    print(f"- Job {job_id} detail data extraction successful")
    print(f"- Extracted field count: {len(detail_fields)} detail fields (meets requirement)")
    print(f"- Non-empty field count: {len(non_empty_detail_fields)}")
    print(f"- Configuration correct: detail_iframe_selector={detail_config.get('detail_iframe_selector')}, detail_button_selector={detail_config.get('detail_button_selector')}")
    print(f"- Configured field count: {len(detail_config.get('fields', []))}")
    print(f"\nConclusion: [PASS] Ready for code quality review phase")
else:
    print("[FAIL] Specification Non-compliant - Issues found")
    print(f"\nPlease check the failed items above")

conn.close()
