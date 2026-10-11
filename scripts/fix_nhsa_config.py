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
    engine = create_engine(settings.DATABASE_URL.replace('aioodbc', 'pyodbc'))

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

if __name__ == "__main__":
    fix_config_sync()
