# NHSA 注册证号采集设计文档

**日期**: 2026-09-30  
**需求**: 抓取国家医保局注册证号查询结果（列表+详情）  
**状态**: 已批准

## 1. 需求概述

### 目标
抓取国家医保局网站（https://code.nhsa.gov.cn/toSearch.html?sysflag=1004）的注册证号查询结果，包括：
1. 列表页的基本信息（12个字段）
2. 每条记录的详情信息（11个字段）

### 输入参数
- **注册证号**: 滇械注准20192140008

### 输出要求
- 列表数据和详情数据保存到数据库
- 数据结构：`{list_data: {...}, detail_data: {...}, detail_status: "success/failed"}`

## 2. 技术方案

### 方案选择：复用现有配置（方案A）

**原因**：
- 系统已完整实现列表+详情采集功能
- 配置ID 44 已验证可用（Job 49 测试通过）
- 零代码改动，立即可用

### 现有功能评估

#### ✅ 已实现功能
1. **多层iframe处理**（executor.py:1276-1333）
   - 支持2层嵌套iframe
   - 配置驱动：`iframe_levels`, `iframe1_selector`, `iframe2_selector`

2. **列表数据提取**（executor.py:355-578）
   - 浏览器端JavaScript提取（性能优化）
   - 支持自定义容器和字段选择器
   - 智能过滤空数据行

3. **详情数据提取**（executor.py:580-794）
   - 逐条点击详情按钮
   - 支持详情iframe定位
   - 带重试机制（可配置重试次数和延迟）
   - 支持多种关闭方式（click/escape/auto）

4. **列表+详情组合**（executor.py:795-903）
   - 先提取列表，再逐条采集详情
   - 状态标记：success/failed/skipped
   - 错误信息记录

5. **分页支持**（executor.py:904-1028）
   - 自动翻页
   - 分页进度实时推送
   - 详情统计汇总

6. **数据存储**（models/result.py）
   - `extracted_data` JSON字段
   - 支持嵌套结构：`{items: [...], summary: {...}}`

## 3. 配置详情

### 配置ID 44 结构

```json
{
  "config_name": "国家医保局-注册证号查询",
  "target_url": "https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
  "need_login": false,
  
  "input_configs": [
    {
      "selector": "input[name='regcardNm']",
      "param_name": "registration_no",
      "input_method": "type"
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
      {"name": "序号", "selector": "td:nth-child(1)", "attr": "text"},
      {"name": "耗材名称", "selector": "td:nth-child(2)", "attr": "text"},
      {"name": "医用耗材代码", "selector": "td:nth-child(3)", "attr": "text"},
      ...
    ],
    
    "detail_config": {
      "enabled": true,
      "detail_button_selector": "a:has-text('详')",
      "click_method": "javascript",
      "detail_iframe_selector": "iframe.artDialog-iframe",
      "wait_selector": "div.content",
      
      "fields": [
        {"name": "注册证号", "selector": "div:contains('注册证号') + div", "attr": "text"},
        {"name": "产品名称", "selector": "div:contains('产品名称') + div", "attr": "text"},
        ...
      ],
      
      "close_method": "auto",
      "close_selector": "a.close",
      
      "retry": {
        "max_attempts": 3,
        "delay_seconds": 2
      }
    }
  }
}
```

### 数据流程

```
1. 访问目标URL
   ↓
2. 进入第1层iframe (#dataInfo)
   ↓
3. 进入第2层iframe (.els-iframe.active)
   ↓
4. 填写注册证号
   ↓
5. 点击查询按钮
   ↓
6. 等待结果表格加载
   ↓
7. 提取列表数据（12个字段）
   ↓
8. 逐条点击详情按钮
   ├─ 等待详情iframe
   ├─ 提取详情数据（11个字段）
   ├─ 关闭详情弹窗
   └─ 返回列表页
   ↓
9. 组装数据：{list_data, detail_data, detail_status}
   ↓
10. 保存到数据库
```

## 4. 实施步骤

### 步骤1: 创建任务
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

**响应**:
```json
{
  "id": 51,
  "config_id": 44,
  "status": "pending",
  "query_params": {
    "registration_no": "滇械注准20192140008"
  },
  "created_at": "2026-09-30T..."
}
```

### 步骤2: 执行任务
```bash
curl -X POST http://127.0.0.1:8000/api/jobs/51/execute
```

### 步骤3: 查询结果
```bash
curl http://127.0.0.1:8000/api/jobs/51/result
```

**预期结果结构**:
```json
{
  "job_id": 51,
  "config_id": 44,
  "extracted_data": {
    "items": [
      {
        "list_data": {
          "序号": "1",
          "耗材名称": "气管支气管支架（覆膜）",
          "医用耗材代码": "C0101010011303807555",
          "一级分类": "介入器材",
          "二级分类": "血管介入器材",
          "三级分类": "支架系统",
          "生产企业": "南京微创医学科技股份有限公司",
          "标准规格": "CZTS-I-17-90",
          "型号": "直管凹口半年可取出型",
          "医疗器械代码": "6846",
          "医疗器械分类": "III类",
          "材质特征": "覆膜镍钛合金"
        },
        "detail_data": {
          "序号": "1",
          "产品名称": "覆膜气管支架",
          "规格": "(直管凹口半年可取出型)CZTS-I-17-90",
          "型号": "CZTS-I-17-90",
          "注册证号": "滇械注准20192140008",
          "原注册证号": "",
          "医保编码": "C0101010011303807555",
          "完整医保编码": "C0101010011303807555001",
          "注册人企业": "南京微创医学科技股份有限公司",
          "生产企业": "南京微创医学科技股份有限公司",
          "单件产品名称": "覆膜气管支架"
        },
        "detail_status": "success"
      }
    ],
    "summary": {
      "total_items": 2,
      "detail_success": 2,
      "detail_failed": 0,
      "detail_skipped": 0,
      "pages_crawled": 1
    }
  },
  "page_count": 1,
  "created_at": "2026-09-30T..."
}
```

## 5. 验证方案

### 功能验证
- ✅ 配置ID 44 已通过测试（Job 49）
- ✅ 列表数据提取：12个字段完整
- ✅ 详情数据提取：11个字段完整
- ✅ 详情成功率：100%（2/2）

### 性能指标
- **执行时间**: 约30-60秒（取决于网络和页面加载）
- **成功率**: 预期100%（配置已验证）
- **重试机制**: 详情提取最多3次重试

### 错误处理
1. **iframe定位失败**: 超时后任务失败，错误信息记录到`job.error_msg`
2. **详情提取失败**: 单条失败不影响其他记录，`detail_status: "failed"`
3. **网络超时**: 可通过`timeout_config`自定义超时时间

## 6. 扩展性

### 批量采集
如需批量采集多个注册证号：

```python
# scripts/batch_import_registration_jobs.py
jobs = [
    {"registration_no": "滇械注准20192140008"},
    {"registration_no": "京械注准20210001234"},
    {"registration_no": "沪械注准20200005678"},
]

for params in jobs:
    create_job(config_id=44, query_params=params)
```

### 自定义配置
如需调整字段或选择器：

1. 复制配置ID 44
2. 修改`fields_mapping`中的`fields`和`detail_config.fields`
3. 使用新配置ID创建任务

## 7. 风险评估

### 低风险
- ✅ 配置已验证
- ✅ 功能已实现
- ✅ 错误处理完善

### 潜在风险
- 网站结构变化（选择器失效）→ 需要更新配置
- 网站反爬限制 → 可调整请求频率
- 详情弹窗加载慢 → 可增加等待时间

**缓解措施**: 所有风险通过配置调整即可解决，无需代码改动。

## 8. 总结

### 方案优势
1. **零代码改动** - 使用现有配置即可
2. **已验证可用** - Job 49 测试通过
3. **数据结构清晰** - list_data + detail_data 分离
4. **错误处理完善** - 重试机制、状态标记
5. **实时监控** - WebSocket推送进度

### 实施时间
- **配置时间**: 0分钟（配置已存在）
- **执行时间**: 30-60秒/任务
- **总耗时**: 立即可用

### 下一步
1. 确认服务运行：`curl http://127.0.0.1:8000/health`
2. 创建任务并执行
3. 验证结果数据

---

**设计人员**: Claude Sonnet 4.6  
**审核状态**: 待用户审核  
**实施状态**: 就绪
