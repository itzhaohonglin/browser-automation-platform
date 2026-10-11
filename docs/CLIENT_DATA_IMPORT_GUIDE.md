# 客户端配置初始化和数据导入指南

## 概述

打包后的客户端提供多种方式来初始化配置和导入任务数据，适用于不同场景。

---

## 方式一：通过 Web 界面（推荐新手）

### 适用场景
- 首次使用
- 少量配置和任务
- 可视化操作

### 操作步骤

1. **启动服务**
   ```bash
   .\startup.bat
   ```

2. **访问 Web 界面**
   ```
   http://127.0.0.1:8000/static/index.html
   ```

3. **创建配置**
   - 点击"配置管理" → "新增配置"
   - 填写表单：
     - 配置名称：国家医保局-注册证号查询
     - 目标URL：https://code.nhsa.gov.cn/toSearch.html?sysflag=1004
     - 输入框配置、字段映射等
   - 保存

4. **创建任务**
   - 点击"任务管理" → "新增任务"
   - 选择配置
   - 填写查询参数（JSON格式）
   - 提交

---

## 方式二：使用初始化脚本（推荐快速开始）

### 适用场景
- 快速体验功能
- 使用预定义的示例配置

### 操作步骤

1. **运行初始化脚本**
   ```bash
   .\init_config.bat
   ```

2. **脚本会自动完成**
   - 创建 NHSA 注册证号查询配置
   - 创建示例任务
   - 配置优先级和超时参数

3. **验证**
   - 启动服务：`.\startup.bat`
   - 访问看板查看配置和任务

**脚本内容**：
```batch
# init_config.bat 会调用
python scripts\init_nhsa_registration_config.py
```

---

## 方式三：批量导入（推荐生产环境）

### 适用场景
- 大量任务导入
- 从 Excel/CSV 文件导入
- 定期批量更新

### 准备工作

#### 1. 创建导入目录
```bash
mkdir import_data
```

#### 2. 准备数据文件

**Excel 格式** (`import_data\jobs.xlsx`)：

| config_id | query_params |
|-----------|--------------|
| 44 | {"registration_no": "滇械注准20192140008"} |
| 44 | {"registration_no": "京械注准20210001234"} |
| 44 | {"registration_no": "沪械注准20200005678"} |

**CSV 格式** (`import_data\jobs.csv`)：
```csv
config_id,query_params
44,"{""registration_no"": ""滇械注准20192140008""}"
44,"{""registration_no"": ""京械注准20210001234""}"
44,"{""registration_no"": ""沪械注准20200005678""}"
```

**注意**：
- `config_id` 必须是已存在的配置ID
- `query_params` 必须是有效的 JSON 字符串
- CSV 中的双引号需要转义为 `""`

#### 3. 执行导入

```bash
.\batch_import.bat
```

**操作流程**：
1. 脚本列出 `import_data\` 目录下的所有文件
2. 输入文件名（如：`jobs.xlsx`）
3. 自动导入所有任务到数据库
4. 显示导入结果

---

## 方式四：通过 API 导入（推荐系统集成）

### 适用场景
- 与其他系统集成
- 自动化流程
- 程序化批量操作

### API 端点

#### 1. 创建配置
```bash
POST http://127.0.0.1:8000/api/configs
Content-Type: application/json

{
  "config_name": "国家医保局-注册证号查询",
  "target_url": "https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
  "need_login": false,
  "input_configs": [
    {
      "selector": "input[name='zczbh']",
      "param_name": "registration_no",
      "label": "注册证号"
    }
  ],
  "submit_selector": "button:has-text('查询')",
  "wait_selector": ".ui-jqgrid-btable",
  "fields_mapping": {
    "iframe_levels": 2,
    "iframe1_selector": "iframe#dataInfo",
    "iframe2_selector": "iframe.els-iframe.active",
    "list_selector": "tbody tr.jqgrow",
    "fields": [
      {"name": "耗材名称", "selector": "td:nth-child(2)", "attr": "text"}
    ]
  },
  "priority": 5,
  "is_active": true
}
```

#### 2. 批量创建任务
```bash
POST http://127.0.0.1:8000/api/jobs/batch
Content-Type: application/json

{
  "config_id": 44,
  "tasks": [
    {"query_params": {"registration_no": "滇械注准20192140008"}},
    {"query_params": {"registration_no": "京械注准20210001234"}},
    {"query_params": {"registration_no": "沪械注准20200005678"}}
  ]
}
```

#### 3. 使用 Python 脚本调用
```python
import requests

# 启动服务
API_BASE = "http://127.0.0.1:8000"

# 创建任务
response = requests.post(
    f"{API_BASE}/api/jobs/batch",
    json={
        "config_id": 44,
        "tasks": [
            {"query_params": {"registration_no": "滇械注准20192140008"}},
            {"query_params": {"registration_no": "京械注准20210001234"}},
        ]
    }
)

print(f"Created {len(response.json()['created'])} jobs")
```

---

## 方式五：直接操作数据库（高级用户）

### 适用场景
- 需要直接修改数据
- 批量更新配置
- 数据迁移

### 操作步骤

#### 1. 连接数据库
```bash
sqlcmd -S localhost -U sa -P YourPassword -d bap
```

#### 2. 插入配置
```sql
INSERT INTO crawler_configs (
    config_name, target_url, need_login, 
    input_configs, submit_selector, wait_selector,
    fields_mapping, priority, is_active, created_at
) VALUES (
    N'国家医保局-注册证号查询',
    N'https://code.nhsa.gov.cn/toSearch.html?sysflag=1004',
    0,
    N'[{"selector":"input[name=''zczbh'']","param_name":"registration_no"}]',
    N'button:has-text(''查询'')',
    N'.ui-jqgrid-btable',
    N'{"iframe_levels":2,"list_selector":"tbody tr.jqgrow","fields":[]}',
    5,
    1,
    GETDATE()
);

-- 获取插入的配置ID
SELECT SCOPE_IDENTITY() AS config_id;
```

#### 3. 批量插入任务
```sql
DECLARE @config_id INT = 44;

INSERT INTO job_queue (config_id, query_params, status, retry_count, priority, created_at, updated_at)
VALUES
    (@config_id, N'{"registration_no":"滇械注准20192140008"}', 'PENDING', 0, 5, GETDATE(), GETDATE()),
    (@config_id, N'{"registration_no":"京械注准20210001234"}', 'PENDING', 0, 5, GETDATE(), GETDATE()),
    (@config_id, N'{"registration_no":"沪械注准20200005678"}', 'PENDING', 0, 5, GETDATE(), GETDATE());

-- 查看插入结果
SELECT COUNT(*) AS total_jobs FROM job_queue WHERE config_id = @config_id;
```

---

## 文件位置说明

打包后的目录结构：

```
dist/browser-automation-platform/
├── browser-automation-platform.exe  # 主程序
├── scripts/                         # Python 脚本目录
│   ├── init_nhsa_registration_config.py  # 初始化配置脚本
│   └── batch_import_registration_jobs.py # 批量导入脚本
├── import_data/                     # 导入数据目录（需手动创建）
│   ├── jobs.xlsx                    # Excel 导入文件
│   └── jobs.csv                     # CSV 导入文件
├── init_config.bat                  # ⭐ 初始化配置脚本
├── batch_import.bat                 # ⭐ 批量导入脚本
└── startup.bat                      # 启动服务
```

---

## 完整使用流程示例

### 场景：首次部署并导入 100 个任务

```bash
# 1. 首次安装
.\install.bat

# 2. 初始化示例配置
.\init_config.bat

# 3. 启动服务查看配置ID
.\startup.bat
# 访问 http://127.0.0.1:8000/static/index.html
# 在"配置管理"中查看配置ID（假设为 44）

# 4. 停止服务（Ctrl+C）

# 5. 准备导入数据
# 创建 import_data\jobs.xlsx，填入 100 条数据

# 6. 批量导入
.\batch_import.bat
# 输入文件名：jobs.xlsx

# 7. 重新启动服务
.\startup.bat

# 8. 查看任务执行
# 访问看板，查看任务自动执行
```

---

## 常见问题

### Q1: 如何获取 config_id？

**方法1：通过 Web 界面**
```
访问：http://127.0.0.1:8000/static/index.html
点击"配置管理"，查看配置列表中的 ID 列
```

**方法2：通过数据库查询**
```sql
SELECT id, config_name FROM crawler_configs WHERE is_active = 1;
```

**方法3：通过 API**
```bash
curl http://127.0.0.1:8000/api/configs
```

### Q2: query_params 的格式要求？

必须是有效的 JSON 对象，键名与配置中 `input_configs` 的 `param_name` 对应：

```json
{
  "registration_no": "滇械注准20192140008",
  "keyword": "医用耗材"
}
```

### Q3: 批量导入失败怎么办？

**检查项**：
1. config_id 是否存在：`SELECT * FROM crawler_configs WHERE id = 44`
2. query_params 格式是否正确（有效的 JSON）
3. Excel/CSV 文件编码是否为 UTF-8
4. 数据库连接是否正常

**查看详细错误**：
```bash
# 直接运行 Python 脚本查看详细错误
python scripts\batch_import_registration_jobs.py import_data\jobs.xlsx
```

### Q4: 如何修改已导入的任务？

**方法1：通过 Web 界面**
```
访问看板 → 任务管理 → 编辑任务
```

**方法2：通过数据库**
```sql
-- 修改任务参数
UPDATE job_queue 
SET query_params = N'{"registration_no":"新的注册证号"}'
WHERE id = 123;

-- 重置失败任务
UPDATE job_queue 
SET status = 'PENDING', error_msg = NULL, retry_count = 0
WHERE status = 'FAILED';
```

---

## 性能建议

### 大量任务导入

- **批次大小**：建议每批导入 1000-5000 条
- **分批导入**：将大文件拆分为多个小文件
- **数据库优化**：导入前暂停服务以提高速度

### 并发执行

- 任务会按优先级和创建时间自动执行
- 默认每 10 秒扫描一次待处理任务
- 可通过修改代码调整并发数（`ProcessPoolManager.max_workers`）

---

**更新日期**：2026-10-01  
**适用版本**：v1.0.0+
