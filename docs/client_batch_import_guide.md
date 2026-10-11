# 客户端批量导入任务完整指南

## 📋 目录
1. [快速开始](#快速开始)
2. [文件格式](#文件格式)
3. [导入流程](#导入流程)
4. [命令行方式](#命令行方式)
5. [常见问题](#常见问题)
6. [最佳实践](#最佳实践)

---

## 快速开始

### 三步完成批量导入

```batch
# 1. 准备数据文件
# 将注册证号列表保存为 import_data\jobs.txt

# 2. 运行批量导入
batch_import.bat

# 3. 启动服务执行任务
startup.bat
```

---

## 文件格式

### 支持的格式

#### ✅ 格式1：纯注册证号（推荐）
```text
川械注准20182010068
川械注准20182170152
川械注准20192220020
滇械注准20192140008
```

#### ✅ 格式2：带序号（Excel 导出格式）
```text
1	川械注准20182010068
2	川械注准20182170152
3	川械注准20192220020
4	滇械注准20192140008
```
**说明**：序号和注册证号之间用 Tab 或空格分隔，脚本会自动提取注册证号。

#### ✅ 格式3：带注释
```text
# 国家医保局注册证号批量导入
# 创建时间：2026-10-11
# 数量：1626 个

川械注准20182010068
川械注准20182170152

# 四川地区
川械注准20192220020
滇械注准20192140008
```
**说明**：以 `#` 开头的行会被忽略，空行也会被跳过。

### 文件要求

- **文件位置**：必须放在 `import_data\` 目录下
- **文件类型**：`.txt` 或 `.csv`
- **编码格式**：UTF-8（推荐）或 GBK
- **文件大小**：无限制（建议单文件不超过 1 万条记录）

---

## 导入流程

### 方式1：使用批处理脚本（推荐）

#### 步骤 1：准备数据文件

1. 打开 `import_data` 目录（如果不存在则创建）
2. 创建文本文件，例如 `jobs.txt`
3. 每行写一个注册证号，保存文件

#### 步骤 2：运行批处理脚本

双击运行 `batch_import.bat`：

```
======================================
  Batch Import Jobs
======================================

Available import files:

jobs.txt
test_data.txt

Enter filename (without path): jobs.txt

[RUN] Importing jobs from import_data\jobs.txt...

================================================================================
批量导入国家医保局注册证号查询任务
================================================================================

读取到 1626 个注册证号

前5个注册证号:
  1. 川械注准20182010068
  2. 川械注准20182170152
  3. 川械注准20192220020
  4. 川械注准20202070035
  5. 滇械注准20192140008

使用配置: 国家医保局-注册证号查询 (ID: 6)

开始创建任务...
[100/1626] 已创建 100 个任务
[200/1626] 已创建 200 个任务
...
[1626/1626] 已创建 1626 个任务

✓ 成功创建 1626 个任务
✓ 任务ID范围: 5 - 1630

======================================
  Import Complete!
======================================

You can now:
  1. Start the service: startup.bat
  2. View tasks in dashboard: http://127.0.0.1:8000/static/index.html
  3. Tasks will be executed automatically
```

#### 步骤 3：启动服务

```batch
startup.bat
```

服务启动后，任务会自动执行。

---

## 命令行方式

### 直接使用 exe 导入（高级用户）

```batch
# 导入任务
browser-automation-platform.exe --import-jobs "import_data\jobs.txt"

# 或使用绝对路径
browser-automation-platform.exe --import-jobs "D:\data\registration_numbers.txt"
```

### 完整命令参考

```batch
# 1. 初始化配置（首次使用必须运行）
browser-automation-platform.exe --init-config

# 2. 批量导入任务
browser-automation-platform.exe --import-jobs "文件路径"

# 3. 安装浏览器驱动（首次部署必须运行）
browser-automation-platform.exe --install-browser

# 4. 执行数据库迁移（更新系统时可能需要）
browser-automation-platform.exe --migrate

# 5. 启动 Web 服务（默认行为）
browser-automation-platform.exe
```

---

## 常见问题

### ❌ 问题1：提示 "未找到国家医保局注册证号查询配置"

**原因**：数据库中没有配置记录。

**解决方法**：
```batch
# 方式1：运行批处理脚本
init_config.bat

# 方式2：命令行方式
browser-automation-platform.exe --init-config
```

### ❌ 问题2：提示 "文件不存在"

**检查清单**：
- [ ] 文件是否在 `import_data\` 目录下
- [ ] 文件名是否正确（包括扩展名）
- [ ] 路径中是否包含特殊字符或空格

**正确示例**：
```batch
✅ import_data\jobs.txt
✅ import_data\注册证号列表.txt
❌ jobs.txt  （缺少 import_data\ 路径）
❌ import_data/jobs.txt  （应该用反斜杠 \）
```

### ❌ 问题3：导入数量不对

**可能原因**：
1. **空行被跳过** - 文件中的空行不会创建任务
2. **注释行被忽略** - 以 `#` 开头的行会被跳过
3. **重复注册证号** - 每个注册证号都会创建一个独立任务（允许重复）

**验证方法**：
```batch
# 检查文件实际行数（Windows PowerShell）
Get-Content import_data\jobs.txt | Measure-Object -Line

# 查看前10行
type import_data\jobs.txt | more
```

### ❌ 问题4：任务导入后不执行

**排查步骤**：

1. **检查服务是否启动**
```batch
# 查看进程
tasklist | findstr browser-automation-platform

# 或访问健康检查接口
curl http://127.0.0.1:8000/health
```

2. **检查任务状态**
   - 打开 Web 看板：http://127.0.0.1:8000/static/index.html
   - 查看任务状态是否为 `pending`

3. **查看日志文件**
```batch
# 打开日志目录
explorer logs

# 查看最新日志
type logs\app.log
```

4. **检查调度器状态**
   - Web 看板右上角显示 "调度器状态：运行中"

### ❌ 问题5：中文乱码

**原因**：文件编码不正确。

**解决方法**：
```
1. 使用记事本打开文件
2. 点击 "文件" → "另存为"
3. 编码选择 "UTF-8"
4. 保存
5. 重新导入
```

### ❌ 问题6：Excel 导出的文件无法识别

**原因**：Excel 默认导出为 Unicode 编码，包含 BOM 标记。

**解决方法**：
```
方式1：使用记事本另存为 UTF-8
方式2：直接复制粘贴到新的文本文件
方式3：使用 CSV UTF-8 格式导出
```

---

## 最佳实践

### 1. 数据准备

#### ✅ 推荐做法
```text
# 使用注释记录元数据
# 批次：2026-10-11-batch1
# 来源：客户提供清单
# 数量：1626 个
# 负责人：张三

川械注准20182010068
川械注准20182170152
...
```

#### ❌ 不推荐做法
```text
川械注准20182010068 备注：紧急
川械注准20182170152（已审核）
```
**原因**：脚本会提取整行作为注册证号，导致参数错误。

### 2. 分批导入

**大量任务建议分批**：

```
import_data/
├── batch1_2026-10-11.txt  (1-1000)
├── batch2_2026-10-11.txt  (1001-2000)
└── batch3_2026-10-11.txt  (2001-3000)
```

**好处**：
- 降低单次导入失败风险
- 便于按批次管理和追踪
- 出错时只需重新导入该批次

### 3. 导入前检查

```batch
# 1. 检查配置是否存在
init_config.bat

# 2. 验证文件格式
type import_data\jobs.txt | more

# 3. 统计行数
find /c /v "" import_data\jobs.txt

# 4. 备份原始文件
copy import_data\jobs.txt import_data\jobs_backup_20261011.txt
```

### 4. 导入后验证

```batch
# 1. 启动服务
startup.bat

# 2. 打开 Web 看板
start http://127.0.0.1:8000/static/index.html

# 3. 检查任务统计
# 看板显示：待处理任务数 = 导入数量

# 4. 随机抽查
# 点击任务查看详情，确认注册证号正确
```

### 5. 命名规范

**推荐的文件命名**：
```
✅ jobs_20261011_batch1.txt
✅ 注册证号_四川地区_20261011.txt
✅ registration_numbers_1626.txt

❌ 新建文本文档.txt
❌ 临时.txt
❌ 1.txt
```

### 6. 版本控制

**建立导入记录**：

```text
import_data/
├── history/
│   ├── 2026-10-11_batch1_1626条.txt
│   ├── 2026-10-12_batch2_500条.txt
│   └── README.md  (记录每次导入的时间、数量、结果)
└── jobs.txt  (当前待导入文件)
```

**README.md 示例**：
```markdown
# 导入历史记录

| 日期 | 文件 | 数量 | 状态 | 备注 |
|------|------|------|------|------|
| 2026-10-11 | batch1_1626条.txt | 1626 | ✅ 成功 | 首次批量导入 |
| 2026-10-12 | batch2_500条.txt | 500 | ✅ 成功 | 补充导入 |
```

---

## 技术细节

### 导入流程图

```
用户准备数据文件
    ↓
放置到 import_data\ 目录
    ↓
运行 batch_import.bat
    ↓
选择文件名
    ↓
调用: browser-automation-platform.exe --import-jobs "文件路径"
    ↓
主程序解析命令行参数
    ↓
执行: scripts/batch_import_registration_jobs.py
    ↓
读取文件内容
    ↓
解析注册证号（支持多种格式）
    ↓
查找配置: config_name LIKE '%国家医保局%注册证号%'
    ↓
批量创建 job_queue 记录
    ↓
提交数据库事务
    ↓
返回导入结果（成功数量、ID范围）
```

### 数据库表结构

导入后的任务存储在 `job_queue` 表：

| 字段 | 类型 | 示例值 | 说明 |
|------|------|--------|------|
| `id` | INTEGER | 1630 | 任务ID（自增主键） |
| `config_id` | INTEGER | 6 | 关联的配置ID |
| `query_params` | JSON | `{"registration_no": "川械注准20182010068"}` | 动态参数 |
| `status` | ENUM | `pending` | 任务状态 |
| `created_at` | DATETIME | `2026-10-11 16:30:00` | 创建时间 |
| `retry_count` | INTEGER | 0 | 重试次数 |

### 脚本工作原理

**batch_import_registration_jobs.py** 核心逻辑：

```python
# 1. 读取文件
with open(file_path, 'r', encoding='utf-8') as f:
    for line in f:
        line = line.strip()
        
        # 跳过空行和注释
        if not line or line.startswith('#'):
            continue
        
        # 处理带序号格式：1\t川械注准20182010068
        parts = line.split('\t')
        if len(parts) >= 2:
            reg_no = parts[1].strip()
        else:
            reg_no = line
        
        registration_numbers.append(reg_no)

# 2. 查找配置
config = await session.execute(
    select(CrawlerConfig)
    .where(CrawlerConfig.config_name.like('%国家医保局%注册证号%'))
    .order_by(CrawlerConfig.id.desc())
).scalars().first()

# 3. 批量创建任务
for reg_no in registration_numbers:
    job = JobQueue(
        config_id=config.id,
        query_params={"registration_no": reg_no},
        status="pending"
    )
    session.add(job)

await session.commit()
```

---

## 相关文档

- **批处理文件手册**：`docs/batch_files_reference.md`
- **环境配置说明**：`docs/env_config_examples.md`
- **限流配置指南**：`docs/rate_limit_guide.md`
- **完整使用手册**：`docs/complete_usage_guide.md`
- **故障排查**：查看日志文件 `logs/app.log`

---

## 技术支持

如遇到问题，请提供以下信息：
1. 错误消息截图
2. `logs/app.log` 最后 50 行
3. 数据文件示例（前 10 行）
4. 系统版本和环境信息
