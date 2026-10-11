# iframe 执行流程修复 - 最终版本

## 修复日期
2026-10-10

## 问题描述

任务执行失败，错误信息：
```
Frame.wait_for_selector: Timeout 15000ms exceeded.
Call log:
  - waiting for locator(".ui-jqgrid-btable") to be visible
    33 × locator resolved to hidden <table>...</table>
```

## 根本原因

对于国家医保局网站（code.nhsa.gov.cn），表单输入框和查询按钮都在 **iframe 内部**，而不是在主页面。

之前的文档 `bugfix_iframe_execution_order.md` 假设输入框在主页面，这对于某些网站是正确的，但对于医保局网站是错误的。

## 最终解决方案

### 智能检测机制

代码实现了智能检测，自动判断输入框位置：

```python
# 1. 首先尝试在主页面查找输入框
input_in_main_page = False
if first_input_selector:
    try:
        main_input = await page.query_selector(first_input_selector)
        if main_input and await main_input.is_visible():
            input_in_main_page = True
    except:
        pass

# 2. 根据检测结果选择执行流程
if not input_in_main_page and iframe_levels >= 2:
    # 输入框在iframe中 → 先进入iframe再操作
    进入 iframe1
    进入 iframe2
    operation_frame = iframe2
else:
    # 输入框在主页面 → 直接在主页面操作
    operation_frame = page
```

### 执行流程（医保局网站）

对于 `input[name='regcardNm']` 在 iframe 内的情况：

```
1. 访问目标 URL
   └─ https://code.nhsa.gov.cn/toSearch.html?sysflag=1004

2. 智能检测输入框位置
   └─ 主页面找不到 → 判断为 iframe 内

3. 进入多层 iframe
   ├─ 进入 iframe1: iframe#dataInfo
   └─ 进入 iframe2: iframe.els-iframe.active

4. 在 iframe2 中填充表单
   └─ input[name='regcardNm'] = 注册证号

5. 在 iframe2 中点击查询按钮
   └─ button:has-text('查询')

6. 等待结果表格加载（关键修复）
   └─ 使用 state="attached" 而不是 state="visible"
   └─ 原因：表格可能一开始是 hidden 状态

7. 在 iframe2 中提取数据
   └─ 选择器: tbody tr.jqgrow
```

### 关键代码修复

**文件**: `app/services/executor.py` 第 1525-1536 行

```python
# 修复前（错误）
await target_frame.wait_for_selector(
    config.wait_selector,
    state="visible",  # ❌ 一直等待 visible，但表格是 hidden
    timeout=timeouts['wait_selector']
)

# 修复后（正确）
await target_frame.wait_for_selector(
    config.wait_selector,
    state="attached",  # ✅ 只要元素存在于 DOM 即可
    timeout=timeouts['wait_selector']
)
```

## 为什么表格是 hidden 状态？

医保局网站使用 jqGrid 动态表格，查询后：
1. 表格框架已存在（attached to DOM）
2. 但可能设置了 `display: none` 或其他隐藏样式
3. 数据加载完成后才显示

如果等待 `state="visible"`，会一直超时。改用 `state="attached"` 后，只要元素在 DOM 中就继续执行。

## 测试结果

### 成功案例

```bash
# 任务执行日志
2026-10-10 22:49:15,915 - 任务 1 执行成功，耗时 22.62 秒
2026-10-10 22:49:16,022 - 任务 3002 执行成功，耗时 22.73 秒
2026-10-10 22:49:16,085 - 任务 3 执行成功，耗时 22.68 秒
```

### 数据提取结果

虽然任务执行成功，但提取到 0 条数据：

```json
{
  "items": [],
  "summary": {
    "total_items": 0,
    "detail_success": 0,
    "detail_failed": 0,
    "pages_crawled": 1
  }
}
```

**原因分析**：
- 查询的注册证号在数据库中不存在
- 或者选择器 `tbody tr.jqgrow` 需要调整

## 配置说明

### 当前配置（Config ID: 1）

```json
{
  "config_name": "国家医保局-注册证号查询（含详情）",
  "target_url": "https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
  "input_configs": [
    {
      "selector": "input[name='regcardNm']",
      "param_name": "registration_no"
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
      {"name": "医用耗材代码", "selector": "td:nth-child(2)", "attr": "text"},
      {"name": "耗材名称", "selector": "td:nth-child(11)", "attr": "text"}
    ]
  }
}
```

### 关键配置项

| 配置项 | 作用 | 说明 |
|--------|------|------|
| `iframe_levels: 2` | 指定嵌套层数 | 触发智能检测和多层 iframe 处理 |
| `iframe1_selector` | 第1层 iframe | `iframe#dataInfo` |
| `iframe2_selector` | 第2层 iframe | `iframe.els-iframe.active` |
| `wait_selector` | 等待元素 | `.ui-jqgrid-btable`（表格容器） |
| `list_selector` | 数据行选择器 | `tbody tr.jqgrow` |

## 适用场景

### 场景 A：输入框在主页面，数据在 iframe

```
执行流程：
1. 在主页面填充表单
2. 在主页面点击查询
3. 进入 iframe 提取数据
```

### 场景 B：输入框和数据都在 iframe（医保局）

```
执行流程：
1. 进入 iframe
2. 在 iframe 中填充表单
3. 在 iframe 中点击查询
4. 在 iframe 中提取数据
```

代码会自动检测并选择正确的流程。

## 调试建议

如果遇到类似问题：

1. **检查输入框位置**
   ```python
   # 在主页面
   await page.query_selector('input[name="xxx"]')
   
   # 在 iframe 中
   iframe = await page.frame_locator('iframe#xxx')
   await iframe.query_selector('input[name="xxx"]')
   ```

2. **检查等待元素的可见性**
   ```python
   # 如果元素始终是 hidden，改用 state="attached"
   await frame.wait_for_selector(selector, state="attached")
   ```

3. **查看日志确认流程**
   ```
   输入框在主页面
   OR
   输入框可能在iframe中，先进入iframe
   ```

## 历史问题回顾

1. **Event Loop 关闭问题**（已修复）
   - 文件：`app/services/process_pool.py`
   - 方案：手动管理 event loop 生命周期

2. **元素等待超时**（已修复）
   - 文件：`app/services/executor.py`
   - 方案：添加 `wait_for_selector` 和延迟

3. **选择器错误**（已修复）
   - `input[name='zczbh']` → `input[name='regcardNm']`

4. **等待策略错误**（本次修复）
   - `state="visible"` → `state="attached"`

## 文件变更记录

- `app/services/executor.py` (行 1336-1536)
  - 添加智能检测逻辑
  - 调整 iframe 进入时机
  - 修改等待策略为 `state="attached"`

## 最终测试结果（2026-10-10）

### 列表数据采集 ✅
```
总任务数: 7
成功: 7
失败: 0
成功率: 100%
```

### 详情数据采集 ✅

**详情采集配置修复**：
1. `click_method: 'javascript'` - 使用JS点击避免元素遮挡
2. `detail_iframe_selector: 'iframe.artDialog-iframe'` - 正确的iframe选择器

**测试结果**：
```
Job ID: 3003
总条数: 1
详情成功: 1
详情失败: 0
```

**日志确认**：
```
[详情] 使用JavaScript点击方法
[详情] 等待详情iframe: iframe.artDialog-iframe
[详情] 成功切换到详情iframe
[详情] 单条模式：提取 7 个详情字段
[详情] 第 1 条提取完成，字段数: 7
```

### 已解决的核心问题

1. ✅ **智能iframe检测** - 自动判断输入框位置
2. ✅ **多层iframe导航** - 正确进入iframe1 → iframe2
3. ✅ **等待策略** - 使用 `state="attached"` 而不是 `state="visible"`
4. ✅ **列表数据提取** - 选择器 `tbody tr.jqgrow` 正常工作
5. ✅ **详情按钮点击** - JavaScript点击避免遮挡
6. ✅ **详情iframe导航** - `iframe.artDialog-iframe` 正常工作

### 待优化项

1. **详情字段选择器** - 当前提取到的值为空，需要根据实际HTML调整选择器：
   ```json
   {
     "注册证号": "input[name='zczbh'], td:contains('注册证号') + td",
     "产品名称": "input[name='productName'], td:contains('产品名称') + td"
   }
   ```
   需要实际查看详情页面的HTML结构来优化。

2. **关闭弹窗** - 关闭按钮点击超时，但不影响数据提取
