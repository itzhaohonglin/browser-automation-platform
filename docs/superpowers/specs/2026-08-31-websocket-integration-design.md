---
name: WebSocket Integration for Real-time Task Monitoring
description: 将执行器与 WebSocket 连接打通，实现任务状态和日志的实时推送
type: feature
---

# WebSocket 集成设计文档

## 1. 概述

### 1.1 目标
将 `PlaywrightExecutor` 与 WebSocket 连接打通，实现任务执行过程中的实时状态和日志推送，满足 PRD 3.6 节"前端实时监控看板"的需求。

### 1.2 范围
- 创建 `WebSocketManager` 连接管理器
- 在执行器关键节点插入消息广播
- 在 FastAPI 应用中注册 WebSocket 路由
- 支持多客户端同时监控

### 1.3 非目标
- 不实现前端页面（仅提供后端 WebSocket 接口）
- 不推送业务数据预览（符合 PRD 要求）
- 不实现消息持久化（仅实时推送）

## 2. 架构设计

### 2.1 整体架构

采用 **全局单例 WebSocketManager + 依赖注入** 模式：

```
Frontend Browser ←→ WebSocket (/ws) ←→ WebSocketManager (全局单例)
                                              ↑
                                              | broadcast(message)
                                              |
                                        PlaywrightExecutor
                                              ↓
                                        Database (jobs/results)
```

### 2.2 组件职责

| 组件 | 职责 | 文件路径 |
|------|------|----------|
| `WebSocketManager` | 管理活跃连接，提供广播接口 | `app/api/websocket.py` |
| `PlaywrightExecutor` | 执行任务，在关键节点推送消息 | `app/services/executor.py` |
| WebSocket 路由 | 处理客户端连接/断开 | `app/main.py` |

### 2.3 设计原则

- **单一职责**：连接管理与任务执行分离
- **向后兼容**：`ws_manager` 参数可选，不传入时不影响现有功能
- **解耦设计**：执行器通过接口广播，不关心连接细节
- **容错性**：连接异常不影响任务执行

## 3. WebSocketManager 详细设计

### 3.1 核心功能

```python
class WebSocketManager:
    """WebSocket 连接管理器（全局单例）"""
    
    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
    
    async def connect(self, websocket: WebSocket):
        """添加新连接"""
        
    async def disconnect(self, websocket: WebSocket):
        """移除连接"""
        
    async def broadcast(self, message: dict):
        """向所有客户端广播消息"""
        
    async def websocket_endpoint(self, websocket: WebSocket):
        """WebSocket 端点处理函数"""
```

### 3.2 消息格式规范

#### 进度消息（Progress）
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

#### 日志消息（Log）
```json
{
    "type": "log",
    "level": "info",
    "message": "任务 123 执行成功，提取 50 条数据",
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

### 3.3 错误处理策略

- **连接断开检测**：广播时捕获 `WebSocketDisconnect` 和其他异常
- **自动清理**：检测到断开的连接立即从 `active_connections` 移除
- **静默失败**：广播失败不抛出异常，不影响任务执行
- **日志记录**：连接异常记录到应用日志

## 4. 执行器集成设计

### 4.1 构造函数修改

```python
class PlaywrightExecutor:
    def __init__(self, ws_manager=None):
        """
        初始化执行器
        
        Args:
            ws_manager: WebSocket 管理器（可选，用于状态推送）
        """
        self.ws_manager = ws_manager
        self.logger = logger
```

### 4.2 消息推送节点（中粒度）

在以下 8-10 个关键节点推送消息：

| 序号 | 节点 | 消息类型 | 示例内容 |
|------|------|----------|----------|
| 1 | 任务开始 | progress | "开始执行任务 123" |
| 2 | 浏览器启动完成 | log (info) | "浏览器启动成功（登录态: taobao）" |
| 3 | 表单填充完成 | log (info) | "表单填充完成" |
| 4 | 提交按钮点击 | log (info) | "点击提交按钮" |
| 5 | 结果页面加载完成 | log (info) | "结果页面加载完成" |
| 6 | 每页数据提取完成 | progress | "正在处理第 3 页" + 当前进度 |
| 7 | 翻页动作 | log (info) | "点击下一页按钮" |
| 8 | 任务成功完成 | progress | "任务 123 执行成功，提取 50 条数据" |
| 9 | 任务失败 | log (error) | "任务 123 执行失败: <错误信息>" |

### 4.3 广播辅助方法

```python
async def _broadcast_progress(self, job_id: int, message: str, current: int = None, total: int = None):
    """推送进度消息"""
    if not self.ws_manager:
        return
    
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
    """推送日志消息"""
    if not self.ws_manager:
        return
    
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

### 4.4 集成示例

```python
async def execute_job(self, job_id: int, session: AsyncSession) -> Dict:
    try:
        # 节点 1: 任务开始
        await self._broadcast_progress(job_id, f"开始执行任务 {job_id}")
        
        # ... 启动浏览器 ...
        
        # 节点 2: 浏览器启动完成
        await self._broadcast_log(
            "info",
            f"浏览器启动成功（登录态: {config.auth_profile if config.need_login else '无'}）",
            job_id
        )
        
        # ... 填充表单 ...
        
        # 节点 3: 表单填充完成
        await self._broadcast_log("info", "表单填充完成", job_id)
        
        # ... 其他步骤 ...
        
    except Exception as e:
        # 节点 9: 任务失败
        await self._broadcast_log("error", f"任务 {job_id} 执行失败: {str(e)}", job_id)
        raise
```

## 5. API 路由集成

### 5.1 main.py 修改

```python
from app.api.websocket import websocket_manager

app = FastAPI(...)

# 注册 WebSocket 路由
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.websocket_endpoint(websocket)

# 其他路由...
```

### 5.2 endpoints.py 修改

```python
from app.api.websocket import websocket_manager

@router.post("/task/run", tags=["任务执行"])
async def run_tasks(...):
    # 创建执行器时传入 websocket_manager
    executor = PlaywrightExecutor(ws_manager=websocket_manager)
    
    # 执行任务...
    for job in jobs:
        result = await executor.execute_job(job.id, db)
        results.append(result)
    
    return {...}
```

## 6. 错误处理与边界情况

### 6.1 连接管理

| 场景 | 处理策略 |
|------|----------|
| 客户端主动断开 | `disconnect()` 方法从集合中移除 |
| 客户端异常断开 | 广播时捕获异常并清理 |
| 服务端重启 | 所有连接断开，客户端需重连 |
| 无客户端连接 | 广播空操作，不影响任务执行 |

### 6.2 任务执行异常

- 任务失败时推送 `type: "log", level: "error"` 消息
- 执行器崩溃不影响 WebSocket 连接（独立的异步上下文）
- 异常堆栈不包含在推送消息中（仅记录到服务端日志）

### 6.3 并发场景

- **多任务串行执行**：所有客户端收到所有任务的消息
- **消息隔离**：每条消息包含 `job_id`，前端可按需过滤
- **无竞态条件**：`set` 的添加/移除是原子操作

### 6.4 性能考虑

- **消息频率**：中粒度推送（每任务 8-10 条），不会造成性能瓶颈
- **连接数限制**：无硬限制，依赖操作系统和内存
- **未来优化**：如需大规模部署，可引入 Redis Pub/Sub 或消息队列

## 7. 测试策略

### 7.1 单元测试

- `WebSocketManager.broadcast()` 的异常处理
- 执行器的 `_broadcast_progress()` 和 `_broadcast_log()` 方法
- `ws_manager=None` 时的向后兼容性

### 7.2 集成测试

- WebSocket 连接建立和断开
- 多客户端同时连接
- 任务执行过程中的消息推送

### 7.3 手动测试（验收标准）

1. 使用浏览器开发者工具或 `wscat` 连接 `ws://127.0.0.1:8000/ws`
2. 调用 `/task/run` 触发任务执行
3. 验证收到的 JSON 消息格式符合规范
4. 验证消息顺序和内容正确

**示例测试脚本**：
```javascript
// 浏览器控制台
const ws = new WebSocket('ws://127.0.0.1:8000/ws');
ws.onmessage = (event) => {
    console.log('收到消息:', JSON.parse(event.data));
};
```

## 8. 实现清单

### 8.1 新增文件

- `app/api/websocket.py`：WebSocket 管理器和路由

### 8.2 修改文件

- `app/services/executor.py`：
  - 构造函数接收 `ws_manager` 参数
  - 添加 `_broadcast_progress()` 和 `_broadcast_log()` 辅助方法
  - 在 8-10 个关键节点插入广播调用
  
- `app/main.py`：
  - 导入 `websocket_manager`
  - 注册 WebSocket 路由 `/ws`
  
- `app/api/endpoints.py`：
  - 导入 `websocket_manager`
  - 在 `/task/run` 中实例化执行器时传入 `ws_manager`

### 8.3 依赖项

无需新增依赖，FastAPI 已内置 WebSocket 支持。

## 9. 后续扩展

### 9.1 短期优化

- 添加心跳机制（ping/pong）检测僵尸连接
- 支持客户端订阅特定 `job_id` 的消息（减少无关消息）

### 9.2 长期演进

- 支持 Server-Sent Events (SSE) 作为备选方案
- 引入 Redis Pub/Sub 支持分布式部署
- 消息持久化（可选），支持历史回放

## 10. 参考资料

- PRD 3.6 节：前端实时监控看板
- FastAPI WebSocket 文档：https://fastapi.tiangolo.com/advanced/websockets/
- RFC 6455：The WebSocket Protocol
