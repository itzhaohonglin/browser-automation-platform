# 详情采集功能设计文档

## 1. 概述

### 1.1 背景
当前系统支持配置驱动的列表数据采集，但无法处理需要"点击详情"才能获取完整数据的场景。例如国家医保局网站（https://code.nhsa.gov.cn/toSearch.html?sysflag=1004）的查询结果，列表只显示基本信息，需要点击"详情"按钮进入详情页才能获取完整数据。

### 1.2 目标
扩展现有 `PlaywrightExecutor` 执行器，增加详情采集能力，实现：
- 配置驱动的详情采集（通过 `detail_config` 配置启用）
- 列表数据与详情数据的主子关系嵌套存储
- 支持详情在iframe中加载的场景
- 详情采集失败时的重试与降级机制
- 向后兼容现有配置（不配置详情则按原流程执行）

### 1.3 适用场景
- 医保局、政府网站等需要逐条点击查看详情的数据采集
- 电商平台商品列表+详情页采集
- 招投标网站公告列表+详情采集
- 任何"列表摘要+详情全文"的数据结构

## 2. 系统架构

### 2.1 整体架构
保持现有的配置驱动架构不变：
```
CrawlerConfig → JobQueue → PlaywrightExecutor → CrawlerResult
```

### 2.2 数据流增强

**原有流程**：
```
访问页面 → 填表 → 提交 → 等待列表 → 提取列表数据 → 翻页 → 保存
```

**新流程**（启用详情采集时）：
```
访问页面 → 填表 → 提交 → 等待列表 →
  遍历每一行：
    ├─ 提取列表字段
    ├─ 点击详情按钮
    ├─ 等待并切换到详情iframe
    ├─ 提取详情字段
    ├─ 关闭详情/返回列表
    └─ 合并数据 (list_data + detail_data)
→ 翻页 → 重复上述流程 → 保存
```

### 2.3 关键设计原则
1. **向后兼容**：`detail_config` 为可选配置，不影响现有功能
2. **职责分离**：详情采集逻辑封装为独立方法
3. **容错性**：单条详情失败不影响其他数据采集
4. **可观测性**：每个详情采集动作通过WebSocket推送进度

## 3. 配置结构设计

### 3.1 CrawlerConfig 表字段
无需修改数据库表结构，所有配置存储在现有的 `fields_mapping` JSON字段中。

### 3.2 fields_mapping 完整结构

```json
{
  "iframe_levels": 2,
  "iframe1_selector": "iframe#mainFrame",
  "iframe2_selector": "iframe#contentFrame",
  
  "list_selector": "#gridlist tbody tr",
  "fields": [
    {"name": "产品名称", "selector": "td:nth-child(1)", "attr": "text"},
    {"name": "注册证号", "selector": "td:nth-child(2)", "attr": "text"},
    {"name": "企业名称", "selector": "td:nth-child(3)", "attr": "text"}
  ],
  
  "detail_config": {
    "enabled": true,
    "detail_button_selector": "td:nth-child(4) a[title='详情']",
    "detail_iframe_selector": "iframe#detailFrame",
    "wait_selector": ".detail-content",
    "close_selector": ".close-btn",
    "close_method": "click",
    "fields": [
      {"name": "详细规格", "selector": "#spec", "attr": "text"},
      {"name": "生产地址", "selector": "#address", "attr": "text"},
      {"name": "注册证编号", "selector": "#cert_no", "attr": "text"},
      {"name": "备注", "selector": "#remark", "attr": "text"}
    ],
    "retry": {
      "max_attempts": 3,
      "delay_seconds": 2
    },
    "timeout": {
      "iframe_load": 10000,
      "wait_selector": 5000
    }
  }
}
```

### 3.3 detail_config 字段说明

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| enabled | boolean | 是 | 是否启用详情采集 |
| detail_button_selector | string | 是 | 详情按钮选择器（相对于列表行） |
| detail_iframe_selector | string | 否 | 详情iframe选择器（如果详情在iframe中） |
| wait_selector | string | 是 | 等待详情内容加载的选择器 |
| close_selector | string | 否 | 关闭详情的按钮选择器 |
| close_method | string | 否 | 关闭方式：click/escape/auto，默认auto |
| fields | array | 是 | 详情页字段提取规则 |
| retry.max_attempts | int | 否 | 单条详情最大重试次数，默认3 |
| retry.delay_seconds | int | 否 | 重试间隔秒数，默认2 |
| timeout.iframe_load | int | 否 | iframe加载超时（毫秒），默认10000 |
| timeout.wait_selector | int | 否 | 等待选择器超时（毫秒），默认5000 |

### 3.4 医保局网站配置示例

```json
{
  "config_name": "医保局医疗器械编码查询",
  "target_url": "https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
  "need_login": false,
  "input_configs": {
    "inputs": [
      {
        "selector": "#regcardNm",
        "param_key": "register_no",
        "input_type": "text"
      }
    ]
  },
  "submit_selector": "#search",
  "wait_selector": "#gridlist tbody tr",
  "pagination_selector": "#next_gridpage",
  "max_pages": 5,
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
      "enabled": true,
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
      }
    }
  }
}
```

对应的查询参数：
```json
{
  "register_no": "川械注准20182170152"
}
```

## 4. 数据存储格式

### 4.1 CrawlerResult.extracted_data 结构

**启用详情采集时的格式**：
```json
{
  "items": [
    {
      "list_data": {
        "序号": "1",
        "医疗器械编码": "C123456",
        "医疗器械名称": "一次性使用无菌注射器",
        "注册证号": "川械注准20182170152"
      },
      "detail_data": {
        "产品名称": "一次性使用无菌注射器",
        "型号规格": "2ml/5ml/10ml",
        "注册人名称": "某某医疗器械有限公司",
        "注册人住所": "四川省成都市XX区XX路XX号",
        "生产地址": "四川省成都市高新区XX路XX号"
      },
      "detail_status": "success"
    },
    {
      "list_data": {
        "序号": "2",
        "医疗器械编码": "C234567",
        "医疗器械名称": "医用口罩",
        "注册证号": "川械注准20192170234"
      },
      "detail_data": {},
      "detail_status": "failed",
      "detail_error": "iframe加载超时，已重试3次"
    }
  ],
  "summary": {
    "total_items": 2,
    "detail_success": 1,
    "detail_failed": 1,
    "pages_crawled": 1
  }
}
```

**字段说明**：
- `list_data`: 列表页提取的字段
- `detail_data`: 详情页提取的字段
- `detail_status`: 详情采集状态
  - `success`: 成功
  - `failed`: 失败（已重试max_attempts次）
  - `skipped`: 跳过（详情按钮不存在等）
- `detail_error`: 失败时的错误信息
- `summary`: 统计信息

### 4.2 向后兼容

当 `detail_config.enabled = false` 或不配置时，保持原格式：
```json
{
  "items": [
    {
      "序号": "1",
      "医疗器械编码": "C123456",
      "医疗器械名称": "一次性使用无菌注射器",
      "注册证号": "川械注准20182170152"
    }
  ]
}
```

## 5. 执行器实现设计

### 5.1 新增方法

#### 5.1.1 `_extract_detail_data()` - 单条详情提取

```python
async def _extract_detail_data(
    self,
    main_page: Union[Page, Frame],
    detail_button: Locator,
    detail_config: Dict,
    row_index: int
) -> Tuple[Dict, str, Optional[str]]:
    """
    提取单条数据的详情
    
    Args:
        main_page: 列表页面/Frame
        detail_button: 详情按钮定位器
        detail_config: 详情配置
        row_index: 当前行索引（用于日志）
    
    Returns:
        (detail_data, status, error_msg)
    """
```

**执行流程**：
1. 点击详情按钮
2. 等待详情iframe出现（如果配置了 `detail_iframe_selector`）
3. 切换到详情iframe（或使用main_page）
4. 等待详情内容加载（`wait_selector`）
5. 提取详情字段（复用 `_extract_page_data` 的字段提取逻辑）
6. 关闭详情：
   - 如果配置了 `close_selector`，点击关闭按钮
   - 如果 `close_method = "escape"`，按ESC键
   - 如果 `close_method = "auto"`，尝试点击关闭按钮，失败则按ESC
7. 等待返回列表页（等待列表选择器重新可见）
8. 返回 `(detail_data, "success", None)`

#### 5.1.2 `_extract_detail_with_retry()` - 带重试的详情提取

```python
async def _extract_detail_with_retry(
    self,
    main_page: Union[Page, Frame],
    detail_button: Locator,
    detail_config: Dict,
    row_index: int
) -> Tuple[Dict, str, Optional[str]]:
    """
    带重试机制的详情提取
    """
    max_attempts = detail_config.get('retry', {}).get('max_attempts', 3)
    delay = detail_config.get('retry', {}).get('delay_seconds', 2)
    
    for attempt in range(max_attempts):
        try:
            return await self._extract_detail_data(
                main_page, detail_button, detail_config, row_index
            )
        except Exception as e:
            self.logger.warning(
                f"第 {row_index} 条详情提取失败（尝试 {attempt + 1}/{max_attempts}）: {e}"
            )
            if attempt < max_attempts - 1:
                await asyncio.sleep(delay)
                continue
            else:
                return {}, "failed", f"{str(e)}，已重试{max_attempts}次"
    
    return {}, "failed", "未知错误"
```

#### 5.1.3 `_extract_list_with_details()` - 列表+详情联合提取

```python
async def _extract_list_with_details(
    self,
    page: Union[Page, Frame],
    fields_mapping: Dict,
    detail_config: Dict,
    job_id: int
) -> List[Dict]:
    """
    提取列表数据并逐条采集详情（单页）
    
    Returns:
        [
            {
                "list_data": {...},
                "detail_data": {...},
                "detail_status": "success/failed/skipped",
                "detail_error": "..." (可选)
            }
        ]
    """
```

**执行流程**：
1. 先提取当前页所有列表数据（调用现有 `_extract_page_data()`）
2. 获取所有列表行的定位器（`page.locator(list_selector)`）
3. 遍历每一行（索引 `i`）：
   - 重新定位该行（避免DOM变化导致引用失效）
   - 在该行内定位详情按钮（`row.locator(detail_button_selector)`）
   - 检查详情按钮是否存在：
     - 不存在：标记 `detail_status = "skipped"`
     - 存在：调用 `_extract_detail_with_retry()` 提取详情
   - 合并数据：`{"list_data": list_data[i], "detail_data": detail_data, "detail_status": status}`
   - 推送进度：`f"正在提取第 {i+1}/{total} 条详情"`
4. 返回完整数据列表

#### 5.1.4 `_extract_list_with_details_paginated()` - 分页+详情

```python
async def _extract_list_with_details_paginated(
    self,
    page: Union[Page, Frame],
    config: CrawlerConfig,
    job_id: int
) -> Tuple[List[Dict], int, Dict]:
    """
    分页提取列表+详情数据
    
    Returns:
        (all_items, page_count, summary)
    """
```

**执行流程**：
1. 初始化统计：`detail_success = 0, detail_failed = 0`
2. 循环翻页（复用现有分页逻辑）：
   - 调用 `_extract_list_with_details()` 提取当前页数据
   - 统计成功/失败数量
   - 推送分页进度
   - 点击下一页
3. 返回 `(all_items, page_count, {"total_items": N, "detail_success": X, "detail_failed": Y})`

### 5.2 修改 `execute_job()` 主流程

在第9步"数据提取"部分增加分支判断：

```python
# 9. 数据提取
detail_enabled = config.fields_mapping.get('detail_config', {}).get('enabled', False)

if detail_enabled:
    self.logger.info("使用详情采集模式")
    all_items, page_count, summary = await self._extract_list_with_details_paginated(
        target_frame, 
        config, 
        job_id
    )
    extracted_data = {
        "items": all_items,
        "summary": summary
    }
else:
    self.logger.info("使用标准列表采集模式")
    # 使用原有逻辑
    if config.pagination_selector and config.max_pages > 1:
        page_results, page_count = await self._extract_with_pagination(...)
    else:
        page_data = await self._extract_with_retry(...)
        page_results = page_data
        page_count = 1
    
    extracted_data = {"items": page_results}
```

## 6. 错误处理与重试策略

### 6.1 三层重试保障

| 层级 | 范围 | 机制 | 配置位置 |
|------|------|------|---------|
| 第一层 | 单条详情 | `_extract_detail_with_retry()` | `detail_config.retry` |
| 第二层 | 列表页 | `_extract_with_retry()` | `extraction_config.retry` |
| 第三层 | 整个任务 | 调度器自动补跑 | 系统全局（retry_count < 3） |

### 6.2 错误分类与处理

| 错误类型 | 处理策略 | 影响范围 | detail_status |
|---------|---------|---------|---------------|
| 详情按钮不存在 | 跳过，记录 `detail_status: "skipped"` | 单条 | skipped |
| 详情iframe加载超时 | 重试N次，失败后跳过 | 单条 | failed |
| 详情字段提取为空 | 返回空对象 `{}` | 单条 | success |
| 详情字段提取异常 | 重试N次，失败后返回空 | 单条 | failed |
| 关闭详情失败 | 尝试ESC键，失败则刷新页面重新进入列表 | 当前页 | N/A |
| 列表提取失败 | 按现有机制重试，失败则任务失败 | 整个任务 | N/A |
| 浏览器崩溃 | 任务失败，等待调度器补跑 | 整个任务 | N/A |

### 6.3 超时配置

| 操作 | 默认超时 | 配置位置 |
|------|---------|---------|
| 点击详情按钮 | 10000ms | `timeout_config.click` |
| 等待详情iframe | 10000ms | `detail_config.timeout.iframe_load` |
| 等待详情内容加载 | 5000ms | `detail_config.timeout.wait_selector` |
| 关闭详情 | 5000ms | `timeout_config.click` |

### 6.4 WebSocket进度推送

**新增事件类型**：

```json
{
  "type": "progress",
  "data": {
    "job_id": 123,
    "status": "processing",
    "current_page": 2,
    "total_pages": 5,
    "detail_progress": {
      "current": 3,
      "total": 10,
      "success": 2,
      "failed": 0
    }
  }
}
```

**日志示例**：
- `"[详情] 开始提取第 1 页详情数据（共 10 条）"`
- `"[详情] 第 3/10 条详情提取成功"`
- `"[详情] 第 5/10 条详情提取失败（尝试 2/3）: iframe加载超时"`
- `"[详情] 第 1 页详情采集完成：成功 8 条，失败 2 条"`
- `"[详情] 全部采集完成：共 50 条，成功 45 条，失败 5 条"`

## 7. 初始化配置数据

### 7.1 数据库插入SQL

```sql
INSERT INTO crawler_configs (
    config_name,
    target_url,
    need_login,
    auth_profile,
    input_configs,
    submit_selector,
    wait_selector,
    pagination_selector,
    max_pages,
    fields_mapping,
    is_active,
    priority
) VALUES (
    '医保局医疗器械编码查询',
    'https://code.nhsa.gov.cn/toSearch.html?sysflag=1004',
    false,
    NULL,
    '{"inputs": [{"selector": "#regcardNm", "param_key": "register_no", "input_type": "text"}]}',
    '#search',
    '#gridlist tbody tr',
    '#next_gridpage',
    5,
    '{
        "iframe_levels": 2,
        "iframe1_selector": "iframe[name=''mainFrame'']",
        "iframe2_selector": "iframe[name=''contentFrame'']",
        "list_selector": "#gridlist tbody tr",
        "fields": [
            {"name": "序号", "selector": "td:nth-child(1)", "attr": "text"},
            {"name": "医疗器械编码", "selector": "td:nth-child(2)", "attr": "text"},
            {"name": "医疗器械名称", "selector": "td:nth-child(3)", "attr": "text"},
            {"name": "注册证号", "selector": "td:nth-child(4)", "attr": "text"}
        ],
        "detail_config": {
            "enabled": true,
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
                "wait_selector": 5000
            }
        }
    }',
    true,
    5
);
```

### 7.2 创建测试任务

```sql
INSERT INTO job_queue (
    config_id,
    query_params,
    status,
    priority
) VALUES (
    (SELECT id FROM crawler_configs WHERE config_name = '医保局医疗器械编码查询'),
    '{"register_no": "川械注准20182170152"}',
    'pending',
    5
);
```

### 7.3 Python脚本方式

```python
# scripts/init_nhsa_config.py
import asyncio
from sqlalchemy import select
from app.core.database import get_session
from app.models.config import CrawlerConfig
from app.models.job import JobQueue

async def init_nhsa_config():
    async with get_session() as session:
        # 创建配置
        config = CrawlerConfig(
            config_name="医保局医疗器械编码查询",
            target_url="https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
            need_login=False,
            input_configs={
                "inputs": [
                    {
                        "selector": "#regcardNm",
                        "param_key": "register_no",
                        "input_type": "text"
                    }
                ]
            },
            submit_selector="#search",
            wait_selector="#gridlist tbody tr",
            pagination_selector="#next_gridpage",
            max_pages=5,
            fields_mapping={
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
                        "wait_selector": 5000
                    }
                }
            },
            is_active=True,
            priority=5
        )
        
        session.add(config)
        await session.commit()
        await session.refresh(config)
        
        print(f"配置已创建，ID: {config.id}")
        
        # 创建测试任务
        job = JobQueue(
            config_id=config.id,
            query_params={"register_no": "川械注准20182170152"},
            priority=5
        )
        
        session.add(job)
        await session.commit()
        await session.refresh(job)
        
        print(f"测试任务已创建，ID: {job.id}")
        print(f"可通过以下命令执行测试：")
        print(f"  curl -X POST http://localhost:8000/api/jobs/{job.id}/execute")

if __name__ == "__main__":
    asyncio.run(init_nhsa_config())
```

## 8. 测试计划

### 8.1 单元测试

#### 测试用例1：详情提取成功
```python
async def test_extract_detail_success():
    """测试正常的详情提取流程"""
    # 模拟点击详情按钮 → iframe加载 → 字段提取 → 关闭
    pass
```

#### 测试用例2：详情提取重试
```python
async def test_extract_detail_retry():
    """测试详情提取失败后的重试机制"""
    # 第1次失败 → 重试 → 第2次成功
    pass
```

#### 测试用例3：详情按钮不存在
```python
async def test_detail_button_not_found():
    """测试详情按钮不存在时的跳过逻辑"""
    # detail_status = "skipped"
    pass
```

#### 测试用例4：分页+详情
```python
async def test_pagination_with_details():
    """测试分页场景下的详情采集"""
    # 第1页10条 → 详情 → 翻页 → 第2页10条 → 详情
    pass
```

### 8.2 集成测试

#### 测试用例5：医保局网站真实场景
```python
async def test_nhsa_real_scenario():
    """
    真实环境测试：
    1. 访问医保局网站
    2. 填入注册证号
    3. 提交查询
    4. 提取列表+详情
    5. 验证数据结构
    """
    pass
```

### 8.3 性能测试

#### 测试用例6：100条数据的详情采集耗时
```python
async def test_performance_100_items():
    """
    性能基准测试：
    - 100条列表数据
    - 每条详情平均耗时 2秒
    - 总耗时应在 220秒内（含分页、重试）
    """
    pass
```

### 8.4 手动测试检查清单

- [ ] 详情iframe正确识别并切换
- [ ] 详情字段提取准确
- [ ] 详情关闭后能正常返回列表
- [ ] 翻页后继续采集详情
- [ ] 单条详情失败不影响其他数据
- [ ] WebSocket进度推送正常
- [ ] 最终数据格式符合设计
- [ ] 向后兼容（不配置detail_config时正常工作）

## 9. 实施步骤

### 9.1 Phase 1：核心功能实现（2-3天）
1. 实现 `_extract_detail_data()` 方法
2. 实现 `_extract_detail_with_retry()` 方法
3. 实现 `_extract_list_with_details()` 方法
4. 修改 `execute_job()` 增加分支判断
5. 单元测试（Mock测试）

### 9.2 Phase 2：分页与集成（1-2天）
1. 实现 `_extract_list_with_details_paginated()` 方法
2. 集成WebSocket进度推送
3. 集成测试（使用测试网站）

### 9.3 Phase 3：真实场景调试（1-2天）
1. 初始化医保局网站配置
2. 真实环境测试
3. 根据实际页面结构调整选择器
4. 调优超时和重试参数

### 9.4 Phase 4：文档与上线（1天）
1. 更新API文档
2. 编写使用说明
3. 性能测试
4. 上线部署

**总计预估时间：5-8天**

## 10. 风险与挑战

### 10.1 技术风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 详情iframe识别失败 | 无法提取详情 | 增加多种识别策略（name/id/src），支持手动指定 |
| 详情关闭后DOM变化 | 列表定位器失效 | 每次操作前重新定位元素 |
| 详情加载时间不确定 | 提取到空数据 | 增加动态等待机制（wait_for_function） |
| 单条详情耗时过长 | 整体任务超时 | 设置单条详情超时上限（30秒），超时则跳过 |

### 10.2 业务风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 医保局网站反爬 | 数据采集失败 | 降低请求频率，模拟人工操作节奏 |
| 页面结构变化 | 选择器失效 | 配置化设计便于快速调整 |
| 详情页数据格式不统一 | 提取逻辑复杂 | 支持条件提取和默认值配置 |

### 10.3 性能风险

| 风险 | 影响 | 缓解措施 |
|------|------|---------|
| 详情逐条采集速度慢 | 用户体验差 | 优化等待时间，增加进度提示 |
| 100条数据耗时过长 | 任务堆积 | 限制单次任务最大数据量，支持分批执行 |
| 浏览器内存泄漏 | 长时间运行崩溃 | 定期关闭并重启浏览器 |

## 11. 后续优化方向

### 11.1 短期优化（1-2个月）
1. **并行详情采集**：支持多标签页同时采集详情（配置项：`parallel_details: true`）
2. **详情缓存**：已采集过的详情数据缓存到Redis，避免重复采集
3. **智能等待**：根据网络速度动态调整等待时间
4. **详情预加载**：鼠标hover时预加载详情iframe

### 11.2 中期优化（3-6个月）
1. **多级详情**：支持"列表 → 详情1 → 详情2"的递归结构
2. **条件详情**：根据列表字段值决定是否采集详情（如：只采集"已审批"状态的详情）
3. **详情字段映射**：支持详情字段与列表字段的合并规则配置
4. **智能选择器**：基于AI自动识别详情按钮和字段

### 11.3 长期优化（6个月+）
1. **可视化配置器**：通过Chrome插件点选生成配置
2. **自适应采集**：自动检测页面结构变化并调整选择器
3. **分布式详情采集**：多机并行采集详情
4. **详情数据关联分析**：基于详情数据的智能分析和推荐

## 12. 附录

### 12.1 相关文档
- `docs/executor_usage.md` - 执行器使用说明
- `docs/database_usage.md` - 数据库操作指南
- `docs/websocket_usage.md` - WebSocket集成说明
- `CLAUDE.md` - 项目开发指南

### 12.2 参考资料
- Playwright iframe处理：https://playwright.dev/docs/frames
- jqGrid表格结构分析：http://www.trirand.com/jqgridwiki/
- 医保局网站：https://code.nhsa.gov.cn/toSearch.html?sysflag=1004

### 12.3 配置模板
详见 `scripts/config_templates/detail_crawler_template.json`

---

**文档版本**：v1.0  
**创建日期**：2026-09-29  
**最后更新**：2026-09-29  
**作者**：Claude (Sonnet 4.6)  
**审核状态**：待审核
