# 国家医保局注册证号查询 - 详情采集设计文档

**创建日期**: 2026-09-30  
**需求**: 抓取注册证号"滇械注准20192140008"的列表数据和详情数据

---

## 一、需求分析

### 目标网站
- URL: https://code.nhsa.gov.cn/toSearch.html?sysflag=1004
- 查询方式: 注册证号查询
- 测试数据: 滇械注准20192140008

### 数据需求
1. **列表数据**: 查询结果的表格行数据（12个字段）
2. **详情数据**: 点击"详情"按钮后的详细信息
3. **数据关联**: 每条列表记录关联一条详情记录

---

## 二、架构评估

### 现有能力
✅ **执行器已支持详情采集**
- `_extract_detail_data()`: 单条详情提取
- `_extract_detail_with_retry()`: 带重试机制
- `_extract_list_with_details()`: 列表+详情提取
- `_extract_list_with_details_paginated()`: 分页列表+详情

✅ **多层iframe支持**
- 支持配置 `iframe_levels`、`iframe1_selector`、`iframe2_selector`
- 自动切换到目标iframe上下文

✅ **详情窗口处理**
- 支持iframe详情页
- 支持多种关闭方式（ESC、按钮点击、自动）
- 失败时自动重试

### 架构结论
**现有架构完全满足需求，无需改造。**

---

## 三、技术设计

### 3.1 配置结构

```python
{
  "config_name": "国家医保局-注册证号查询（含详情）",
  "target_url": "https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
  
  # 输入配置
  "input_configs": [
    {
      "selector": "input[name='zczbh']",
      "param_name": "registration_no"
    }
  ],
  
  # 字段映射
  "fields_mapping": {
    "iframe_levels": 2,
    "iframe1_selector": "iframe#dataInfo",
    "iframe2_selector": "iframe.els-iframe.active",
    "list_selector": "tbody tr.jqgrow",
    
    # 列表字段（12个）
    "fields": [...],
    
    # 详情配置
    "detail_config": {
      "enabled": true,
      "detail_button_selector": "a:has-text('详情')",
      "detail_iframe_selector": "iframe[src*='detail']",
      "wait_selector": "table, .detail-content",
      "fields": [
        {"name": "注册证号", "selector": "...", "attr": "text"},
        {"name": "产品名称", "selector": "...", "attr": "text"},
        {"name": "规格型号", "selector": "...", "attr": "text"},
        {"name": "注册人名称", "selector": "...", "attr": "text"},
        {"name": "生产地址", "selector": "...", "attr": "text"},
        {"name": "产品标准", "selector": "...", "attr": "text"},
        {"name": "适用范围", "selector": "...", "attr": "text"}
      ],
      "close_method": "auto",
      "retry": {
        "max_attempts": 3,
        "delay_seconds": 2
      }
    }
  }
}
```

### 3.2 执行流程

```
1. 访问目标URL
   ↓
2. 进入第2层iframe
   ↓
3. 填写注册证号 → 点击查询
   ↓
4. 等待列表加载
   ↓
5. 提取列表数据（所有行）
   ↓
6. 遍历每一行:
   a. 定位详情按钮
   b. 点击详情按钮
   c. 切换到详情iframe
   d. 等待详情内容加载
   e. 提取详情字段
   f. 关闭详情窗口
   g. 返回列表页
   ↓
7. 组装数据并保存
```

### 3.3 数据结构

#### 数据库存储
```json
{
  "items": [
    {
      "list_data": {
        "序号": "1",
        "医用耗材代码": "C0101010011303807555",
        "一级分类": "非血管介入治疗类材料",
        "耗材名称": "气管支气管支架（覆膜）",
        "生产企业": "淮安市西格玛医用实业有限公司"
      },
      "detail_data": {
        "注册证号": "滇械注准20192140008",
        "产品名称": "一次性使用气管支气管支架",
        "规格型号": "多种规格",
        "注册人名称": "某医疗器械公司",
        "生产地址": "云南省昆明市...",
        "产品标准": "YZB/...",
        "适用范围": "用于气管或支气管狭窄..."
      },
      "detail_status": "success"
    }
  ],
  "summary": {
    "total_items": 5,
    "detail_success": 5,
    "detail_failed": 0
  }
}
```

---

## 四、不确定项与调试策略

### 4.1 待验证的选择器

由于无法实际访问网站，以下选择器需要运行时验证：

| 选择器 | 预设值 | 可能的替代方案 |
|--------|--------|----------------|
| detail_button_selector | `a:has-text('详情')` | `a[onclick*='detail']`, `button.detail-btn` |
| detail_iframe_selector | `iframe[src*='detail']` | `.ui-dialog iframe`, 直接在dialog中无iframe |
| detail字段选择器 | `td:contains('label') + td` | `input[name='field']`, `.form-group span` |

### 4.2 调试流程

**步骤1: 运行初始化脚本**
```bash
python scripts/init_nhsa_registration_config.py
```

**步骤2: 执行测试任务**
```bash
curl -X POST http://127.0.0.1:8000/api/jobs/任务ID/execute
```

**步骤3: 查看日志并调整**
- 根据日志找到失败的选择器
- 使用浏览器开发者工具确定正确选择器
- 更新数据库配置
- 重新执行

---

## 五、实施步骤

### 阶段1: 初始化配置
1. 运行 `init_nhsa_registration_config.py`
2. 验证配置和测试任务已创建

### 阶段2: 首次执行测试
1. 启动服务
2. 执行测试任务
3. 观察日志

### 阶段3: 选择器调整
1. 使用开发者工具检查页面结构
2. 更新选择器配置
3. 重新执行

### 阶段4: 数据验证
1. 查询 `crawler_results` 表
2. 验证数据完整性

---

## 六、总结

### 技术方案
- **无需系统改造**: 现有架构完全支持
- **配置驱动**: 通过数据库配置实现
- **渐进式调试**: 先列表后详情

### 核心优势
1. 零代码改动
2. 灵活可调
3. 失败隔离
4. 完整日志

### 下一步行动
1. 运行初始化脚本
2. 执行测试
3. 调整选择器
4. 验证数据

---

**实施脚本**: `scripts/init_nhsa_registration_config.py`  
**参考文档**: `docs/detail_extraction_debug_guide.md`
