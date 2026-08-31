# WebSocket 手动测试指南

## 前置条件
1. 启动应用：`uvicorn app.main:app --reload`
2. 确保数据库中有待处理的任务

## 测试步骤

### 测试 1: 基本连接
1. 用浏览器打开 `tests/manual/test_websocket_client.html`
2. 点击"连接 WebSocket"按钮
3. **验证**: 状态显示"已连接"，消息区显示"连接成功"

### 测试 2: 任务执行监控
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

### 测试 3: 多客户端广播
1. 打开两个浏览器标签，都加载 `test_websocket_client.html`
2. 两个标签都点击"连接 WebSocket"
3. 调用 `/task/run` 触发任务
4. **验证**: 两个客户端都收到相同的消息

### 测试 4: 断线重连
1. 连接 WebSocket
2. 点击"断开连接"
3. 点击"连接 WebSocket"重新连接
4. 调用 `/task/run`
5. **验证**: 重连后仍能正常收到消息

### 测试 5: 消息格式验证
1. 连接 WebSocket 并触发任务
2. 打开浏览器开发者工具 - Network - WS 标签
3. **验证**: 所有消息都符合以下格式：
   - Progress: `{"type": "progress", "job_id": 123, "message": "...", "timestamp": "..."}`
   - Log: `{"type": "log", "level": "info", "message": "...", "job_id": 123, "timestamp": "..."}`

## 预期结果
- 所有测试通过
- 消息实时推送，无延迟
- 消息格式正确
- 多客户端同步接收
