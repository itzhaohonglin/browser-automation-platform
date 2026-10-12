# 配置文件更新指南

## 生产部署推荐配置

### 推荐值（中等偏严格）
```bash
REQUEST_RATE_LIMIT_ENABLED=true
REQUEST_RATE_LIMIT_INTERVAL_SECONDS=6
```

**说明**：
- 6秒间隔 = 每分钟10个请求
- 适合政府网站、医保局等严格的站点
- 10条详情列表约需1分钟完成
- 既安全又不会太慢

### 其他推荐场景

#### 场景1：非常严格的政府网站
```bash
REQUEST_RATE_LIMIT_ENABLED=true
REQUEST_RATE_LIMIT_INTERVAL_SECONDS=10
```
- 每分钟6个请求
- 最安全，适合反爬严格的网站

#### 场景2：一般网站（平衡速度）
```bash
REQUEST_RATE_LIMIT_ENABLED=true
REQUEST_RATE_LIMIT_INTERVAL_SECONDS=5
```
- 每分钟12个请求
- 默认推荐值

#### 场景3：内部系统（测试环境）
```bash
REQUEST_RATE_LIMIT_ENABLED=false
REQUEST_RATE_LIMIT_INTERVAL_SECONDS=5
```
- 禁用限流，全速执行

---

## 需要更新的配置文件

### 1. 主项目环境变量模板

**文件路径**：
- `.env.example`
- `.env.template`（如果存在）

**在 MAX_WORKERS 配置后添加**：

```bash
# 并发控制
MAX_WORKERS=3
WORKER_MEMORY_LIMIT_MB=512

# ========================================
# 请求级限流配置（全局默认）
# ========================================
# 控制任务执行过程中每个HTTP请求的频率
# 适用场景：防止因请求过快被目标网站封禁

# 是否启用请求级限流（true/false）
# 生产环境推荐：true
REQUEST_RATE_LIMIT_ENABLED=true

# 每个HTTP请求之间的间隔时间（秒）
# 生产环境推荐：6（每分钟10个请求）
REQUEST_RATE_LIMIT_INTERVAL_SECONDS=6

# 推荐配置：
# - 严格限流（政府网站）：10秒
# - 中等限流（一般网站）：6秒
# - 宽松限流（内部系统）：3秒
#
# 注意：
# 1. 这是全局默认配置，对所有采集配置生效
# 2. 可以在数据库中为特定配置覆盖此设置
# 3. 修改后需要重启服务才能生效
# 4. 列表详情采集：每个详情都是一个请求
#    示例：10条详情 × 6秒 = 约1分钟

# ========================================
# 智能重试配置
# ========================================
```

---

### 2. 打包版本环境变量模板

**文件路径**：
- `dist/browser-automation-platform/.env.example`
- `dist/browser-automation-platform/.env.template`
- `dist/browser-automation-platform/_internal/.env.example`
- `dist/browser-automation-platform/_internal/.env.template`

**添加相同内容**（同上）

---

### 3. 打包版本安装脚本

**文件路径**：`dist/browser-automation-platform/install.bat`

**在配置说明部分（约60-80行）添加**：

```batch
echo    [并发控制] (Optional, default 3)
echo    MAX_WORKERS=3
echo.
echo    [请求级限流] (Optional, RECOMMENDED for strict websites)
echo    REQUEST_RATE_LIMIT_ENABLED=true
echo    REQUEST_RATE_LIMIT_INTERVAL_SECONDS=6  # Seconds between each HTTP request
echo.
echo    Recommended: 6-10 seconds for government websites
echo    Note: Each detail click is one HTTP request
echo.
echo    [智能重试] (Optional)
```

---

## 快速更新命令

### Windows 批处理脚本

创建 `update_env_templates.bat`：

```batch
@echo off
echo Updating environment variable templates...

REM 主项目
echo.>> .env.example
echo # ========================================>> .env.example
echo # 请求级限流配置（全局默认）>> .env.example
echo # ========================================>> .env.example
echo REQUEST_RATE_LIMIT_ENABLED=true>> .env.example
echo REQUEST_RATE_LIMIT_INTERVAL_SECONDS=6>> .env.example
echo.>> .env.example

REM 打包版本
echo.>> dist\browser-automation-platform\.env.example
echo # ========================================>> dist\browser-automation-platform\.env.example
echo # 请求级限流配置>> dist\browser-automation-platform\.env.example
echo # ========================================>> dist\browser-automation-platform\.env.example
echo REQUEST_RATE_LIMIT_ENABLED=true>> dist\browser-automation-platform\.env.example
echo REQUEST_RATE_LIMIT_INTERVAL_SECONDS=6>> dist\browser-automation-platform\.env.example

echo Done! Please review the changes.
pause
```

---

## 你的 .env 文件配置

### 立即可用的配置

在你的 `.env` 文件中添加：

```bash
# 请求级限流（生产推荐配置）
REQUEST_RATE_LIMIT_ENABLED=true
REQUEST_RATE_LIMIT_INTERVAL_SECONDS=6
```

然后重启服务：
```bash
# 停止服务
Ctrl+C

# 重新启动
python -m app.main
# 或
startup.bat
```

---

## 验证配置生效

### 1. 检查启动日志

启动服务后，执行任务时应该看到：
```
[限流] 已启用请求级限流: 每 6 秒一个请求（来源: 全局默认）
```

### 2. 观察任务执行

执行任务时，日志会显示：
```
[INFO] 访问页面...
[限流] 点击查询 - 等待 5.2 秒
[INFO] 查询完成
[详情] 处理第 1/10 条数据
[限流] 点击详情 - 等待 5.8 秒
[详情] 第 1 条详情提取成功
[详情] 处理第 2/10 条数据
[限流] 点击详情 - 等待 5.5 秒
...
```

### 3. 计算耗时

- 10条详情 × 6秒 = 约60秒
- 加上页面加载时间 ≈ 70-80秒完成

---

## 性能对比

### 不同配置的耗时对比（10条详情）

| 配置 | 间隔 | 限流耗时 | 总耗时（约） | 适用场景 |
|------|------|---------|------------|---------|
| 严格 | 10秒 | 100秒 | 2分钟 | 政府网站 |
| **推荐** | **6秒** | **60秒** | **1.5分钟** | **大部分场景** |
| 中等 | 5秒 | 50秒 | 1分钟 | 一般网站 |
| 宽松 | 3秒 | 30秒 | 40秒 | 内部系统 |
| 禁用 | 0秒 | 0秒 | 10秒 | 测试环境 |

---

## 调优建议

### 如果被封禁
```bash
# 增加间隔
REQUEST_RATE_LIMIT_INTERVAL_SECONDS=10
```

### 如果速度太慢
```bash
# 减少间隔（风险自负）
REQUEST_RATE_LIMIT_INTERVAL_SECONDS=4
```

### 针对特定网站

保持 `.env` 的全局配置不变，在数据库中为特定配置覆盖：

```sql
-- 严格的政府网站
UPDATE crawler_configs
SET extraction_config = JSON_MODIFY(
    ISNULL(extraction_config, '{}'),
    '$.request_rate_limit',
    JSON_QUERY('{"enabled": true, "interval_seconds": 10}')
)
WHERE config_name LIKE '%政府%' OR config_name LIKE '%医保%';

-- 宽松的内部系统
UPDATE crawler_configs
SET extraction_config = JSON_MODIFY(
    ISNULL(extraction_config, '{}'),
    '$.request_rate_limit',
    JSON_QUERY('{"enabled": true, "interval_seconds": 3}')
)
WHERE config_name LIKE '%内部%';
```

---

## 总结

### ✅ 立即执行

1. **更新你的 .env 文件**：
   ```bash
   REQUEST_RATE_LIMIT_ENABLED=true
   REQUEST_RATE_LIMIT_INTERVAL_SECONDS=6
   ```

2. **重启服务**

3. **观察日志验证**

### 📝 后续完善（可选）

1. 手动更新 `.env.example` 模板文件
2. 更新打包版本的配置文件
3. 根据实际效果调整 `interval_seconds`

**推荐的生产配置已确定：`interval_seconds=6`** ✅
