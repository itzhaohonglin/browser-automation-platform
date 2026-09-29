# 项目结构清理设计方案

**日期**: 2026-09-29  
**类型**: 项目维护  
**状态**: 待审核

## 概述

对浏览器自动化平台项目进行结构化清理，删除临时测试文件，重组工具脚本目录，优化项目结构以提高可维护性。

## 目标

1. 删除所有临时测试文件和输出文件
2. 创建规范的 `scripts/` 目录存放工具脚本
3. 更新 `.gitignore` 规则以支持工具脚本的版本控制
4. 保持所有功能性代码和测试套件完整
5. 提交当前未提交的代码变更

## 清理范围

### 1. 需要删除的文件

**临时测试文件**（8个 nhsa 相关文件）：
- `nhsa_config.json` - 测试配置
- `nhsa_final_config.json` - 最终测试配置
- `nhsa_final_result.png` - 测试截图
- `nhsa_iframe.html` - 测试 HTML
- `nhsa_iframe_result.png` - 测试截图
- `nhsa_initial.png` - 初始测试截图
- `nhsa_medical_analysis.png` - 医疗分析测试截图
- `nhsa_medical_page.html` - 医疗页面测试 HTML
- `nhsa_page.html` - 页面测试 HTML

**测试输出文件**：
- `executor_test_output.txt` - 执行器测试输出
- `test_output.log` - 测试日志

**备份文件**：
- `backup_20260928_211309.sql` - 数据库备份

**临时文档**：
- `SETUP_COMPLETE.md` - 安装完成标记

**删除理由**：这些文件都是开发过程中产生的临时文件，不应该提交到版本控制系统。它们要么是测试特定站点（国家医保服务平台）的产物，要么是调试输出，对项目的长期维护没有价值。

### 2. 需要重组的文件

**工具脚本** - 移动到 `scripts/` 目录：
- `verify_migration.py` → `scripts/verify_migration.py`
- `test_auth.sh` → `scripts/test_auth.sh`
- `test_auth.ps1` → `scripts/test_auth.ps1`

**重组理由**：这些是有价值的工具脚本，应该保留并纳入版本控制。创建专门的 `scripts/` 目录符合项目组织的最佳实践，使项目结构更清晰。

### 3. 需要保留的内容

**测试套件** - 完整保留 `tests/` 目录：
- 16 个测试文件涵盖告警、配置、执行器、指标、调度器、WebSocket 等核心功能
- `conftest.py` - pytest 配置
- 这些是项目质量保证的重要组成部分

**核心代码** - `app/` 目录所有文件保持不变

**文档** - `docs/` 目录保持不变

**配置文件** - 所有配置文件保持不变（.env.example, alembic.ini, requirements.txt 等）

## 实施步骤

### 第 1 步：创建 scripts 目录
```bash
mkdir scripts
```

### 第 2 步：移动工具脚本
```bash
git mv verify_migration.py scripts/
git mv test_auth.sh scripts/
git mv test_auth.ps1 scripts/
```

**注意**：使用 `git mv` 而不是普通的 `mv` 命令，以保留 git 历史记录。

### 第 3 步：删除临时文件
```bash
rm nhsa_*.json nhsa_*.html nhsa_*.png
rm executor_test_output.txt test_output.log
rm backup_20260928_211309.sql
rm SETUP_COMPLETE.md
```

### 第 4 步：更新 .gitignore

**修改前**（第 136-138 行）：
```gitignore
# Temporary test scripts
/*.py
!setup.py
```

**修改后**：
```gitignore
# Temporary test scripts in root
/*.py
!setup.py

# But allow scripts directory
!scripts/
```

**变更说明**：
- 保持根目录 `.py` 文件的忽略规则（防止临时测试脚本污染仓库）
- 添加 `!scripts/` 例外规则，允许 scripts 目录下的文件被追踪
- 这样既保护了项目根目录的整洁，又允许工具脚本进入版本控制

### 第 5 步：暂存并提交当前修改

**当前未提交的文件**：
- `app/api/endpoints.py` - 已修改
- `static/app.js` - 已修改
- `static/index.html` - 已修改
- `static/style.css` - 已修改
- `tests/test_config_schemas.py` - 已修改

这些文件包含功能性改进，应该在清理之前或同时提交。

**提交策略**：
```bash
# 选项 A：分两次提交（推荐）
git add app/api/endpoints.py static/* tests/test_config_schemas.py
git commit -m "feat: update API endpoints and frontend UI"

git add scripts/ .gitignore
git commit -m "refactor: reorganize project structure and clean up temp files"

# 选项 B：一次提交
git add .
git commit -m "refactor: clean up project structure and commit pending changes"
```

推荐选项 A，因为它将功能改进和结构清理分开，使 git 历史更清晰。

### 第 6 步：更新相关文档

需要更新脚本路径引用的文档：

**CLAUDE.md** - 更新命令部分：
```markdown
### 测试
```bash
# 测试登录态管理功能
bash scripts/test_auth.sh  # Linux/Mac
.\scripts\test_auth.ps1    # Windows PowerShell
```
```

**README.md** - 如果有相关引用也需要更新

**docs/ 下的文档** - 检查是否有对这些脚本的引用

### 第 7 步：验证清理结果

```bash
# 检查 git 状态
git status

# 确认临时文件已删除
ls *.json *.html *.png *.txt *.log 2>/dev/null | wc -l  # 应该为 0

# 确认 scripts 目录结构
ls -la scripts/

# 运行测试确保功能完整
pytest tests/ -v
```

## 预期结果

### 文件系统变化

**根目录清理后**：
- 减少 13 个临时文件
- 根目录只保留必要的配置文件和文档
- 新增 `scripts/` 目录包含 3 个工具脚本

**目录结构**：
```
browser-automation-platform/
├── .claude/
├── .git/
├── .github/
├── alembic/
├── app/                    # 应用代码（保持不变）
├── auth_files/             # 登录态文件（保持不变）
├── docs/                   # 文档（保持不变）
├── logs/                   # 日志目录（保持不变）
├── scripts/                # 新增：工具脚本目录
│   ├── verify_migration.py
│   ├── test_auth.sh
│   └── test_auth.ps1
├── static/                 # 静态文件（保持不变）
├── tests/                  # 测试套件（完整保留）
├── .env.example
├── .gitignore              # 更新规则
├── alembic.ini
├── CLAUDE.md               # 更新脚本路径
├── README.md
├── requirements.txt
└── setup.cfg
```

### Git 历史

**预期提交**：
1. `feat: update API endpoints and frontend UI` - 提交功能改进
2. `refactor: reorganize project structure and clean up temp files` - 清理和重组

### 文档更新

- CLAUDE.md 中的脚本路径已更新
- README.md 中的相关引用已更新（如有）
- docs/ 下的文档已同步更新（如有）

## 风险评估

### 低风险
- **删除临时文件**：这些文件不影响任何功能，可以安全删除
- **移动工具脚本**：使用 `git mv` 保留历史，不会丢失信息

### 无风险
- **保留测试套件**：所有测试文件完整保留，质量保证不受影响
- **更新 .gitignore**：只是添加例外规则，不影响现有忽略规则

### 需要注意
- **文档同步**：确保所有文档中的脚本路径引用都已更新
- **CI/CD 配置**：如果有 CI/CD 流程调用这些脚本，需要更新路径

## 回滚方案

如果需要回滚：

```bash
# 回滚到清理前的状态
git reset --hard HEAD~1  # 如果是最后一次提交

# 或者基于具体提交
git revert <commit-hash>

# 恢复临时文件（如果需要）
# 由于这些是临时文件，通常不需要恢复
```

## 后续维护建议

1. **遵守目录规范**：
   - 工具脚本放在 `scripts/`
   - 测试文件放在 `tests/`
   - 临时文件不提交到 git

2. **定期清理**：
   - 每周检查根目录是否有新的临时文件
   - 使用 `git status` 确认未追踪文件

3. **备份策略**：
   - 数据库备份应该放在 `backups/` 目录（添加到 .gitignore）
   - 或使用专门的备份系统，不放在项目目录

4. **文档同步**：
   - 每次移动文件或重命名时，同步更新相关文档
   - 在 PR review 中检查文档是否同步

## 验收标准

清理完成后应满足以下标准：

- [ ] 根目录不存在 `nhsa_*` 开头的文件
- [ ] 根目录不存在 `*_output.txt` 或 `*.log` 文件
- [ ] 根目录不存在 `.sql` 备份文件
- [ ] `scripts/` 目录包含 3 个工具脚本
- [ ] `.gitignore` 已更新，包含 `!scripts/` 规则
- [ ] CLAUDE.md 中的脚本路径已更新为 `scripts/`
- [ ] 所有测试通过：`pytest tests/ -v`
- [ ] `git status` 显示工作区干净（或只有预期的未追踪文件）
- [ ] 功能验证：`python scripts/verify_migration.py` 正常运行
- [ ] 登录态测试脚本可以从新路径执行

## 总结

这是一次保守且结构化的项目清理，在删除无用文件的同时改善了项目组织。通过创建 `scripts/` 目录并更新 `.gitignore` 规则，我们建立了清晰的文件组织规范，为项目的长期维护奠定了良好基础。

清理后的项目将更加整洁、结构更清晰，同时保持了所有核心功能和测试能力的完整性。
