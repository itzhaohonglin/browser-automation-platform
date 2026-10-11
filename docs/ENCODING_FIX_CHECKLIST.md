====================================
  中文编码修复 - 快速检查清单
====================================

在执行迁移前，请确认以下配置：

## ✅ 配置检查清单

### 1. 环境变量配置 (.env)

打开 .env 文件，检查 DATABASE_URL：

❌ 错误示例：
DATABASE_URL=mssql+aioodbc://sa:Pass@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server

✅ 正确示例：
DATABASE_URL=mssql+aioodbc://sa:Pass@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server&charset=UTF-8
                                                                                            ^^^^^^^^^^^^^^^^
                                                                                            必须有这个！

### 2. 数据库创建

检查数据库是否指定了 COLLATE：

```sql
-- 查询数据库排序规则
SELECT DATABASEPROPERTYEX('bap', 'Collation') AS DatabaseCollation;
```

期望结果：`Chinese_PRC_CI_AS`

如果不是，需要重建数据库：
```sql
DROP DATABASE bap;
CREATE DATABASE bap COLLATE Chinese_PRC_CI_AS;
```

### 3. 数据库连接测试

```bash
# 测试连接
python -c "from app.core.config import settings; print('DATABASE_URL:', settings.DATABASE_URL)"
```

应该能看到完整的连接字符串（包含 charset=UTF-8）

### 4. 迁移脚本检查

```bash
# 查看迁移脚本是否存在
ls alembic/versions/19798be7d82c_fix_chinese_encoding_add_collate.py
```

应该显示文件存在

## 🚀 执行迁移

配置检查通过后，执行：

```bash
# 1. 查看当前状态
alembic current

# 2. 执行迁移
alembic upgrade head

# 3. 验证结果
python scripts/test_chinese_encoding.py
```

## 📊 验证结果

### 测试脚本输出应该包含：

✓ 数据库排序规则: Chinese_PRC_CI_AS
✓ 所有文本字段都使用 NVARCHAR（支持 Unicode）
✓ 所有测试通过！中文编码正常工作。

### 或手动验证：

```sql
-- 查看字段类型（应该是 nvarchar）
SELECT COLUMN_NAME, DATA_TYPE, COLLATION_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'crawler_configs' AND COLUMN_NAME = 'config_name';
```

期望结果：
- DATA_TYPE: nvarchar
- COLLATION_NAME: Chinese_PRC_CI_AS

## ⚠️ 常见错误

### 错误 1：连接失败
```
sqlalchemy.exc.InterfaceError: Login failed for user 'sa'
```
→ 检查 .env 中的数据库密码是否正确

### 错误 2：字符集错误
```
UnicodeDecodeError: 'ascii' codec can't decode
```
→ 检查 DATABASE_URL 是否包含 &charset=UTF-8

### 错误 3：中文还是乱码
→ 旧数据已损坏，需要重新导入配置

## 📝 完成标志

全部完成后，你应该能够：

✅ 创建包含中文的配置
✅ 在数据库中看到正确的中文
✅ 在前端页面正常显示中文
✅ JSON 字段中的中文也正常

====================================
