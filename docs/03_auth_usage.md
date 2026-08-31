# 登录态管理功能使用说明

## 功能概述

实现了 PRD 3.2 章节的"看板UI驱动登录态"功能，支持多站点登录态隔离管理。

## API 接口

### 1. 启动登录会话 `POST /auth/start`

拉起有头浏览器，跳转到登录页面供管理员手动登录。

**请求参数：**
- `profile` (必填): 登录态标识，如 `taobao`、`jd`、`test`
- `login_url` (可选): 登录页面URL，默认为 `https://www.baidu.com`

**示例：**
```bash
curl -X POST "http://127.0.0.1:8000/auth/start?profile=test&login_url=https://www.baidu.com"
```

**返回：**
```json
{
  "status": "success",
  "message": "浏览器已打开，请在窗口中完成登录操作",
  "profile": "test",
  "login_url": "https://www.baidu.com"
}
```

**说明：** 调用此接口后，系统会自动打开浏览器窗口并跳转到指定的登录页面。

---

### 2. 保存登录态 `POST /auth/save`

在浏览器中完成登录后，调用此接口保存登录态到文件。

**请求参数：**
- `profile` (必填): 登录态标识，必须与 `/auth/start` 中使用的相同

**示例：**
```bash
curl -X POST "http://127.0.0.1:8000/auth/save?profile=test"
```

**返回：**
```json
{
  "status": "success",
  "message": "test 登录态已成功保存",
  "file_path": "auth_files/auth_test.json",
  "profile": "test"
}
```

**说明：** 
- 登录态会保存到 `auth_files/auth_{profile}.json` 文件中
- 保存成功后浏览器会自动关闭
- 文件包含 cookies、localStorage 等登录信息

---

### 3. 查看登录态状态 `GET /auth/status`

查看所有已保存的登录态文件和当前活跃的登录会话。

**示例：**
```bash
curl "http://127.0.0.1:8000/auth/status"
```

**返回：**
```json
{
  "saved_profiles": [
    {
      "profile": "test",
      "file_path": "auth_files/auth_test.json",
      "status": "saved"
    }
  ],
  "active_sessions": [],
  "total_saved": 1,
  "total_active": 0
}
```

---

### 4. 关闭活跃会话 `DELETE /auth/session/{profile}`

关闭指定 profile 的浏览器会话（不保存登录态）。

**示例：**
```bash
curl -X DELETE "http://127.0.0.1:8000/auth/session/test"
```

**使用场景：** 如果不小心打开了浏览器但不想保存，可以调用此接口关闭。

---

### 5. 删除登录态文件 `DELETE /auth/file/{profile}`

删除已保存的登录态文件。

**示例：**
```bash
curl -X DELETE "http://127.0.0.1:8000/auth/file/test"
```

**使用场景：** 清理过期或不需要的登录态。

---

## 完整使用流程

### 步骤 1: 启动浏览器
```bash
curl -X POST "http://127.0.0.1:8000/auth/start?profile=taobao&login_url=https://login.taobao.com"
```

此时电脑会自动打开浏览器窗口，跳转到淘宝登录页面。

### 步骤 2: 手动登录
在打开的浏览器窗口中：
1. 输入账号密码
2. 完成验证码验证
3. 确认登录成功

### 步骤 3: 保存登录态
```bash
curl -X POST "http://127.0.0.1:8000/auth/save?profile=taobao"
```

浏览器会自动关闭，登录态保存到 `auth_files/auth_taobao.json`。

### 步骤 4: 验证保存结果
```bash
curl "http://127.0.0.1:8000/auth/status"
```

确认 `saved_profiles` 列表中包含 `taobao`。

---

## 多站点管理示例

可以同时管理多个站点的登录态：

```bash
# 保存淘宝登录态
curl -X POST "http://127.0.0.1:8000/auth/start?profile=taobao&login_url=https://login.taobao.com"
# ... 手动登录 ...
curl -X POST "http://127.0.0.1:8000/auth/save?profile=taobao"

# 保存京东登录态
curl -X POST "http://127.0.0.1:8000/auth/start?profile=jd&login_url=https://passport.jd.com"
# ... 手动登录 ...
curl -X POST "http://127.0.0.1:8000/auth/save?profile=jd"
```

最终 `auth_files/` 目录结构：
```
auth_files/
├── auth_taobao.json
└── auth_jd.json
```

---

## 文件结构

登录态文件 (`auth_{profile}.json`) 包含：
- **cookies**: 浏览器 cookies 数组
- **origins**: localStorage 和 sessionStorage 数据
- **用途**: Playwright 可以使用此文件恢复登录状态

示例内容：
```json
{
  "cookies": [
    {
      "name": "session_id",
      "value": "xxxxx",
      "domain": ".example.com",
      "path": "/",
      "expires": 1234567890,
      "httpOnly": true,
      "secure": true
    }
  ],
  "origins": []
}
```

---

## 技术实现

### 后端架构
- **`app/api/endpoints.py`**: API 路由定义
- **`app/services/auth_manager.py`**: Playwright 浏览器控制逻辑
- **全局单例**: `auth_manager` 管理所有活跃会话

### 关键特性
1. **多站点隔离**: 每个 profile 独立存储，互不干扰
2. **会话管理**: 支持同时打开多个浏览器会话
3. **自动清理**: 保存成功后自动关闭浏览器
4. **错误处理**: 启动失败时自动清理资源

### Windows 兼容性
代码已适配 Windows 平台的 asyncio 事件循环策略：
```python
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
```

---

## 验收结果 ✅

所有验收标准均已通过：

- [x] POST `/auth/start?profile=test` 可以自动打开浏览器
- [x] 浏览器窗口跳转到指定 URL
- [x] POST `/auth/save?profile=test` 成功保存登录态
- [x] `auth_files/auth_test.json` 文件正常生成
- [x] 文件内容包含完整的 cookies 信息
- [x] API 文档在 `/docs` 中正常展示

---

## Swagger UI 访问

访问 http://127.0.0.1:8000/docs 可以在线测试所有接口。

![Swagger UI](https://via.placeholder.com/800x400?text=Swagger+UI+Screenshot)

---

## 下一步开发

登录态管理功能已完成，后续可以开发：

1. **数据库模型**: 创建 `crawler_configs` 表存储 `login_url`
2. **执行器集成**: 在 `executor.py` 中使用保存的登录态
3. **前端看板**: 可视化登录态管理界面
4. **过期检测**: 自动检测登录态是否过期

---

## 常见问题

**Q: 浏览器没有自动打开？**  
A: 检查是否安装了 Playwright 浏览器驱动：`playwright install chromium`

**Q: 提示 "未找到活跃的登录会话"？**  
A: 确保先调用 `/auth/start` 打开浏览器，然后再调用 `/auth/save`

**Q: 如何更新已有的登录态？**  
A: 直接调用 `/auth/start` 会覆盖旧会话，登录后再次保存即可

**Q: 登录态文件可以手动编辑吗？**  
A: 不建议。文件由 Playwright 自动生成，格式固定，手动编辑可能导致无法使用
