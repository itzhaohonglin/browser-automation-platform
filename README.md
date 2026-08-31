# 浏览器自动化数据采集平台

配置驱动的 RPA 数据采集系统，基于 FastAPI + Playwright 构建。

## 项目状态

✅ **阶段一：项目骨架初始化完成**  
✅ **阶段二：登录态管理功能完成**

## 已完成功能

- [x] Python 项目环境初始化
- [x] FastAPI 基础框架搭建
- [x] 静态文件服务配置
- [x] 配置管理模块
- [x] Playwright 浏览器驱动安装
- [x] **登录态管理 API** (PRD 3.2)
  - [x] 拉起有头浏览器进行登录
  - [x] 保存登录态到文件
  - [x] 多站点登录态隔离
  - [x] 登录态状态查询
  - [x] 会话管理和清理

## 技术栈

- **后端**: FastAPI 0.115.0 + Uvicorn 0.30.6
- **浏览器自动化**: Playwright 1.47.0
- **数据库**: SQLAlchemy 2.0.35 + PyMySQL 1.1.1
- **任务调度**: APScheduler 3.10.4
- **前端**: 原生 HTML/CSS/JavaScript
- **Python**: 3.10+

## 快速开始

### 1. 安装依赖

```bash
pip install -r requirements.txt
playwright install chromium
```

### 2. 配置环境变量

复制 `.env.example` 为 `.env` 并修改配置：

```bash
cp .env.example .env
```

### 3. 启动服务

```bash
uvicorn app.main:app --reload
```

或者直接运行：

```bash
python -m app.main
```

### 4. 访问服务

- **API 文档**: http://127.0.0.1:8000/docs
- **静态页面**: http://127.0.0.1:8000/static/index.html
- **健康检查**: http://127.0.0.1:8000/health

### 5. 测试登录态管理功能

```bash
# Linux/Mac
bash test_auth.sh

# Windows PowerShell
.\test_auth.ps1

# 或手动测试
curl -X POST "http://127.0.0.1:8000/auth/start?profile=test&login_url=https://www.baidu.com"
# 在打开的浏览器中完成登录
curl -X POST "http://127.0.0.1:8000/auth/save?profile=test"
```

详细使用说明请查看 [docs/03_auth_usage.md](docs/03_auth_usage.md)

## 项目结构

```
browser-automation-platform/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI 入口 ✅
│   ├── api/
│   │   └── endpoints.py        # 登录态管理 API ✅
│   ├── core/
│   │   ├── config.py           # 配置管理 ✅
│   │   └── database.py         # 数据库连接（待开发）
│   ├── models/                 # ORM 模型（待开发）
│   ├── services/
│   │   └── auth_manager.py     # 登录态管理服务 ✅
│   └── utils/                  # 工具函数（待开发）
├── auth_files/                 # 登录态存储目录 ✅
├── static/                     # 前端静态文件
│   └── index.html              # ✅
├── docs/                       # 项目文档
│   ├── 01_prd.md              # 产品需求文档
│   ├── 02_tech_design.md      # 技术设计文档
│   └── 03_auth_usage.md       # 登录态使用说明 ✅
├── test_auth.sh                # 测试脚本 (Linux/Mac) ✅
├── test_auth.ps1               # 测试脚本 (Windows) ✅
├── requirements.txt            # ✅
├── .env.example                # ✅
└── README.md                   # ✅
```

## 验收标准 ✅

- [x] 终端执行 `uvicorn app.main:app --reload` 能启动
- [x] 浏览器访问 `http://127.0.0.1:8000/docs` 显示 Swagger 页面
- [x] 静态文件服务正常工作
- [x] 健康检查接口返回正常

## 下一步开发计划

根据技术设计文档 `docs/02_tech_design.md`，后续开发优先级：

1. **数据库建表和 ORM 模型映射**
   - 创建 `crawler_configs`、`job_queue`、`crawler_results` 三张表
   - 实现 SQLAlchemy ORM 模型
   - 配置 Alembic 数据库迁移

2. **核心执行器开发**
   - 完善 `app/services/executor.py`
   - 实现 Playwright 自动化逻辑
   - 支持多输入框配置和分页抓取

3. **定时任务调度**
   - 集成 APScheduler
   - 实现失败任务重试机制

4. **前端监控看板**
   - WebSocket 实时推送
   - 登录态管理界面
   - 任务进度展示

## 环境要求

- Python 3.10+
- MySQL 8.0+ (后续开发需要)
- Windows/Linux/macOS

## 许可证

内部项目
