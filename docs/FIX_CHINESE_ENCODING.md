# SQL Server 中文编码问题修复指南

## 问题描述

SQL Server 数据库中的中文内容显示为 ASCII 转义字符，而不是原始中文文本。这是由于：
1. 数据库连接字符串缺少编码参数
2. 表字段使用 VARCHAR 而非 NVARCHAR（不支持 Unicode）
3. 缺少 COLLATE 排序规则设置

## 解决方案

### 方案 1：修改连接字符串（推荐，无需迁移）

在 `.env` 文件中的 `DATABASE_URL` 添加 `charset=UTF-8` 参数：

```bash
# 修改前
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server

# 修改后（添加 &charset=UTF-8）
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server&charset=UTF-8
```

**优点**：
- 无需修改数据库表结构
- 立即生效，只需重启应用
- 不影响现有数据

**适用场景**：
- 数据库已创建时使用了 `COLLATE Chinese_PRC_CI_AS`
- 只是连接层面的编码问题

### 方案 2：执行数据库迁移（彻底解决）

如果方案 1 不生效，说明表结构本身存在问题，需要执行迁移：

```bash
# 1. 检查当前迁移状态
alembic current

# 2. 执行迁移（将 VARCHAR 改为 NVARCHAR + COLLATE）
alembic upgrade head

# 3. 验证迁移
alembic history
```

**迁移内容**：
- 将所有 `VARCHAR` 字段改为 `NVARCHAR`（支持 Unicode）
- 为所有文本字段添加 `COLLATE Chinese_PRC_CI_AS`

**影响的表和字段**：
- `crawler_configs`: config_name, target_url, auth_profile, login_url, submit_selector, wait_selector, pagination_selector
- `job_queue`: error_msg
- `alert_rules`: rule_name, metric_name, condition
- `alert_history`: notify_status, alert_message, notify_error
- `system_configs`: config_key, config_value, description
- `metrics_timeseries`: metric_name

### 方案 3：重建数据库（最彻底，适合开发环境）

如果是开发环境且数据不重要，可以重建数据库：

```bash
# 1. 备份数据（如果需要）
python scripts/export_sample_data.py

# 2. 删除数据库
sqlcmd -S localhost -U sa -P YourPassword -Q "DROP DATABASE bap;"

# 3. 重新创建数据库（指定 COLLATE）
sqlcmd -S localhost -U sa -P YourPassword -Q "CREATE DATABASE bap COLLATE Chinese_PRC_CI_AS;"

# 4. 执行迁移
alembic upgrade head

# 5. 导入数据（如果需要）
python scripts/batch_import_*.py
```

## 验证修复效果

### 1. 测试插入中文数据

```python
# test_chinese_encoding.py
import asyncio
from app.core.database import get_session
from app.models.config import CrawlerConfig

async def test_chinese():
    async with get_session() as session:
        # 插入测试数据
        config = CrawlerConfig(
            config_name="测试中文编码",
            target_url="https://example.com",
            need_login=False,
            input_configs=[{"selector": "input", "param_name": "关键词"}],
            submit_selector="button",
            wait_selector=".result",
            fields_mapping={"fields": [{"name": "名称", "selector": "td"}]},
            priority=5,
            max_pages=1
        )
        session.add(config)
        await session.commit()
        print(f"插入成功，ID: {config.id}, 名称: {config.config_name}")
        
        # 查询验证
        result = await session.get(CrawlerConfig, config.id)
        print(f"查询结果: {result.config_name}")
        assert result.config_name == "测试中文编码", "中文显示不正确！"
        print("✓ 中文编码测试通过")

if __name__ == "__main__":
    asyncio.run(test_chinese())
```

运行测试：
```bash
python test_chinese_encoding.py
```

### 2. 检查数据库字段类型

```sql
-- 查看表结构
SELECT 
    TABLE_NAME,
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH,
    COLLATION_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'crawler_configs'
ORDER BY ORDINAL_POSITION;
```

**预期结果**：
- `DATA_TYPE` 应为 `nvarchar`（而非 `varchar`）
- `COLLATION_NAME` 应为 `Chinese_PRC_CI_AS`

### 3. 测试现有数据

```sql
-- 查询现有配置
SELECT id, config_name, target_url FROM crawler_configs;

-- 如果看到乱码，说明旧数据已损坏，需要重新导入
```

## 常见问题

### Q1: 执行迁移后还是乱码？
**A**: 旧数据可能已经损坏。方案：
1. 删除旧数据：`DELETE FROM crawler_configs;`
2. 重新导入配置：`python scripts/init_nhsa_registration_config.py`

### Q2: 迁移报错 "Cannot alter column because it is part of an index"？
**A**: 需要先删除索引，修改列，再重建索引：
```sql
-- 1. 查看索引
EXEC sp_helpindex 'crawler_configs';

-- 2. 删除相关索引
DROP INDEX idx_auth_profile ON crawler_configs;

-- 3. 执行迁移
alembic upgrade head

-- 4. 重建索引（迁移脚本应该自动处理）
```

### Q3: 连接字符串中已有 charset=UTF-8，但还是乱码？
**A**: 检查 ODBC 驱动版本：
```bash
# Windows 上查看已安装的 ODBC 驱动
odbcad32
```

推荐使用 **ODBC Driver 17 for SQL Server** 或更新版本。

### Q4: JSON 字段中的中文也乱码？
**A**: JSON 字段（`input_configs`, `fields_mapping`, `query_params` 等）存储的是 JSON 文本，也受字符编码影响。解决方案：
1. 确保列类型为 `NVARCHAR(MAX)` 或 `NTEXT`
2. 在 Python 中确保使用 UTF-8：
```python
import json
data = {"名称": "测试"}
json_str = json.dumps(data, ensure_ascii=False)  # 关键：ensure_ascii=False
```

## 数据库连接字符串完整示例

```bash
# Windows 认证
DATABASE_URL=mssql+aioodbc://localhost/bap?driver=ODBC+Driver+17+for+SQL+Server&charset=UTF-8&TrustServerCertificate=yes

# SQL Server 认证
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server&charset=UTF-8

# 远程服务器
DATABASE_URL=mssql+aioodbc://user:pass@192.168.1.100:1433/bap?driver=ODBC+Driver+17+for+SQL+Server&charset=UTF-8&Encrypt=yes
```

## 最佳实践

1. **新建数据库时就指定 COLLATE**：
   ```sql
   CREATE DATABASE bap COLLATE Chinese_PRC_CI_AS;
   ```

2. **连接字符串始终包含 charset=UTF-8**：
   ```
   ?driver=ODBC+Driver+17+for+SQL+Server&charset=UTF-8
   ```

3. **Python 代码中处理 JSON 时使用 ensure_ascii=False**：
   ```python
   json.dumps(data, ensure_ascii=False, indent=2)
   ```

4. **SQLAlchemy 模型中显式指定 Unicode 类型**：
   ```python
   from sqlalchemy import String
   
   class Model(Base):
       name = Column(String(100, collation='Chinese_PRC_CI_AS'), nullable=False)
   ```

## 回滚方案

如果迁移出现问题，可以回滚：

```bash
# 回滚到上一个版本
alembic downgrade -1

# 回滚到指定版本
alembic downgrade f1028eaaa97b

# 查看可回滚的版本
alembic history
```

## 总结

**推荐操作顺序**：
1. 先尝试**方案 1**（修改连接字符串） → 重启应用 → 测试
2. 如果无效，执行**方案 2**（数据库迁移） → 重新导入数据
3. 开发环境可直接使用**方案 3**（重建数据库）

**核心要点**：
- SQL Server 中文必须用 `NVARCHAR`（而非 `VARCHAR`）
- 连接字符串添加 `charset=UTF-8`
- 数据库/表设置 `COLLATE Chinese_PRC_CI_AS`
- Python JSON 处理使用 `ensure_ascii=False`
