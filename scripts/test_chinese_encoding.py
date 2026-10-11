"""
测试 SQL Server 中文编码是否正常

使用方法：
    python scripts/test_chinese_encoding.py
"""
import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.core.database import get_session
from app.models.config import CrawlerConfig
from sqlalchemy import text


async def test_database_collation():
    """测试数据库排序规则"""
    print("\n" + "="*60)
    print("1. 检查数据库排序规则（COLLATE）")
    print("="*60)

    async with get_session() as session:
        # 查询数据库 COLLATE
        result = await session.execute(
            text("SELECT DATABASEPROPERTYEX('bap', 'Collation') AS DatabaseCollation")
        )
        row = result.fetchone()
        collation = row[0] if row else "Unknown"

        print(f"数据库排序规则: {collation}")
        if "Chinese_PRC_CI_AS" in collation or "UTF8" in collation:
            print("✓ 数据库排序规则支持中文")
        else:
            print("✗ 警告：数据库排序规则可能不支持中文")


async def test_table_columns():
    """测试表字段类型"""
    print("\n" + "="*60)
    print("2. 检查 crawler_configs 表字段类型")
    print("="*60)

    async with get_session() as session:
        result = await session.execute(text("""
            SELECT
                COLUMN_NAME,
                DATA_TYPE,
                CHARACTER_MAXIMUM_LENGTH,
                COLLATION_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_NAME = 'crawler_configs'
                AND DATA_TYPE IN ('varchar', 'nvarchar', 'text', 'ntext')
            ORDER BY ORDINAL_POSITION
        """))

        print(f"{'字段名':<30} {'类型':<15} {'长度':<10} {'排序规则'}")
        print("-" * 80)

        all_unicode = True
        for row in result:
            col_name, data_type, max_length, collation = row
            print(f"{col_name:<30} {data_type:<15} {str(max_length) if max_length else 'MAX':<10} {collation or 'N/A'}")

            # 检查是否使用 NVARCHAR（支持 Unicode）
            if data_type.lower() in ['varchar', 'text']:
                all_unicode = False

        if all_unicode:
            print("\n✓ 所有文本字段都使用 NVARCHAR（支持 Unicode）")
        else:
            print("\n✗ 警告：某些字段使用 VARCHAR，可能不支持中文")


async def test_insert_chinese():
    """测试插入和查询中文数据"""
    print("\n" + "="*60)
    print("3. 测试插入和查询中文数据")
    print("="*60)

    test_data = {
        "config_name": "测试中文编码_国家医保局",
        "target_url": "https://测试.中国/搜索",
        "auth_profile": "测试账号",
        "input_configs": [
            {
                "selector": "input[name='关键词']",
                "param_name": "注册证号",
                "input_method": "输入"
            }
        ],
        "fields_mapping": {
            "fields": [
                {"name": "耗材名称", "selector": "td:nth-child(1)"},
                {"name": "注册证号", "selector": "td:nth-child(2)"},
                {"name": "生产企业", "selector": "td:nth-child(3)"}
            ]
        }
    }

    async with get_session() as session:
        # 插入测试数据
        print(f"\n插入测试数据: {test_data['config_name']}")

        config = CrawlerConfig(
            config_name=test_data["config_name"],
            target_url=test_data["target_url"],
            need_login=False,
            auth_profile=test_data["auth_profile"],
            input_configs=test_data["input_configs"],
            submit_selector="button.查询",
            wait_selector=".结果列表",
            fields_mapping=test_data["fields_mapping"],
            priority=5,
            max_pages=1
        )

        session.add(config)
        await session.commit()
        config_id = config.id

        print(f"✓ 插入成功，ID: {config_id}")

        # 查询验证
        print(f"\n查询 ID={config_id} 的数据...")
        result = await session.get(CrawlerConfig, config_id)

        if not result:
            print("✗ 查询失败：找不到记录")
            return False

        # 验证字段
        print(f"\n数据库返回内容:")
        print(f"  配置名称: {result.config_name}")
        print(f"  目标URL: {result.target_url}")
        print(f"  登录配置: {result.auth_profile}")
        print(f"  输入配置: {result.input_configs}")
        print(f"  字段映射: {result.fields_mapping}")

        # 检查是否有乱码
        success = True
        if result.config_name != test_data["config_name"]:
            print(f"\n✗ 配置名称不匹配！")
            print(f"  期望: {test_data['config_name']}")
            print(f"  实际: {result.config_name}")
            success = False

        if result.target_url != test_data["target_url"]:
            print(f"\n✗ 目标URL不匹配！")
            print(f"  期望: {test_data['target_url']}")
            print(f"  实际: {result.target_url}")
            success = False

        # 检查 JSON 字段中的中文
        if result.input_configs[0]["param_name"] != "注册证号":
            print(f"\n✗ JSON 字段中文不匹配！")
            print(f"  期望: 注册证号")
            print(f"  实际: {result.input_configs[0]['param_name']}")
            success = False

        # 清理测试数据
        print(f"\n清理测试数据（ID={config_id}）...")
        await session.delete(result)
        await session.commit()
        print("✓ 测试数据已清理")

        return success


async def main():
    print("\n" + "="*60)
    print("  SQL Server 中文编码测试")
    print("="*60)

    try:
        # 测试 1: 数据库排序规则
        await test_database_collation()

        # 测试 2: 表字段类型
        await test_table_columns()

        # 测试 3: 插入和查询中文
        success = await test_insert_chinese()

        # 总结
        print("\n" + "="*60)
        print("  测试结果总结")
        print("="*60)

        if success:
            print("\n✓ 所有测试通过！中文编码正常工作。")
            print("\n建议：")
            print("  1. 确保 .env 中的 DATABASE_URL 包含 charset=UTF-8")
            print("  2. 数据库创建时使用 COLLATE Chinese_PRC_CI_AS")
            print("  3. 使用 NVARCHAR 而非 VARCHAR 存储中文")
        else:
            print("\n✗ 测试失败！中文编码存在问题。")
            print("\n解决方案：")
            print("  1. 修改 .env 文件，在 DATABASE_URL 中添加 &charset=UTF-8")
            print("  2. 执行数据库迁移: alembic upgrade head")
            print("  3. 如果还是失败，参考 docs/FIX_CHINESE_ENCODING.md")

        print("\n" + "="*60)

    except Exception as e:
        print(f"\n✗ 测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
