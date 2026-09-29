# 详情采集功能调试指南

## 概述

本文档提供详情采集功能的真实环境调试指导。由于该功能涉及实际网站访问，需要根据真实页面结构调整选择器配置。

## 前置准备

### 1. 确保服务已启动

```bash
uvicorn app.main:app --reload
```

### 2. 确保测试任务已创建

```bash
python -m scripts.init_nhsa_config
```

脚本会输出任务ID，例如：
```
[OK] 测试任务已创建，ID: 18
```

## 调试步骤

### Step 1: 首次执行测试

使用以下任一方式执行测试任务：

**方法1：API接口**
```bash
curl -X POST http://localhost:8000/api/jobs/18/execute
```

**方法2：前端看板**
访问 http://localhost:8000/static/index.html

### Step 2: 查看执行日志

观察后台日志输出，重点关注：

- `[详情]` 前缀的日志
- iframe 切换是否成功
- 列表数据是否提取到
- 详情按钮是否找到
- 详情数据是否提取成功

**正常日志示例：**
```
INFO - [详情] 列表数据提取完成，共 10 条
INFO - [详情] 第 1 条：点击详情按钮
INFO - [详情] 第 1 条：等待详情iframe加载
INFO - [详情] 第 1 条：详情数据提取成功
INFO - [详情] 第 1 条：关闭详情窗口
```

**异常日志示例：**
```
WARNING - [详情] 第 1 条：详情按钮不存在，跳过
ERROR - [详情] 第 1 条：无法获取详情iframe
```

### Step 3: 查看结果数据

查询数据库确认采集结果：

```sql
SELECT 
    id, 
    job_id, 
    JSON_EXTRACT(extracted_data, '$.summary') as summary,
    JSON_LENGTH(extracted_data, '$.items') as item_count
FROM crawler_results 
WHERE job_id = 18
ORDER BY id DESC 
LIMIT 1;
```

**预期结果：**
- `summary.total_items` > 0
- `summary.detail_success` > 0
- `item_count` > 0

**检查单条数据：**
```sql
SELECT 
    JSON_EXTRACT(extracted_data, '$.items[0]') as first_item
FROM crawler_results 
WHERE job_id = 18
ORDER BY id DESC 
LIMIT 1;
```

预期包含 `list_data` 和 `detail_data` 两个字段。

## 常见问题排查

### 问题1：iframe选择器不正确

**症状：**
```
ERROR - [详情] 无法获取详情iframe: iframe[name='mainFrame']
```

**排查步骤：**

1. 在浏览器中打开目标网站
2. 按 F12 打开开发者工具
3. 切换到 Elements 标签
4. 查找页面中的 `<iframe>` 标签
5. 检查 iframe 的 `name` 或 `id` 属性

**解决方法：**

修改 `scripts/init_nhsa_config.py` 中的 iframe 选择器：

```python
"iframe1_selector": "iframe[name='实际的name属性']",
# 或使用 id
"iframe1_selector": "iframe#实际的id",
```

如果有多层嵌套，逐层确认：
```python
"iframe_levels": 2,
"iframe1_selector": "iframe[name='mainFrame']",  # 第一层
"iframe2_selector": "iframe[name='contentFrame']",  # 第二层
```

### 问题2：列表数据为空

**症状：**
```
WARNING - [详情] 列表数据为空，跳过详情采集
```

**排查步骤：**

在浏览器控制台验证选择器：
```javascript
// 切换到正确的iframe后
document.querySelectorAll("#gridlist tbody tr")
```

**解决方法：**

1. 确认列表容器的实际ID或class
2. 修改 `list_selector`：

```python
# 示例1：使用class
"list_selector": ".result-table tbody tr",

# 示例2：使用更具体的选择器
"list_selector": "table.data-grid tbody tr:not(.empty)",
```

### 问题3：详情按钮不存在

**症状：**
```
WARNING - [详情] 第 1 条：详情按钮不存在，跳过
```

**排查步骤：**

1. 检查列表行的HTML结构
2. 找到"详情"或"查看"按钮所在的列
3. 确认按钮的标签类型（`<a>`, `<button>`, 等）

**示例HTML结构：**
```html
<tr>
  <td>1</td>
  <td>编码</td>
  <td>名称</td>
  <td class="operation">
    <a href="#" class="detail-link">详情</a>
  </td>
</tr>
```

**解决方法：**

修改 `detail_button_selector`：

```python
# 方法1：按位置选择
"detail_button_selector": "td:nth-child(5) a",

# 方法2：按class选择
"detail_button_selector": "td.operation a",

# 方法3：按文本内容选择（需要更复杂的逻辑）
"detail_button_selector": "td a:has-text('详情')",
```

### 问题4：详情iframe选择器错误

**症状：**
```
ERROR - [详情] 第 1 条：无法获取详情iframe
```

**排查步骤：**

1. 点击详情按钮后
2. 检查是否弹出对话框/模态窗口
3. 在开发者工具中查找新出现的iframe

**常见情况：**

**情况A：弹出层中有iframe**
```html
<div class="modal">
  <iframe id="detailFrame" src="..."></iframe>
</div>
```

**情况B：直接在页面中插入iframe**
```html
<iframe name="detailIframe" class="detail-view"></iframe>
```

**情况C：没有iframe，直接DOM渲染**
在这种情况下，需要修改逻辑，不使用iframe：

```python
"detail_iframe_selector": "",  # 留空表示无iframe
"wait_selector": ".detail-container",  # 直接等待详情容器
```

**解决方法：**

```python
# 使用id
"detail_iframe_selector": "iframe#detailFrame",

# 使用name
"detail_iframe_selector": "iframe[name='detailIframe']",

# 使用class
"detail_iframe_selector": "iframe.detail-view",
```

### 问题5：详情字段提取为空

**症状：**
```json
{
  "detail_status": "success",
  "detail_data": {
    "产品名称": "",
    "型号规格": "",
    "注册人名称": ""
  }
}
```

**排查步骤：**

1. 在详情页/iframe中检查实际的HTML结构
2. 验证字段选择器

**在浏览器控制台测试：**
```javascript
// 如果在iframe中，先切到iframe
document.querySelector("#productName")?.innerText
document.querySelector("#specification")?.innerText
```

**常见HTML结构：**

**结构1：表单输入框**
```html
<input id="productName" value="产品A" readonly>
```

**结构2：表格显示**
```html
<table>
  <tr>
    <td class="label">产品名称：</td>
    <td class="value">产品A</td>
  </tr>
</table>
```

**结构3：div显示**
```html
<div class="info-row">
  <span class="label">产品名称：</span>
  <span class="value">产品A</span>
</div>
```

**解决方法：**

根据实际结构调整选择器和属性：

```python
# 情况1：input框，取value属性
{"name": "产品名称", "selector": "#productName", "attr": "value"},

# 情况2：表格，取text
{"name": "产品名称", "selector": "tr:has(td:contains('产品名称')) td.value", "attr": "text"},

# 情况3：div，取text
{"name": "产品名称", "selector": ".info-row .value", "attr": "text"},
```

### 问题6：详情窗口无法关闭

**症状：**
后续数据采集失败，或浏览器卡住

**排查步骤：**

1. 检查详情窗口的关闭方式
2. 是否有关闭按钮？
3. 是否支持ESC键关闭？

**解决方法：**

修改关闭方式配置：

```python
# 方法1：使用ESC键（默认）
"close_method": "escape",

# 方法2：点击关闭按钮
"close_method": "button",
"close_button_selector": ".modal-close",

# 方法3：点击遮罩层
"close_method": "button",
"close_button_selector": ".modal-overlay",
```

## 选择器调整示例

### 完整配置示例

```python
"fields_mapping": {
    "iframe_levels": 2,
    "iframe1_selector": "iframe[name='mainFrame']",
    "iframe2_selector": "iframe[name='contentFrame']",
    "list_selector": "#gridlist tbody tr",
    "fields": [
        {"name": "序号", "selector": "td:nth-child(1)", "attr": "text"},
        {"name": "医疗器械编码", "selector": "td:nth-child(2)", "attr": "text"},
        {"name": "医疗器械名称", "selector": "td:nth-child(3)", "attr": "text"},
        {"name": "注册证号", "selector": "td:nth-child(4)", "attr": "text"}
    ],
    "detail_config": {
        "enabled": True,
        "detail_button_selector": "td:nth-child(5) a",
        "detail_iframe_selector": "iframe#detailIframe",
        "wait_selector": ".detail-table",
        "close_method": "escape",
        "fields": [
            {"name": "产品名称", "selector": "#productName", "attr": "text"},
            {"name": "型号规格", "selector": "#specification", "attr": "text"},
            {"name": "注册人名称", "selector": "#registrant", "attr": "text"},
            {"name": "注册人住所", "selector": "#address", "attr": "text"},
            {"name": "生产地址", "selector": "#productionAddress", "attr": "text"}
        ],
        "retry": {
            "max_attempts": 3,
            "delay_seconds": 2
        },
        "timeout": {
            "iframe_load": 10000,
            "wait_selector": 5000,
            "click": 10000
        }
    }
}
```

### 调整流程

1. **备份原配置**（可选）
2. **修改 `scripts/init_nhsa_config.py`**
3. **清空旧数据**（可选）：
   ```sql
   DELETE FROM crawler_results WHERE job_id IN (SELECT id FROM job_queue WHERE config_id = 43);
   DELETE FROM job_queue WHERE config_id = 43;
   DELETE FROM crawler_configs WHERE id = 43;
   ```
4. **重新初始化**：
   ```bash
   python -m scripts.init_nhsa_config
   ```
5. **再次测试**
6. **查看结果**

## 调试技巧

### 1. 启用详细日志

在 `.env` 文件中设置：
```
LOG_LEVEL=DEBUG
```

### 2. 使用有头模式

在 `.env` 文件中设置：
```
HEADLESS_MODE=False
```

这样可以看到浏览器实际操作过程。

### 3. 增加等待时间

如果页面加载慢，可以增加超时时间：

```python
"timeout": {
    "iframe_load": 15000,  # 增加到15秒
    "wait_selector": 10000,  # 增加到10秒
    "click": 15000
}
```

### 4. 减少重试次数（加快调试）

```python
"retry": {
    "max_attempts": 1,  # 调试时设为1，避免等待
    "delay_seconds": 1
}
```

### 5. 限制页数（加快调试）

```python
max_pages=1,  # 只采集第一页
```

### 6. WebSocket实时监控

打开前端看板，实时查看任务状态和日志：
```
http://localhost:8000/static/index.html
```

## 验证清单

调试完成后，确认以下项目：

- [ ] 列表数据能正常提取
- [ ] 详情按钮能正常找到并点击
- [ ] 详情iframe能正常加载
- [ ] 详情字段能正常提取
- [ ] 详情窗口能正常关闭
- [ ] 多页数据能正常翻页
- [ ] 统计数据正确（total_items, detail_success, detail_failed）
- [ ] 数据库中有完整的 list_data 和 detail_data

## 提交配置

确认调试成功后，提交调整后的配置：

```bash
git add scripts/init_nhsa_config.py
git commit -m "fix: adjust NHSA selectors based on real page structure"
git push
```

## 常见错误码

| 错误信息 | 原因 | 解决方法 |
|---------|------|---------|
| 无法获取详情iframe | iframe选择器错误 | 检查iframe的name/id属性 |
| 详情按钮不存在 | 按钮选择器错误 | 检查按钮所在的td位置 |
| 等待详情容器超时 | wait_selector错误或加载慢 | 增加超时时间或修改选择器 |
| 列表数据为空 | list_selector错误 | 检查列表容器的实际结构 |

## 联系支持

如遇到无法解决的问题，请提供：

1. 完整的错误日志
2. 目标网站的URL
3. 当前的配置JSON
4. 浏览器开发者工具中的HTML截图

## 附录：浏览器开发者工具使用

### 打开开发者工具
- Windows/Linux: F12 或 Ctrl+Shift+I
- Mac: Cmd+Option+I

### 查找元素
1. 点击左上角的"选择元素"图标
2. 鼠标悬停在页面元素上
3. 在Elements标签中查看HTML结构

### 测试选择器
在Console标签中执行：
```javascript
// 测试CSS选择器
document.querySelector("your-selector")
document.querySelectorAll("your-selector")

// 查看元素内容
element.innerText
element.getAttribute("value")

// 查看iframe
frames  // 列出所有iframe
```

### 切换iframe上下文
在Console标签上方的下拉菜单中选择目标iframe。
