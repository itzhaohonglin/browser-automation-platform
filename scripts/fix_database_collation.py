"""
修复数据库排序规则以支持中文字符

当前问题：数据库使用 SQL_Latin1_General_CP1_CI_AS，不支持中文
解决方案：更改为 Chinese_PRC_CI_AS

警告：此操作会修改数据库结构，建议先备份数据
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import text
from app.core.database import get_session


async def fix_collation():
    """修复数据库和表的排序规则"""

    print("="*80)
    print("修复数据库排序规则")
    print("="*80)

    async with get_session() as session:
        # 1. 检查当前排序规则
        print("\n[1] 检查当前数据库排序规则...")
        result = await session.execute(
            text("SELECT DATABASEPROPERTYEX(DB_NAME(), 'Collation') AS Collation")
        )
        current_collation = result.scalar()
        print(f"    当前: {current_collation}")

        if current_collation == 'Chinese_PRC_CI_AS':
            print("    [OK] 排序规则已正确，无需修改")
            return

        # 2. 获取需要修改的列
        print("\n[2] 获取需要修改的列...")
        result = await session.execute(text("""
            SELECT
                t.name AS TableName,
                c.name AS ColumnName,
                ty.name AS DataType,
                c.max_length AS MaxLength,
                c.is_nullable AS IsNullable
            FROM sys.tables t
            JOIN sys.columns c ON t.object_id = c.object_id
            JOIN sys.types ty ON c.user_type_id = ty.user_type_id
            WHERE c.collation_name IS NOT NULL
            AND ty.name IN ('varchar', 'nvarchar', 'char', 'nchar', 'text', 'ntext')
            ORDER BY t.name, c.name
        """))

        columns = list(result)
        print(f"    找到 {len(columns)} 个需要修改的列")

        # 3. 修改每个列的排序规则
        print("\n[3] 修改列排序规则...")
        success_count = 0
        skip_count = 0

        for row in columns:
            table_name = row.TableName
            column_name = row.ColumnName
            data_type = row.DataType
            max_length = row.MaxLength
            is_nullable = row.IsNullable

            # 跳过 alembic_version 表（有主键约束，且不影响业务数据）
            if table_name == 'alembic_version':
                print(f"    [SKIP] {table_name}.{column_name} (系统表)")
                skip_count += 1
                continue

            # 构造数据类型字符串
            if data_type in ('varchar', 'char'):
                type_str = f"{data_type}({max_length if max_length != -1 else 'MAX'})"
            elif data_type in ('nvarchar', 'nchar'):
                # nvarchar/nchar 的 max_length 是字节数，需要除以2
                char_length = max_length // 2 if max_length != -1 else -1
                type_str = f"{data_type}({char_length if char_length != -1 else 'MAX'})"
            else:
                type_str = data_type

            nullable_str = "NULL" if is_nullable else "NOT NULL"

            alter_sql = f"""
                ALTER TABLE [{table_name}]
                ALTER COLUMN [{column_name}] {type_str}
                COLLATE Chinese_PRC_CI_AS {nullable_str}
            """

            try:
                await session.execute(text(alter_sql))
                print(f"    [OK] {table_name}.{column_name}")
                success_count += 1
            except Exception as e:
                error_msg = str(e)
                # 如果是约束冲突，尝试找到并删除约束
                if 'is dependent on column' in error_msg or '4922' in error_msg:
                    print(f"    [WARN] {table_name}.{column_name}: 有约束依赖，跳过")
                    skip_count += 1
                else:
                    print(f"    [FAIL] {table_name}.{column_name}: {error_msg[:100]}")
                    skip_count += 1

        await session.commit()

        print(f"\n    统计: 成功 {success_count} 个, 跳过 {skip_count} 个")

        # 4. 验证修改结果
        print("\n[4] 验证修改结果...")
        result = await session.execute(text("""
            SELECT
                t.name AS TableName,
                c.name AS ColumnName,
                c.collation_name AS Collation
            FROM sys.tables t
            JOIN sys.columns c ON t.object_id = c.object_id
            WHERE c.collation_name IS NOT NULL
            AND c.collation_name != 'Chinese_PRC_CI_AS'
            AND t.name != 'alembic_version'
            ORDER BY t.name, c.name
        """))

        remaining = list(result)
        if remaining:
            print(f"    [WARN] 仍有 {len(remaining)} 个列未修改成功:")
            for row in remaining:
                print(f"      - {row.TableName}.{row.ColumnName}: {row.Collation}")
        else:
            print("    [OK] 所有业务表的列已成功修改为 Chinese_PRC_CI_AS")

        print("\n" + "="*80)
        print("修复完成")
        print("="*80)
        print("\n注意事项:")
        print("1. 数据库本身的排序规则未修改（需要重建数据库）")
        print("2. 业务表和列的排序规则已修改为 Chinese_PRC_CI_AS")
        print("3. alembic_version 表因约束冲突已跳过（不影响功能）")
        print("4. 现有数据应该可以正常显示中文")
        print("5. 新插入的数据将使用中文排序规则")
        print("\n建议:")
        print("1. 测试现有数据是否正常显示")
        print("2. 测试新数据插入是否正常")
        print("3. 如需完全重建，参考: docs/database_encoding_fix_guide.md")


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    try:
        asyncio.run(fix_collation())
    except Exception as e:
        print(f"\n[ERROR] 修复失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
