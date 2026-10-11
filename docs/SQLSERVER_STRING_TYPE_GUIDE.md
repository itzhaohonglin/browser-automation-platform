# SQL Server String 类型说明文档

## 问题：SQLAlchemy String() 在 SQL Server 上的映射

### 默认行为
```python
String(100)  →  SQL Server: VARCHAR(100)  ❌ 不支持中文
```

### 正确做法：指定 Unicode
```python
String(100)  →  NVARCHAR(100) ✅ 支持中文
```

## 解决方案

### 方案 1：修改模型定义（推荐）

在所有模型中使用 `String()` 时添加 `collation` 参数：

```python
from sqlalchemy import String

# 修改前
config_name: Mapped[str] = mapped_column(String(100), nullable=False)

# 修改后
config_name: Mapped[str] = mapped_column(
    String(100, collation='Chinese_PRC_CI_AS'), 
    nullable=False
)
```

### 方案 2：全局配置（更简单）

在 `app/models/base.py` 中配置全局默认值，让所有 String 自动使用 NVARCHAR：

```python
# app/models/base.py
from sqlalchemy import String
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    """所有模型的基类"""
    
    # 全局类型映射：String → NVARCHAR (SQL Server)
    type_annotation_map = {
        str: String().with_variant(
            String(collation='Chinese_PRC_CI_AS'), 
            'mssql'
        )
    }
```

### 方案 3：只通过迁移修改（最简单，但不彻底）

不修改模型代码，只通过迁移脚本修改数据库：

```bash
alembic upgrade head
```

优点：不需要改代码
缺点：新建表时还是会用 VARCHAR，需要手动记得修改

## 当前项目的建议

### 立即执行（紧急修复）

```bash
# 1. 执行已创建的迁移脚本（将现有表从 VARCHAR 改为 NVARCHAR）
alembic upgrade head

# 2. 测试
python scripts/test_chinese_encoding.py
```

### 长期方案（防止未来问题）

修改模型定义，确保新建表也使用 NVARCHAR：

1. **更新所有模型文件**
   - `app/models/config.py`
   - `app/models/job.py`
   - `app/models/result.py`
   - `app/models/metrics.py`（如果有）

2. **在每个 String() 字段添加 collation**
   ```python
   String(100, collation='Chinese_PRC_CI_AS')
   ```

## 验证方法

### 1. 查看数据库实际类型
```sql
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH,
    COLLATION_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'crawler_configs'
ORDER BY ORDINAL_POSITION;
```

期望结果：
- `DATA_TYPE` = `nvarchar`（不是 `varchar`）
- `COLLATION_NAME` = `Chinese_PRC_CI_AS`

### 2. 运行测试脚本
```bash
python scripts/test_chinese_encoding.py
```

应该看到：
```
✓ 所有文本字段都使用 NVARCHAR（支持 Unicode）
✓ 所有测试通过！中文编码正常工作。
```

## 注意事项

### VARCHAR vs NVARCHAR 性能影响
- NVARCHAR 每个字符占用 2 字节（VARCHAR 是 1 字节）
- 存储空间增加约 2 倍
- 对于小型系统影响可忽略
- **中文支持的必要代价**

### 已有数据迁移
迁移脚本会自动转换：
- 英文数据：正常转换 ✓
- 中文数据：
  - 如果之前是乱码 → 转换后还是乱码（无法恢复）
  - 如果之前正常 → 转换后保持正常 ✓

### 建议
对于已有乱码数据，迁移后需要重新导入：
```bash
# 删除乱码数据
DELETE FROM crawler_configs WHERE config_name LIKE '%\u%';

# 重新导入
python scripts/init_nhsa_registration_config.py
```
