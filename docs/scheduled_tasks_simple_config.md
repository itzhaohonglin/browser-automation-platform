# 周期性任务配置指南（简化版）

## 🚀 超简单配置方式

每个任务一个配置项，格式：

```bash
SCHEDULE_CONFIG_<配置ID>=启用状态,间隔分钟,参数JSON
```

---

## 📝 配置示例

### 示例 1：每天执行一次

```bash
# 配置ID 44，启用，每1440分钟（24小时）执行一次
SCHEDULE_CONFIG_44=true,1440,{"registration_no":"滇械注准20192140008"}
```

### 示例 2：每小时执行一次

```bash
# 配置ID 50，启用，每60分钟执行一次
SCHEDULE_CONFIG_50=true,60,{"keyword":"医疗器械"}
```

### 示例 3：禁用任务

```bash
# 配置ID 44，禁用
SCHEDULE_CONFIG_44=false,1440,{"registration_no":"滇械注准20192140008"}
```

### 示例 4：配置多个任务

```bash
# 任务1：每天执行
SCHEDULE_CONFIG_44=true,1440,{"registration_no":"滇械注准20192140008"}

# 任务2：每小时执行
SCHEDULE_CONFIG_50=true,60,{"keyword":"医疗器械"}

# 任务3：每6小时执行
SCHEDULE_CONFIG_55=true,360,{"category":"高值耗材"}
```

### 示例 5：无参数任务

```bash
# 如果任务不需要参数，第三部分留空或传空对象
SCHEDULE_CONFIG_60=true,720,{}
```

---

## 📋 配置格式说明

```bash
SCHEDULE_CONFIG_<ID>=<enabled>,<interval_minutes>,<query_params>
```

| 部分 | 说明 | 示例 |
|------|------|------|
| `<ID>` | 采集配置ID（数字） | `44` |
| `<enabled>` | 是否启用（true/false） | `true` |
| `<interval_minutes>` | 执行间隔（分钟数） | `1440` |
| `<query_params>` | 任务参数（JSON格式） | `{"registration_no":"xxx"}` |

---

## ⏰ 常用时间间隔

| 频率 | 填多少 |
|------|--------|
| 每10分钟 | 10 |
| 每30分钟 | 30 |
| 每小时 | 60 |
| 每6小时 | 360 |
| 每12小时 | 720 |
| 每天 | 1440 |
| 每周 | 10080 |

---

## 🔧 完整的 .env 文件示例

```bash
# ===========================================
# 数据库配置
# ===========================================
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server

# ===========================================
# 应用配置
# ===========================================
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=False
HEADLESS_MODE=True

# ===========================================
# 进程池配置
# ===========================================
MAX_WORKERS=3
WORKER_MEMORY_LIMIT_MB=512

# ===========================================
# 任务调度配置
# ===========================================
DISPATCH_INTERVAL_MINUTES=1
RETRY_INTERVAL_MINUTES=30
MAX_RETRY_COUNT=3

# ===========================================
# 周期性任务调度配置
# ===========================================
SCHEDULE_CHECK_INTERVAL_MINUTES=5
SCHEDULE_FIRST_RUN_DELAY_MINUTES=2

# 周期性任务配置（每个任务一行）
# 格式：SCHEDULE_CONFIG_<配置ID>=启用,间隔分钟,参数JSON
#
# 示例：配置ID 44，每天执行一次
SCHEDULE_CONFIG_44=true,1440,{"registration_no":"滇械注准20192140008"}
#
# 示例：配置ID 50，每小时执行一次
# SCHEDULE_CONFIG_50=true,60,{"keyword":"医疗器械"}
#
# 示例：配置ID 55，每6小时执行一次
# SCHEDULE_CONFIG_55=true,360,{"category":"高值耗材"}

# ===========================================
# 请求级限流配置
# ===========================================
REQUEST_RATE_LIMIT_ENABLED=False
REQUEST_RATE_LIMIT_INTERVAL_SECONDS=5.0
```

---

## 🎯 配置步骤

### 步骤 1：查询配置ID

```sql
-- 查询你的采集配置ID
SELECT id, config_name FROM crawler_configs WHERE is_active = 1;

-- 示例结果：
-- id | config_name
-- 44 | 国家医保局-注册证号查询
```

### 步骤 2：打开 .env 文件

用记事本或任何文本编辑器打开项目根目录的 `.env` 文件

### 步骤 3：添加配置

```bash
# 配置格式：SCHEDULE_CONFIG_<ID>=启用,间隔,参数
SCHEDULE_CONFIG_44=true,1440,{"registration_no":"滇械注准20192140008"}
```

### 步骤 4：保存并重启服务

```bash
python -m app.main
```

### 步骤 5：查看日志验证

```log
INFO - 成功加载 1 个周期性任务配置
INFO - 加载配置: <ScheduledTaskConfig(config_id=44, enabled=True, interval=1440min)>
```

---

## ✅ 配置示例对照表

| 需求 | 配置 |
|------|------|
| 每天采集注册证号 | `SCHEDULE_CONFIG_44=true,1440,{"registration_no":"滇械注准20192140008"}` |
| 每小时监控关键词 | `SCHEDULE_CONFIG_50=true,60,{"keyword":"医疗器械"}` |
| 每6小时采集价格 | `SCHEDULE_CONFIG_55=true,360,{"product_type":"耗材"}` |
| 每30分钟检查库存 | `SCHEDULE_CONFIG_60=true,30,{"warehouse":"北京"}` |
| 暂时禁用任务 | `SCHEDULE_CONFIG_44=false,1440,{"registration_no":"滇械注准20192140008"}` |

---

## 🐛 常见问题

### Q1: 如何禁用某个任务？

将 `true` 改为 `false`：

```bash
# 禁用
SCHEDULE_CONFIG_44=false,1440,{"registration_no":"xxx"}
```

或者直接注释掉这一行：

```bash
# SCHEDULE_CONFIG_44=true,1440,{"registration_no":"xxx"}
```

### Q2: 如何修改执行间隔？

修改中间的数字：

```bash
# 从每天改为每6小时
SCHEDULE_CONFIG_44=true,360,{"registration_no":"xxx"}
```

### Q3: 参数可以有多个吗？

可以，JSON 格式支持多个参数：

```bash
SCHEDULE_CONFIG_50=true,60,{"keyword":"医疗器械","category":"高值耗材","region":"北京"}
```

### Q4: 参数中有逗号怎么办？

JSON 内部的逗号不影响，只要格式正确：

```bash
SCHEDULE_CONFIG_50=true,60,{"name":"产品A,产品B","type":"医疗"}
```

### Q5: 修改配置后如何生效？

重启服务：

```bash
python -m app.main
```

---

## 📊 优势对比

| 配置方式 | 复杂度 | 示例 |
|---------|--------|------|
| **新方式（推荐）** ⭐⭐⭐⭐⭐ | 简单 | `SCHEDULE_CONFIG_44=true,1440,{"registration_no":"xxx"}` |
| 旧方式（JSON） | 复杂 | `SCHEDULED_TASKS='[{"config_id":44,"enabled":true,...}]'` |

**新方式优势**：
- ✅ 一目了然，一行一个任务
- ✅ 容易编辑，不会弄错 JSON 格式
- ✅ 添加/删除任务方便
- ✅ 注释方便
- ✅ 不需要担心引号、逗号、括号匹配

---

## 🎓 完整教程

假设你想每天自动采集一次注册证号 "滇械注准20192140008"：

1. **查询配置ID**（假设是 44）
2. **打开 .env 文件**
3. **添加一行**：
   ```bash
   SCHEDULE_CONFIG_44=true,1440,{"registration_no":"滇械注准20192140008"}
   ```
4. **保存文件**
5. **重启服务**：`python -m app.main`
6. **完成！** 系统会自动每24小时执行一次

---

## 📝 总结

**配置格式**：
```bash
SCHEDULE_CONFIG_<ID>=<true/false>,<间隔分钟>,<参数JSON>
```

**实际示例**：
```bash
SCHEDULE_CONFIG_44=true,1440,{"registration_no":"滇械注准20192140008"}
```

就这么简单！
