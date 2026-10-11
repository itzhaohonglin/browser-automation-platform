"""
数据导入脚本 - 支持多种格式导入

支持格式：
- 文本文件 (.txt)
- Excel 文件 (.xlsx, .xls)
- CSV 文件 (.csv)

使用方法：
    python import_data.py --file data.txt --config-id 44
    python import_data.py --excel data.xlsx --column "注册证号" --config-id 44
    python import_data.py --csv data.csv --column "注册证号" --config-id 44
"""

import asyncio
import argparse
import sys
from pathlib import Path
from typing import List, Optional

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig
from app.models.job import JobQueue


def read_text_file(file_path: str) -> List[str]:
    """从文本文件读取注册证号"""
    registration_numbers = []

    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()

            # 跳过注释行和空行
            if not line or line.startswith('#'):
                continue

            registration_numbers.append(line)

    return registration_numbers


def read_excel_file(file_path: str, column_name: str = "注册证号") -> List[str]:
    """从 Excel 文件读取注册证号"""
    try:
        import pandas as pd
    except ImportError:
        print("[错误] 未安装 pandas 库")
        print("请运行: pip install pandas openpyxl")
        sys.exit(1)

    # 读取 Excel
    df = pd.read_excel(file_path)

    # 检查列是否存在
    if column_name not in df.columns:
        print(f"[错误] Excel 文件中未找到列: {column_name}")
        print(f"可用的列: {', '.join(df.columns)}")
        sys.exit(1)

    # 提取注册证号（去除空值）
    registration_numbers = df[column_name].dropna().astype(str).tolist()

    return registration_numbers


def read_csv_file(file_path: str, column_name: str = "注册证号") -> List[str]:
    """从 CSV 文件读取注册证号"""
    try:
        import pandas as pd
    except ImportError:
        print("[错误] 未安装 pandas 库")
        print("请运行: pip install pandas")
        sys.exit(1)

    # 读取 CSV
    df = pd.read_csv(file_path, encoding='utf-8')

    # 检查列是否存在
    if column_name not in df.columns:
        print(f"[错误] CSV 文件中未找到列: {column_name}")
        print(f"可用的列: {', '.join(df.columns)}")
        sys.exit(1)

    # 提取注册证号（去除空值）
    registration_numbers = df[column_name].dropna().astype(str).tolist()

    return registration_numbers


async def import_jobs(
    registration_numbers: List[str],
    config_id: int,
    param_name: str = "registration_no"
) -> List[int]:
    """
    批量导入任务

    Args:
        registration_numbers: 注册证号列表
        config_id: 配置ID
        param_name: 参数名称（对应 input_configs 中的 param_name）

    Returns:
        创建的任务ID列表
    """
    print("=" * 80)
    print("批量导入任务")
    print("=" * 80)
    print()

    async with get_session() as session:
        # 验证配置是否存在
        config = await session.get(CrawlerConfig, config_id)
        if not config:
            print(f"[错误] 配置ID {config_id} 不存在")
            print()
            print("请先创建配置或指定正确的配置ID")
            sys.exit(1)

        print(f"使用配置: {config.config_name} (ID: {config_id})")
        print(f"待导入数量: {len(registration_numbers)} 个")
        print()

        # 去重
        unique_numbers = list(set(registration_numbers))
        if len(unique_numbers) < len(registration_numbers):
            print(f"[提示] 去重后剩余 {len(unique_numbers)} 个唯一值")
            print()

        # 创建任务
        created_jobs = []

        for idx, reg_no in enumerate(unique_numbers, 1):
            job = JobQueue(
                config_id=config_id,
                query_params={
                    param_name: reg_no
                },
                status="pending"
            )
            session.add(job)
            await session.flush()  # 获取 job.id

            print(f"[{idx}/{len(unique_numbers)}] 创建任务 ID={job.id}, {param_name}={reg_no}")
            created_jobs.append(job.id)

        await session.commit()

        print()
        print(f"✓ 成功创建 {len(created_jobs)} 个任务")
        print(f"✓ 任务ID范围: {min(created_jobs)} - {max(created_jobs)}")

        return created_jobs


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="数据导入工具")

    # 输入文件
    parser.add_argument("--file", help="文本文件路径 (.txt)")
    parser.add_argument("--excel", help="Excel 文件路径 (.xlsx, .xls)")
    parser.add_argument("--csv", help="CSV 文件路径 (.csv)")

    # 配置参数
    parser.add_argument("--column", default="注册证号", help="Excel/CSV 列名（默认：注册证号）")
    parser.add_argument("--config-id", type=int, required=True, help="配置ID")
    parser.add_argument("--param-name", default="registration_no", help="参数名称（默认：registration_no）")

    args = parser.parse_args()

    # 确定导入方式
    registration_numbers = []

    if args.file:
        print(f"[读取] 文本文件: {args.file}")
        registration_numbers = read_text_file(args.file)

    elif args.excel:
        print(f"[读取] Excel 文件: {args.excel}")
        registration_numbers = read_excel_file(args.excel, args.column)

    elif args.csv:
        print(f"[读取] CSV 文件: {args.csv}")
        registration_numbers = read_csv_file(args.csv, args.column)

    else:
        print("[错误] 请指定输入文件")
        print()
        print("使用方法：")
        print("  python import_data.py --file data.txt --config-id 44")
        print("  python import_data.py --excel data.xlsx --column 注册证号 --config-id 44")
        print("  python import_data.py --csv data.csv --column 注册证号 --config-id 44")
        sys.exit(1)

    if not registration_numbers:
        print("[错误] 文件中没有有效数据")
        sys.exit(1)

    print(f"[完成] 读取到 {len(registration_numbers)} 条数据")
    print()

    # 导入任务
    job_ids = await import_jobs(
        registration_numbers=registration_numbers,
        config_id=args.config_id,
        param_name=args.param_name
    )

    # 输出执行说明
    print()
    print("=" * 80)
    print("执行任务")
    print("=" * 80)
    print()
    print("方法1：通过前端看板")
    print("  访问: http://127.0.0.1:8000/static/index.html")
    print("  找到对应任务，点击执行")
    print()
    print("方法2：通过 API 批量执行")
    print(f"  for job_id in range({min(job_ids)}, {max(job_ids) + 1})")
    print("      curl -X POST http://127.0.0.1:8000/api/jobs/$job_id/execute")
    print()
    print("方法3：等待调度器自动执行")
    print("  调度器会在每30分钟扫描 pending 状态的任务并执行")
    print()


if __name__ == "__main__":
    try:
        if sys.platform == "win32":
            # Windows 平台需要设置事件循环策略
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(0)
    except Exception as e:
        print(f"\n[错误] 导入失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
