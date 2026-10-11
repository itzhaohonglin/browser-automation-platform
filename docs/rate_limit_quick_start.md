# 限流功能快速使用指南

## 场景1：基础使用 - 全局限流

### 步骤1：配置限流参数

编辑 `.env` 文件：

```bash
# 启用限流
RATE_LIMIT_ENABLED=true

# 时间窗口：60分钟
RATE_LIMIT_WINDOW_MINUTES=60

# 窗口内最多执行50个任务（严格限流）
RATE_LIMIT_MAX_TASKS=50

# 全局限流模式
RATE_LIMIT_PER_CONFIG=false
```

### 步骤2：重启应用

```bash
# 停止应用（Ctrl+C）
# 重新启动
uvicorn app.main:app --reload
```

### 步骤3：验证配置

```bash
# 查询限流配置
curl http://localhost:8000/api/rate-limit/config

# 预期响应：
{
  "success": true,
  "data": {
    "enabled": true,
    "window_minutes": 60,
    "max_tasks": 50,
    "per_config": false
  }
}
```

### 步骤4：查看限流状态

```bash
# 查询当前限流状态
curl http://localhost:8000/api/rate-limit/status

# 响应示例：
{
  "success": true,
  "data": {
    "enabled": true,
    "window_minutes": 60,
    "max_tasks": 50,
    "current_count": 0,      # 当前窗口内已执行0个任务
    "remaining": 50,         # 还可以执行50个任务
    "utilization": "0/50 (0.0%)"
  }
}
```

### 步骤5：提交任务并观察限流

```bash
# 假设你有配置ID=44的采集任务
# 提交60个任务（超过限流上限50）

# 方法1：通过API批量创建
curl -X POST http://localhost:8000/api/jobs/batch \
  -H "Content-Type: application/json" \
  -d '{
    "config_id": 44,
    "jobs": [
      {"query_params": {"keyword": "test1"}},
      {"query_params": {"keyword": "test2"}},
      ... （共60个）
    ]
  }'

# 方法2：通过数据库直接插入
# （参考 scripts/batch_import_registration_jobs.py）
```

### 步骤6：观察限流效果

```bash
# 等待调度器分发任务（默认每30分钟一次，或等待pending任务被处理）

# 查询限流状态
curl http://localhost:8000/api/rate-limit/status

# 预期响应（执行了50个任务后）：
{
  "success": true,
  "data": {
    "enabled": true,
    "window_minutes": 60,
    "max_tasks": 50,
    "current_count": 50,     # 已达到上限
    "remaining": 0,          # 无剩余配额
    "utilization": "50/50 (100.0%)"
  }
}

# 查看等待时间
curl http://localhost:8000/api/rate-limit/wait-time

# 响应示例：
{
  "success": true,
  "data": {
    "wait_seconds": 3000,    # 需要等待3000秒（50分钟）
    "wait_minutes": 50.0,
    "can_execute_now": false
  }
}
```

### 步骤7：查看日志

打开应用日志，你会看到类似信息：

```
INFO - 任务 #61 (config_id=44) 因限流跳过，需等待 3000 秒
INFO - 达到全局限流上限: 50/50 任务在 60 分钟内
```

---

## 场景2：多站点采集 - 按配置限流

### 适用场景

- 同时采集多个不同网站
- 每个网站有不同的访问限制
- 需要每个配置独立计算限流配额

### 配置示例

```bash
# 启用限流
RATE_LIMIT_ENABLED=true

# 时间窗口：60分钟
RATE_LIMIT_WINDOW_MINUTES=60

# 每个配置每小时最多100个任务
RATE_LIMIT_MAX_TASKS=100

# 按配置限流（关键配置）
RATE_LIMIT_PER_CONFIG=true
```

### 效果

- **配置44（淘宝）**：每小时最多100个任务
- **配置45（京东）**：每小时最多100个任务
- **配置46（NHSA）**：每小时最多100个任务

它们互不影响，各自独立计算。

### 查询特定配置的限流状态

```bash
# 查询配置44的限流状态
curl http://localhost:8000/api/rate-limit/status?config_id=44

# 查询配置45的限流状态
curl http://localhost:8000/api/rate-limit/status?config_id=45
```

---

## 场景3：短时间精细控制

### 适用场景

- 目标网站对短期内的访问频率有严格限制
- 需要精确控制每10分钟的访问量

### 配置示例

```bash
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=10    # 10分钟窗口
RATE_LIMIT_MAX_TASKS=20         # 每10分钟20个任务
RATE_LIMIT_PER_CONFIG=false
```

### 效果

- 每10分钟最多执行20个任务
- 相当于每小时120个任务
- 但分布更均匀，避免短时间内大量请求

---

## 场景4：紧急情况 - 重置限流

### 适用场景

- 限流配额已用完，但有紧急任务需要执行
- 测试时需要清空计数器

### 操作步骤

```bash
# 1. 重置所有限流计数器
curl -X POST http://localhost:8000/api/rate-limit/reset

# 响应：
{
  "success": true,
  "message": "已重置所有限流计数器"
}

# 2. 重置特定配置的限流计数器
curl -X POST http://localhost:8000/api/rate-limit/reset?config_id=44

# 响应：
{
  "success": true,
  "message": "已重置配置 44 的限流计数器"
}

# 3. 验证重置结果
curl http://localhost:8000/api/rate-limit/status

# 响应：
{
  "success": true,
  "data": {
    "current_count": 0,      # 已清零
    "remaining": 50,
    "utilization": "0/50 (0.0%)"
  }
}
```

**⚠️ 注意**：重置计数器会立即清空所有历史记录，请谨慎使用！

---

## 场景5：监控和调优

### 定期监控限流使用率

创建一个监控脚本：

```bash
#!/bin/bash
# monitor_rate_limit.sh

while true; do
    echo "==================== $(date) ===================="
    
    # 查询限流状态
    curl -s http://localhost:8000/api/rate-limit/status | \
        python -c "
import sys, json
data = json.load(sys.stdin)['data']
print(f'窗口: {data[\"window_minutes\"]}分钟')
print(f'上限: {data[\"max_tasks\"]}个任务')
print(f'已用: {data[\"current_count\"]}个任务')
print(f'剩余: {data[\"remaining\"]}个任务')
print(f'使用率: {data[\"utilization\"]}')
"
    
    # 每5分钟检查一次
    sleep 300
done
```

运行监控：

```bash
chmod +x monitor_rate_limit.sh
./monitor_rate_limit.sh
```

### 根据监控结果调优

**如果使用率持续 < 50%**：
```bash
# 限流过于宽松，可以增加任务数
RATE_LIMIT_MAX_TASKS=150  # 从100增加到150
```

**如果使用率持续 > 80%**：
```bash
# 接近限流上限，任务会被延迟
RATE_LIMIT_MAX_TASKS=200  # 从100增加到200
# 或者延长时间窗口
RATE_LIMIT_WINDOW_MINUTES=120  # 从60分钟延长到120分钟
```

**如果出现429错误或被封禁**：
```bash
# 限流太宽松，需要降低
RATE_LIMIT_MAX_TASKS=30   # 从100降低到30
RATE_LIMIT_WINDOW_MINUTES=60
```

---

## 场景6：与并发控制结合

### 理解两者的关系

```bash
# 并发控制（短期）
MAX_WORKERS=3  # 同时最多3个任务在执行

# 限流控制（长期）
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100  # 每小时最多100个任务
```

### 计算实际吞吐量

**示例1：并发受限**
```bash
MAX_WORKERS=3
RATE_LIMIT_MAX_TASKS=300
# 假设单任务耗时2分钟

# 理论吞吐量：
# - 并发限制：3个/2分钟 = 1.5个/分钟 = 90个/小时
# - 限流限制：300个/小时
# 实际吞吐量 = min(90, 300) = 90个/小时（受并发限制）
```

**示例2：限流受限**
```bash
MAX_WORKERS=5
RATE_LIMIT_MAX_TASKS=50
# 假设单任务耗时1分钟

# 理论吞吐量：
# - 并发限制：5个/分钟 = 300个/小时
# - 限流限制：50个/小时
# 实际吞吐量 = min(300, 50) = 50个/小时（受限流限制）
```

### 最佳配置建议

```bash
# 平衡配置（推荐）
MAX_WORKERS=3
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=180  # 略高于理论并发吞吐量

# 这样配置的效果：
# - 短期受并发控制（3个同时执行）
# - 长期受限流保护（每小时180个）
# - 两者配合，既保证速度又避免被封
```

---

## 场景7：前端集成（可选）

在监控看板中显示限流状态：

```javascript
// 在 static/index.html 中添加

// 定时查询限流状态
setInterval(async () => {
    const response = await fetch('/api/rate-limit/status');
    const result = await response.json();
    
    if (result.success) {
        const data = result.data;
        
        // 更新UI显示
        document.getElementById('rate-limit-status').innerHTML = `
            <div class="rate-limit-info">
                <span>限流状态: ${data.enabled ? '已启用' : '未启用'}</span>
                <span>时间窗口: ${data.window_minutes}分钟</span>
                <span>使用情况: ${data.utilization}</span>
                <div class="progress-bar">
                    <div class="progress" style="width: ${data.current_count / data.max_tasks * 100}%"></div>
                </div>
            </div>
        `;
    }
}, 30000); // 每30秒更新一次
```

---

## 常见问题

### Q1: 限流会影响正在执行的任务吗？
**A**: 不会。限流只影响任务的分发（pending → processing），已经在执行的任务不受影响。

### Q2: 如果达到限流上限，任务会丢失吗？
**A**: 不会丢失。任务仍然保持 `pending` 状态，等待时间窗口滑动后会自动执行。

### Q3: 如何临时关闭限流？
**A**: 
```bash
# 方法1：修改配置
RATE_LIMIT_ENABLED=false

# 方法2：重置计数器（临时突破）
curl -X POST http://localhost:8000/api/rate-limit/reset
```

### Q4: 限流配置需要重启应用吗？
**A**: 是的，所有 `.env` 配置修改都需要重启应用才能生效。

### Q5: 如何查看限流是否起作用？
**A**: 查看应用日志，搜索 "限流" 或 "rate limit" 关键词：
```bash
# Linux/Mac
tail -f logs/app.log | grep 限流

# Windows
# 直接查看日志文件或使用 findstr
```

---

## 快速参考

### API 端点

| 接口 | 方法 | 说明 | 示例 |
|------|------|------|------|
| `/api/rate-limit/config` | GET | 查询配置 | `curl http://localhost:8000/api/rate-limit/config` |
| `/api/rate-limit/status` | GET | 查询状态 | `curl http://localhost:8000/api/rate-limit/status?config_id=44` |
| `/api/rate-limit/wait-time` | GET | 查询等待时间 | `curl http://localhost:8000/api/rate-limit/wait-time` |
| `/api/rate-limit/reset` | POST | 重置计数器 | `curl -X POST http://localhost:8000/api/rate-limit/reset` |

### 配置参数

| 参数 | 默认值 | 说明 | 推荐值 |
|------|--------|------|--------|
| `RATE_LIMIT_ENABLED` | false | 是否启用 | true |
| `RATE_LIMIT_WINDOW_MINUTES` | 60 | 时间窗口（分钟） | 30-120 |
| `RATE_LIMIT_MAX_TASKS` | 100 | 窗口内最大任务数 | 50-300 |
| `RATE_LIMIT_PER_CONFIG` | false | 按配置限流 | 多站点时true |

---

## 相关文档

- **详细配置指南**: `docs/rate_limit_guide.md`
- **实现原理**: `docs/rate_limit_implementation.md`
- **配置示例**: `docs/env_config_examples.md`
- **项目文档**: `CLAUDE.md`
