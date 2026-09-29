"""验证数据库迁移结果"""
from sqlalchemy import create_engine, inspect
import os
from dotenv import load_dotenv

load_dotenv()

# 创建同步引擎用于验证（使用pymysql）
DATABASE_URL = os.getenv('DATABASE_URL', 'mysql+pymysql://root:root@localhost:3306/bap')
if 'aiomysql' in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace('aiomysql', 'pymysql')

sync_engine = create_engine(DATABASE_URL)

try:
    inspector = inspect(sync_engine)

    # 检查 crawler_configs 新字段
    config_cols = [col['name'] for col in inspector.get_columns('crawler_configs')]
    assert 'timeout_config' in config_cols, 'timeout_config 字段未找到'
    assert 'extraction_config' in config_cols, 'extraction_config 字段未找到'
    assert 'priority' in config_cols, 'priority 字段未找到'

    # 检查 system_configs 表
    assert 'system_configs' in inspector.get_table_names(), 'system_configs 表未找到'

    # 检查 system_configs 表结构
    system_cols = [col['name'] for col in inspector.get_columns('system_configs')]
    assert 'config_key' in system_cols
    assert 'config_value' in system_cols
    assert 'description' in system_cols
    assert 'updated_at' in system_cols

    # 检查 job_queue 的 priority 字段
    job_cols = [col['name'] for col in inspector.get_columns('job_queue')]
    assert 'priority' in job_cols, 'job_queue.priority 字段未找到'

    print('[PASS] Database migration verification passed')
    print('[PASS] crawler_configs new fields: timeout_config, extraction_config, priority')
    print(f'[PASS] system_configs table created with fields: {", ".join(system_cols)}')
    print('[PASS] job_queue new field: priority')

    # 验证默认配置数据
    from sqlalchemy import text
    with sync_engine.connect() as conn:
        result = conn.execute(text("SELECT config_key, config_value FROM system_configs"))
        configs = result.fetchall()
        print(f'[PASS] Default system configs inserted: {len(configs)} records')
        for key, value in configs:
            print(f'  - {key}: {value}')

except Exception as e:
    print(f'[FAIL] Verification failed: {e}')
    raise
finally:
    sync_engine.dispose()
