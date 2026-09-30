# 国家医保局注册证号查询配置指南

## 配置概述

本配置用于采集国家医保局医疗器械信息系统中的注册证号查询结果。

- **配置ID**: 44
- **查询方式**: 注册证号精确查询
- **测试注册证号**: 滇械注准20192140008
- **功能**: 列表数据采集 + 详情数据采集
- **采集状态**: 已验证可用

## 关键配置项

### 目标网址
- **主URL**: https://www.nhsa.gov.cn/
- **查询功能**: 医疗器械信息查询系统

### 输入配置

输入表单配置用于向网页注入搜索参数：

```json
{
  "selector": "input[name='regcardNm']",
  "param_name": "registration_no",
  "input_method": "type",
  "clear_before": true
}
```

**说明**:
- `selector`: 输入框的CSS选择器
- `param_name`: 任务参数中的字段名称
- `input_method`: 输入方法（type/set_value）
- `clear_before`: 输入前是否清空

### iframe 配置

系统使用多层 iframe 结构，需要逐层定位：

```json
{
  "iframe_levels": 2,
  "iframe_config": [
    {
      "level": 1,
      "selector": "iframe#dataInfo",
      "wait_method": "visibility"
    },
    {
      "level": 2,
      "selector": "iframe.els-iframe.active",
      "wait_method": "visibility"
    }
  ]
}
```

**说明**:
- `iframe_levels`: iframe嵌套层数
- `level 1`: 第一层iframe（ID选择器）
- `level 2`: 第二层iframe（class选择器）
- `wait_method`: 定位前的等待策略

### 列表数据采集配置

从搜索结果表格中提取数据字段：

```json
{
  "list_selector": "table tbody tr",
  "fields": [
    {"name": "序号", "selector": "td:nth-child(1)"},
    {"name": "耗材名称", "selector": "td:nth-child(2)"},
    {"name": "医用耗材代码", "selector": "td:nth-child(3)"},
    {"name": "一级分类", "selector": "td:nth-child(4)"},
    {"name": "二级分类", "selector": "td:nth-child(5)"},
    {"name": "三级分类", "selector": "td:nth-child(6)"},
    {"name": "生产企业", "selector": "td:nth-child(7)"},
    {"name": "标准规格", "selector": "td:nth-child(8)"},
    {"name": "型号", "selector": "td:nth-child(9)"},
    {"name": "医疗器械代码", "selector": "td:nth-child(10)"},
    {"name": "医疗器械分类", "selector": "td:nth-child(11)"},
    {"name": "材质特征", "selector": "td:nth-child(12)"}
  ]
}
```

**字段数量**: 12个

### 详情数据采集配置

点击详情按钮进入详情页面，提取详细信息：

```json
{
  "detail_button_selector": "a:has-text('详')",
  "click_method": "javascript",
  "click_delay_ms": 500,
  "detail_iframe_selector": "iframe.artDialog-iframe",
  "detail_fields": [
    {"name": "序号", "selector": "div:contains('序号') + div"},
    {"name": "产品名称", "selector": "div:contains('产品名称') + div"},
    {"name": "规格", "selector": "div:contains('规格') + div"},
    {"name": "型号", "selector": "div:contains('型号') + div"},
    {"name": "注册证号", "selector": "div:contains('注册证号') + div"},
    {"name": "原注册证号", "selector": "div:contains('原注册证号') + div"},
    {"name": "医保编码", "selector": "div:contains('医保编码') + div"},
    {"name": "完整医保编码", "selector": "div:contains('完整医保编码') + div"},
    {"name": "注册人企业", "selector": "div:contains('注册人企业') + div"},
    {"name": "生产企业", "selector": "div:contains('生产企业') + div"},
    {"name": "单件产品名称", "selector": "div:contains('单件产品名称') + div"}
  ]
}
```

**说明**:
- `detail_button_selector`: 详情按钮选择器
- `click_method`: 点击方法（click/javascript）
- `detail_iframe_selector`: 详情页面的iframe选择器
- `detail_fields`: 详情页面字段列表

**字段数量**: 11个

## 数据结构

### 导出数据格式

每条任务的采集结果采用以下结构：

```json
{
  "job_id": 49,
  "config_id": 44,
  "extracted_data": {
    "items": {
      "items": [
        {
          "list_data": {
            "序号": "1",
            "耗材名称": "气管支气管支架（覆膜）",
            "医用耗材代码": "C0101010011303807555",
            ...
          },
          "detail_data": {
            "序号": "1",
            "产品名称": "覆膜气管支架",
            "规格": "(直管凹口半年可取出型)CZTS-I-17-90",
            ...
          },
          "detail_status": "success"
        }
      ],
      "summary": {
        "total_items": 2,
        "detail_success": 2,
        "detail_failed": 0,
        "pages_crawled": 1,
        "detail_skipped": 0
      }
    }
  },
  "page_count": 1,
  "created_at": "2026-09-30T08:24:49"
}
```

### 关键字段说明

- **list_data**: 从列表页面提取的数据（12个字段）
- **detail_data**: 从详情页面提取的数据（11个字段）
- **detail_status**: 详情采集状态（success/failed）
- **summary**: 数据采集汇总统计

## 使用方法

### 创建采集任务

使用API创建一个新的采集任务：

```bash
curl -X POST http://127.0.0.1:8000/api/jobs \
  -H "Content-Type: application/json" \
  -d '{
    "config_id": 44,
    "query_params": {
      "registration_no": "滇械注准20192140008"
    }
  }'
```

**响应示例**:
```json
{
  "id": 50,
  "config_id": 44,
  "status": "pending",
  "query_params": {
    "registration_no": "滇械注准20192140008"
  },
  "created_at": "2026-09-30T16:35:00"
}
```

### 执行任务

触发任务执行：

```bash
curl -X POST http://127.0.0.1:8000/api/jobs/{JOB_ID}/execute
```

### 查询任务结果

获取任务执行结果：

```bash
curl http://127.0.0.1:8000/api/jobs/{JOB_ID}/result
```

### 监控任务进度

通过WebSocket监听实时任务进度：

```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/ws');
ws.onmessage = (event) => {
  const message = JSON.parse(event.data);
  console.log('Status:', message.type, message.data);
};
```

## 验证脚本

### 导出样本数据

```bash
python scripts/export_sample_data.py
```

导出Job 49的样本数据到 `docs/sample_data_job49.json`

### 验证数据结构

```bash
python scripts/validate_data_structure.py
```

验证导出数据的完整性和准确性

## 常见问题

### Q: 采集时提示找不到iframe
A: 网页的iframe结构可能动态变化。使用浏览器开发者工具检查当前的iframe选择器，更新配置中的 `iframe_config` 部分。

### Q: 详情页面采集失败
A: 
1. 检查详情按钮是否可见
2. 增加 `click_delay_ms` 等待页面加载
3. 验证详情iframe选择器是否正确

### Q: 采集数据为空
A:
1. 检查输入框选择器是否正确
2. 确保查询参数值有效（例如注册证号格式）
3. 查看执行日志了解具体错误信息

## 参考文档

- 采集配置模型: `app/models/config.py`
- 执行器实现: `app/services/executor.py`
- API端点: `app/api/jobs.py`
- 样本数据: `docs/sample_data_job49.json`
