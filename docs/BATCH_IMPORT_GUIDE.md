# 批量导入注册证号 - 完整流程指南

你的数据文件包含 **1626 个医疗器械注册证号**，需要批量导入到数据库。

## ⚠️ 当前问题

错误信息显示：`Invalid object name 'crawler_configs'` 
**原因**：数据库表还未创建，需要先初始化数据库。

---

## ✅ 完整导入流程

### 步骤 1：初始化数据库

```bash
# 确保数据库已创建
sqlcmd -S localhost -U sa -P YourPassword -Q "CREATE DATABASE bap COLLATE Chinese_PRC_CI_AS;"

# 运行数据库迁移
cd D:\dev\PyCharmProjects\browser-automation-platform
alembic upgrade head
```

### 步骤 2：初始化 NHSA 配置

```bash
python scripts/init_nhsa_registration_config.py
```

这会创建一个配置记录，通常 `config_id = 44`

### 步骤 3：批量导入注册证号

```bash
python scripts/import_registration_numbers_from_txt.py
```

脚本会：
- 读取 `docs/1.txt` 中的 1626 个注册证号
- 检查已存在的任务（避免重复）
- 批量创建新任务（每批 100 个）
- 显示导入进度

### 步骤 4：启动服务

```bash
python -m app.main
```

### 步骤 5：查看执行

访问：`http://127.0.0.1:8000/static/index.html`

任务会自动执行：
- 每 10 秒扫描一次待处理任务
- 按优先级和创建时间排序
- 失败任务自动重试（最多 3 次）

---

## 📊 预期结果

```
总注册证号：1626 个
├─ 新增任务：1626 个（首次导入）
├─ 已存在：0 个
└─ 执行时间：约 1-2 小时（取决于网站响应速度）
```

---

## 🔧 快速一键执行（推荐）

创建一个批处理脚本自动完成所有步骤：

```batch
@echo off
echo ======================================
echo   批量导入注册证号 - 一键执行
echo ======================================

cd D:\dev\PyCharmProjects\browser-automation-platform

echo [1/4] 初始化数据库...
alembic upgrade head
if errorlevel 1 (
    echo [ERROR] 数据库初始化失败
    pause
    exit /b 1
)

echo [2/4] 创建 NHSA 配置...
python scripts\init_nhsa_registration_config.py
if errorlevel 1 (
    echo [ERROR] 配置初始化失败
    pause
    exit /b 1
)

echo [3/4] 批量导入任务...
python scripts\import_registration_numbers_from_txt.py

echo [4/4] 任务导入完成！
echo.
echo 下一步：
echo   1. 启动服务: python -m app.main
echo   2. 访问看板: http://127.0.0.1:8000/static/index.html
echo.

pause
```

保存为 `quick_import.bat` 并运行。

---

## 🐛 常见问题

### Q1: 数据库连接失败

**检查**：
```bash
# .env 文件必须使用 aioodbc
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server
```

### Q2: 配置已存在

如果配置已创建，跳过步骤 2，直接运行步骤 3。

脚本会自动：
- 查找现有 NHSA 配置
- 检查已导入的任务
- 只导入新的注册证号

### Q3: 如何查看导入进度

导入完成后：
1. 启动服务
2. 访问看板
3. 查看"任务统计"和"执行日志"

### Q4: 如何修改 config_id

如果你想使用其他配置，编辑脚本中的 SQL：

```python
# 修改为指定 config_id
config_id = 44  # 改为你的 config_id
```

---

## 📝 数据文件格式

你的 `docs/1.txt` 格式正确：

```
川械注准20182010068
川械注准20182170152
川械注准20192220020
...（共 1626 行）
```

每行一个注册证号，脚本会自动转换为：

```json
{"registration_no": "川械注准20182010068"}
```

---

## 💡 手动导入（备用方案）

如果脚本无法运行，可以直接用 SQL：

```sql
-- 假设 config_id = 44
DECLARE @config_id INT = 44;

INSERT INTO job_queue (config_id, query_params, status, retry_count, priority, created_at, updated_at)
VALUES
    (@config_id, '{"registration_no":"川械注准20182010068"}', 'PENDING', 0, 5, GETDATE(), GETDATE()),
    (@config_id, '{"registration_no":"川械注准20182170152"}', 'PENDING', 0, 5, GETDATE(), GETDATE()),
    -- ... 继续添加
    (@config_id, '{"registration_no":"浙甬械备20230065"}', 'PENDING', 0, 5, GETDATE(), GETDATE());
```

但这种方式比较繁琐，**强烈推荐使用脚本**。

---

**创建日期**：2026-10-01
**数据量**：1626 个注册证号
**预计导入时间**：< 1 分钟
