# 详情采集配置界面设计文档

**日期**：2026-09-29  
**版本**：1.0  
**目标**：为浏览器自动化平台添加可视化配置界面，支持"列表+详情"两级数据采集

---

## 1. 背景与目标

### 1.1 业务需求

用户需要采集医保局网站（https://code.nhsa.gov.cn/toSearch.html?sysflag=1004）的医用耗材信息：

- **列表页**：搜索结果展示注册证号、产品名称等基础信息
- **详情页**：点击"详情"按钮后弹出窗口，显示规格型号、生产地址等完整信息
- **数据关联**：需要将列表数据与对应的详情数据关联存储

### 1.2 现状分析

**已实现功能**（80%完成度）：

✅ 执行器核心逻辑已实现：
- `_extract_detail_data()` - 单条详情提取
- `_extract_detail_with_retry()` - 带重试机制
- `_extract_list_with_details()` - 单页列表+详情采集
- `_extract_list_with_details_paginated()` - 分页列表+详情采集

✅ 数据存储结构已设计：
```json
{
  "items": [
    {
      "list_data": {...},
      "detail_data": {...},
      "detail_status": "success/failed/skipped"
    }
  ],
  "summary": {...}
}
```

❌ 缺失功能：
- **配置界面**：目前需要直接操作数据库配置 JSON，用户体验差
- **测试验证**：无法快速验证配置是否正确
- **错误诊断**：配置错误时缺少友好的错误提示

### 1.3 设计目标

**核心目标**：提供一个可视化配置界面，让用户无需直接操作数据库即可配置采集规则。

**成功标准**：
1. 用户能通过网页表单配置列表字段和详情字段
2. 用户能实时测试配置是否有效（返回样本数据）
3. 配置错误时提供明确的错误提示
4. 配置保存后立即生效（无需重启服务）

---

## 2. 技术方案

### 2.1 架构概览

```
┌─────────────────────────────────────────────────────────┐
│                    前端配置界面                          │
│  config_manager.html + config_manager.js + CSS          │
└─────────────────┬───────────────────────────────────────┘
                  │ HTTP API
                  ↓
┌─────────────────────────────────────────────────────────┐
│                  后端 API 层                             │
│  POST /api/configs/{id}/test  测试配置                  │
│  PUT  /api/configs/{id}       保存配置                  │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────────────┐
│              数据库（crawler_configs 表）                │
│  fields_mapping (JSON): 存储列表+详情配置               │
└─────────────────┬───────────────────────────────────────┘
                  │
                  ↓
┌─────────────────────────────────────────────────────────┐
│            执行器（PlaywrightExecutor）                  │
│  读取配置 → 采集列表 → 逐条采集详情 → 保存结果          │
└─────────────────────────────────────────────────────────┘
```

### 2.2 配置数据结构

**存储位置**：`CrawlerConfig.fields_mapping` (JSON 字段)

**完整结构**：

```json
{
  "list_selector": "table tbody tr",
  "fields": [
    {
      "name": "注册证号",
      "selector": "td:nth-child(1)",
      "attr": "text"
    },
    {
      "name": "产品名称",
      "selector": "td:nth-child(2)",
      "attr": "text"
    }
  ],
  "detail_config": {
    "enabled": true,
    "detail_button_selector": "a.detail-btn",
    "wait_selector": ".modal-content",
    "detail_iframe_selector": null,
    "fields": [
      {
        "name": "规格型号",
        "selector": ".spec",
        "attr": "text"
      },
      {
        "name": "生产地址",
        "selector": ".address",
        "attr": "text"
      }
    ],
    "close_method": "auto",
    "close_selector": ".close-btn",
    "timeout": {
      "click": 10000,
      "wait_selector": 5000,
      "close": 5000
    },
    "retry": {
      "max_attempts": 3,
      "delay_seconds": 2
    }
  }
}
```

**字段说明**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `list_selector` | string | 是 | 列表容器选择器（用于定位每一行） |
| `fields` | array | 是 | 列表字段配置数组 |
| `fields[].name` | string | 是 | 字段名称（显示在结果中） |
| `fields[].selector` | string | 是 | CSS 选择器（相对于容器） |
| `fields[].attr` | string | 是 | 提取属性（text/href/src） |
| `detail_config.enabled` | boolean | 是 | 是否启用详情采集 |
| `detail_config.detail_button_selector` | string | 是 | 详情按钮选择器（相对于列表行） |
| `detail_config.wait_selector` | string | 是 | 详情内容等待选择器 |
| `detail_config.detail_iframe_selector` | string | 否 | 详情iframe选择器（如果详情在iframe中） |
| `detail_config.fields` | array | 是 | 详情字段配置数组 |
| `detail_config.close_method` | string | 是 | 关闭方式（click/escape/auto） |
| `detail_config.close_selector` | string | 否 | 关闭按钮选择器（close_method=click时必填） |
| `detail_config.timeout` | object | 否 | 超时配置（毫秒） |
| `detail_config.retry` | object | 否 | 重试配置 |

---

## 3. 前端设计

### 3.1 页面结构

**文件清单**：
- `static/config_manager.html` - 页面结构
- `static/config_manager.js` - 交互逻辑
- `static/config_manager.css` - 样式

**页面布局**：

```
┌─────────────────────────────────────────────────────────┐
│  [← 返回]  配置管理 - 医保局耗材采集                    │
├─────────────────────────────────────────────────────────┤
│  第一步：配置列表字段                                    │
│  ┌───────────────────────────────────────────────────┐  │
│  │ 列表容器选择器：[table tbody tr            ]  (?) │  │
│  │                                                   │  │
│  │ 列表字段：                                        │  │
│  │  字段名称         选择器              属性        │  │
│  │  [注册证号]       [td:nth-child(1)]   [text ▼] [X]│  │
│  │  [产品名称]       [td:nth-child(2)]   [text ▼] [X]│  │
│  │  [+ 添加字段]                                     │  │
│  └───────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│  第二步：配置详情采集（可选）                            │
│  ┌───────────────────────────────────────────────────┐  │
│  │ ☑ 启用详情采集                                    │  │
│  │                                                   │  │
│  │ 详情按钮选择器：[a.detail-btn          ]  (?)    │  │
│  │ 详情等待选择器：[.modal-content        ]  (?)    │  │
│  │ 详情iframe选择器：[                     ]  (可选) │  │
│  │                                                   │  │
│  │ 详情字段：                                        │  │
│  │  字段名称         选择器              属性        │  │
│  │  [规格型号]       [.spec]             [text ▼] [X]│  │
│  │  [生产地址]       [.address]          [text ▼] [X]│  │
│  │  [+ 添加详情字段]                                 │  │
│  │                                                   │  │
│  │ 高级配置：                                        │  │
│  │  关闭方式： ○ 点击按钮  ○ ESC键  ● 自动         │  │
│  │  关闭按钮选择器：[.close-btn           ]          │  │
│  │  最大重试次数：[3]  重试延迟：[2] 秒             │  │
│  └───────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│  第三步：测试与保存                                      │
│  ┌───────────────────────────────────────────────────┐  │
│  │ [测试配置]  [保存配置]                            │  │
│  │                                                   │  │
│  │ 测试结果：                                        │  │
│  │  ✓ 成功提取 3 条数据，详情采集成功 3 条          │  │
│  │                                                   │  │
│  │  样本数据（第1条）：                              │  │
│  │  列表数据：                                       │  │
│  │    注册证号: 滇械注准20192140008                  │  │
│  │    产品名称: 一次性使用无菌注射器                 │  │
│  │  详情数据：                                       │  │
│  │    规格型号: 2ml                                  │  │
│  │    生产地址: 云南省昆明市...                      │  │
│  │  详情状态: success                                │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### 3.2 交互流程

**配置流程**：

1. 用户进入配置页面（从配置列表点击"编辑"）
2. 填写列表容器选择器和列表字段
3. 勾选"启用详情采集"，填写详情配置
4. 点击"测试配置"按钮
5. 后端执行测试采集（最多3条样本）
6. 前端展示测试结果（成功/失败/样本数据）
7. 确认无误后点击"保存配置"
8. 保存成功后返回配置列表

**测试采集逻辑**：

```javascript
// 前端伪代码
async function testConfig() {
  const config = collectFormData();
  
  showLoading("正在测试采集...");
  
  const response = await fetch(`/api/configs/${configId}/test`, {
    method: 'POST',
    body: JSON.stringify(config)
  });
  
  const result = await response.json();
  
  if (result.success) {
    showSuccess(result.data);
  } else {
    showError(result.error);
  }
}

function showSuccess(data) {
  // 显示采集统计
  display(`✓ 成功提取 ${data.total_tested} 条数据`);
  display(`详情采集成功 ${data.success_count} 条`);
  
  // 显示样本数据（前3条）
  for (let item of data.sample_items) {
    displaySample(item);
  }
}
```

### 3.3 表单验证

**客户端验证**（前端 JavaScript）：

| 字段 | 验证规则 | 错误提示 |
|------|----------|----------|
| 列表容器选择器 | 非空 | "请输入列表容器选择器" |
| 列表字段.name | 非空 | "字段名称不能为空" |
| 列表字段.selector | 非空 | "选择器不能为空" |
| 详情按钮选择器 | 启用详情时必填 | "请输入详情按钮选择器" |
| 详情等待选择器 | 启用详情时必填 | "请输入详情等待选择器" |
| 关闭按钮选择器 | close_method=click时必填 | "请输入关闭按钮选择器" |

**服务端验证**（后端 API）：

- 配置格式有效性（JSON schema 验证）
- 选择器语法有效性（CSS selector 语法检查）
- 必填字段完整性

---

## 4. 后端设计

### 4.1 新增 API

#### API 1：测试配置

**端点**：`POST /api/configs/{config_id}/test`

**功能**：使用临时配置执行测试采集，返回前3条样本数据

**请求体**：

```json
{
  "list_selector": "table tbody tr",
  "fields": [...],
  "detail_config": {...},
  "query_params": {
    "注册证号": "滇械注准20192140008"
  }
}
```

**响应**：

```json
{
  "success": true,
  "data": {
    "total_tested": 3,
    "success_count": 3,
    "failed_count": 0,
    "sample_items": [
      {
        "list_data": {...},
        "detail_data": {...},
        "detail_status": "success"
      }
    ]
  }
}
```

**错误响应**：

```json
{
  "success": false,
  "error": "详情按钮选择器未找到：a.detail-btn",
  "error_type": "selector_not_found"
}
```

**实现逻辑**：

```python
@router.post("/configs/{config_id}/test")
async def test_config(
    config_id: int,
    test_request: ConfigTestRequest,
    session: AsyncSession = Depends(get_session)
):
    """测试配置是否有效"""
    
    # 1. 查询配置
    config = await session.get(CrawlerConfig, config_id)
    if not config:
        raise HTTPException(404, "配置不存在")
    
    # 2. 使用临时配置覆盖
    config.fields_mapping = test_request.fields_mapping
    
    # 3. 创建临时任务
    temp_job = JobQueue(
        config_id=config_id,
        query_params=test_request.query_params,
        status=JobStatus.PENDING
    )
    session.add(temp_job)
    await session.flush()
    
    # 4. 执行采集（限制3条）
    executor = PlaywrightExecutor()
    
    try:
        # 修改 max_pages=1，只采集第一页
        original_max_pages = config.max_pages
        config.max_pages = 1
        
        result = await executor.execute_job(temp_job.id, session)
        
        # 恢复原始配置
        config.max_pages = original_max_pages
        
        # 5. 提取样本数据（前3条）
        if result["status"] == "success":
            items = result.get("extracted_data", {}).get("items", [])
            sample_items = items[:3]
            
            success_count = sum(
                1 for item in sample_items
                if item["detail_status"] == "success"
            )
            failed_count = sum(
                1 for item in sample_items
                if item["detail_status"] == "failed"
            )
            
            return {
                "success": True,
                "data": {
                    "total_tested": len(sample_items),
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "sample_items": sample_items
                }
            }
        else:
            raise HTTPException(500, result.get("error"))
            
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "error_type": "execution_error"
        }
    finally:
        # 清理临时任务
        await session.delete(temp_job)
        await session.commit()
```

#### API 2：保存配置（已存在，可能需增强）

**端点**：`PUT /api/configs/{config_id}`

**功能**：保存配置到数据库

**请求体**：

```json
{
  "fields_mapping": {
    "list_selector": "...",
    "fields": [...],
    "detail_config": {...}
  }
}
```

---

## 5. 执行器调整

### 5.1 当前实现验证

**需要验证的点**：

1. ✅ 弹窗模式是否正确处理（不是新标签页）
2. ✅ `close_method: "auto"` 是否实现
3. ✅ 详情失败时是否正确标记 `detail_status: "failed"`
4. ✅ 是否支持 `detail_iframe_selector`（可选）

**预期行为**（基于代码审查）：

```python
# executor.py 第 586-726 行
async def _extract_detail_data(...):
    # 1. 点击详情按钮
    await detail_button.click(timeout=click_timeout)
    
    # 2. 等待详情内容（弹窗或iframe）
    if detail_iframe_selector:
        # 切换到iframe
        detail_frame = await main_page.wait_for_selector(...)
    else:
        # 在主页面查找详情元素
        detail_frame = main_page
    
    # 3. 提取详情字段
    detail_data = await detail_frame.evaluate(...)
    
    # 4. 关闭详情
    if close_method == "click":
        await detail_frame.click(close_selector)
    elif close_method == "escape":
        await detail_frame.keyboard.press('Escape')
    elif close_method == "auto":
        # 优先尝试点击，失败则ESC
        try:
            await detail_frame.click(close_selector)
        except:
            await detail_frame.keyboard.press('Escape')
    
    return detail_data, "success", None
```

**可能需要的调整**：

如果弹窗是通过 JavaScript 动态创建的（不在原始 DOM 中），需要确保：

```python
# 等待弹窗出现
await main_page.wait_for_selector(
    wait_selector,
    state="visible",
    timeout=wait_timeout
)

# 在主页面context中查找详情元素（不是frame）
detail_data = await main_page.evaluate("""
    (fields) => {
        // 在整个 document 中查找（包括动态弹窗）
        const result = {};
        for (const field of fields) {
            const element = document.querySelector(field.selector);
            if (element) {
                result[field.name] = element.innerText.trim();
            }
        }
        return result;
    }
""", detail_fields)
```

### 5.2 错误处理增强

**需要区分的错误类型**：

| 错误类型 | 错误信息格式 | 返回给前端 |
|----------|-------------|-----------|
| 详情按钮未找到 | "详情按钮不存在：{selector}" | selector_not_found |
| 详情内容加载超时 | "详情内容加载超时：{wait_selector}" | load_timeout |
| 详情字段提取失败 | "字段 {field_name} 提取失败" | field_extract_error |
| 关闭操作失败 | "关闭详情失败" | close_error |

**实现方式**（在 `_extract_detail_data` 中）：

```python
try:
    # ... 详情提取逻辑
except PlaywrightTimeoutError as e:
    if "detail_button" in str(e):
        error_msg = f"详情按钮不存在：{detail_button_selector}"
        error_type = "selector_not_found"
    elif "wait_selector" in str(e):
        error_msg = f"详情内容加载超时：{wait_selector}"
        error_type = "load_timeout"
    else:
        error_msg = str(e)
        error_type = "timeout_error"
    
    return {}, "failed", error_msg
```

---

## 6. 数据流

### 6.1 配置测试流程

```
用户填写表单
    ↓
点击"测试配置"
    ↓
前端收集表单数据 → POST /api/configs/{id}/test
    ↓
后端创建临时任务
    ↓
执行器读取临时配置
    ↓
启动浏览器 → 访问目标URL → 填充表单 → 提交
    ↓
提取列表数据（第一页）
    ↓
逐条点击详情按钮 → 提取详情数据 → 关闭详情
    ↓
返回前3条样本数据
    ↓
前端展示测试结果
    ↓
用户确认 → 点击"保存配置"
    ↓
配置写入数据库
```

### 6.2 正式采集流程（无变化）

```
用户创建任务 → POST /api/jobs
    ↓
任务进入队列（status=pending）
    ↓
调度器轮询 → 发现pending任务
    ↓
执行器读取配置（包含detail_config）
    ↓
启动浏览器 → 执行采集
    ↓
保存结果到 crawler_results 表
    ↓
WebSocket 推送进度
```

---

## 7. 医保局网站配置示例

基于目标网站 https://code.nhsa.gov.cn/toSearch.html?sysflag=1004

### 7.1 预期配置

**列表页配置**（需实际测试确认选择器）：

```json
{
  "list_selector": "table#jqGrid tbody tr",
  "fields": [
    {"name": "序号", "selector": "td:nth-child(1)", "attr": "text"},
    {"name": "医保编码", "selector": "td:nth-child(2)", "attr": "text"},
    {"name": "产品名称", "selector": "td:nth-child(3)", "attr": "text"},
    {"name": "注册证号", "selector": "td:nth-child(4)", "attr": "text"},
    {"name": "规格", "selector": "td:nth-child(5)", "attr": "text"},
    {"name": "型号", "selector": "td:nth-child(6)", "attr": "text"}
  ]
}
```

**详情页配置**（假设详情在弹窗中）：

```json
{
  "detail_config": {
    "enabled": true,
    "detail_button_selector": "a.detail-link",
    "wait_selector": ".modal-body",
    "detail_iframe_selector": "#detailIframe",
    "fields": [
      {"name": "注册人名称", "selector": ".registrant-name", "attr": "text"},
      {"name": "生产企业名称", "selector": ".manufacturer-name", "attr": "text"},
      {"name": "生产地址", "selector": ".address", "attr": "text"},
      {"name": "产品标准", "selector": ".standard", "attr": "text"},
      {"name": "产品描述", "selector": ".description", "attr": "text"}
    ],
    "close_method": "auto",
    "close_selector": ".close-btn",
    "timeout": {
      "click": 10000,
      "wait_selector": 5000,
      "iframe_load": 10000,
      "close": 5000
    },
    "retry": {
      "max_attempts": 3,
      "delay_seconds": 2
    }
  }
}
```

### 7.2 初始化脚本

创建 `scripts/init_nhsa_config.py`：

```python
"""
医保局网站配置初始化脚本

用途：快速创建医保局耗材采集配置
运行：python scripts/init_nhsa_config.py
"""

import asyncio
from app.core.database import get_session
from app.models.config import CrawlerConfig

async def init_nhsa_config():
    """初始化医保局配置"""
    
    config = CrawlerConfig(
        config_name="医保局-医用耗材信息",
        target_url="https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
        need_login=False,
        
        # 输入配置
        input_configs={
            "inputs": [
                {
                    "selector": "#registrationNumber",
                    "param_key": "registration_number",
                    "input_type": "text"
                }
            ]
        },
        
        # 提交和等待
        submit_selector="#searchBtn",
        wait_selector="table#jqGrid tbody tr",
        
        # 字段映射（需实际测试后调整）
        fields_mapping={
            "iframe_levels": 2,
            "iframe1_selector": "#iframe1",
            "iframe2_selector": "#contentIframe",
            
            "list_selector": "table#jqGrid tbody tr",
            "fields": [
                {"name": "序号", "selector": "td:nth-child(1)", "attr": "text"},
                {"name": "医保编码", "selector": "td:nth-child(2)", "attr": "text"},
                {"name": "产品名称", "selector": "td:nth-child(3)", "attr": "text"},
                {"name": "注册证号", "selector": "td:nth-child(4)", "attr": "text"}
            ],
            
            "detail_config": {
                "enabled": True,
                "detail_button_selector": "a.detail-link",
                "wait_selector": ".modal-body",
                "detail_iframe_selector": "#detailIframe",
                "fields": [
                    {"name": "注册人名称", "selector": ".registrant", "attr": "text"},
                    {"name": "生产企业", "selector": ".manufacturer", "attr": "text"},
                    {"name": "生产地址", "selector": ".address", "attr": "text"}
                ],
                "close_method": "auto",
                "close_selector": ".close-btn",
                "timeout": {
                    "click": 10000,
                    "wait_selector": 5000,
                    "iframe_load": 10000,
                    "close": 5000
                },
                "retry": {
                    "max_attempts": 3,
                    "delay_seconds": 2
                }
            }
        },
        
        # 分页配置
        pagination_selector="#next_page",
        max_pages=5,
        
        # 超时配置
        timeout_config={
            "page_load": 30000,
            "wait_selector": 15000,
            "click": 10000
        }
    )
    
    async with get_session() as session:
        session.add(config)
        await session.commit()
        await session.refresh(config)
        
        print(f"✓ 配置创建成功，ID: {config.id}")
        print(f"  配置名称: {config.config_name}")
        print(f"  目标URL: {config.target_url}")
        print(f"  详情采集: {'启用' if config.fields_mapping.get('detail_config', {}).get('enabled') else '禁用'}")
        
        return config.id

if __name__ == "__main__":
    asyncio.run(init_nhsa_config())
```

---

## 8. 实施计划

### 8.1 阶段划分

**阶段1：配置界面（2-3小时）**

1. 创建 `static/config_manager.html`
2. 创建 `static/config_manager.js`
3. 创建 `static/config_manager.css`
4. 在配置列表页添加"编辑配置"入口

**阶段2：后端API（1-2小时）**

1. 实现 `POST /api/configs/{id}/test`
2. 增强 `PUT /api/configs/{id}`（如需要）
3. 添加请求/响应模型（Pydantic）

**阶段3：执行器验证（1小时）**

1. 验证弹窗模式处理
2. 验证 auto 关闭模式
3. 增强错误消息

**阶段4：医保局配置（1小时）**

1. 手动测试网站，确认选择器
2. 创建初始化脚本
3. 通过配置界面测试采集

**总计**：5-7小时

### 8.2 风险与缓解

| 风险 | 影响 | 概率 | 缓解措施 |
|------|------|------|----------|
| 医保局网站选择器变化 | 配置失效 | 中 | 提供选择器诊断工具 |
| 详情弹窗渲染延迟 | 提取失败 | 中 | 增加等待时间配置 |
| iframe 嵌套层级复杂 | 定位困难 | 低 | 已支持多层iframe |
| 反爬机制触发 | 访问被限制 | 低 | 添加请求延迟配置 |

---

## 9. 验收标准

### 9.1 功能验收

- [ ] 用户能通过配置界面添加/编辑列表字段
- [ ] 用户能通过配置界面添加/编辑详情字段
- [ ] 点击"测试配置"能返回样本数据
- [ ] 测试失败时显示明确的错误提示
- [ ] 保存配置后，正式任务能使用新配置
- [ ] 医保局网站能成功采集列表+详情数据

### 9.2 性能验收

- [ ] 测试采集（3条）在30秒内完成
- [ ] 配置界面加载时间 < 2秒
- [ ] 表单提交响应时间 < 1秒

### 9.3 用户体验验收

- [ ] 表单验证错误提示清晰易懂
- [ ] 样本数据展示格式友好
- [ ] 帮助提示（?）说明清晰
- [ ] 移动端基本可用

---

## 10. 后续优化方向

**优先级P1**（本次实施）：
- ✅ 配置界面
- ✅ 测试API
- ✅ 医保局配置

**优先级P2**（未来迭代）：
- 选择器可视化选择（类似浏览器开发者工具）
- 配置模板库（常见网站预设）
- 批量测试（测试多个注册证号）
- 详情采集进度实时展示

**优先级P3**（长期规划）：
- AI 自动识别页面结构并生成配置
- 断点续采（记录已采集详情）
- 数据去重（基于注册证号等唯一字段）
- 数据导出（Excel/CSV）

---

## 11. 附录

### 11.1 CSS 选择器速查

| 选择器 | 说明 | 示例 |
|--------|------|------|
| `#id` | ID选择器 | `#searchBtn` |
| `.class` | 类选择器 | `.detail-btn` |
| `tag` | 标签选择器 | `table` |
| `parent > child` | 直接子元素 | `tbody > tr` |
| `ancestor descendant` | 后代元素 | `table td` |
| `:nth-child(n)` | 第n个子元素 | `td:nth-child(2)` |
| `[attr=value]` | 属性选择器 | `[data-id="123"]` |

### 11.2 常见错误排查

| 现象 | 可能原因 | 解决方案 |
|------|----------|----------|
| 测试返回0条数据 | 列表选择器错误 | 检查 list_selector |
| 详情按钮点击无响应 | 选择器匹配多个元素 | 使用更精确的选择器 |
| 详情数据全为空 | 详情选择器错误 | 使用浏览器开发者工具验证 |
| 页面加载超时 | 网络慢或反爬限制 | 增加 timeout 配置 |

---

**文档版本历史**：

| 版本 | 日期 | 作者 | 变更说明 |
|------|------|------|----------|
| 1.0 | 2026-09-29 | Claude | 初始版本 |
