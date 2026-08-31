# WebSocket 实时监控使用指南

本文档说明如何连接和使用平台的 WebSocket 接口，实现任务执行过程的实时监控。

## 1. 概述

### 1.1 功能说明

WebSocket 接口提供任务执行过程中的实时状态推送，包括：
- **进度更新**：任务开始、执行中、完成的进度信息
- **日志推送**：任务执行过程中的关键操作日志
- **错误通知**：任务执行失败时的错误信息

### 1.2 适用场景

- 前端实时监控看板
- 任务执行进度展示
- 调试和运维监控
- 多客户端同时监控

## 2. 连接方式

### 2.1 WebSocket 端点

```
ws://localhost:8000/ws
```

生产环境请替换为实际的服务器地址和协议（wss://）。

### 2.2 JavaScript 连接示例

```javascript
// 创建 WebSocket 连接
const ws = new WebSocket('ws://localhost:8000/ws');

// 连接成功
ws.onopen = () => {
    console.log('WebSocket 连接已建立');
};

// 接收消息
ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    console.log('收到消息:', message);
    
    // 根据消息类型处理
    switch (message.type) {
        case 'progress':
            handleProgress(message);
            break;
        case 'log':
            handleLog(message);
            break;
        default:
            console.warn('未知消息类型:', message.type);
    }
};

// 连接关闭
ws.onclose = (event) => {
    console.log('WebSocket 连接已关闭', event.code, event.reason);
    // 可选：实现自动重连逻辑
};

// 连接错误
ws.onerror = (error) => {
    console.error('WebSocket 错误:', error);
};
```

### 2.3 Python 连接示例

使用 `websockets` 库：

```python
import asyncio
import json
import websockets

async def monitor_tasks():
    uri = "ws://localhost:8000/ws"
    
    async with websockets.connect(uri) as websocket:
        print("WebSocket 连接已建立")
        
        async for message in websocket:
            data = json.loads(message)
            print(f"收到消息: {data}")
            
            if data['type'] == 'progress':
                print(f"进度: {data['message']}")
            elif data['type'] == 'log':
                print(f"日志 [{data['level']}]: {data['message']}")

if __name__ == "__main__":
    asyncio.run(monitor_tasks())
```

安装依赖：
```bash
pip install websockets
```

## 3. 消息格式

### 3.1 进度消息（Progress）

任务执行过程中的关键进度节点推送。

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

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定为 `"progress"` |
| `job_id` | int | 是 | 任务 ID |
| `message` | string | 是 | 人类可读的进度描述 |
| `progress` | object | 否 | 进度信息，包含 `current` 和 `total` |
| `timestamp` | string | 是 | ISO 8601 格式时间戳 |

**示例场景**：
- 任务开始：`"开始执行任务 123"`
- 数据提取：`"正在处理第 3 页"` + `{"current": 3, "total": 10}`
- 任务完成：`"任务 123 执行成功，提取 50 条数据"`

### 3.2 日志消息（Log）

任务执行过程中的操作日志和错误信息。

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

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `type` | string | 是 | 固定为 `"log"` |
| `level` | string | 是 | 日志级别：`"info"` / `"warning"` / `"error"` |
| `message` | string | 是 | 日志内容 |
| `job_id` | int | 否 | 关联的任务 ID |
| `timestamp` | string | 是 | ISO 8601 格式时间戳 |

**日志级别说明**：
- `info`：正常操作日志（浏览器启动、表单填充、数据提取等）
- `warning`：警告信息（性能问题、异常恢复等）
- `error`：错误信息（任务失败、异常终止等）

## 4. 消息推送节点

任务执行过程中，系统会在以下关键节点推送消息：

| 序号 | 节点 | 消息类型 | 示例内容 |
|------|------|----------|----------|
| 1 | 任务开始 | progress | `"开始执行任务 123"` |
| 2 | 浏览器启动完成 | log (info) | `"浏览器启动成功（登录态: taobao）"` |
| 3 | 表单填充完成 | log (info) | `"表单填充完成"` |
| 4 | 提交按钮点击 | log (info) | `"点击提交按钮"` |
| 5 | 结果页面加载完成 | log (info) | `"结果页面加载完成"` |
| 6 | 每页数据提取完成 | progress | `"正在处理第 3 页"` + 当前进度 |
| 7 | 翻页动作 | log (info) | `"点击下一页按钮"` |
| 8 | 任务成功完成 | progress | `"任务 123 执行成功，提取 50 条数据"` |
| 9 | 任务失败 | log (error) | `"任务 123 执行失败: <错误信息>"` |

**特点**：
- 中粒度推送：每个任务约 8-10 条消息
- 包含关键操作节点，不推送过于细节的步骤
- 消息顺序与任务执行流程一致

## 5. 多客户端支持

### 5.1 广播机制

WebSocket 接口采用广播模式：
- 所有连接的客户端都会收到所有任务的消息
- 每条消息包含 `job_id` 字段，客户端可按需过滤

### 5.2 消息过滤示例

```javascript
// 仅处理特定任务的消息
const targetJobId = 123;

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    // 过滤：仅处理目标任务的消息
    if (message.job_id === targetJobId) {
        console.log(`任务 ${targetJobId} 的消息:`, message);
        updateUI(message);
    }
};
```

### 5.3 多任务监控示例

```javascript
// 同时监控多个任务
const taskMonitors = new Map(); // job_id -> 监控器对象

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    const jobId = message.job_id;
    
    if (!taskMonitors.has(jobId)) {
        // 创建新的任务监控器
        taskMonitors.set(jobId, {
            jobId,
            messages: [],
            startTime: new Date()
        });
    }
    
    const monitor = taskMonitors.get(jobId);
    monitor.messages.push(message);
    
    // 更新 UI
    updateTaskPanel(monitor);
};
```

## 6. 错误处理

### 6.1 连接断开处理

```javascript
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 5;
const RECONNECT_DELAY = 3000; // 3 秒

function connectWebSocket() {
    const ws = new WebSocket('ws://localhost:8000/ws');
    
    ws.onopen = () => {
        console.log('WebSocket 连接成功');
        reconnectAttempts = 0; // 重置重连次数
    };
    
    ws.onclose = (event) => {
        console.log('WebSocket 连接关闭:', event.code);
        
        // 自动重连
        if (reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
            reconnectAttempts++;
            console.log(`尝试重连 (${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})...`);
            setTimeout(connectWebSocket, RECONNECT_DELAY);
        } else {
            console.error('达到最大重连次数，停止重连');
        }
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket 错误:', error);
    };
    
    return ws;
}

const ws = connectWebSocket();
```

### 6.2 消息解析错误处理

```javascript
ws.onmessage = (event) => {
    try {
        const message = JSON.parse(event.data);
        
        // 验证消息格式
        if (!message.type || !message.timestamp) {
            console.warn('消息格式不完整:', message);
            return;
        }
        
        // 处理消息
        handleMessage(message);
        
    } catch (error) {
        console.error('消息解析失败:', error, event.data);
    }
};
```

### 6.3 服务端重启处理

服务端重启时，所有 WebSocket 连接会断开。客户端应实现自动重连机制（见 6.1）。

## 7. 心跳机制

### 7.1 客户端心跳（可选）

虽然当前服务端未实现心跳要求，但建议客户端主动发送心跳以检测连接状态：

```javascript
let heartbeatInterval;

ws.onopen = () => {
    console.log('WebSocket 连接成功');
    
    // 每 30 秒发送一次心跳（可选）
    heartbeatInterval = setInterval(() => {
        if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
        }
    }, 30000);
};

ws.onclose = () => {
    console.log('WebSocket 连接关闭');
    clearInterval(heartbeatInterval);
};
```

**注意**：当前服务端会忽略客户端发送的消息，心跳仅用于检测连接状态。

## 8. 性能考虑

### 8.1 消息频率

- **中粒度推送**：每个任务约 8-10 条消息
- **消息大小**：单条消息约 200-500 字节（JSON 格式）
- **推送间隔**：取决于任务执行速度，典型间隔 1-5 秒

### 8.2 连接数限制

- 当前版本无硬连接数限制
- 实际限制取决于服务器资源（内存、网络）
- 建议单服务器连接数不超过 1000

### 8.3 大规模部署建议

如需支持大量客户端，可考虑以下优化：
- 引入 Redis Pub/Sub 实现分布式消息推送
- 使用负载均衡器（支持 WebSocket 的 Nginx/HAProxy）
- 实现消息队列（RabbitMQ/Kafka）缓冲高峰流量

## 9. 故障排查

### 9.1 无法建立连接

**症状**：`WebSocket.onerror` 触发，连接无法建立

**排查步骤**：
1. 检查服务端是否启动：`curl http://localhost:8000/`
2. 检查防火墙设置：确保 8000 端口可访问
3. 检查协议：确认使用 `ws://`（非 HTTPS）或 `wss://`（HTTPS）
4. 检查浏览器控制台：查看详细错误信息

### 9.2 收不到消息

**症状**：连接成功，但 `ws.onmessage` 不触发

**排查步骤**：
1. 确认是否有任务正在执行：调用 `/task/run` 触发任务
2. 检查服务端日志：查看是否有消息广播记录
3. 验证消息过滤逻辑：确认没有错误过滤掉消息
4. 使用开发者工具：查看 WebSocket 面板的消息记录

### 9.3 连接频繁断开

**症状**：`ws.onclose` 频繁触发

**排查步骤**：
1. 检查网络稳定性：使用 `ping` 测试服务器连通性
2. 检查服务端资源：查看 CPU/内存使用率
3. 检查代理/负载均衡器设置：确认支持 WebSocket 长连接
4. 增加超时时间：配置代理/负载均衡器的 WebSocket 超时

### 9.4 调试工具

**浏览器开发者工具**：
1. 打开 Chrome DevTools（F12）
2. 切换到 "Network" 标签
3. 筛选 "WS"（WebSocket）
4. 查看连接状态和消息记录

**命令行工具**：
```bash
# 使用 wscat 连接（需要安装：npm install -g wscat）
wscat -c ws://localhost:8000/ws

# 使用 websocat 连接（需要安装：cargo install websocat）
websocat ws://localhost:8000/ws
```

## 10. 完整示例

### 10.1 简单监控页面

```html
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>任务监控</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        #status { padding: 10px; margin-bottom: 10px; border-radius: 5px; }
        .connected { background-color: #d4edda; color: #155724; }
        .disconnected { background-color: #f8d7da; color: #721c24; }
        #messages { height: 400px; overflow-y: auto; border: 1px solid #ccc; padding: 10px; }
        .message { padding: 5px; margin: 5px 0; border-radius: 3px; }
        .progress { background-color: #d1ecf1; }
        .log-info { background-color: #d4edda; }
        .log-error { background-color: #f8d7da; }
    </style>
</head>
<body>
    <h1>任务执行监控</h1>
    <div id="status" class="disconnected">未连接</div>
    <div id="messages"></div>

    <script>
        const statusDiv = document.getElementById('status');
        const messagesDiv = document.getElementById('messages');
        
        // 连接 WebSocket
        const ws = new WebSocket('ws://localhost:8000/ws');
        
        ws.onopen = () => {
            statusDiv.textContent = 'WebSocket 已连接';
            statusDiv.className = 'connected';
        };
        
        ws.onmessage = (event) => {
            const message = JSON.parse(event.data);
            
            // 创建消息元素
            const messageDiv = document.createElement('div');
            messageDiv.className = 'message';
            
            // 根据消息类型设置样式
            if (message.type === 'progress') {
                messageDiv.classList.add('progress');
                messageDiv.textContent = `[进度] 任务 ${message.job_id}: ${message.message}`;
                
                if (message.progress) {
                    messageDiv.textContent += ` (${message.progress.current}/${message.progress.total})`;
                }
            } else if (message.type === 'log') {
                messageDiv.classList.add(`log-${message.level}`);
                messageDiv.textContent = `[${message.level.toUpperCase()}] ${message.message}`;
            }
            
            // 添加时间戳
            const time = new Date(message.timestamp).toLocaleTimeString();
            messageDiv.textContent += ` - ${time}`;
            
            // 添加到页面
            messagesDiv.appendChild(messageDiv);
            messagesDiv.scrollTop = messagesDiv.scrollHeight;
        };
        
        ws.onclose = () => {
            statusDiv.textContent = 'WebSocket 已断开';
            statusDiv.className = 'disconnected';
        };
        
        ws.onerror = (error) => {
            console.error('WebSocket 错误:', error);
        };
    </script>
</body>
</html>
```

### 10.2 使用方法

1. 启动后端服务：
```bash
uvicorn app.main:app --reload
```

2. 打开监控页面（保存为 `monitor.html` 并在浏览器中打开）

3. 触发任务执行：
```bash
curl -X POST http://localhost:8000/task/run \
  -H "Content-Type: application/json" \
  -d '{
    "task_ids": [1, 2, 3]
  }'
```

4. 在监控页面中查看实时消息推送

## 11. 参考资料

- [WebSocket 协议（RFC 6455）](https://datatracker.ietf.org/doc/html/rfc6455)
- [FastAPI WebSocket 文档](https://fastapi.tiangolo.com/advanced/websockets/)
- [MDN WebSocket API](https://developer.mozilla.org/en-US/docs/Web/API/WebSocket)

## 12. 常见问题

**Q: WebSocket 和 HTTP 轮询有什么区别？**

A: WebSocket 是全双工通信协议，服务端可以主动推送消息，延迟低、效率高。HTTP 轮询需要客户端定时请求，延迟高、资源消耗大。

**Q: 如何知道某个任务的执行进度？**

A: 连接 WebSocket 后，每条消息都包含 `job_id` 字段，客户端可以根据 `job_id` 过滤消息，并根据 `progress` 字段计算进度百分比。

**Q: 服务端重启后历史消息会丢失吗？**

A: 是的。当前版本仅提供实时推送，不持久化消息。如需历史回放，请自行实现消息存储或等待后续版本支持。

**Q: 可以向服务端发送消息吗？**

A: 当前版本为单向推送，服务端会忽略客户端发送的消息。未来版本可能支持双向交互（如任务控制）。

**Q: 如何在生产环境中使用？**

A: 生产环境建议使用 `wss://`（WebSocket over TLS）并配置反向代理（Nginx/HAProxy），确保连接安全和稳定性。
