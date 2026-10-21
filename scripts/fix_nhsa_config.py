"""
修复NHSA配置 - 更新输入框选择器
"""
import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from sqlalchemy import create_engine, text
from app.core.config import settings
import json

def fix_config_sync():
    """同步方式修复配置"""
    # 创建同步引擎（一次性脚本，使用较小的连接池）
    engine = create_engine(
        settings.DATABASE_URL.replace('aioodbc', 'pyodbc'),
        pool_pre_ping=True,            # 使用前检测连接有效性
        pool_size=2,                   # 脚本只需要少量连接
        max_overflow=1,                # 最小溢出
        pool_recycle=600,              # 10分钟回收
        pool_timeout=30                # 获取连接超时
    )

    try:
        with engine.connect() as conn:
        # 更新输入框配置
        new_input_configs = json.dumps([{
            "selector": "input[name='regcardNm']",
            "param_name": "registration_no",
            "label": "注册证号",
            "required": True
        }])

        result = conn.execute(text("""
            UPDATE crawler_configs
            SET input_configs = :new_config
            WHERE id = 1
        """), {
            'new_config': new_input_configs
        })

        conn.commit()

        print("="*80)
        print("配置更新成功！")
        print("="*80)

        # 验证更新
        verify = conn.execute(text("SELECT input_configs FROM crawler_configs WHERE id = 1"))
        row = verify.fetchone()

        if row:
            updated_config = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            print("\n更新后的配置:")
            print(json.dumps(updated_config, indent=2, ensure_ascii=False))

            print("\n验证:")
            if updated_config[0]['selector'] == "input[name='regcardNm']":
                print("✓ 输入框选择器已正确更新")
            else:
                print("✗ 输入框选择器更新失败")
    finally:
        # 确保关闭引擎，释放连接
        engine.dispose()

if __name__ == "__main__":
    fix_config_sync()
