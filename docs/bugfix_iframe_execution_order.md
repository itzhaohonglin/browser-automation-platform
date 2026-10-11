# 任务失败根本原因及修复方案

## 问题根源

**任务失败的根本原因：代码执行流程错误**

### 错误的执行流程（修复前）

```
1. 访问目标 URL
2. ❌ 检测到 iframe_levels=2，立即进入 iframe
   - 进入 iframe1 (#dataInfo)
   - 进入 iframe2 (.els-iframe.active)
3. ❌ 在 iframe2 中查找 input[name='zczbh']
   - 找不到！因为输入框在主页面
   - 超时失败：TimeoutError: 元素 input[name='zczbh'] 等待超时
```

### 正确的执行流程（修复后）

```
1. 访问目标 URL
2. ✅ 在主页面填充 input[name='zczbh']
3. ✅ 在主页面点击查询按钮
4. ✅ 等待结果容器出现
5. ✅ 现在进入 iframe 提取数据
   - 进入 iframe1 (#dataInfo)
   - 进入 iframe2 (.els-iframe.active)
6. ✅ 在 iframe2 中提取数据表格
```

## 核心问题

配置中的 `iframe_levels` 是用于**数据提取**的，不是用于**表单填充**的。

- **表单输入框**：在主页面
- **数据结果表格**：在 iframe 内

但代码错误地在填充表单之前就进入了 iframe，导致找不到输入框元素。

## 修复内容

### 文件：app/services/executor.py

#### 修复1：调整执行顺序

**修改位置**：第 1340-1450 行

**关键改动**：
1. 先在主页面填充表单（步骤5）
2. 在主页面点击提交按钮（步骤6）
3. 等待结果加载（步骤7）
4. **然后**才进入 iframe 进行数据提取（步骤8）

```python
# 修改前（错误）：
# 步骤5: 进入 iframe
# 步骤6: 填充表单 ❌ 找不到元素
# 步骤7: 点击提交

# 修改后（正确）：
# 步骤5: 在主页面填充表单 ✅
# 步骤6: 在主页面点击提交 ✅
# 步骤7: 等待结果加载
# 步骤8: 进入 iframe 提取数据 ✅
```

#### 修复2：自动检测逻辑优化

当没有配置 `iframe_levels` 时，自动检测逻辑改为查找数据表格而不是输入框：

```python
# 修改前：查找输入框来选择 frame
inputs = await frame.query_selector_all('input')

# 修改后：查找数据容器来选择 frame
table_selector = config.fields_mapping.get('list_selector', 'table')
tables = await frame.query_selector_all(table_selector)
```

## 之前的修复回顾

### 1. Event Loop 修复（已完成）

**问题**：进程池中 `asyncio.run()` 导致 event loop 关闭
**修复**：使用 `asyncio.new_event_loop()` 手动管理生命周期
**文件**：app/services/process_pool.py

### 2. 元素等待增强（已完成）

**问题**：填充表单前没有等待元素可见
**修复**：添加 `wait_for_selector` 和额外延迟
**文件**：app/services/executor.py

### 3. 执行流程修复（本次）

**问题**：在错误的位置（iframe内）查找输入框
**修复**：调整执行顺序，先填充表单再进入 iframe
**文件**：app/services/executor.py

## 预期效果

修复后，任务应该能够：

1. ✅ 成功在主页面找到并填充 `input[name='zczbh']`
2. ✅ 成功点击查询按钮
3. ✅ 等待结果加载
4. ✅ 成功进入 iframe 提取数据
5. ✅ 完成整个采集流程

## 测试建议

1. 观察新任务的执行日志
2. 确认日志顺序为：
   - 填充字段
   - 点击提交按钮  
   - 等待结果加载
   - 进入第1层iframe
   - 进入第2层iframe
   - 提取数据
3. 检查任务状态是否变为 success

## 配置说明

对于类似的采集任务，配置结构应该是：

```python
{
    "input_configs": [
        {
            "selector": "input[name='xxx']",  # 主页面的输入框
            "param_name": "xxx"
        }
    ],
    "submit_selector": "button",  # 主页面的提交按钮
    "wait_selector": ".result-container",  # 主页面的结果容器
    "fields_mapping": {
        "iframe_levels": 2,  # 用于数据提取
        "iframe1_selector": "iframe#first",
        "iframe2_selector": "iframe.second",
        "list_selector": "tbody tr",  # iframe 内的数据
        "fields": [...]
    }
}
```

**关键理解**：
- `input_configs`、`submit_selector`、`wait_selector` → 操作主页面
- `fields_mapping` 中的 iframe 配置 → 提取数据时使用
