====================================
  执行中文编码迁移 - 操作指南
====================================

## 前提条件

1. ✅ 数据库已创建并可连接
2. ✅ .env 文件已配置正确的 DATABASE_URL
3. ✅ 已添加 &charset=UTF-8 参数到连接字符串

## 执行步骤

### 步骤 1：检查当前迁移状态

```bash
cd D:\dev\PyCharmProjects\browser-automation-platform
alembic current
```

期望输出：
```
f1028eaaa97b (head)
```

### 步骤 2：查看待执行的迁移

```bash
alembic history
```

应该看到：
```
f1028eaaa97b -> 19798be7d82c (head), fix_chinese_encoding_add_collate
f1028eaaa97b, initial schema for sql server
```

### 步骤 3：执行迁移（关键步骤）

```bash
alembic upgrade head
```

期望输出：
```
INFO  [alembic.runtime.migration] Running upgrade f1028eaaa97b -> 19798be7d82c, fix_chinese_encoding_add_collate
```

**这个步骤会做什么？**
- 将所有 VARCHAR 字段改为 NVARCHAR
- 为所有文本字段添加 COLLATE Chinese_PRC_CI_AS
- 自动保留现有数据（不会丢失）

### 步骤 4：验证迁移结果

#### 方法 1：运行测试脚本（推荐）
```bash
python scripts/test_chinese_encoding.py
```

期望输出：
```
======================================
1. 检查数据库排序规则（COLLATE）
======================================
数据库排序规则: Chinese_PRC_CI_AS
✓ 数据库排序规则支持中文

======================================
2. 检查 crawler_configs 表字段类型
======================================
字段名                          类型            长度       排序规则
--------------------------------------------------------------------------------
config_name                    nvarchar        100        Chinese_PRC_CI_AS
target_url                     nvarchar        500        Chinese_PRC_CI_AS
...
✓ 所有文本字段都使用 NVARCHAR（支持 Unicode）

======================================
3. 测试插入和查询中文数据
======================================
✓ 所有测试通过！中文编码正常工作。
```

#### 方法 2：手动查询数据库
```sql
-- 查看字段类型
SELECT 
    COLUMN_NAME,
    DATA_TYPE,
    CHARACTER_MAXIMUM_LENGTH,
    COLLATION_NAME
FROM INFORMATION_SCHEMA.COLUMNS
WHERE TABLE_NAME = 'crawler_configs'
ORDER BY ORDINAL_POSITION;
```

验证点：
- ✅ DATA_TYPE = 'nvarchar'（不是 'varchar'）
- ✅ COLLATION_NAME = 'Chinese_PRC_CI_AS'

### 步骤 5：处理旧数据（如果需要）

如果数据库中已有中文数据，检查是否正常显示：

```sql
-- 查看现有配置
SELECT id, config_name, target_url FROM crawler_configs;
```

**情况 A：中文显示正常** ✓
- 无需操作，迁移成功

**情况 B：中文显示为乱码** ✗
- 旧数据已损坏，需要重新导入
- 操作步骤：
  ```bash
  # 1. 删除乱码数据
  # （在数据库中执行 DELETE 语句）
  
  # 2. 重新导入配置
  python scripts/init_nhsa_registration_config.py
  
  # 3. 重新导入任务（如果有）
  python scripts/batch_import_registration_jobs.py
  ```

## 常见问题

### Q1: 迁移执行失败，报错 "Cannot alter column because it is part of an index"

**原因**：字段被索引约束，无法直接修改

**解决方案**：手动删除索引后重试
```sql
-- 查看索引
EXEC sp_helpindex 'crawler_configs';

-- 删除相关索引（示例）
DROP INDEX idx_auth_profile ON crawler_configs;

-- 再次执行迁移
alembic upgrade head

-- 索引会自动重建
```

### Q2: 迁移执行后还是乱码

**检查清单**：
1. ✅ .env 中 DATABASE_URL 包含 `&charset=UTF-8`
2. ✅ 数据库创建时指定了 `COLLATE Chinese_PRC_CI_AS`
3. ✅ 字段类型已改为 NVARCHAR（运行测试脚本验证）

如果以上都正确，可能是旧数据问题，参考步骤 5 重新导入数据。

### Q3: 如何回滚迁移

如果迁移出现问题，可以回滚：

```bash
# 回滚到上一个版本
alembic downgrade -1

# 或回滚到指定版本
alembic downgrade f1028eaaa97b
```

**警告**：回滚会将 NVARCHAR 改回 VARCHAR，中文会再次乱码。

### Q4: 迁移执行很慢

**原因**：ALTER TABLE 需要重建表结构

**说明**：
- 小表（<10万行）：通常 1-5 分钟
- 大表（>10万行）：可能需要 10-30 分钟
- 耐心等待，不要中断

## 验证成功的标志

执行完成后，你应该能够：

✅ 在数据库中存储中文配置名称
✅ 在 API 响应中看到正确的中文
✅ 在前端页面正常显示中文
✅ JSON 字段中的中文也正常显示

## 测试用例

```bash
# 启动服务
python -m app.main

# 在浏览器中访问
http://127.0.0.1:8000/static/index.html

# 创建一个测试配置，包含中文：
- 配置名称：测试中文编码
- 目标URL：https://测试.com

# 检查是否正常显示
```

## 完成后的清理

迁移成功后，无需额外清理。以下文件保留用于记录：

- ✅ alembic/versions/19798be7d82c_*.py - 迁移脚本（保留）
- ✅ docs/FIX_CHINESE_ENCODING.md - 文档（保留）
- ✅ scripts/test_chinese_encoding.py - 测试脚本（保留）

====================================
需要帮助？

如果遇到问题，请：
1. 查看详细文档：docs/FIX_CHINESE_ENCODING.md
2. 运行测试脚本：python scripts/test_chinese_encoding.py
3. 检查日志输出
====================================
