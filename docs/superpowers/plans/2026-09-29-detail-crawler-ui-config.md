# 详情采集配置界面实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为浏览器自动化平台添加可视化配置界面，支持"列表+详情"两级数据采集，无需直接操作数据库

**Architecture:** 前端采用纯 HTML/CSS/JavaScript（无框架），通过 REST API 与后端交互；后端新增测试 API（POST /api/configs/{id}/test），创建临时任务执行测试采集并返回样本数据；执行器复用现有的详情采集逻辑（已实现80%）

**Tech Stack:** FastAPI, Playwright, SQLAlchemy, 原生 JavaScript, CSS Grid, Fetch API

---

## 文件结构规划

### 新增文件

**前端文件**：
- `static/config_manager.html` - 配置管理页面主结构（三步式表单）
- `static/config_manager.js` - 前端交互逻辑（表单收集、API调用、结果展示）
- `static/config_manager.css` - 样式文件（响应式布局、表单美化）

**后端文件**：
- `app/api/config_test.py` - 配置测试 API 路由（新增）
- `app/schemas/config_test.py` - 请求/响应模型（Pydantic schemas）

**脚本文件**：
- `scripts/init_nhsa_config.py` - 医保局网站配置初始化脚本

### 修改文件

- `app/main.py` - 注册新路由（config_test_router）
- `static/index.html` - 添加配置管理入口链接（可选）

---

## Task 1: 创建请求/响应模型

**Files:**
- Create: `app/schemas/config_test.py`

- [ ] **Step 1: 创建 Pydantic 模型文件**

```python
# app/schemas/config_test.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FieldMapping(BaseModel):
    """字段映射"""
    name: str = Field(..., description="字段名称")
    selector: str = Field(..., description="CSS 选择器")
    attr: str = Field(..., description="提取属性：text/href/src")


class DetailConfigTimeout(BaseModel):
    """详情超时配置"""
    click: int = Field(10000, description="点击超时（毫秒）")
    wait_selector: int = Field(5000, description="等待选择器超时（毫秒）")
    iframe_load: Optional[int] = Field(10000, description="iframe 加载超时（毫秒）")
    close: int = Field(5000, description="关闭超时（毫秒）")


class DetailConfigRetry(BaseModel):
    """详情重试配置"""
    max_attempts: int = Field(3, description="最大重试次数")
    delay_seconds: int = Field(2, description="重试延迟（秒）")


class DetailConfig(BaseModel):
    """详情采集配置"""
    enabled: bool = Field(False, description="是否启用详情采集")
    detail_button_selector: Optional[str] = Field(None, description="详情按钮选择器")
    wait_selector: Optional[str] = Field(None, description="详情等待选择器")
    detail_iframe_selector: Optional[str] = Field(None, description="详情iframe选择器")
    fields: List[FieldMapping] = Field(default_factory=list, description="详情字段列表")
    close_method: str = Field("auto", description="关闭方式：click/escape/auto")
    close_selector: Optional[str] = Field(None, description="关闭按钮选择器")
    timeout: DetailConfigTimeout = Field(default_factory=DetailConfigTimeout)
    retry: DetailConfigRetry = Field(default_factory=DetailConfigRetry)


class ConfigTestRequest(BaseModel):
    """配置测试请求"""
    fields_mapping: Dict[str, Any] = Field(..., description="字段映射配置")
    query_params: Dict[str, str] = Field(..., description="查询参数")


class SampleItem(BaseModel):
    """样本数据项"""
    list_data: Dict[str, str] = Field(..., description="列表数据")
    detail_data: Dict[str, str] = Field(default_factory=dict, description="详情数据")
    detail_status: str = Field(..., description="详情状态：success/failed/skipped")
    detail_error: Optional[str] = Field(None, description="详情错误信息")


class ConfigTestResponse(BaseModel):
    """配置测试响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="测试数据")
    error: Optional[str] = Field(None, description="错误信息")
    error_type: Optional[str] = Field(None, description="错误类型")
```

- [ ] **Step 2: 验证模型导入**

运行验证脚本：

```bash
python -c "from app.schemas.config_test import ConfigTestRequest, ConfigTestResponse; print('✓ 模型导入成功')"
```

Expected: `✓ 模型导入成功`

- [ ] **Step 3: Commit**

```bash
git add app/schemas/config_test.py
git commit -m "feat: add config test request/response schemas

新增 Pydantic 模型：
- ConfigTestRequest: 配置测试请求模型
- ConfigTestResponse: 配置测试响应模型
- DetailConfig: 详情采集配置模型
- FieldMapping: 字段映射模型

用于配置测试 API 的数据验证

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 2: 创建配置测试 API

**Files:**
- Create: `app/api/config_test.py`

- [ ] **Step 1: 创建配置测试 API 路由**

```python
# app/api/config_test.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_session
from app.models.config import CrawlerConfig
from app.models.job import JobQueue, JobStatus
from app.services.executor import PlaywrightExecutor
from app.schemas.config_test import ConfigTestRequest, ConfigTestResponse

router = APIRouter(prefix="/api/configs", tags=["配置测试"])


@router.post("/{config_id}/test", response_model=ConfigTestResponse)
async def test_config(
    config_id: int,
    test_request: ConfigTestRequest,
    session: AsyncSession = Depends(get_session)
):
    """
    测试配置是否有效
    
    功能：
    1. 使用临时配置创建任务
    2. 执行采集（限制第1页，最多3条）
    3. 返回样本数据
    4. 清理临时任务
    
    Args:
        config_id: 配置 ID
        test_request: 测试请求（包含 fields_mapping 和 query_params）
        session: 数据库 session
    
    Returns:
        ConfigTestResponse: 测试结果
    """
    
    # 1. 查询配置
    stmt = select(CrawlerConfig).where(CrawlerConfig.id == config_id)
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail=f"配置不存在：{config_id}")
    
    # 2. 保存原始配置
    original_fields_mapping = config.fields_mapping
    original_max_pages = config.max_pages
    
    # 3. 使用临时配置覆盖
    config.fields_mapping = test_request.fields_mapping
    config.max_pages = 1  # 只采集第1页
    
    # 4. 创建临时任务
    temp_job = JobQueue(
        config_id=config_id,
        query_params=test_request.query_params,
        status=JobStatus.PENDING
    )
    session.add(temp_job)
    await session.flush()
    
    # 5. 执行采集
    executor = PlaywrightExecutor()
    
    try:
        result_data = await executor.execute_job(temp_job.id, session)
        
        # 6. 恢复原始配置
        config.fields_mapping = original_fields_mapping
        config.max_pages = original_max_pages
        
        # 7. 提取样本数据（前3条）
        if result_data["status"] == "success":
            extracted_data = result_data.get("extracted_data", {})
            items = extracted_data.get("items", [])
            sample_items = items[:3]
            
            # 统计详情状态
            success_count = sum(
                1 for item in sample_items
                if item.get("detail_status") == "success"
            )
            failed_count = sum(
                1 for item in sample_items
                if item.get("detail_status") == "failed"
            )
            skipped_count = sum(
                1 for item in sample_items
                if item.get("detail_status") == "skipped"
            )
            
            return ConfigTestResponse(
                success=True,
                data={
                    "total_tested": len(sample_items),
                    "success_count": success_count,
                    "failed_count": failed_count,
                    "skipped_count": skipped_count,
                    "sample_items": sample_items
                }
            )
        else:
            # 执行失败
            error_msg = result_data.get("error", "未知错误")
            return ConfigTestResponse(
                success=False,
                error=error_msg,
                error_type="execution_error"
            )
            
    except Exception as e:
        # 恢复原始配置
        config.fields_mapping = original_fields_mapping
        config.max_pages = original_max_pages
        
        return ConfigTestResponse(
            success=False,
            error=str(e),
            error_type="exception"
        )
    finally:
        # 清理临时任务
        await session.delete(temp_job)
        await session.commit()
```

- [ ] **Step 2: 验证 API 导入**

```bash
python -c "from app.api.config_test import router; print('✓ API 路由导入成功')"
```

Expected: `✓ API 路由导入成功`

- [ ] **Step 3: Commit**

```bash
git add app/api/config_test.py
git commit -m "feat: add config test API endpoint

新增 API：
- POST /api/configs/{id}/test: 测试配置有效性

功能：
- 创建临时任务执行测试采集
- 限制采集第1页最多3条数据
- 返回样本数据和统计信息
- 自动清理临时任务

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 3: 注册配置测试 API 路由

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: 在 main.py 中导入路由**

在 `app/main.py` 的导入部分添加：

```python
from app.api.config_test import router as config_test_router
```

- [ ] **Step 2: 注册路由**

在路由注册部分（`app.include_router` 附近）添加：

```python
app.include_router(config_test_router)
```

- [ ] **Step 3: 验证服务启动**

```bash
python -c "from app.main import app; print('✓ 服务启动验证通过')"
```

Expected: `✓ 服务启动验证通过`

- [ ] **Step 4: Commit**

```bash
git add app/main.py
git commit -m "feat: register config test API router

在主应用中注册配置测试路由

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 4: 创建配置管理页面 HTML

**Files:**
- Create: `static/config_manager.html`

- [ ] **Step 1: 创建 HTML 页面结构（第1部分）**

```html
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>配置管理 - 浏览器自动化平台</title>
    <link rel="stylesheet" href="/static/config_manager.css">
</head>
<body>
    <div class="container">
        <header class="page-header">
            <a href="/static/index.html" class="back-btn">← 返回</a>
            <h1>配置管理</h1>
            <div class="config-id">配置 ID: <span id="config-id-display">-</span></div>
        </header>

        <main class="config-form">
            <!-- 第一步：列表字段配置 -->
            <section class="form-section">
                <h2>第一步：配置列表字段</h2>
                
                <div class="form-group">
                    <label for="list-selector">
                        列表容器选择器 <span class="required">*</span>
                        <span class="help-icon" title="用于定位每一行的 CSS 选择器，例如：table tbody tr">?</span>
                    </label>
                    <input type="text" 
                           id="list-selector" 
                           class="form-control" 
                           placeholder="table tbody tr"
                           required>
                    <div class="error-message" id="list-selector-error"></div>
                </div>

                <div class="form-group">
                    <label>列表字段</label>
                    <div id="list-fields-container" class="fields-container">
                        <!-- 动态生成字段行 -->
                    </div>
                    <button type="button" class="btn-secondary" id="add-list-field">+ 添加字段</button>
                </div>
            </section>

            <!-- 第二步：详情采集配置 -->
            <section class="form-section">
                <h2>第二步：配置详情采集（可选）</h2>
                
                <div class="form-group">
                    <label class="checkbox-label">
                        <input type="checkbox" id="enable-detail" class="checkbox">
                        <span>启用详情采集</span>
                    </label>
                </div>

                <div id="detail-config-panel" class="detail-panel" style="display: none;">
                    <div class="form-group">
                        <label for="detail-button-selector">
                            详情按钮选择器 <span class="required">*</span>
                            <span class="help-icon" title="详情按钮的 CSS 选择器（相对于列表行），例如：a.detail-btn">?</span>
                        </label>
                        <input type="text" 
                               id="detail-button-selector" 
                               class="form-control" 
                               placeholder="a.detail-btn">
                        <div class="error-message" id="detail-button-selector-error"></div>
                    </div>

                    <div class="form-group">
                        <label for="detail-wait-selector">
                            详情等待选择器 <span class="required">*</span>
                            <span class="help-icon" title="详情内容的 CSS 选择器，用于等待详情加载完成，例如：.modal-content">?</span>
                        </label>
                        <input type="text" 
                               id="detail-wait-selector" 
                               class="form-control" 
                               placeholder=".modal-content">
                        <div class="error-message" id="detail-wait-selector-error"></div>
                    </div>

                    <div class="form-group">
                        <label for="detail-iframe-selector">
                            详情 iframe 选择器（可选）
                            <span class="help-icon" title="如果详情在 iframe 中，填写 iframe 的选择器，例如：#detailIframe">?</span>
                        </label>
                        <input type="text" 
                               id="detail-iframe-selector" 
                               class="form-control" 
                               placeholder="#detailIframe">
                    </div>

                    <div class="form-group">
                        <label>详情字段</label>
                        <div id="detail-fields-container" class="fields-container">
                            <!-- 动态生成详情字段行 -->
                        </div>
                        <button type="button" class="btn-secondary" id="add-detail-field">+ 添加详情字段</button>
                    </div>

                    <!-- 高级配置 -->
                    <details class="advanced-config">
                        <summary>高级配置</summary>
                        
                        <div class="form-group">
                            <label>关闭方式</label>
                            <div class="radio-group">
                                <label class="radio-label">
                                    <input type="radio" name="close-method" value="click">
                                    <span>点击按钮</span>
                                </label>
                                <label class="radio-label">
                                    <input type="radio" name="close-method" value="escape">
                                    <span>按 ESC 键</span>
                                </label>
                                <label class="radio-label">
                                    <input type="radio" name="close-method" value="auto" checked>
                                    <span>自动选择（推荐）</span>
                                </label>
                            </div>
                        </div>

                        <div class="form-group" id="close-selector-group">
                            <label for="close-selector">
                                关闭按钮选择器
                                <span class="help-icon" title="关闭按钮的 CSS 选择器，例如：.close-btn">?</span>
                            </label>
                            <input type="text" 
                                   id="close-selector" 
                                   class="form-control" 
                                   placeholder=".close-btn">
                        </div>

                        <div class="form-row">
                            <div class="form-group">
                                <label for="max-attempts">最大重试次数</label>
                                <input type="number" 
                                       id="max-attempts" 
                                       class="form-control" 
                                       value="3" 
                                       min="1" 
                                       max="10">
                            </div>
                            <div class="form-group">
                                <label for="retry-delay">重试延迟（秒）</label>
                                <input type="number" 
                                       id="retry-delay" 
                                       class="form-control" 
                                       value="2" 
                                       min="1" 
                                       max="10">
                            </div>
                        </div>
                    </details>
                </div>
            </section>

            <!-- 第三步：测试与保存 -->
            <section class="form-section">
                <h2>第三步：测试与保存</h2>
                
                <div class="action-buttons">
                    <button type="button" class="btn-primary" id="test-config">测试配置</button>
                    <button type="button" class="btn-success" id="save-config">保存配置</button>
                </div>

                <div id="test-result-panel" class="test-result" style="display: none;">
                    <h3>测试结果</h3>
                    <div id="test-result-content"></div>
                </div>
            </section>
        </main>
    </div>

    <script src="/static/config_manager.js"></script>
</body>
</html>
```

- [ ] **Step 2: 验证 HTML 文件有效性**

```bash
python -c "from pathlib import Path; html = Path('static/config_manager.html').read_text(encoding='utf-8'); print('✓ HTML 文件创建成功，大小:', len(html), 'bytes')"
```

Expected: `✓ HTML 文件创建成功，大小: XXXX bytes`

- [ ] **Step 3: Commit**

```bash
git add static/config_manager.html
git commit -m "feat: add config manager HTML structure

新增配置管理页面：
- 第一步：列表字段配置
- 第二步：详情采集配置（可选）
- 第三步：测试与保存

包含表单验证提示和帮助说明

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 5: 创建配置管理页面样式

**Files:**
- Create: `static/config_manager.css`

- [ ] **Step 1: 创建 CSS 样式文件（第1部分 - 基础样式）**

```css
/* static/config_manager.css */

/* 全局样式 */
* {
    margin: 0;
    padding: 0;
    box-sizing: border-box;
}

body {
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
    font-size: 14px;
    line-height: 1.6;
    color: #333;
    background: #f5f5f5;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

/* 页面头部 */
.page-header {
    display: flex;
    align-items: center;
    gap: 20px;
    margin-bottom: 30px;
    padding: 20px;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.back-btn {
    padding: 8px 16px;
    background: #f0f0f0;
    color: #333;
    text-decoration: none;
    border-radius: 4px;
    transition: background 0.3s;
}

.back-btn:hover {
    background: #e0e0e0;
}

.page-header h1 {
    flex: 1;
    font-size: 24px;
    font-weight: 600;
}

.config-id {
    color: #666;
    font-size: 14px;
}

/* 表单区域 */
.config-form {
    display: flex;
    flex-direction: column;
    gap: 20px;
}

.form-section {
    background: #fff;
    padding: 30px;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.form-section h2 {
    font-size: 18px;
    font-weight: 600;
    margin-bottom: 20px;
    padding-bottom: 10px;
    border-bottom: 2px solid #e0e0e0;
}

/* 表单组 */
.form-group {
    margin-bottom: 20px;
}

.form-group label {
    display: block;
    margin-bottom: 8px;
    font-weight: 500;
    color: #333;
}

.required {
    color: #f44336;
}

.help-icon {
    display: inline-block;
    width: 18px;
    height: 18px;
    line-height: 18px;
    text-align: center;
    background: #2196f3;
    color: #fff;
    border-radius: 50%;
    font-size: 12px;
    cursor: help;
    margin-left: 4px;
}

.form-control {
    width: 100%;
    padding: 10px 12px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
    transition: border-color 0.3s;
}

.form-control:focus {
    outline: none;
    border-color: #2196f3;
}

.form-control.error {
    border-color: #f44336;
}

.error-message {
    color: #f44336;
    font-size: 12px;
    margin-top: 4px;
    display: none;
}

.error-message.show {
    display: block;
}

/* 复选框和单选框 */
.checkbox-label,
.radio-label {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    margin-right: 20px;
}

.checkbox,
input[type="radio"] {
    width: 18px;
    height: 18px;
    cursor: pointer;
}

.radio-group {
    display: flex;
    gap: 20px;
    flex-wrap: wrap;
}

/* 字段容器 */
.fields-container {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 15px;
}

.field-row {
    display: grid;
    grid-template-columns: 2fr 3fr 1fr auto;
    gap: 10px;
    align-items: start;
}

.field-row input,
.field-row select {
    padding: 8px 10px;
    border: 1px solid #ddd;
    border-radius: 4px;
    font-size: 14px;
}

.field-row select {
    cursor: pointer;
}

.btn-remove {
    padding: 8px 12px;
    background: #f44336;
    color: #fff;
    border: none;
    border-radius: 4px;
    cursor: pointer;
    font-size: 14px;
    transition: background 0.3s;
}

.btn-remove:hover {
    background: #d32f2f;
}

/* 详情面板 */
.detail-panel {
    margin-top: 20px;
    padding: 20px;
    background: #f9f9f9;
    border-radius: 4px;
    border: 1px solid #e0e0e0;
}

/* 高级配置 */
.advanced-config {
    margin-top: 20px;
    padding: 15px;
    background: #f5f5f5;
    border-radius: 4px;
}

.advanced-config summary {
    cursor: pointer;
    font-weight: 500;
    user-select: none;
}

.advanced-config[open] summary {
    margin-bottom: 15px;
}

/* 表单行 */
.form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 15px;
}

/* 按钮 */
.action-buttons {
    display: flex;
    gap: 15px;
    margin-bottom: 20px;
}

.btn-primary,
.btn-success,
.btn-secondary {
    padding: 12px 24px;
    border: none;
    border-radius: 4px;
    font-size: 14px;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.3s;
}

.btn-primary {
    background: #2196f3;
    color: #fff;
}

.btn-primary:hover {
    background: #1976d2;
}

.btn-primary:disabled {
    background: #bbb;
    cursor: not-allowed;
}

.btn-success {
    background: #4caf50;
    color: #fff;
}

.btn-success:hover {
    background: #43a047;
}

.btn-success:disabled {
    background: #bbb;
    cursor: not-allowed;
}

.btn-secondary {
    background: #f0f0f0;
    color: #333;
}

.btn-secondary:hover {
    background: #e0e0e0;
}

/* 测试结果 */
.test-result {
    margin-top: 20px;
    padding: 20px;
    background: #f9f9f9;
    border-radius: 4px;
    border: 1px solid #e0e0e0;
}

.test-result h3 {
    font-size: 16px;
    margin-bottom: 15px;
}

.test-status {
    padding: 10px 15px;
    border-radius: 4px;
    margin-bottom: 15px;
    font-weight: 500;
}

.test-status.success {
    background: #e8f5e9;
    color: #2e7d32;
    border: 1px solid #4caf50;
}

.test-status.error {
    background: #ffebee;
    color: #c62828;
    border: 1px solid #f44336;
}

.sample-data {
    margin-top: 15px;
}

.sample-item {
    padding: 15px;
    background: #fff;
    border: 1px solid #ddd;
    border-radius: 4px;
    margin-bottom: 10px;
}

.sample-item h4 {
    font-size: 14px;
    margin-bottom: 10px;
    color: #666;
}

.data-field {
    display: grid;
    grid-template-columns: 150px 1fr;
    gap: 10px;
    padding: 5px 0;
    border-bottom: 1px solid #f0f0f0;
}

.data-field:last-child {
    border-bottom: none;
}

.data-field-label {
    font-weight: 500;
    color: #666;
}

.data-field-value {
    color: #333;
    word-break: break-word;
}

/* 加载状态 */
.loading {
    display: inline-block;
    width: 16px;
    height: 16px;
    border: 2px solid #f3f3f3;
    border-top: 2px solid #2196f3;
    border-radius: 50%;
    animation: spin 1s linear infinite;
}

@keyframes spin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}

/* 响应式设计 */
@media (max-width: 768px) {
    .container {
        padding: 10px;
    }

    .field-row {
        grid-template-columns: 1fr;
    }

    .form-row {
        grid-template-columns: 1fr;
    }

    .action-buttons {
        flex-direction: column;
    }

    .btn-primary,
    .btn-success {
        width: 100%;
    }
}
```

- [ ] **Step 2: 验证 CSS 文件**

```bash
python -c "from pathlib import Path; css = Path('static/config_manager.css').read_text(encoding='utf-8'); print('✓ CSS 文件创建成功，大小:', len(css), 'bytes')"
```

Expected: `✓ CSS 文件创建成功，大小: XXXX bytes`

- [ ] **Step 3: Commit**

```bash
git add static/config_manager.css
git commit -m "feat: add config manager CSS styles

新增配置管理页面样式：
- 响应式布局（桌面/移动端）
- 表单美化和交互反馈
- 测试结果展示样式
- 加载状态动画

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 6: 创建配置管理 JavaScript（第1部分 - 表单管理）

**Files:**
- Create: `static/config_manager.js`

- [ ] **Step 1: 创建 JavaScript 文件框架**

```javascript
// static/config_manager.js

// 全局状态
const state = {
    configId: null,
    listFields: [],
    detailFields: []
};

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 从 URL 获取配置 ID
    const urlParams = new URLSearchParams(window.location.search);
    state.configId = urlParams.get('id');
    
    if (!state.configId) {
        alert('缺少配置 ID 参数');
        window.location.href = '/static/index.html';
        return;
    }
    
    document.getElementById('config-id-display').textContent = state.configId;
    
    // 初始化事件监听
    initEventListeners();
    
    // 加载配置数据
    loadConfig();
});

/**
 * 初始化事件监听器
 */
function initEventListeners() {
    // 列表字段：添加字段按钮
    document.getElementById('add-list-field').addEventListener('click', function() {
        addListField();
    });
    
    // 详情字段：添加字段按钮
    document.getElementById('add-detail-field').addEventListener('click', function() {
        addDetailField();
    });
    
    // 启用详情采集复选框
    document.getElementById('enable-detail').addEventListener('change', function(e) {
        const panel = document.getElementById('detail-config-panel');
        panel.style.display = e.target.checked ? 'block' : 'none';
    });
    
    // 关闭方式单选框
    const closeMethodRadios = document.querySelectorAll('input[name="close-method"]');
    closeMethodRadios.forEach(radio => {
        radio.addEventListener('change', function() {
            updateCloseSelectorVisibility();
        });
    });
    
    // 测试配置按钮
    document.getElementById('test-config').addEventListener('click', function() {
        testConfig();
    });
    
    // 保存配置按钮
    document.getElementById('save-config').addEventListener('click', function() {
        saveConfig();
    });
}

/**
 * 添加列表字段行
 */
function addListField(name = '', selector = '', attr = 'text') {
    const container = document.getElementById('list-fields-container');
    const row = createFieldRow(name, selector, attr, 'list');
    container.appendChild(row);
    state.listFields.push({ name, selector, attr });
}

/**
 * 添加详情字段行
 */
function addDetailField(name = '', selector = '', attr = 'text') {
    const container = document.getElementById('detail-fields-container');
    const row = createFieldRow(name, selector, attr, 'detail');
    container.appendChild(row);
    state.detailFields.push({ name, selector, attr });
}

/**
 * 创建字段行 DOM 元素
 */
function createFieldRow(name, selector, attr, type) {
    const row = document.createElement('div');
    row.className = 'field-row';
    
    row.innerHTML = `
        <input type="text" 
               class="field-name" 
               placeholder="字段名称" 
               value="${name}"
               data-type="${type}">
        <input type="text" 
               class="field-selector" 
               placeholder="CSS 选择器" 
               value="${selector}"
               data-type="${type}">
        <select class="field-attr" data-type="${type}">
            <option value="text" ${attr === 'text' ? 'selected' : ''}>text</option>
            <option value="href" ${attr === 'href' ? 'selected' : ''}>href</option>
            <option value="src" ${attr === 'src' ? 'selected' : ''}>src</option>
        </select>
        <button type="button" class="btn-remove" onclick="removeFieldRow(this, '${type}')">删除</button>
    `;
    
    return row;
}

/**
 * 删除字段行
 */
function removeFieldRow(button, type) {
    const row = button.parentElement;
    const index = Array.from(row.parentElement.children).indexOf(row);
    
    row.remove();
    
    if (type === 'list') {
        state.listFields.splice(index, 1);
    } else {
        state.detailFields.splice(index, 1);
    }
}

/**
 * 更新关闭选择器输入框的可见性
 */
function updateCloseSelectorVisibility() {
    const closeMethod = document.querySelector('input[name="close-method"]:checked').value;
    const closeSelectorGroup = document.getElementById('close-selector-group');
    
    // 只有选择 "click" 或 "auto" 时才显示关闭选择器输入框
    closeSelectorGroup.style.display = (closeMethod === 'click' || closeMethod === 'auto') ? 'block' : 'none';
}
```

- [ ] **Step 2: 验证 JavaScript 文件**

```bash
python -c "from pathlib import Path; js = Path('static/config_manager.js').read_text(encoding='utf-8'); print('✓ JavaScript 文件创建成功，大小:', len(js), 'bytes')"
```

Expected: `✓ JavaScript 文件创建成功，大小: XXXX bytes`

- [ ] **Step 3: Commit**

```bash
git add static/config_manager.js
git commit -m "feat: add config manager JavaScript (part 1 - form management)

新增前端交互逻辑（第1部分）：
- 表单初始化和事件监听
- 动态添加/删除字段行
- 表单状态管理

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 7: 创建配置管理 JavaScript（第2部分 - 数据加载与收集）

**Files:**
- Modify: `static/config_manager.js`

- [ ] **Step 1: 在 config_manager.js 中添加数据加载功能**

在文件末尾添加：

```javascript
/**
 * 加载配置数据
 */
async function loadConfig() {
    try {
        const response = await fetch(`/api/configs/${state.configId}`);
        
        if (!response.ok) {
            throw new Error(`加载配置失败: ${response.statusText}`);
        }
        
        const result = await response.json();
        const config = result.data;
        
        // 填充列表容器选择器
        document.getElementById('list-selector').value = config.fields_mapping?.list_selector || '';
        
        // 填充列表字段
        const listFields = config.fields_mapping?.fields || [];
        listFields.forEach(field => {
            addListField(field.name, field.selector, field.attr);
        });
        
        // 如果没有字段，添加一个空行
        if (listFields.length === 0) {
            addListField();
        }
        
        // 填充详情配置
        const detailConfig = config.fields_mapping?.detail_config;
        if (detailConfig && detailConfig.enabled) {
            document.getElementById('enable-detail').checked = true;
            document.getElementById('detail-config-panel').style.display = 'block';
            
            document.getElementById('detail-button-selector').value = detailConfig.detail_button_selector || '';
            document.getElementById('detail-wait-selector').value = detailConfig.wait_selector || '';
            document.getElementById('detail-iframe-selector').value = detailConfig.detail_iframe_selector || '';
            
            // 填充详情字段
            const detailFields = detailConfig.fields || [];
            detailFields.forEach(field => {
                addDetailField(field.name, field.selector, field.attr);
            });
            
            if (detailFields.length === 0) {
                addDetailField();
            }
            
            // 填充高级配置
            const closeMethod = detailConfig.close_method || 'auto';
            document.querySelector(`input[name="close-method"][value="${closeMethod}"]`).checked = true;
            document.getElementById('close-selector').value = detailConfig.close_selector || '';
            
            if (detailConfig.retry) {
                document.getElementById('max-attempts').value = detailConfig.retry.max_attempts || 3;
                document.getElementById('retry-delay').value = detailConfig.retry.delay_seconds || 2;
            }
            
            updateCloseSelectorVisibility();
        } else {
            // 默认添加一个空字段行
            addDetailField();
        }
        
    } catch (error) {
        console.error('加载配置失败:', error);
        alert(`加载配置失败: ${error.message}`);
    }
}

/**
 * 收集表单数据
 */
function collectFormData() {
    // 收集列表字段
    const listFields = [];
    const listFieldRows = document.querySelectorAll('#list-fields-container .field-row');
    
    listFieldRows.forEach(row => {
        const name = row.querySelector('.field-name').value.trim();
        const selector = row.querySelector('.field-selector').value.trim();
        const attr = row.querySelector('.field-attr').value;
        
        if (name && selector) {
            listFields.push({ name, selector, attr });
        }
    });
    
    // 收集详情字段
    const detailFields = [];
    const detailFieldRows = document.querySelectorAll('#detail-fields-container .field-row');
    
    detailFieldRows.forEach(row => {
        const name = row.querySelector('.field-name').value.trim();
        const selector = row.querySelector('.field-selector').value.trim();
        const attr = row.querySelector('.field-attr').value;
        
        if (name && selector) {
            detailFields.push({ name, selector, attr });
        }
    });
    
    // 构建配置对象
    const listSelector = document.getElementById('list-selector').value.trim();
    const enableDetail = document.getElementById('enable-detail').checked;
    
    const fieldsMapping = {
        list_selector: listSelector,
        fields: listFields
    };
    
    if (enableDetail) {
        const closeMethod = document.querySelector('input[name="close-method"]:checked').value;
        
        fieldsMapping.detail_config = {
            enabled: true,
            detail_button_selector: document.getElementById('detail-button-selector').value.trim(),
            wait_selector: document.getElementById('detail-wait-selector').value.trim(),
            detail_iframe_selector: document.getElementById('detail-iframe-selector').value.trim() || null,
            fields: detailFields,
            close_method: closeMethod,
            close_selector: document.getElementById('close-selector').value.trim() || null,
            timeout: {
                click: 10000,
                wait_selector: 5000,
                iframe_load: 10000,
                close: 5000
            },
            retry: {
                max_attempts: parseInt(document.getElementById('max-attempts').value) || 3,
                delay_seconds: parseInt(document.getElementById('retry-delay').value) || 2
            }
        };
    } else {
        fieldsMapping.detail_config = {
            enabled: false
        };
    }
    
    return fieldsMapping;
}

/**
 * 验证表单数据
 */
function validateFormData(fieldsMapping) {
    const errors = [];
    
    // 验证列表容器选择器
    if (!fieldsMapping.list_selector) {
        errors.push('列表容器选择器不能为空');
        showFieldError('list-selector', '请输入列表容器选择器');
    }
    
    // 验证列表字段
    if (fieldsMapping.fields.length === 0) {
        errors.push('至少需要配置一个列表字段');
    }
    
    // 验证详情配置
    if (fieldsMapping.detail_config && fieldsMapping.detail_config.enabled) {
        if (!fieldsMapping.detail_config.detail_button_selector) {
            errors.push('详情按钮选择器不能为空');
            showFieldError('detail-button-selector', '请输入详情按钮选择器');
        }
        
        if (!fieldsMapping.detail_config.wait_selector) {
            errors.push('详情等待选择器不能为空');
            showFieldError('detail-wait-selector', '请输入详情等待选择器');
        }
        
        if (fieldsMapping.detail_config.fields.length === 0) {
            errors.push('至少需要配置一个详情字段');
        }
    }
    
    return errors;
}

/**
 * 显示字段错误
 */
function showFieldError(fieldId, message) {
    const field = document.getElementById(fieldId);
    const errorElement = document.getElementById(`${fieldId}-error`);
    
    if (field) {
        field.classList.add('error');
    }
    
    if (errorElement) {
        errorElement.textContent = message;
        errorElement.classList.add('show');
    }
}

/**
 * 清除所有字段错误
 */
function clearFieldErrors() {
    document.querySelectorAll('.form-control.error').forEach(el => {
        el.classList.remove('error');
    });
    
    document.querySelectorAll('.error-message.show').forEach(el => {
        el.classList.remove('show');
        el.textContent = '';
    });
}
```

- [ ] **Step 2: 验证 JavaScript 更新**

```bash
python -c "from pathlib import Path; js = Path('static/config_manager.js').read_text(encoding='utf-8'); print('✓ JavaScript 更新成功，大小:', len(js), 'bytes')"
```

Expected: `✓ JavaScript 更新成功，大小: XXXX bytes`

- [ ] **Step 3: Commit**

```bash
git add static/config_manager.js
git commit -m "feat: add config manager JavaScript (part 2 - data loading & collection)

新增功能（第2部分）：
- loadConfig(): 从 API 加载配置数据
- collectFormData(): 收集表单数据
- validateFormData(): 验证表单数据
- 字段错误提示显示和清除

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 8: 创建配置管理 JavaScript（第3部分 - 测试与保存）

**Files:**
- Modify: `static/config_manager.js`

- [ ] **Step 1: 在 config_manager.js 中添加测试和保存功能**

在文件末尾添加：

```javascript
/**
 * 测试配置
 */
async function testConfig() {
    // 清除之前的错误
    clearFieldErrors();
    
    // 收集表单数据
    const fieldsMapping = collectFormData();
    
    // 验证表单数据
    const errors = validateFormData(fieldsMapping);
    if (errors.length > 0) {
        alert('表单验证失败:\n' + errors.join('\n'));
        return;
    }
    
    // 获取查询参数（从配置中获取第一个输入框的值）
    const queryParams = {};
    try {
        const configResponse = await fetch(`/api/configs/${state.configId}`);
        const configResult = await configResponse.json();
        const inputConfigs = configResult.data.input_configs?.inputs || [];
        
        if (inputConfigs.length > 0) {
            const firstInput = inputConfigs[0];
            const paramKey = firstInput.param_key || 'keyword';
            queryParams[paramKey] = prompt(`请输入测试用的 ${paramKey}:`, '滇械注准20192140008') || '';
        }
    } catch (error) {
        console.error('获取查询参数失败:', error);
    }
    
    // 禁用测试按钮
    const testButton = document.getElementById('test-config');
    testButton.disabled = true;
    testButton.innerHTML = '<span class="loading"></span> 测试中...';
    
    // 显示测试结果面板
    const resultPanel = document.getElementById('test-result-panel');
    const resultContent = document.getElementById('test-result-content');
    resultPanel.style.display = 'block';
    resultContent.innerHTML = '<p>正在执行测试采集，请稍候...</p>';
    
    try {
        const response = await fetch(`/api/configs/${state.configId}/test`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fields_mapping: fieldsMapping,
                query_params: queryParams
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            displayTestSuccess(result.data);
        } else {
            displayTestError(result.error, result.error_type);
        }
        
    } catch (error) {
        displayTestError(error.message, 'network_error');
    } finally {
        // 恢复测试按钮
        testButton.disabled = false;
        testButton.textContent = '测试配置';
    }
}

/**
 * 显示测试成功结果
 */
function displayTestSuccess(data) {
    const resultContent = document.getElementById('test-result-content');
    
    let html = `
        <div class="test-status success">
            ✓ 成功提取 ${data.total_tested} 条数据
            （详情成功 ${data.success_count} 条，失败 ${data.failed_count} 条，跳过 ${data.skipped_count} 条）
        </div>
    `;
    
    if (data.sample_items && data.sample_items.length > 0) {
        html += '<div class="sample-data">';
        
        data.sample_items.forEach((item, index) => {
            html += `
                <div class="sample-item">
                    <h4>样本数据（第 ${index + 1} 条）</h4>
                    
                    <div class="data-section">
                        <strong>列表数据：</strong>
                        ${renderDataFields(item.list_data)}
                    </div>
                    
                    <div class="data-section">
                        <strong>详情数据：</strong>
                        ${renderDataFields(item.detail_data)}
                        <div class="data-field">
                            <span class="data-field-label">详情状态:</span>
                            <span class="data-field-value">${item.detail_status}</span>
                        </div>
                        ${item.detail_error ? `
                            <div class="data-field">
                                <span class="data-field-label">错误信息:</span>
                                <span class="data-field-value" style="color: #f44336;">${item.detail_error}</span>
                            </div>
                        ` : ''}
                    </div>
                </div>
            `;
        });
        
        html += '</div>';
    }
    
    resultContent.innerHTML = html;
}

/**
 * 渲染数据字段
 */
function renderDataFields(data) {
    if (!data || Object.keys(data).length === 0) {
        return '<p style="color: #999;">无数据</p>';
    }
    
    let html = '';
    for (const [key, value] of Object.entries(data)) {
        html += `
            <div class="data-field">
                <span class="data-field-label">${key}:</span>
                <span class="data-field-value">${value}</span>
            </div>
        `;
    }
    return html;
}

/**
 * 显示测试错误
 */
function displayTestError(error, errorType) {
    const resultContent = document.getElementById('test-result-content');
    
    let errorMessage = error;
    let suggestion = '';
    
    switch (errorType) {
        case 'selector_not_found':
            suggestion = '建议：检查选择器是否正确，或使用浏览器开发者工具验证';
            break;
        case 'load_timeout':
            suggestion = '建议：增加等待时间，或检查网络连接';
            break;
        case 'execution_error':
            suggestion = '建议：检查配置是否完整，或查看服务器日志';
            break;
        default:
            suggestion = '建议：检查配置并重试';
    }
    
    resultContent.innerHTML = `
        <div class="test-status error">
            ✗ 测试失败
        </div>
        <p><strong>错误信息：</strong>${errorMessage}</p>
        <p><strong>${suggestion}</strong></p>
    `;
}

/**
 * 保存配置
 */
async function saveConfig() {
    // 清除之前的错误
    clearFieldErrors();
    
    // 收集表单数据
    const fieldsMapping = collectFormData();
    
    // 验证表单数据
    const errors = validateFormData(fieldsMapping);
    if (errors.length > 0) {
        alert('表单验证失败:\n' + errors.join('\n'));
        return;
    }
    
    // 确认保存
    if (!confirm('确定要保存配置吗？')) {
        return;
    }
    
    // 禁用保存按钮
    const saveButton = document.getElementById('save-config');
    saveButton.disabled = true;
    saveButton.textContent = '保存中...';
    
    try {
        const response = await fetch(`/api/configs/${state.configId}`, {
            method: 'PUT',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                fields_mapping: fieldsMapping
            })
        });
        
        if (!response.ok) {
            throw new Error(`保存失败: ${response.statusText}`);
        }
        
        alert('配置保存成功！');
        
        // 可选：返回配置列表页
        // window.location.href = '/static/index.html';
        
    } catch (error) {
        alert(`保存配置失败: ${error.message}`);
    } finally {
        // 恢复保存按钮
        saveButton.disabled = false;
        saveButton.textContent = '保存配置';
    }
}
```

- [ ] **Step 2: 验证 JavaScript 完整性**

```bash
python -c "from pathlib import Path; js = Path('static/config_manager.js').read_text(encoding='utf-8'); print('✓ JavaScript 完整，大小:', len(js), 'bytes')"
```

Expected: `✓ JavaScript 完整，大小: XXXX bytes`

- [ ] **Step 3: Commit**

```bash
git add static/config_manager.js
git commit -m "feat: add config manager JavaScript (part 3 - test & save)

新增功能（第3部分）：
- testConfig(): 测试配置并显示结果
- saveConfig(): 保存配置到数据库
- displayTestSuccess(): 展示测试成功结果
- displayTestError(): 展示测试错误信息

完成配置管理前端功能

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 9: 创建医保局配置初始化脚本

**Files:**
- Create: `scripts/init_nhsa_config.py`

- [ ] **Step 1: 创建初始化脚本**

```python
#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
医保局网站配置初始化脚本

用途：快速创建医保局耗材采集配置
运行：python scripts/init_nhsa_config.py

注意：选择器需要实际测试后调整
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig


async def init_nhsa_config():
    """初始化医保局配置"""
    
    print("开始创建医保局配置...")
    
    config = CrawlerConfig(
        config_name="医保局-医用耗材信息",
        target_url="https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
        need_login=False,
        
        # 输入配置
        input_configs={
            "inputs": [
                {
                    "selector": "#registrationNumber",
                    "param_key": "registration_number",
                    "input_type": "text"
                }
            ]
        },
        
        # 提交和等待
        submit_selector="#searchBtn",
        wait_selector="table#jqGrid tbody tr",
        
        # 字段映射（需实际测试后调整）
        fields_mapping={
            "iframe_levels": 2,
            "iframe1_selector": "#iframe1",
            "iframe2_selector": "#contentIframe",
            
            "list_selector": "table#jqGrid tbody tr",
            "fields": [
                {"name": "序号", "selector": "td:nth-child(1)", "attr": "text"},
                {"name": "医保编码", "selector": "td:nth-child(2)", "attr": "text"},
                {"name": "产品名称", "selector": "td:nth-child(3)", "attr": "text"},
                {"name": "注册证号", "selector": "td:nth-child(4)", "attr": "text"},
                {"name": "规格", "selector": "td:nth-child(5)", "attr": "text"},
                {"name": "型号", "selector": "td:nth-child(6)", "attr": "text"}
            ],
            
            "detail_config": {
                "enabled": True,
                "detail_button_selector": "a.detail-link",
                "wait_selector": ".modal-body",
                "detail_iframe_selector": "#detailIframe",
                "fields": [
                    {"name": "注册人名称", "selector": ".registrant-name", "attr": "text"},
                    {"name": "生产企业名称", "selector": ".manufacturer-name", "attr": "text"},
                    {"name": "生产地址", "selector": ".address", "attr": "text"},
                    {"name": "产品标准", "selector": ".standard", "attr": "text"},
                    {"name": "产品描述", "selector": ".description", "attr": "text"}
                ],
                "close_method": "auto",
                "close_selector": ".close-btn",
                "timeout": {
                    "click": 10000,
                    "wait_selector": 5000,
                    "iframe_load": 10000,
                    "close": 5000
                },
                "retry": {
                    "max_attempts": 3,
                    "delay_seconds": 2
                }
            }
        },
        
        # 分页配置
        pagination_selector="#next_page",
        max_pages=5,
        
        # 超时配置
        timeout_config={
            "page_load": 30000,
            "wait_selector": 15000,
            "click": 10000
        }
    )
    
    async with get_session() as session:
        session.add(config)
        await session.commit()
        await session.refresh(config)
        
        print("\n" + "="*60)
        print("✓ 配置创建成功")
        print("="*60)
        print(f"配置 ID: {config.id}")
        print(f"配置名称: {config.config_name}")
        print(f"目标 URL: {config.target_url}")
        print(f"详情采集: {'启用' if config.fields_mapping.get('detail_config', {}).get('enabled') else '禁用'}")
        print()
        print("下一步:")
        print(f"1. 访问 http://localhost:8000/static/config_manager.html?id={config.id}")
        print("2. 根据实际网站结构调整选择器")
        print("3. 点击「测试配置」验证")
        print("4. 确认无误后保存配置")
        print("="*60)
        
        return config.id


if __name__ == "__main__":
    try:
        config_id = asyncio.run(init_nhsa_config())
    except Exception as e:
        print(f"\n✗ 配置创建失败: {e}")
        sys.exit(1)
```

- [ ] **Step 2: 测试脚本执行**

```bash
python scripts/init_nhsa_config.py
```

Expected: 输出包含 "✓ 配置创建成功" 和配置 ID

- [ ] **Step 3: Commit**

```bash
git add scripts/init_nhsa_config.py
git commit -m "feat: add NHSA config initialization script

新增医保局配置初始化脚本：
- 快速创建医保局耗材采集配置
- 包含列表字段和详情字段配置模板
- 提供后续操作指引

运行：python scripts/init_nhsa_config.py

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## Task 10: 端到端测试

**Files:**
- None (测试任务)

- [ ] **Step 1: 启动服务**

```bash
uvicorn app.main:app --reload
```

Expected: 服务在 http://localhost:8000 启动

- [ ] **Step 2: 创建测试配置**

```bash
python scripts/init_nhsa_config.py
```

Expected: 输出配置 ID（例如：配置 ID: 3）

- [ ] **Step 3: 访问配置管理页面**

在浏览器中打开：
```
http://localhost:8000/static/config_manager.html?id=3
```

Expected: 页面正常加载，显示配置表单

- [ ] **Step 4: 验证表单加载**

检查页面是否正确显示：
- 列表容器选择器：`table#jqGrid tbody tr`
- 列表字段：6个字段（序号、医保编码、产品名称等）
- 详情采集：已启用
- 详情字段：5个字段（注册人名称、生产企业名称等）

Expected: 所有字段正确显示

- [ ] **Step 5: 测试字段操作**

1. 点击「+ 添加字段」按钮
2. 填写新字段信息
3. 点击「删除」按钮

Expected: 字段正常添加和删除

- [ ] **Step 6: 测试表单验证**

1. 清空「列表容器选择器」
2. 点击「测试配置」按钮

Expected: 显示错误提示"请输入列表容器选择器"

- [ ] **Step 7: 测试配置测试功能（模拟）**

注意：由于医保局网站实际选择器未知，此步骤可能失败，这是预期的。

1. 恢复「列表容器选择器」值
2. 点击「测试配置」按钮
3. 输入测试参数（如：滇械注准20192140008）
4. 观察测试结果

Expected: 
- 如果选择器正确：显示样本数据
- 如果选择器错误：显示友好的错误提示

- [ ] **Step 8: 测试保存功能**

1. 修改某个字段名称
2. 点击「保存配置」按钮
3. 确认保存

Expected: 显示"配置保存成功！"

- [ ] **Step 9: 验证保存结果**

重新加载页面，检查修改是否保存

Expected: 修改的字段名称正确显示

- [ ] **Step 10: 停止服务**

按 Ctrl+C 停止服务

Expected: 服务正常停止

- [ ] **Step 11: Commit 测试文档**

创建测试记录文件 `docs/testing/config_manager_test_log.md`：

```markdown
# 配置管理界面测试日志

**测试日期**: 2026-09-29  
**测试人员**: [填写]  
**测试环境**: Windows/Mac/Linux  

## 测试结果

| 测试项 | 状态 | 备注 |
|--------|------|------|
| 服务启动 | ✓/✗ | |
| 配置初始化 | ✓/✗ | 配置 ID: ___ |
| 页面加载 | ✓/✗ | |
| 表单加载 | ✓/✗ | |
| 字段操作 | ✓/✗ | |
| 表单验证 | ✓/✗ | |
| 配置测试 | ✓/✗ | |
| 配置保存 | ✓/✗ | |

## 问题记录

[记录测试中发现的问题]
```

```bash
git add docs/testing/config_manager_test_log.md
git commit -m "docs: add config manager test log template

新增配置管理界面测试日志模板

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## 自检清单

### 规范覆盖
- [x] Task 1: 创建请求/响应模型
- [x] Task 2: 创建配置测试 API
- [x] Task 3: 注册 API 路由
- [x] Task 4: 创建配置管理 HTML
- [x] Task 5: 创建配置管理 CSS
- [x] Task 6-8: 创建配置管理 JavaScript（分3部分）
- [x] Task 9: 创建医保局配置初始化脚本
- [x] Task 10: 端到端测试

### 占位符检查
- [x] 无 TBD/TODO
- [x] 所有代码块完整
- [x] 所有命令可执行

### 类型一致性
- [x] API 端点：`/api/configs/{id}/test`
- [x] 模型名称：`ConfigTestRequest`, `ConfigTestResponse`
- [x] 字段名称：`fields_mapping`, `detail_config`
- [x] 方法签名匹配

---

## 实施注意事项

1. **选择器调整**: 医保局网站的实际选择器需要通过浏览器开发者工具确认后调整
2. **iframe 层级**: 如果网站有多层 iframe，需要根据实际情况调整 `iframe_levels` 和选择器
3. **测试采集时间**: 首次测试采集可能需要较长时间（30秒以上），需耐心等待
4. **错误诊断**: 如果测试失败，检查浏览器控制台和服务器日志获取详细错误信息

---

## 预期成果

完成本计划后，系统将具备以下能力：

1. ✅ 用户可通过网页界面配置列表字段和详情字段
2. ✅ 用户可实时测试配置并查看样本数据
3. ✅ 配置保存后立即生效，无需重启服务
4. ✅ 医保局网站配置已初始化，可直接使用或调整

**总开发时间**: 约 5-7 小时
**代码行数**: 约 1500+ 行（前端 + 后端 + 脚本）
