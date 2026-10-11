# 详情分页问题解决方案

## 问题分析

经过调试发现的核心问题：
1. jqGrid在多个详情弹窗间会保留页码状态
2. 第一个列表项从第1页开始，第二个从第3页开始，第三个继续往后
3. 所有详情记录的第一个字段值相同（UUID），导致基于第一字段的重复检测失败

## 解决方案（按用户建议）

### 简化的翻页逻辑

```python
# 1. 打开详情弹窗后，重置jqGrid到第1页
await detail_frame.evaluate("""
    () => {
        const grid = jQuery('table.ui-jqgrid-btable:first')[0];
        if (grid && grid.id) {
            jQuery('#' + grid.id).jqGrid('setGridParam', {page: 1}).trigger('reloadGrid');
        }
    }
""")
await asyncio.sleep(2)

# 2. 循环提取每一页
while detail_page <= max_pages:
    # 提取当前页数据
    page_items = extract_current_page()
    all_items.extend(page_items)
    
    # 检查"下一页"按钮状态
    button_disabled = await detail_frame.evaluate("""
        (selector) => {
            const btn = document.querySelector(selector);
            return btn?.classList.contains('ui-state-disabled') || false;
        }
    """, next_button_selector)
    
    # 如果按钮禁用，说明没有下一页了
    if button_disabled:
        break
    
    # 点击下一页（使用jqGrid API）
    await detail_frame.evaluate("""
        () => {
            const grid = jQuery('table.ui-jqgrid-btable:first')[0];
            if (grid && grid.id) {
                const currentPage = jQuery('#' + grid.id).jqGrid('getGridParam', 'page');
                jQuery('#' + grid.id).jqGrid('setGridParam', {page: currentPage + 1}).trigger('reloadGrid');
            }
        }
    """)
    await asyncio.sleep(3)
    detail_page += 1
```

### 配置要求

```json
{
  "detail_list_mode": true,
  "detail_list_selector": "tbody tr.jqgrow",
  "detail_pagination_selector": "#next_gridpage",
  "max_detail_pages": 10
}
```

## 实施步骤

1. 移除基于总记录数的判断逻辑
2. 移除基于重复数据的检测逻辑
3. 只保留基于按钮状态的简单判断
4. 确保每次打开详情弹窗时重置到第1页

---

## 2026-10-11 完整诊断报告

### 测试案例
- **注册证号**: 鄂械注准20142061254
- **预期结果**: 列表3条，详情分别为24、28、29条

### 实际测试结果

**列表页**: 3条数据 ✓

**详情页数据量**:
1. 第1条: 24条（1页，`total_pages: 1`）✓
2. 第2条: 28条（2页，`total_pages: 2`，第1页显示25条）⚠️ 需要翻页
3. 第3条: 29条（2页，`total_pages: 2`，第1页显示25条）⚠️ 需要翻页

### 根本原因

1. **输入框选择器问题** ✓ 已解决
   - 原配置: `input[name='zczbh']`
   - 实际应为: `input[name='regcardNm']`

2. **详情页分页问题** - 核心问题
   - 详情默认每页25条
   - 超过25条的详情需要翻页才能获取完整数据
   - 当前代码已实现详情分页逻辑（第661-768行）
   - 配置已包含 `detail_pagination_selector: #next_gridpage`

3. **验证码影响**
   - 首次测试时验证码阻止查询，返回0条数据
   - 验证码移除后，数据正常获取

### 代码验证

**执行器代码检查** (`app/services/executor.py`)：

✓ 重置逻辑（第665-678行）：
```python
# 重要：重置jqGrid到第1页（避免保留之前的页码状态）
await detail_frame.evaluate("""
    () => {
        const grid = jQuery('table.ui-jqgrid-btable:first')[0];
        if (grid && grid.id) {
            jQuery('#' + grid.id).jqGrid('setGridParam', {page: 1}).trigger('reloadGrid');
        }
    }
""")
```

✓ 分页循环（第689-767行）：
```python
while detail_page <= max_detail_pages:
    # 提取当前页
    # 检查按钮状态
    button_disabled = await detail_frame.evaluate(...)
    if button_disabled:
        break
    # 翻页
    await detail_frame.evaluate(...)
```

**结论：代码逻辑正确，无需修改！**

### 配置检查

当前配置（ID=1）：
```json
{
  "detail_config": {
    "enabled": true,
    "detail_list_mode": true,
    "detail_list_selector": "tbody tr.jqgrow",
    "detail_pagination_selector": "#next_gridpage",
    "max_detail_pages": 10
  }
}
```

**问题：输入框选择器错误！**

### 解决方案

#### 方案1: 更新现有配置（快速）

```sql
UPDATE crawler_configs 
SET input_configs = '[{"selector":"input[name=''regcardNm'']","param_name":"registration_no","label":"注册证号","required":true}]'
WHERE id = 1;
```

#### 方案2: 重新初始化配置（推荐）

创建脚本 `scripts/fix_nhsa_config.py`:

```python
import asyncio
from sqlalchemy import text
from app.core.database import get_session

async def fix_config():
    async with get_session() as session:
        # 更新输入框配置
        await session.execute(text("""
            UPDATE crawler_configs 
            SET input_configs = :new_config
            WHERE id = 1
        """), {
            'new_config': '[{"selector":"input[name=\'regcardNm\']","param_name":"registration_no","label":"注册证号","required":true}]'
        })
        await session.commit()
        print("配置已更新！")

if __name__ == "__main__":
    asyncio.run(fix_config())
```

### 验证测试

1. 更新配置后，创建测试任务
2. 运行任务
3. 检查结果：
   - 列表：3条
   - 第1条详情：24条
   - 第2条详情：28条（应自动翻页获取完整数据）
   - 第3条详情：29条（应自动翻页获取完整数据）

### 总结

**问题定位**：
- ✓ 输入框选择器错误 → 需要修正配置
- ✓ 详情分页逻辑正确 → 无需修改代码
- ✓ 配置包含分页设置 → 无需修改配置

**唯一需要修改**：
更新 `input_configs[0].selector` 从 `input[name='zczbh']` 改为 `input[name='regcardNm']`

**预期结果**：
修正后，程序应该能够：
1. 正确查询到3条列表数据
2. 自动进入每条的详情页
3. 自动翻页获取所有详情数据（24、28、29条）
4. 返回完整的结构化数据
