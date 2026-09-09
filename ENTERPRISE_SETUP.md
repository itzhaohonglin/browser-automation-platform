# README: 企业级项目规范

本文档记录了项目配置改进和最佳实践。

## 已完成的企业级改进

### 1. 安全配置强化
- ✅ 移除 `config.py` 中的硬编码数据库密码
- ✅ `DATABASE_URL` 改为必填项，必须通过环境变量提供
- ✅ 生产环境默认 `DEBUG=False`
- ✅ 更新 `.env.example` 提供完整配置模板

### 2. 代码质量工具
- ✅ `.pre-commit-config.yaml` - Git 提交前自动检查
  - Black (代码格式化)
  - isort (import 排序)
  - flake8 (代码检查)
  - bandit (安全扫描)
  - 通用检查（尾随空格、大文件、私钥泄露等）

- ✅ `setup.cfg` - pytest、coverage、flake8、isort 配置
- ✅ `pyproject.toml` - bandit 安全检查配置
- ✅ `requirements-dev.txt` - 开发依赖管理

### 3. CI/CD 流程
- ✅ `.github/workflows/ci.yml` - GitHub Actions
  - Python 3.10/3.11/3.12 多版本测试
  - MySQL 8.0 集成测试
  - 代码格式检查
  - 安全扫描
  - 测试覆盖率上传

### 4. .gitignore 优化
- ✅ 精细化 `.claude/` 目录控制
  - 忽略个人配置 (settings.local.json, memory/, plans/)
  - 保留团队配置 (settings.json)
- ✅ 完整的 Python 项目忽略规则
- ✅ 多平台支持 (Windows/macOS/Linux)

## 使用指南

### 安装开发工具
```bash
# 安装开发依赖
pip install -r requirements-dev.txt

# 安装 pre-commit hooks
pre-commit install

# 首次运行（检查所有文件）
pre-commit run --all-files
```

### 代码格式化
```bash
# 格式化代码
black app/ tests/
isort app/ tests/

# 检查但不修改
black --check app/ tests/
```

### 运行测试
```bash
# 运行所有测试
pytest

# 带覆盖率报告
pytest --cov=app --cov-report=html

# 查看覆盖率报告
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

### 安全检查
```bash
# 扫描安全问题
bandit -r app/ -c pyproject.toml
```

## 需要手动处理的清理项

以下文件建议移动或删除：

1. **临时文档** (建议移到 docs/archive/ 或删除)
   - BUILD_VERIFICATION_REPORT.md
   - TASK_B_ACCEPTANCE.md
   - TASK_B_SUMMARY.md

2. **测试文件位置** (建议移到 tests/ 目录)
   - test_websocket_client.html
   - test_websocket_integration.py (如果在根目录)
   - conftest.py → tests/conftest.py

3. **敏感文件** (已存在，需手动清理)
   - auth_files/auth_test.json (包含真实登录态)

4. **Git 分支规范**
   - 当前在 `master` 分支，主分支是 `main`
   - 建议统一到 `main` 分支

## 环境变量配置

复制 `.env.example` 到 `.env` 并修改：

```bash
cp .env.example .env
# 编辑 .env 填入真实数据库连接信息
```

**重要**: `.env` 文件包含敏感信息，已在 `.gitignore` 中忽略，不会提交到版本控制。

## 下一步建议

1. 运行 `pre-commit run --all-files` 检查现有代码
2. 修复所有格式和安全问题
3. 清理临时文件
4. 配置 GitHub Actions secrets (DATABASE_URL 等)
5. 考虑添加依赖锁定 (pip-tools 或 poetry)
