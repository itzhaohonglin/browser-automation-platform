# 详情关闭按钮问题 - 修复方案

## 问题确认

**根本原因：关闭按钮不在详情iframe中，而在主iframe中！**

测试结果显示：
- 详情iframe（detail_frame）：没有有效的关闭按钮
- 主iframe（iframe2）：有 `button.ui-dialog-close`（可见的关闭按钮）

当前代码在 `detail_frame` 中查找关闭按钮，所以关闭失败。

## 修复方案

### 方案1：修改执行器代码（推荐）

修改 `app/services/executor.py` 第813-848行的关闭逻辑：

```python
# 5. 关闭详情（失败不影响数据返回）
try:
    close_method = detail_config.get('close_method', 'auto')
    close_selector = detail_config.get('close_selector')
    close_timeout = detail_config.get('timeout', {}).get('close', 5000)

    # 重要：关闭按钮在主frame（main_page），不在详情iframe（detail_frame）
    close_target_frame = main_page  # 修改：使用main_page而不是detail_frame

    if close_method == 'click' and close_selector:
        # 点击关闭按钮
        self.logger.info(f"[详情] 点击关闭按钮: {close_selector}")
        await close_target_frame.click(close_selector, timeout=close_timeout)
    elif close_method == 'escape':
        # 按ESC键
        self.logger.info(f"[详情] 按ESC键关闭")
        await close_target_frame.keyboard.press('Escape')
    elif close_method == 'auto':
        # 自动选择：优先点击，失败则ESC
        if close_selector:
            try:
                await close_target_frame.click(close_selector, timeout=close_timeout)
            except Exception as e:
                self.logger.info(f"[详情] 关闭按钮点击失败 ({e})，改用ESC键")
                await close_target_frame.keyboard.press('Escape')
        else:
            await close_target_frame.keyboard.press('Escape')

    # 6. 等待返回列表页
    await asyncio.sleep(0.5)

except Exception as e:
    self.logger.warning(f"[详情] 关闭操作失败，但数据已提取: {e}")
    # 尝试强制ESC作为后备
    try:
        await main_page.keyboard.press('Escape')  # 修改：使用main_page
        await asyncio.sleep(0.5)
    except:
        pass
```

### 方案2：更新配置（快速临时方案）

更新配置使用正确的关闭选择器：

```python
# 更新数据库配置
detail_config = {
    ...
    "close_method": "click",
    "close_selector": "button.ui-dialog-close",  # 正确的选择器
    ...
}
```

**但这还不够！** 因为代码会在 `detail_frame` 中查找，而按钮在 `main_page` 中，所以还是会失败。

**结论：必须同时修改代码和配置！**

## 实施步骤

### 步骤1：修改执行器代码

编辑 `app/services/executor.py`：

1. 找到第813行附近的关闭逻辑
2. 将所有 `detail_frame` 改为 `main_page`（在关闭部分）
3. 确保 `main_page` 变量可访问（已经是函数参数）

### 步骤2：更新配置

```sql
UPDATE crawler_configs
SET fields_mapping = JSON_MODIFY(
    fields_mapping,
    '$.detail_config.close_selector',
    'button.ui-dialog-close'
)
WHERE id = 1;
```

或使用Python脚本：

```python
import json
from sqlalchemy import create_engine, text
from app.core.config import settings

engine = create_engine(settings.DATABASE_URL.replace('aioodbc', 'pyodbc'))

with engine.connect() as conn:
    # 读取当前配置
    result = conn.execute(text('SELECT fields_mapping FROM crawler_configs WHERE id = 1'))
    row = result.fetchone()
    fields_mapping = json.loads(row[0]) if isinstance(row[0], str) else row[0]
    
    # 更新关闭配置
    fields_mapping['detail_config']['close_method'] = 'click'
    fields_mapping['detail_config']['close_selector'] = 'button.ui-dialog-close'
    
    # 保存
    conn.execute(text("""
        UPDATE crawler_configs
        SET fields_mapping = :new_mapping
        WHERE id = 1
    """), {'new_mapping': json.dumps(fields_mapping)})
    conn.commit()
    
    print("配置已更新")
```

### 步骤3：验证测试

1. 重启服务（确保代码更改生效）
2. 创建新测试任务
3. 执行并验证结果：
   - 第1条：24条
   - 第2条：28条（应该正确了）
   - 第3条：29条（应该正确了）

## 预期结果

修复后：
- 每次详情采集完成后，关闭按钮正确点击
- 弹窗关闭，回到列表页
- 下一条详情采集时，打开的是新的详情
- 所有详情数据量正确（24, 28, 29）
