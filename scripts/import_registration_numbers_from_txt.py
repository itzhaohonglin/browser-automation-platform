"""
批量导入注册证号任务脚本（简化版，直接使用 SQL）

从 docs/1.txt 读取注册证号列表，批量创建任务
"""

import asyncio
import sys
import json
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.core.database import async_engine


async def import_registration_numbers():
    """从 docs/1.txt 批量导入注册证号"""

    print("="*80)
    print("批量导入注册证号任务")
    print("="*80)

    # 读取注册证号列表
    data_file = project_root / "docs" / "1.txt"
    if not data_file.exists():
        print(f"\n[ERROR] 数据文件不存在: {data_file}")
        return

    with open(data_file, "r", encoding="utf-8") as f:
        registration_numbers = [line.strip() for line in f if line.strip()]

    print(f"\n[INFO] 读取到 {len(registration_numbers)} 个注册证号")

    # 连接数据库
    async with async_engine.begin() as conn:
        # 查找 NHSA 配置
        result = await conn.execute(text("""
            SELECT id, config_name
            FROM crawler_configs
            WHERE is_active = 1 AND config_name LIKE '%国家医保局%'
            ORDER BY id DESC
        """))

        config = result.fetchone()

        if not config:
            print("\n[ERROR] 未找到国家医保局相关配置")
            print("[INFO] 请先运行: python scripts/init_nhsa_registration_config.py")
            return

        config_id = config[0]
        config_name = config[1]
        print(f"\n[INFO] 使用配置: {config_name} (ID: {config_id})")

        # 检查已存在的任务
        result = await conn.execute(text("""
            SELECT query_params
            FROM job_queue
            WHERE config_id = :config_id
        """), {"config_id": config_id})

        existing_jobs = result.fetchall()
        existing_params = set()
        for row in existing_jobs:
            try:
                params = json.loads(row[0]) if isinstance(row[0], str) else row[0]
                if isinstance(params, dict) and "registration_no" in params:
                    existing_params.add(params["registration_no"])
            except:
                pass

        print(f"[INFO] 数据库中已有 {len(existing_params)} 个任务")

        # 过滤出需要导入的注册证号
        new_numbers = [num for num in registration_numbers if num not in existing_params]

        if not new_numbers:
            print("\n[INFO] 所有注册证号已存在，无需导入")
            return

        print(f"[INFO] 需要导入 {len(new_numbers)} 个新任务")
        print(f"[INFO] 跳过 {len(registration_numbers) - len(new_numbers)} 个已存在的任务")

        # 确认导入
        print(f"\n即将创建 {len(new_numbers)} 个任务，每个任务查询一个注册证号")
        confirm = input("继续？(y/n): ").strip().lower()

        if confirm != 'y':
            print("\n[INFO] 操作已取消")
            return

        # 批量插入任务
        print(f"\n[START] 开始批量创建任务...")

        batch_size = 100  # 每批次100个
        created_count = 0
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # SQL Server 格式

        for i in range(0, len(new_numbers), batch_size):
            batch = new_numbers[i:i+batch_size]

            # 构建批量插入语句
            values_list = []
            params = {}

            for idx, reg_no in enumerate(batch):
                query_params = json.dumps({"registration_no": reg_no}, ensure_ascii=False)
                param_key = f"qp_{i}_{idx}"
                values_list.append(f"({config_id}, :{param_key}, 'PENDING', 0, 5, '{now}', '{now}')")
                params[param_key] = query_params

            sql = f"""
                INSERT INTO job_queue
                (config_id, query_params, status, retry_count, priority, created_at, updated_at)
                VALUES {', '.join(values_list)}
            """

            await conn.execute(text(sql), params)

            created_count += len(batch)
            print(f"[PROGRESS] 已创建 {created_count}/{len(new_numbers)} 个任务")

        print(f"\n[SUCCESS] 成功导入 {created_count} 个任务")
        print(f"\n任务统计:")
        print(f"  - 配置ID: {config_id}")
        print(f"  - 总任务数: {len(registration_numbers)}")
        print(f"  - 新增任务: {created_count}")
        print(f"  - 已存在: {len(registration_numbers) - created_count}")

        print(f"\n下一步:")
        print(f"  1. 启动服务: python -m app.main")
        print(f"  2. 访问看板: http://127.0.0.1:8000/static/index.html")
        print(f"  3. 任务将自动执行")


if __name__ == "__main__":
    try:
        asyncio.run(import_registration_numbers())
    except KeyboardInterrupt:
        print("\n\n[INFO] 操作已取消")
    except Exception as e:
        print(f"\n[ERROR] 发生错误: {e}")
        import traceback
        traceback.print_exc()
