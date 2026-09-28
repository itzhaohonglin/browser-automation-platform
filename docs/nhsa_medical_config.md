# 国家医保局医用耗材查询配置

## 配置信息

**配置ID**: 40  
**任务ID**: 12  
**创建时间**: 2026-09-24

## 网站结构

### URL
```
https://code.nhsa.gov.cn/toSearch.html?sysflag=1004
```

### 页面结构特点
1. **多层iframe嵌套**（共2层）
   - 第1层iframe: `iframe#dataInfo` → `/hc/toHcListContainer.html`
   - 第2层iframe: `iframe.els-iframe.active` → `/hc/toPublicList4.html`
   - 实际查询表单在第2层iframe中

2. **查询表单**
   - 输入框选择器: `input[name='specificationCode']`
   - 查询按钮: `button:has-text('查询')`
   - 测试代码: `C01010100113038`

3. **结果表格**
   - 表格选择器: `.ui-jqgrid-btable`
   - 数据行选择器: `tbody tr.jqgrow`
   - 预期结果数: 2条记录

## 数据字段映射

| 序号 | 字段名 | 选择器 | 示例数据 |
|------|--------|--------|----------|
| 1 | 序号 | `td:nth-child(1)` | 1 |
| 2 | 医用耗材代码 | `td:nth-child(2)` | C0101010011303807555 |
| 3 | 一级分类 | `td:nth-child(3)` | 非血管介入治疗类材料 |
| 4 | 二级分类 | `td:nth-child(4)` | 呼吸介入材料 |
| 5 | 三级分类 | `td:nth-child(5)` | 气管支气管支架 |
| 6 | 标准规格 | `td:nth-child(6)` | 支架类 |
| 7 | 型号 | `td:nth-child(7)` | - |
| 8 | 材质特征 | `td:nth-child(8)` | 不锈钢 |
| 9 | 医疗器械分类 | `td:nth-child(9)` | 覆膜 |
| 10 | 医疗器械代码 | `td:nth-child(10)` | 001001 |
| 11 | 耗材名称 | `td:nth-child(11)` | 气管支气管支架（覆膜） |
| 12 | 生产企业 | `td:nth-child(12)` | 淮安市西格玛医用实业有限公司 |

## 测试查询

### 查询参数
```json
{
  "medical_code": "C01010100113038"
}
```

### 预期结果
- 返回2条记录
- 第1条: 序号1, 代码 C0101010011303807555
- 第2条: （需要实际执行查看）

## 数据库配置（crawler_configs表）

```python
{
  "config_name": "国家医保局-医用耗材信息查询",
  "target_url": "https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
  "need_login": False,
  "input_configs": [
    {
      "selector": "input[name='specificationCode']",
      "param_name": "medical_code",
      "label": "医用耗材代码",
      "required": True,
      "iframe_levels": 2,
      "iframe1_selector": "iframe#dataInfo",
      "iframe2_selector": "iframe.els-iframe.active"
    }
  ],
  "submit_selector": "button:has-text('查询')",
  "wait_selector": ".ui-jqgrid-btable",
  "fields_mapping": {
    "iframe_levels": 2,
    "iframe1_selector": "iframe#dataInfo",
    "iframe2_selector": "iframe.els-iframe.active",
    "table_selector": ".ui-jqgrid-btable",
    "row_selector": "tbody tr.jqgrow",
    "fields": [...]
  },
  "pagination_selector": None,
  "max_pages": 1,
  "is_active": True
}
```

## 执行步骤

### 1. 启动服务
```bash
uvicorn app.main:app --reload
```

### 2. 执行任务
```bash
# 方式1: 通过API触发
curl -X POST http://127.0.0.1:8000/api/jobs/12/execute

# 方式2: 通过前端看板
访问: http://127.0.0.1:8000/static/index.html
找到任务ID 12，点击"执行"按钮
```

### 3. 查看结果
```bash
# 查询任务状态
curl http://127.0.0.1:8000/api/jobs/12

# 查询采集结果
curl http://127.0.0.1:8000/api/results?job_id=12
```

## 注意事项

1. **iframe嵌套处理**
   - 当前executor.py可能需要适配多层iframe
   - 建议在执行器中添加递归进入iframe的逻辑

2. **选择器稳定性**
   - `button:has-text('查询')` 依赖按钮文本，如果网站更新需调整
   - `.ui-jqgrid-btable` 是jqGrid表格的标准类名，相对稳定

3. **等待时间**
   - 建议在点击查询后等待3-5秒
   - 可使用 `wait_selector` 确保表格加载完成

4. **数据提取**
   - 注意区分表头行和数据行（使用`tbody tr.jqgrow`）
   - 第一行可能为空或为占位行，需要过滤

## 分析文件

- `analyze_nhsa_final.py` - 网站结构分析脚本
- `nhsa_final_config.json` - 提取的配置信息
- `nhsa_final_result.png` - 查询结果截图
- `create_nhsa_config_final.py` - 数据库初始化脚本
