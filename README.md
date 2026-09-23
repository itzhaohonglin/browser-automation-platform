# 浏览器自动化数据采集平台

<div align="center">

![Python Version](https://img.shields.io/badge/python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115.0-009688)
![Playwright](https://img.shields.io/badge/Playwright-1.47.0-2EAD33)
![License](https://img.shields.io/badge/license-Internal-orange)
![Code Style](https://img.shields.io/badge/code%20style-black-000000)

**配置驱动的 RPA 数据采集系统**

基于 FastAPI + Playwright 构建的企业级浏览器自动化平台

[功能特性](#-功能特性) • [快速开始](#-快速开始) • [架构设计](#-架构设计) • [开发指南](#-开发指南) • [文档](#-文档)

</div>

---

## 📋 目录

- [功能特性](#-功能特性)
- [技术栈](#-技术栈)
- [快速开始](#-快速开始)
- [架构设计](#-架构设计)
- [核心功能](#-核心功能)
- [开发指南](#-开发指南)
- [测试](#-测试)
- [部署](#-部署)
- [文档](#-文档)
- [项目状态](#-项目状态)

---

## ✨ 功能特性

### 核心能力

- 🎯 **配置驱动** - 通过数据库配置采集规则，无需修改代码
- 🔐 **登录态管理** - 多站点登录态隔离、持久化、自动恢复
- 📊 **实时监控** - WebSocket 推送任务状态、日志、统计数据
- 🔄 **智能调度** - 失败任务自动补跑、重试次数限制、优雅启停
- 🖥️ **监控看板** - 实时统计、任务进度、登录态状态可视化
- 🚀 **异步高性能** - 基于 FastAPI 异步框架和 Playwright 异步 API

### 已完成功能

- ✅ FastAPI 基础框架搭建
- ✅ Playwright 浏览器驱动集成
- ✅ 登录态管理 API（有头浏览器登录、状态保存、会话管理）
- ✅ 定时任务调度（APScheduler、失败补跑、重试限制）
- ✅ WebSocket 实时通信（状态推送、日志推送、断线重连）
- ✅ 前端监控看板（统计卡片、任务进度、日志滚动）
- ✅ 数据库 ORM 模型（SQLAlchemy + Alembic）
- ✅ 任务执行器（配置解析、表单填充、数据提取、分页抓取）
- ✅ 企业级配置（pre-commit、CI/CD、代码规范）

---

## 🛠 技术栈

| 类别 | 技术 | 版本 | 说明 |
|------|------|------|------|
| **后端框架** | FastAPI | 0.115.0 | 异步高性能 Web 框架 |
| **Web 服务器** | Uvicorn | 0.30.6 | ASGI 服务器 |
| **浏览器自动化** | Playwright | 1.47.0 | 跨浏览器自动化库 |
| **数据库 ORM** | SQLAlchemy | 2.0.35 | 异步 ORM |
| **数据库驱动** | aiomysql | 0.2.0 | 异步 MySQL 驱动 |
| **数据库迁移** | Alembic | 1.13.2 | 数据库版本管理 |
| **任务调度** | APScheduler | 3.10.4 | 定时任务框架 |
| **配置管理** | Pydantic | 2.9.2 | 数据验证和配置 |
| **WebSocket** | websockets | 13.1 | 实时通信 |
| **前端** | HTML/CSS/JS | - | 原生实现 |

**开发工具**:
- Black - 代码格式化
- isort - import 排序
- flake8 - 代码检查
- pytest - 测试框架
- bandit - 安全扫描
- pre-commit - Git hooks

---

## 🚀 快速开始

### 环境要求

- Python 3.10 或更高版本
- MySQL 8.0 或更高版本
- Windows/Linux/macOS

### 安装步骤

#### 1. 克隆项目

```bash
git clone <repository-url>
cd browser-automation-platform
```

#### 2. 创建虚拟环境

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# Linux/macOS
source venv/bin/activate
```

#### 3. 安装依赖

```bash
# 生产依赖
pip install -r requirements.txt

# 开发依赖（可选）
pip install -r requirements-dev.txt

# 安装 Playwright 浏览器
playwright install chromium
```

#### 4. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，填入真实配置
# 必填项: DATABASE_URL
```

**`.env` 配置示例**:
```env
DATABASE_URL=mysql+aiomysql://username:password@localhost:3306/bap
DEBUG=False
HEADLESS_MODE=True
LOG_LEVEL=INFO
```

#### 5. 初始化数据库

```bash
# 创建数据库
mysql -u root -p -e "CREATE DATABASE bap CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"

# 运行数据库迁移
alembic upgrade head
```

#### 6. 启动服务

```bash
# 开发模式（自动重载）
uvicorn app.main:app --reload

# 生产模式
python -m app.main
```

#### 7. 访问服务

- 🌐 **API 文档**: http://127.0.0.1:8000/docs
- 📊 **监控看板**: http://127.0.0.1:8000/static/index.html
- 💚 **健康检查**: http://127.0.0.1:8000/health
- 🔌 **WebSocket**: ws://127.0.0.1:8000/ws

---

## 🏗 架构设计

### 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端监控看板                           │
│         (HTML/CSS/JS + WebSocket 实时通信)                   │
└────────────────────┬────────────────────────────────────────┘
                     │ HTTP / WebSocket
┌────────────────────▼────────────────────────────────────────┐
│                     FastAPI 应用层                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ API Endpoints│  │  WebSocket   │  │   Scheduler  │      │
│  │  (REST API)  │  │   Manager    │  │ (APScheduler)│      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                     服务层 (Services)                        │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ Auth Manager │  │   Executor   │  │  Scheduler   │      │
│  │ (登录态管理) │  │  (任务执行)   │  │  (定时调度)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                数据层 (SQLAlchemy ORM)                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │CrawlerConfig │  │  JobQueue    │  │CrawlerResult │      │
│  │  (采集配置)   │  │  (任务队列)   │  │  (采集结果)   │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
└────────────────────┬────────────────────────────────────────┘
                     │
┌────────────────────▼────────────────────────────────────────┐
│                      MySQL 数据库                            │
└─────────────────────────────────────────────────────────────┘

             ┌──────────────────────────┐
             │    Playwright Browser    │
             │   (浏览器自动化执行)       │
             └──────────────────────────┘
```

### 核心流程

```
1. 配置管理
   ├─ 数据库定义采集规则（目标URL、选择器、字段映射）
   ├─ 支持登录态配置（auth_profile、login_url）
   └─ 灵活的多输入框和分页配置

2. 任务调度
   ├─ 任务队列（job_queue）存储待执行任务
   ├─ Scheduler 每 30 分钟扫描失败任务
   └─ 自动重试（最多 3 次）

3. 执行流程
   ├─ Executor 读取任务和配置
   ├─ 启动 Playwright 浏览器
   ├─ 加载登录态（如需要）
   ├─ 填充表单、提交查询
   ├─ 等待结果、提取数据
   ├─ 自动分页抓取
   └─ 保存到 crawler_results 表

4. 实时监控
   ├─ WebSocket 推送任务状态
   ├─ 推送执行日志
   ├─ 推送统计数据
   └─ 前端看板实时展示
```

---

## 💡 核心功能

### 1. 配置管理 API

通过 RESTful API 管理采集配置（CRUD 操作）：

#### 创建配置
```bash
# POST /api/configs
curl -X POST "http://127.0.0.1:8000/api/configs" \
  -H "Content-Type: application/json" \
  -d '{
    "config_name": "百度搜索测试",
    "target_url": "https://www.baidu.com",
    "input_configs": {
      "inputs": [
        {
          "selector": "#kw",
          "param_key": "keyword",
          "input_type": "text"
        }
      ]
    },
    "submit_selector": "#su",
    "wait_selector": "#content_left",
    "fields_mapping": {
      "list_selector": ".c-container",
      "fields": [
        {"name": "title", "selector": "h3 a", "attr": "text"},
        {"name": "url", "selector": "h3 a", "attr": "href"}
      ]
    },
    "max_pages": 3
  }'
```

#### 获取配置列表
```bash
# GET /api/configs - 支持分页和过滤
curl "http://127.0.0.1:8000/api/configs?page=1&page_size=20&is_active=true"
```

#### 获取配置详情
```bash
# GET /api/configs/{config_id}
curl "http://127.0.0.1:8000/api/configs/1"
```

#### 更新配置
```bash
# PUT /api/configs/{config_id} - 支持部分更新
curl -X PUT "http://127.0.0.1:8000/api/configs/1" \
  -H "Content-Type: application/json" \
  -d '{"max_pages": 10, "is_active": false}'
```

#### 删除配置
```bash
# DELETE /api/configs/{config_id}
# 注意：如果存在待执行任务，将返回 409 Conflict
curl -X DELETE "http://127.0.0.1:8000/api/configs/1"
```

**API 文档**: 访问 http://127.0.0.1:8000/docs 查看完整的 Swagger UI 文档

### 2. 登录态管理

支持多站点登录态隔离和持久化：

```bash
# 启动有头浏览器，手动登录
curl -X POST "http://127.0.0.1:8000/auth/start?profile=taobao&login_url=https://login.taobao.com"

# 保存登录态（cookies + localStorage）
curl -X POST "http://127.0.0.1:8000/auth/save?profile=taobao"

# 查询登录态状态
curl "http://127.0.0.1:8000/auth/status?profile=taobao"

# 清理登录态
curl -X DELETE "http://127.0.0.1:8000/auth/clear?profile=taobao"
```

详细说明: [docs/03_auth_usage.md](docs/03_auth_usage.md)

### 3. 任务执行

配置驱动的自动化执行：

```python
# 数据库配置示例
{
  "config_name": "淘宝商品搜索",
  "target_url": "https://www.taobao.com",
  "need_login": true,
  "auth_profile": "taobao",
  "input_configs": [
    {"selector": "#q", "value": "{keyword}", "type": "fill"}
  ],
  "submit_selector": "button.search-btn",
  "wait_selector": ".items-list",
  "fields_mapping": {
    "title": ".title::text",
    "price": ".price::text"
  },
  "pagination_selector": ".next-btn",
  "max_pages": 5
}
```

详细说明: [docs/executor_usage.md](docs/executor_usage.md)

### 4. 定时调度

自动补跑失败任务：

- 每 30 分钟扫描失败任务
- 最多重试 3 次
- 优雅启停（防止任务中断）

详细说明: [docs/scheduler_usage.md](docs/scheduler_usage.md)

### 5. 实时监控

WebSocket 实时推送：

```javascript
// 前端连接 WebSocket
const ws = new WebSocket('ws://127.0.0.1:8000/ws');

// 接收实时消息
ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  // data.type: 'status' | 'log' | 'stats'
};
```

详细说明: [docs/websocket_usage.md](docs/websocket_usage.md)

---

## 👨‍💻 开发指南

### 开发环境设置

```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 安装 pre-commit hooks
pre-commit install

# 首次运行检查所有文件
pre-commit run --all-files
```

### 代码规范

项目使用以下工具保证代码质量：

```bash
# 代码格式化
black app/ tests/
isort app/ tests/

# 代码检查
flake8 app/ tests/

# 安全扫描
bandit -r app/ -c pyproject.toml

# 类型检查（可选）
mypy app/
```

### 数据库迁移

```bash
# 创建迁移脚本
alembic revision --autogenerate -m "描述信息"

# 执行迁移
alembic upgrade head

# 回滚迁移
alembic downgrade -1

# 查看迁移历史
alembic history
```

### 项目结构

```
browser-automation-platform/
├── app/                        # 应用主目录
│   ├── main.py                 # FastAPI 入口
│   ├── api/                    # API 路由
│   │   ├── endpoints.py        # REST API 端点
│   │   └── websocket.py        # WebSocket 管理器
│   ├── core/                   # 核心配置
│   │   ├── config.py           # 应用配置
│   │   └── database.py         # 数据库连接
│   ├── models/                 # ORM 模型
│   │   ├── config.py           # 采集配置模型
│   │   ├── job.py              # 任务队列模型
│   │   └── result.py           # 采集结果模型
│   ├── services/               # 业务逻辑
│   │   ├── auth_manager.py     # 登录态管理
│   │   ├── executor.py         # 任务执行器
│   │   └── scheduler.py        # 定时调度器
│   └── utils/                  # 工具函数
├── alembic/                    # 数据库迁移
│   └── versions/               # 迁移脚本
├── auth_files/                 # 登录态存储（.gitignore）
├── docs/                       # 项目文档
├── static/                     # 前端静态文件
│   └── index.html              # 监控看板
├── tests/                      # 测试文件
├── .env.example                # 环境变量模板
├── .gitignore                  # Git 忽略规则
├── .pre-commit-config.yaml     # Pre-commit 配置
├── requirements.txt            # 生产依赖
├── requirements-dev.txt        # 开发依赖
├── setup.cfg                   # 工具配置
├── pyproject.toml              # 项目配置
└── README.md                   # 项目说明
```

---

## 🧪 测试

### 运行测试

```bash
# 运行所有测试
pytest

# 运行单个测试文件
pytest tests/test_executor_websocket.py

# 带详细输出
pytest -v -s

# 带覆盖率报告
pytest --cov=app --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

### 测试覆盖率

目标: 80%+ 代码覆盖率

当前覆盖情况:
- Core 模块: ✅
- Services 模块: ✅
- API 模块: ✅
- Models 模块: ✅

---

## 🚢 部署

### 生产环境配置

```env
# .env
DEBUG=False
HEADLESS_MODE=True
LOG_LEVEL=INFO
DATABASE_URL=mysql+aiomysql://user:pass@prod-host:3306/bap
```

### Docker 部署（规划中）

```bash
# 构建镜像
docker build -t browser-automation-platform .

# 运行容器
docker-compose up -d
```

### 系统服务

```bash
# 使用 systemd（Linux）
sudo cp browser-automation.service /etc/systemd/system/
sudo systemctl enable browser-automation
sudo systemctl start browser-automation
```

---

## 📚 文档

### 核心文档

- [产品需求文档 (PRD)](docs/01_prd.md)
- [技术设计方案 (TDD)](docs/02_tech_design.md)
- [登录态管理使用指南](docs/03_auth_usage.md)
- [数据库使用指南](docs/database_usage.md)
- [执行器使用指南](docs/executor_usage.md)
- [调度器使用指南](docs/scheduler_usage.md)
- [WebSocket 使用指南](docs/websocket_usage.md)

### 开发文档

- [CLAUDE.md](CLAUDE.md) - Claude Code 项目指引
- [ENTERPRISE_SETUP.md](ENTERPRISE_SETUP.md) - 企业级配置说明
- [IMPROVEMENTS.md](IMPROVEMENTS.md) - 项目改进总结

### API 文档

启动服务后访问: http://127.0.0.1:8000/docs

---

## 📊 项目状态

### 开发进度

| 模块 | 状态 | 完成度 |
|------|------|--------|
| 项目骨架 | ✅ 完成 | 100% |
| 登录态管理 | ✅ 完成 | 100% |
| 数据库 ORM | ✅ 完成 | 100% |
| 任务执行器 | ✅ 完成 | 100% |
| 定时调度器 | ✅ 完成 | 100% |
| WebSocket | ✅ 完成 | 100% |
| 监控看板 | ✅ 完成 | 100% |
| 企业级配置 | ✅ 完成 | 100% |
| CI/CD | ✅ 完成 | 100% |
| Docker 部署 | ⏳ 规划中 | 0% |

### 版本历史

- **v1.0.0** (2026-09) - 初始版本发布
  - 核心功能完成
  - 企业级配置完善
  - CI/CD 集成

---

## 🤝 贡献指南

### 开发流程

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'feat: Add some AmazingFeature'`)
4. 推送分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

### Commit 规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: 新功能
fix: 修复 bug
docs: 文档更新
style: 代码格式调整
refactor: 重构
test: 测试相关
chore: 构建/工具链相关
```

---

## 📄 许可证

内部项目 - 仅供企业内部使用

---

## 💬 支持

如有问题或建议，请联系项目维护团队。

---

<div align="center">

**[⬆ 返回顶部](#浏览器自动化数据采集平台)**

Made with ❤️ by Browser Automation Team

</div>
