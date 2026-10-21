# 配置文件更新说明

## 本次改动涉及的配置

### ✅ **数据库连接池优化 - 无需配置**

以下参数已在代码中硬编码（`app/core/database.py`），**不需要**添加到 .env：

```python
# 这些是底层技术参数，已优化完成，无需用户配置
pool_size=10                  # 连接池大小（原 5）
max_overflow=5                # 最大溢出连接（原 10）
pool_recycle=1200             # 连接回收时间 20分钟（原 3600秒）
pool_timeout=30               # 获取连接超时（新增）
```

**为什么不做成可配置？**
1. 这些是技术参数，需要专业知识才能正确调整
2. 已根据 SQL Server 特性和系统并发需求优化
3. 错误配置可能导致严重问题（连接泄漏、性能下降）
4. 适用于 95% 的使用场景

**例外场景：**
如果你的部署规模非常大（如：100+ 并发用户），可以考虑暴露这些配置。但对于当前的 RPA 数据采集平台，**强烈建议使用默认值**。

---

### ✅ **安全修复 - 必须添加配置**

#### 1. CORS 配置（必须）

**添加到 `.env`：**
```bash
# CORS 允许的源（逗号分隔，不要有空格）
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

**生产环境示例：**
```bash
# 替换为你的实际域名
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

**对应的代码修改（`app/core/config.py`）：**
```python
class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # CORS 配置
    CORS_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"
```

---

#### 2. API 认证配置（强烈推荐）

**添加到 `.env`：**
```bash
# API 认证配置（临时方案，生产环境应使用 JWT）
API_USERNAME=admin
API_PASSWORD=your_strong_password_min_16_chars_XyZ123!@#
```

**密码要求：**
- 至少 16 个字符
- 包含大小写字母、数字、特殊字符
- 不要使用常见密码或个人信息

**对应的代码修改（`app/core/config.py`）：**
```python
class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # API 认证配置
    API_USERNAME: str = "admin"
    API_PASSWORD: Optional[str] = None  # 必须在 .env 中设置
```

---

#### 3. 登录态加密密钥（可选但推荐）

**首次运行生成密钥：**
```bash
python -c "from app.core.encryption import migrate_auth_files; migrate_auth_files()"
```

**将输出的密钥添加到 `.env`：**
```bash
# 登录态加密密钥（保护 auth_files 中的敏感数据）
AUTH_ENCRYPTION_KEY=your_generated_fernet_key_here_32_bytes_base64_encoded
```

**对应的代码修改（`app/core/config.py`）：**
```python
class Settings(BaseSettings):
    # ... 现有配置 ...
    
    # 登录态加密配置
    AUTH_ENCRYPTION_KEY: Optional[str] = None
```

---

## 📝 **完整的 .env 文件示例**

### 最小配置（必须项）

```bash
# ========================================
# 数据库配置（必须）
# ========================================
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server

# ========================================
# 应用配置
# ========================================
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=false
LOG_LEVEL=INFO

# ========================================
# Playwright 配置
# ========================================
HEADLESS_MODE=true

# ========================================
# 任务调度配置
# ========================================
MAX_WORKERS=3
RETRY_INTERVAL_MINUTES=30
MAX_RETRY_COUNT=3

# ========================================
# 安全配置（新增 - 必须配置）
# ========================================
# CORS 允许的源（逗号分隔）
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# API 认证
API_USERNAME=admin
API_PASSWORD=change_this_to_a_strong_password_min_16_chars

# 登录态加密（可选，首次运行时生成）
# AUTH_ENCRYPTION_KEY=
```

### 完整配置（包含所有选项）

```bash
# ========================================
# 数据库配置
# ========================================
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost:1433/bap?driver=ODBC+Driver+17+for+SQL+Server

# ========================================
# 应用配置
# ========================================
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=false
LOG_LEVEL=INFO
# LOG_FILE=logs/app.log

# ========================================
# Playwright 配置
# ========================================
HEADLESS_MODE=true
AUTH_FILES_DIR=auth_files

# ========================================
# 任务调度配置
# ========================================
DISPATCH_INTERVAL_MINUTES=30
RETRY_INTERVAL_MINUTES=30
MAX_RETRY_COUNT=3
RETRY_BATCH_SIZE=100

# 智能重试配置
RETRY_MIN_WAIT_MINUTES=60
RETRY_SKIP_IF_PENDING_OVER=100

# ========================================
# 进程池配置
# ========================================
MAX_WORKERS=3
WORKER_MEMORY_LIMIT_MB=512

# ========================================
# 请求级限流配置（全局默认）
# ========================================
REQUEST_RATE_LIMIT_ENABLED=false
REQUEST_RATE_LIMIT_INTERVAL_SECONDS=5.0

# ========================================
# 周期性任务配置
# ========================================
SCHEDULE_CHECK_INTERVAL_MINUTES=5
SCHEDULE_FIRST_RUN_DELAY_MINUTES=2

# ========================================
# 全局重新执行配置
# ========================================
AUTO_RECREATE_SUCCESS_JOBS=false
AUTO_RECREATE_INTERVAL_MINUTES=1440

# ========================================
# 安全配置（新增）
# ========================================
# CORS 允许的源（逗号分隔，生产环境必须修改）
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# API 认证配置
API_USERNAME=admin
API_PASSWORD=change_this_to_a_strong_password_min_16_chars

# 登录态加密密钥（运行迁移脚本后生成）
# AUTH_ENCRYPTION_KEY=
```

---

## 🔄 **升级步骤**

### 1. 备份现有配置

```bash
cp .env .env.backup.$(date +%Y%m%d)
```

### 2. 添加新配置项

打开 `.env` 文件，添加以下内容到文件末尾：

```bash
# ========================================
# 安全配置（2026-10-20 添加）
# ========================================
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
API_USERNAME=admin
API_PASSWORD=请修改为强密码
```

### 3. 修改默认密码

**重要：** 必须修改 `API_PASSWORD` 为强密码！

### 4. 限制文件权限

```bash
chmod 600 .env
```

### 5. 验证配置

```bash
# 检查配置是否正确
python -c "from app.core.config import settings; print('✓ 配置加载成功')"

# 检查数据库连接池
python scripts/verify_connection_pool_config.py
```

### 6. 重启应用

```bash
# 停止现有应用
# 启动应用
python -m app.main
```

### 7. 测试认证

```bash
# 未认证应该返回 401
curl http://localhost:8000/api/configs

# 使用认证应该返回 200
curl -u admin:your_password http://localhost:8000/api/configs
```

---

## ⚠️ **常见问题**

### Q1: 数据库连接池参数可以自定义吗？

**A:** 不推荐。当前值已经过优化，适用于绝大多数场景。如果确实需要调整：
- 只在确定理解这些参数含义的情况下修改
- 参考 `docs/database_connection_pool_optimization.md`
- 修改 `app/core/database.py` 中的硬编码值

### Q2: 忘记 API_PASSWORD 怎么办？

**A:** 直接修改 `.env` 文件中的密码，重启应用即可。

### Q3: AUTH_ENCRYPTION_KEY 丢失了怎么办？

**A:** 如果丢失，将无法解密现有的登录态文件。需要：
1. 重新生成密钥
2. 重新手动登录保存登录态

### Q4: 生产环境 CORS_ORIGINS 应该设置什么？

**A:** 设置为你的实际域名，例如：
```bash
CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

**绝对不要**在生产环境使用 `CORS_ORIGINS=*`！

---

## 📋 **检查清单**

升级完成后，检查以下项目：

- [ ] `.env` 文件包含 `CORS_ORIGINS`
- [ ] `.env` 文件包含 `API_USERNAME` 和 `API_PASSWORD`
- [ ] `API_PASSWORD` 已修改为强密码（不是默认值）
- [ ] `.env` 文件权限为 600 (`chmod 600 .env`)
- [ ] 应用可以正常启动
- [ ] API 需要认证才能访问（测试 401/200 响应）
- [ ] 数据库连接池配置验证通过

---

## 📚 **相关文档**

- `docs/database_connection_pool_optimization.md` - 连接池优化详解
- `docs/SECURITY_FIX_GUIDE.md` - 安全修复指南
- `docs/SECURITY_AUDIT_REPORT.md` - 完整安全审计报告
- `CLAUDE.md` - 项目开发指南
