# WebSocket Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将执行器与 WebSocket 连接打通，实现任务执行过程中的实时状态和日志推送

**Architecture:** 创建全局 `WebSocketManager` 单例管理所有活跃连接，执行器通过依赖注入接收 manager 实例，在关键节点调用 `broadcast()` 推送消息。采用中粒度推送（每任务 8-10 条消息），消息格式固定为 `{"type": "progress", ...}` 和 `{"type": "log", ...}`。

**Tech Stack:** FastAPI WebSocket, asyncio, Python 3.9+

---

## File Structure

**New Files:**
- `app/api/websocket.py` - WebSocket 连接管理器和端点处理

**Modified Files:**
- `app/services/executor.py` - 添加 WebSocket 广播支持
- `app/main.py` - 注册 WebSocket 路由
- `app/api/endpoints.py` - 实例化执行器时传入 websocket_manager

---

## Task 1: Create WebSocketManager

**Files:**
- Create: `app/api/websocket.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_websocket.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi import WebSocket
from app.api.websocket import WebSocketManager


@pytest.mark.asyncio
async def test_websocket_manager_connect():
    """测试连接添加"""
    manager = WebSocketManager()
    mock_ws = MagicMock(spec=WebSocket)
    
    await manager.connect(mock_ws)
    
    assert mock_ws in manager.active_connections
    assert len(manager.active_connections) == 1


@pytest.mark.asyncio
async def test_websocket_manager_disconnect():
    """测试连接移除"""
    manager = WebSocketManager()
    mock_ws = MagicMock(spec=WebSocket)
    
    await manager.connect(mock_ws)
    await manager.disconnect(mock_ws)
    
    assert mock_ws not in manager.active_connections
    assert len(manager.active_connections) == 0


@pytest.mark.asyncio
async def test_websocket_manager_broadcast():
    """测试消息广播"""
    manager = WebSocketManager()
    mock_ws1 = MagicMock(spec=WebSocket)
    mock_ws1.send_json = AsyncMock()
    mock_ws2 = MagicMock(spec=WebSocket)
    mock_ws2.send_json = AsyncMock()
    
    await manager.connect(mock_ws1)
    await manager.connect(mock_ws2)
    
    message = {"type": "progress", "message": "test"}
    await manager.broadcast(message)
    
    mock_ws1.send_json.assert_called_once_with(message)
    mock_ws2.send_json.assert_called_once_with(message)


@pytest.mark.asyncio
async def test_websocket_manager_broadcast_handles_disconnected():
    """测试广播时自动清理断开的连接"""
    manager = WebSocketManager()
    mock_ws_good = MagicMock(spec=WebSocket)
    mock_ws_good.send_json = AsyncMock()
    mock_ws_bad = MagicMock(spec=WebSocket)
    mock_ws_bad.send_json = AsyncMock(side_effect=Exception("Connection closed"))
    
    await manager.connect(mock_ws_good)
    await manager.connect(mock_ws_bad)
    
    message = {"type": "log", "message": "test"}
    await manager.broadcast(message)
    
    # 正常连接应该收到消息
    mock_ws_good.send_json.assert_called_once_with(message)
    # 异常连接应该被移除
    assert mock_ws_bad not in manager.active_connections
    assert mock_ws_good in manager.active_connections
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_websocket.py -v`

Expected: FAIL with "ModuleNotFoundError: No module named 'app.api.websocket'"

- [ ] **Step 3: Create WebSocketManager implementation**

```python
# app/api/websocket.py
import logging
from typing import Set
from fastapi import WebSocket, WebSocketDisconnect
import json

logger = logging.getLogger(__name__)


class WebSocketManager:
    """WebSocket 连接管理器（全局单例）"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """
        添加新连接
        
        Args:
            websocket: WebSocket 连接对象
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        logger.info(f"新客户端连接，当前连接数: {len(self.active_connections)}")
    
    async def disconnect(self, websocket: WebSocket):
        """
        移除连接
        
        Args:
            websocket: WebSocket 连接对象
        """
        self.active_connections.discard(websocket)
        logger.info(f"客户端断开，当前连接数: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        """
        向所有客户端广播消息
        
        Args:
            message: 要广播的消息字典
        """
        if not self.active_connections:
            return
        
        disconnected = set()
        
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"发送消息失败，移除连接: {e}")
                disconnected.add(connection)
        
        # 清理断开的连接
        for connection in disconnected:
            self.active_connections.discard(connection)
    
    async def websocket_endpoint(self, websocket: WebSocket):
        """
        WebSocket 端点处理函数
        
        Args:
            websocket: WebSocket 连接对象
        """
        await self.connect(websocket)
        
        try:
            # 保持连接直到客户端断开
            while True:
                # 接收客户端消息（心跳或其他）
                data = await websocket.receive_text()
                logger.debug(f"收到客户端消息: {data}")
                
                # 可选：回应心跳
                if data == "ping":
                    await websocket.send_text("pong")
        
        except WebSocketDisconnect:
            logger.info("客户端主动断开连接")
        except Exception as e:
            logger.error(f"WebSocket 连接异常: {e}", exc_info=True)
        finally:
            await self.disconnect(websocket)


# 创建全局单例
websocket_manager = WebSocketManager()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/test_websocket.py -v`

Expected: All tests PASS

- [ ] **Step 5: Commit**

```bash
git add app/api/websocket.py tests/test_websocket.py
git commit -m "feat: add WebSocketManager for connection management"
```

---

## Task 2: Add WebSocket Support to Executor

**Files:**
- Modify: `app/services/executor.py:31-39` (constructor)
- Modify: `app/services/executor.py` (add helper methods)

- [ ] **Step 1: Write the failing test**

```python
# tests/test_executor_websocket.py
import pytest
from unittest.mock import AsyncMock, MagicMock
from app.services.executor import PlaywrightExecutor


@pytest.mark.asyncio
async def test_executor_accepts_ws_manager():
    """测试执行器接受 ws_manager 参数"""
    mock_ws_manager = MagicMock()
    executor = PlaywrightExecutor(ws_manager=mock_ws_manager)
    
    assert executor.ws_manager is mock_ws_manager


@pytest.mark.asyncio
async def test_executor_works_without_ws_manager():
    """测试执行器在没有 ws_manager 时正常工作"""
    executor = PlaywrightExecutor()
    
    assert executor.ws_manager is None


@pytest.mark.asyncio
async def test_broadcast_progress_with_manager():
    """测试 _broadcast_progress 调用 ws_manager"""
    mock_ws_manager = MagicMock()
    mock_ws_manager.broadcast = AsyncMock()
    executor = PlaywrightExecutor(ws_manager=mock_ws_manager)
    
    await executor._broadcast_progress(123, "测试消息", current=3, total=10)
    
    mock_ws_manager.broadcast.assert_called_once()
    call_args = mock_ws_manager.broadcast.call_args[0][0]
    assert call_args["type"] == "progress"
    assert call_args["job_id"] == 123
    assert call_args["message"] == "测试消息"
    assert call_args["progress"]["current"] == 3
    assert call_args["progress"]["total"] == 10
    assert "timestamp" in call_args


@pytest.mark.asyncio
async def test_broadcast_progress_without_manager():
    """测试 _broadcast_progress 在没有 manager 时不报错"""
    executor = PlaywrightExecutor()
    
    # 不应该抛出异常
    await executor._broadcast_progress(123, "测试消息")


@pytest.mark.asyncio
async def test_broadcast_log_with_manager():
    """测试 _broadcast_log 调用 ws_manager"""
    mock_ws_manager = MagicMock()
    mock_ws_manager.broadcast = AsyncMock()
    executor = PlaywrightExecutor(ws_manager=mock_ws_manager)
    
    await executor._broadcast_log("info", "测试日志", job_id=456)
    
    mock_ws_manager.broadcast.assert_called_once()
    call_args = mock_ws_manager.broadcast.call_args[0][0]
    assert call_args["type"] == "log"
    assert call_args["level"] == "info"
    assert call_args["message"] == "测试日志"
    assert call_args["job_id"] == 456
    assert "timestamp" in call_args


@pytest.mark.asyncio
async def test_broadcast_log_without_job_id():
    """测试 _broadcast_log 可以不传 job_id"""
    mock_ws_manager = MagicMock()
    mock_ws_manager.broadcast = AsyncMock()
    executor = PlaywrightExecutor(ws_manager=mock_ws_manager)
    
    await executor._broadcast_log("error", "系统错误")
    
    call_args = mock_ws_manager.broadcast.call_args[0][0]
    assert "job_id" not in call_args
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_executor_websocket.py -v`

Expected: FAIL with "AttributeError: 'PlaywrightExecutor' object has no attribute '_broadcast_progress'"

- [ ] **Step 3: Modify executor constructor**

```python
# app/services/executor.py
# Modify the __init__ method (around line 31-39)

def __init__(self, ws_manager=None):
    """
    初始化执行器

    Args:
        ws_manager: WebSocket 管理器（可选，用于状态推送）
    """
    self.ws_manager = ws_manager
    self.logger = logger
```

- [ ] **Step 4: Add broadcast helper methods to executor**

```python
# app/services/executor.py
# Add these methods after __init__ (around line 40)

async def _broadcast_progress(self, job_id: int, message: str, current: int = None, total: int = None):
    """
    推送进度消息
    
    Args:
        job_id: 任务 ID
        message: 进度描述
        current: 当前进度（可选）
        total: 总进度（可选）
    """
    if not self.ws_manager:
        return
    
    from datetime import datetime
    
    payload = {
        "type": "progress",
        "job_id": job_id,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    
    if current is not None and total is not None:
        payload["progress"] = {"current": current, "total": total}
    
    await self.ws_manager.broadcast(payload)

async def _broadcast_log(self, level: str, message: str, job_id: int = None):
    """
    推送日志消息
    
    Args:
        level: 日志级别（info/warning/error）
        message: 日志内容
        job_id: 任务 ID（可选）
    """
    if not self.ws_manager:
        return
    
    from datetime import datetime
    
    payload = {
        "type": "log",
        "level": level,
        "message": message,
        "timestamp": datetime.now().isoformat()
    }
    
    if job_id is not None:
        payload["job_id"] = job_id
    
    await self.ws_manager.broadcast(payload)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_executor_websocket.py -v`

Expected: All tests PASS

- [ ] **Step 6: Commit**

```bash
git add app/services/executor.py tests/test_executor_websocket.py
git commit -m "feat: add WebSocket broadcast support to executor"
```

---

## Task 3: Integrate WebSocket Broadcasts in execute_job

**Files:**
- Modify: `app/services/executor.py:318-452` (execute_job method)

- [ ] **Step 1: Add broadcast at task start (line ~352)**

```python
# app/services/executor.py
# After line 352: self.logger.info(f"开始执行任务 {job_id}，配置: {config.config_name}")

# 节点 1: 任务开始
await self._broadcast_progress(job_id, f"开始执行任务 {job_id}")
```

- [ ] **Step 2: Add broadcast after browser launch (line ~362)**

```python
# app/services/executor.py
# After line 362: self.logger.info(f"浏览器启动成功（登录态: {config.auth_profile if config.need_login else '无'}）")

# 节点 2: 浏览器启动完成
await self._broadcast_log(
    "info",
    f"浏览器启动成功（登录态: {config.auth_profile if config.need_login else '无'}）",
    job_id
)
```

- [ ] **Step 3: Add broadcast after form filling (line ~370)**

```python
# app/services/executor.py
# After line 370: await self._fill_form(page, config.input_configs, job.query_params)

# 节点 3: 表单填充完成
await self._broadcast_log("info", "表单填充完成", job_id)
```

- [ ] **Step 4: Add broadcast after submit click (line ~374)**

```python
# app/services/executor.py
# After line 374: await page.click(config.submit_selector, timeout=TIMEOUTS['click'])

# 节点 4: 提交按钮点击
await self._broadcast_log("info", "点击提交按钮", job_id)
```

- [ ] **Step 5: Add broadcast after result page loaded (line ~385)**

```python
# app/services/executor.py
# After line 385: self.logger.info("结果页面加载完成")

# 节点 5: 结果页面加载完成
await self._broadcast_log("info", "结果页面加载完成", job_id)
```

- [ ] **Step 6: Add broadcast after successful completion (line ~417)**

```python
# app/services/executor.py
# After line 417: self.logger.info(f"任务 {job_id} 执行成功，耗时 {execution_time:.2f} 秒")

# 节点 8: 任务成功完成
await self._broadcast_progress(
    job_id,
    f"任务 {job_id} 执行成功，提取 {len(extracted_data)} 条数据，耗时 {execution_time:.2f} 秒"
)
```

- [ ] **Step 7: Add broadcast on failure (line ~428)**

```python
# app/services/executor.py
# After line 428: self.logger.error(f"任务 {job_id} 执行失败: {e}", exc_info=True)

# 节点 9: 任务失败
await self._broadcast_log("error", f"任务 {job_id} 执行失败: {str(e)}", job_id)
```

- [ ] **Step 8: Commit**

```bash
git add app/services/executor.py
git commit -m "feat: integrate WebSocket broadcasts in execute_job"
```

---

## Task 4: Add Pagination Progress Broadcasts

**Files:**
- Modify: `app/services/executor.py:176-241` (_extract_with_pagination method)

- [ ] **Step 1: Add broadcast after each page extraction (line ~206)**

```python
# app/services/executor.py
# After line 206: self.logger.info(f"第 {current_page} 页提取 {len(page_data)} 条数据")

# 节点 6: 每页数据提取完成
await self._broadcast_progress(
    job_id=None,  # pagination method doesn't have job_id, will be added as parameter
    message=f"第 {current_page} 页提取 {len(page_data)} 条数据",
    current=current_page,
    total=max_pages
)
```

- [ ] **Step 2: Add job_id parameter to _extract_with_pagination**

```python
# app/services/executor.py
# Modify method signature (line 176)

async def _extract_with_pagination(
    self,
    page: Page,
    fields_mapping: Dict,
    pagination_selector: str,
    wait_selector: str,
    max_pages: int,
    job_id: int = None  # Add this parameter
) -> Tuple[List[Dict], int]:
    """
    翻页提取数据

    Args:
        page: 页面对象
        fields_mapping: 字段映射规则
        pagination_selector: 下一页按钮选择器
        wait_selector: 等待加载完成的选择器
        max_pages: 最大翻页数
        job_id: 任务 ID（用于 WebSocket 推送）

    Returns:
        (所有数据列表, 实际页数)
    """
```

- [ ] **Step 3: Update broadcast call with job_id (line ~206)**

```python
# app/services/executor.py
# Replace the broadcast call added in Step 1

# 节点 6: 每页数据提取完成
await self._broadcast_progress(
    job_id=job_id,
    message=f"正在处理第 {current_page} 页",
    current=current_page,
    total=max_pages
)
```

- [ ] **Step 4: Add broadcast before pagination click (line ~229)**

```python
# app/services/executor.py
# After line 229: await next_button.click(timeout=TIMEOUTS['click'])

# 节点 7: 翻页动作
if job_id:
    await self._broadcast_log("info", f"点击下一页按钮（第 {current_page + 1} 页）", job_id)
```

- [ ] **Step 5: Update execute_job to pass job_id (line ~389)**

```python
# app/services/executor.py
# Modify the call to _extract_with_pagination (around line 389)

extracted_data, page_count = await self._extract_with_pagination(
    page,
    config.fields_mapping,
    config.pagination_selector,
    config.wait_selector,
    config.max_pages,
    job_id  # Add this argument
)
```

- [ ] **Step 6: Commit**

```bash
git add app/services/executor.py
git commit -m "feat: add pagination progress broadcasts"
```

---

## Task 5: Register WebSocket Route in FastAPI

**Files:**
- Modify: `app/main.py:1-68`

- [ ] **Step 1: Write integration test**

```python
# tests/test_websocket_integration.py
import pytest
from fastapi.testclient import TestClient
from app.main import app


def test_websocket_endpoint_exists():
    """测试 WebSocket 端点存在"""
    client = TestClient(app)
    
    with client.websocket_connect("/ws") as websocket:
        # 发送 ping
        websocket.send_text("ping")
        # 应该收到 pong
        data = websocket.receive_text()
        assert data == "pong"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/test_websocket_integration.py -v`

Expected: FAIL with "404: Not Found" (route not registered)

- [ ] **Step 3: Import websocket_manager in main.py**

```python
# app/main.py
# Add this import after line 8 (after from app.api.endpoints import router)

from app.api.websocket import websocket_manager
```

- [ ] **Step 4: Register WebSocket route**

```python
# app/main.py
# Add this after line 38 (after app.include_router(router))

# 注册 WebSocket 路由
@app.websocket("/ws")
async def websocket_endpoint(websocket):
    await websocket_manager.websocket_endpoint(websocket)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest tests/test_websocket_integration.py -v`

Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add app/main.py tests/test_websocket_integration.py
git commit -m "feat: register WebSocket route in FastAPI app"
```

---

## Task 6: Update /task/run Endpoint

**Files:**
- Modify: `app/api/endpoints.py:143-211`

- [ ] **Step 1: Import websocket_manager**

```python
# app/api/endpoints.py
# Add this import after line 13 (after from app.services.auth_manager import auth_manager)

from app.api.websocket import websocket_manager
```

- [ ] **Step 2: Pass websocket_manager to executor**

```python
# app/api/endpoints.py
# Modify line 181 (executor instantiation)

# 2. 创建执行器（传入 websocket_manager）
executor = PlaywrightExecutor(ws_manager=websocket_manager)
```

- [ ] **Step 3: Commit**

```bash
git add app/api/endpoints.py
git commit -m "feat: pass websocket_manager to executor in /task/run"
```

---

## Task 7: End-to-End Manual Testing

**Files:**
- Create: `tests/manual/test_websocket_client.html`

- [ ] **Step 1: Create manual test HTML file**

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>WebSocket 测试客户端</title>
    <style>
        body {
            font-family: monospace;
            padding: 20px;
        }
        #messages {
            border: 1px solid #ccc;
            height: 400px;
            overflow-y: scroll;
            padding: 10px;
            background: #f5f5f5;
        }
        .message {
            margin: 5px 0;
            padding: 5px;
            border-radius: 3px;
        }
        .progress {
            background: #e3f2fd;
        }
        .log-info {
            background: #f1f8e9;
        }
        .log-error {
            background: #ffebee;
        }
        button {
            margin: 10px 5px;
            padding: 10px 20px;
        }
    </style>
</head>
<body>
    <h1>WebSocket 测试客户端</h1>
    
    <div>
        <button id="connectBtn">连接 WebSocket</button>
        <button id="disconnectBtn" disabled>断开连接</button>
        <button id="clearBtn">清空消息</button>
        <span id="status">未连接</span>
    </div>
    
    <h2>收到的消息：</h2>
    <div id="messages"></div>
    
    <script>
        let ws = null;
        const messagesDiv = document.getElementById('messages');
        const statusSpan = document.getElementById('status');
        const connectBtn = document.getElementById('connectBtn');
        const disconnectBtn = document.getElementById('disconnectBtn');
        const clearBtn = document.getElementById('clearBtn');
        
        connectBtn.onclick = () => {
            ws = new WebSocket('ws://127.0.0.1:8000/ws');
            
            ws.onopen = () => {
                statusSpan.textContent = '已连接';
                statusSpan.style.color = 'green';
                connectBtn.disabled = true;
                disconnectBtn.disabled = false;
                addMessage('system', '连接成功');
            };
            
            ws.onmessage = (event) => {
                const data = JSON.parse(event.data);
                const type = data.type;
                const className = type === 'progress' ? 'progress' : `log-${data.level}`;
                
                let content = `[${data.type}] ${data.message}`;
                if (data.job_id) {
                    content += ` (Job ${data.job_id})`;
                }
                if (data.progress) {
                    content += ` - ${data.progress.current}/${data.progress.total}`;
                }
                
                addMessage(className, content);
            };
            
            ws.onerror = (error) => {
                addMessage('log-error', `错误: ${error}`);
            };
            
            ws.onclose = () => {
                statusSpan.textContent = '已断开';
                statusSpan.style.color = 'red';
                connectBtn.disabled = false;
                disconnectBtn.disabled = true;
                addMessage('system', '连接关闭');
            };
        };
        
        disconnectBtn.onclick = () => {
            if (ws) {
                ws.close();
            }
        };
        
        clearBtn.onclick = () => {
            messagesDiv.innerHTML = '';
        };
        
        function addMessage(className, content) {
            const div = document.createElement('div');
            div.className = `message ${className}`;
            div.textContent = `[${new Date().toLocaleTimeString()}] ${content}`;
            messagesDiv.appendChild(div);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        }
    </script>
</body>
</html>
```

- [ ] **Step 2: Create manual test instructions**

```markdown
# tests/manual/WEBSOCKET_TEST_INSTRUCTIONS.md

## WebSocket 手动测试指南

### 前置条件
1. 启动应用：`uvicorn app.main:app --reload`
2. 确保数据库中有待处理的任务

### 测试步骤

#### 测试 1: 基本连接
1. 用浏览器打开 `tests/manual/test_websocket_client.html`
2. 点击"连接 WebSocket"按钮
3. **验证**: 状态显示"已连接"，消息区显示"连接成功"

#### 测试 2: 任务执行监控
1. 保持 WebSocket 连接
2. 在另一个浏览器标签打开 `http://127.0.0.1:8000/docs`
3. 调用 `/task/run` 接口，传入 `config_id` 和 `limit=1`
4. **验证**: WebSocket 客户端实时收到以下消息：
   - [progress] 开始执行任务 X
   - [log] 浏览器启动成功
   - [log] 表单填充完成
   - [log] 点击提交按钮
   - [log] 结果页面加载完成
   - [progress] 正在处理第 N 页（如果有翻页）
   - [log] 点击下一页按钮（如果有翻页）
   - [progress] 任务 X 执行成功

#### 测试 3: 多客户端广播
1. 打开两个浏览器标签，都加载 `test_websocket_client.html`
2. 两个标签都点击"连接 WebSocket"
3. 调用 `/task/run` 触发任务
4. **验证**: 两个客户端都收到相同的消息

#### 测试 4: 断线重连
1. 连接 WebSocket
2. 点击"断开连接"
3. 点击"连接 WebSocket"重新连接
4. 调用 `/task/run`
5. **验证**: 重连后仍能正常收到消息

#### 测试 5: 消息格式验证
1. 连接 WebSocket 并触发任务
2. 打开浏览器开发者工具 - Network - WS 标签
3. **验证**: 所有消息都符合以下格式：
   - Progress: `{"type": "progress", "job_id": 123, "message": "...", "timestamp": "..."}`
   - Log: `{"type": "log", "level": "info", "message": "...", "job_id": 123, "timestamp": "..."}`

### 预期结果
- 所有测试通过
- 消息实时推送，无延迟
- 消息格式正确
- 多客户端同步接收
```

- [ ] **Step 3: Run manual tests**

1. 启动应用：`uvicorn app.main:app --reload`
2. 按照 `WEBSOCKET_TEST_INSTRUCTIONS.md` 执行所有测试
3. 记录测试结果

Expected: 所有测试场景通过

- [ ] **Step 4: Commit test files**

```bash
git add tests/manual/test_websocket_client.html tests/manual/WEBSOCKET_TEST_INSTRUCTIONS.md
git commit -m "test: add manual WebSocket testing files"
```

---

## Task 8: Update Documentation

**Files:**
- Create: `docs/websocket_usage.md`

- [ ] **Step 1: Create usage documentation**

```markdown
# WebSocket 实时监控使用指南

## 概述

本系统支持通过 WebSocket 实时监控任务执行状态和日志。前端可以连接到 WebSocket 端点，接收任务执行过程中的实时消息推送。

## 连接方式

### WebSocket 端点
```
ws://127.0.0.1:8000/ws
```

### JavaScript 示例
```javascript
const ws = new WebSocket('ws://127.0.0.1:8000/ws');

ws.onopen = () => {
    console.log('WebSocket 连接成功');
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('收到消息:', message);
    
    if (message.type === 'progress') {
        // 处理进度消息
        updateProgress(message.job_id, message.message, message.progress);
    } else if (message.type === 'log') {
        // 处理日志消息
        addLog(message.level, message.message, message.job_id);
    }
};

ws.onerror = (error) => {
    console.error('WebSocket 错误:', error);
};

ws.onclose = () => {
    console.log('WebSocket 连接关闭');
};
```

## 消息格式

### 进度消息 (Progress)

```json
{
    "type": "progress",
    "job_id": 123,
    "message": "正在处理第 3 页",
    "progress": {
        "current": 3,
        "total": 10
    },
    "timestamp": "2026-08-31T10:30:00.123456"
}
```

**字段说明**：
- `type`: 固定为 `"progress"`
- `job_id`: 任务 ID
- `message`: 人类可读的进度描述
- `progress`: 可选，包含 `current` 和 `total` 字段
- `timestamp`: ISO 8601 格式时间戳

### 日志消息 (Log)

```json
{
    "type": "log",
    "level": "info",
    "message": "浏览器启动成功（登录态: taobao）",
    "job_id": 123,
    "timestamp": "2026-08-31T10:30:00.123456"
}
```

**字段说明**：
- `type`: 固定为 `"log"`
- `level`: 日志级别（`"info"` / `"warning"` / `"error"`）
- `message`: 日志内容
- `job_id`: 可选，关联的任务 ID
- `timestamp`: ISO 8601 格式时间戳

## 消息推送节点

任务执行过程中会在以下节点推送消息：

1. **任务开始** (progress) - "开始执行任务 123"
2. **浏览器启动完成** (log/info) - "浏览器启动成功（登录态: xxx）"
3. **表单填充完成** (log/info) - "表单填充完成"
4. **提交按钮点击** (log/info) - "点击提交按钮"
5. **结果页面加载完成** (log/info) - "结果页面加载完成"
6. **每页数据提取完成** (progress) - "正在处理第 N 页" + 进度信息
7. **翻页动作** (log/info) - "点击下一页按钮"
8. **任务成功完成** (progress) - "任务 123 执行成功，提取 X 条数据"
9. **任务失败** (log/error) - "任务 123 执行失败: 错误信息"

## 多客户端支持

- 支持多个前端客户端同时连接
- 所有客户端接收相同的消息广播
- 客户端可以根据 `job_id` 字段过滤感兴趣的任务

## 错误处理

### 连接断开
- 客户端主动断开：服务端自动清理连接
- 客户端异常断开：服务端在下次广播时检测并清理
- 服务端重启：所有连接断开，客户端需要重连

### 任务执行异常
- 任务失败会推送 `type: "log", level: "error"` 消息
- 执行器崩溃不影响 WebSocket 连接

## 心跳机制

客户端可以发送 `"ping"` 消息，服务端会回复 `"pong"`：

```javascript
// 每 30 秒发送心跳
setInterval(() => {
    if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping');
    }
}, 30000);
```

## 前端实现示例

参考 `tests/manual/test_websocket_client.html` 中的完整实现示例。

## 性能考虑

- 消息频率：中粒度推送（每任务 8-10 条消息）
- 连接数限制：无硬限制，依赖操作系统和内存
- 消息大小：每条消息约 100-300 字节

## 故障排查

### 无法连接
1. 检查服务是否启动：`curl http://127.0.0.1:8000/health`
2. 检查防火墙设置
3. 确认 WebSocket 路由已注册

### 收不到消息
1. 检查任务是否正在执行
2. 确认执行器实例化时传入了 `websocket_manager`
3. 查看服务端日志是否有异常

### 连接频繁断开
1. 检查网络稳定性
2. 实现心跳机制保持连接
3. 实现自动重连逻辑
```

- [ ] **Step 2: Commit documentation**

```bash
git add docs/websocket_usage.md
git commit -m "docs: add WebSocket usage guide"
```

---

## Spec Coverage Review

✅ **Section 1: 概述** - Task 1-2 创建 WebSocketManager 和集成执行器  
✅ **Section 2: 架构设计** - Task 1-2 实现全局单例 + 依赖注入模式  
✅ **Section 3: WebSocketManager 详细设计** - Task 1 完整实现  
✅ **Section 4: 执行器集成设计** - Task 2-4 添加广播支持和集成调用  
✅ **Section 5: API 路由集成** - Task 5-6 注册路由和更新端点  
✅ **Section 6: 错误处理与边界情况** - Task 1 的异常处理逻辑  
✅ **Section 7: 测试策略** - Task 1-2 单元测试，Task 7 手动测试  
✅ **Section 8: 实现清单** - 所有任务覆盖  
✅ **Section 10: 参考资料** - Task 8 文档

无遗漏需求。
