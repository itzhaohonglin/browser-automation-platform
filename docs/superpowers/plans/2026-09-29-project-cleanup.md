# 项目结构清理实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 清理项目临时文件，重组工具脚本到 scripts/ 目录，优化项目结构

**Architecture:** 采用保守清理策略，保留所有功能代码和测试套件，仅删除临时文件并重组工具脚本目录结构

**Tech Stack:** Git, Bash

---

## 文件结构映射

**创建的目录**:
- `scripts/` - 工具脚本目录

**移动的文件**:
- `verify_migration.py` → `scripts/verify_migration.py`
- `test_auth.sh` → `scripts/test_auth.sh`
- `test_auth.ps1` → `scripts/test_auth.ps1`

**修改的文件**:
- `.gitignore` - 添加 scripts/ 例外规则
- `CLAUDE.md` - 更新脚本路径引用

**删除的文件**:
- `nhsa_config.json`, `nhsa_final_config.json`, `nhsa_final_result.png`
- `nhsa_iframe.html`, `nhsa_iframe_result.png`, `nhsa_initial.png`
- `nhsa_medical_analysis.png`, `nhsa_medical_page.html`, `nhsa_page.html`
- `executor_test_output.txt`, `test_output.log`
- `backup_20260928_211309.sql`, `SETUP_COMPLETE.md`

---

## Task 1: 提交当前未提交的代码变更

**Files:**
- Modify: `app/api/endpoints.py`, `static/app.js`, `static/index.html`, `static/style.css`, `tests/test_config_schemas.py`

- [ ] **Step 1: 检查当前 git 状态**

```bash
git status
```

Expected: 显示 5 个已修改文件 (M app/api/endpoints.py, M static/app.js, M static/index.html, M static/style.css, M tests/test_config_schemas.py)

- [ ] **Step 2: 暂存功能改进文件**

```bash
git add app/api/endpoints.py static/app.js static/index.html static/style.css tests/test_config_schemas.py
```

Expected: 无输出表示成功

- [ ] **Step 3: 验证暂存状态**

```bash
git status
```

Expected: 显示 5 个文件在暂存区 (Changes to be committed)

- [ ] **Step 4: 提交功能改进**

```bash
git commit -m "feat: update API endpoints and frontend UI"
```

Expected: 提交成功，显示 5 个文件被修改

- [ ] **Step 5: 确认提交完成**

```bash
git log --oneline -1
```

Expected: 最新提交显示 "feat: update API endpoints and frontend UI"

---

## Task 2: 创建 scripts 目录并移动工具脚本

**Files:**
- Create: `scripts/` (目录)
- Move: `verify_migration.py` → `scripts/verify_migration.py`
- Move: `test_auth.sh` → `scripts/test_auth.sh`
- Move: `test_auth.ps1` → `scripts/test_auth.ps1`

- [ ] **Step 1: 创建 scripts 目录**

```bash
mkdir scripts
```

Expected: 无输出表示成功

- [ ] **Step 2: 验证目录创建**

```bash
ls -ld scripts
```

Expected: 显示 scripts 目录存在

- [ ] **Step 3: 移动 verify_migration.py**

```bash
git mv verify_migration.py scripts/
```

Expected: 无输出表示成功

- [ ] **Step 4: 移动 test_auth.sh**

```bash
git mv test_auth.sh scripts/
```

Expected: 无输出表示成功

- [ ] **Step 5: 移动 test_auth.ps1**

```bash
git mv test_auth.ps1 scripts/
```

Expected: 无输出表示成功

- [ ] **Step 6: 验证文件已移动**

```bash
ls -la scripts/
```

Expected: 显示 3 个文件 (verify_migration.py, test_auth.sh, test_auth.ps1)

- [ ] **Step 7: 检查 git 状态**

```bash
git status
```

Expected: 显示 3 个文件被重命名 (renamed: verify_migration.py -> scripts/verify_migration.py 等)

---

## Task 3: 删除临时测试文件

**Files:**
- Delete: `nhsa_config.json`, `nhsa_final_config.json`, `nhsa_final_result.png`
- Delete: `nhsa_iframe.html`, `nhsa_iframe_result.png`, `nhsa_initial.png`
- Delete: `nhsa_medical_analysis.png`, `nhsa_medical_page.html`, `nhsa_page.html`
- Delete: `executor_test_output.txt`, `test_output.log`
- Delete: `backup_20260928_211309.sql`, `SETUP_COMPLETE.md`

- [ ] **Step 1: 列出要删除的 nhsa 文件**

```bash
ls nhsa_* 2>/dev/null
```

Expected: 显示 9 个 nhsa_ 开头的文件

- [ ] **Step 2: 删除 nhsa 配置和 HTML 文件**

```bash
rm nhsa_config.json nhsa_final_config.json nhsa_iframe.html nhsa_medical_page.html nhsa_page.html
```

Expected: 无输出表示成功

- [ ] **Step 3: 删除 nhsa 截图文件**

```bash
rm nhsa_final_result.png nhsa_iframe_result.png nhsa_initial.png nhsa_medical_analysis.png
```

Expected: 无输出表示成功

- [ ] **Step 4: 删除测试输出文件**

```bash
rm executor_test_output.txt test_output.log
```

Expected: 无输出表示成功

- [ ] **Step 5: 删除备份和临时文档**

```bash
rm backup_20260928_211309.sql SETUP_COMPLETE.md
```

Expected: 无输出表示成功

- [ ] **Step 6: 验证文件已删除**

```bash
ls nhsa_* executor_test_output.txt test_output.log backup_*.sql SETUP_COMPLETE.md 2>/dev/null | wc -l
```

Expected: 输出 0 (所有文件已删除)

---

## Task 4: 更新 .gitignore 规则

**Files:**
- Modify: `.gitignore:136-138`

- [ ] **Step 1: 读取当前 .gitignore 的相关部分**

```bash
tail -5 .gitignore
```

Expected: 显示最后 5 行，包含 "/*.py" 和 "!setup.py"

- [ ] **Step 2: 备份当前 .gitignore**

```bash
cp .gitignore .gitignore.bak
```

Expected: 无输出表示成功

- [ ] **Step 3: 更新 .gitignore 添加 scripts/ 例外**

修改 `.gitignore` 文件第 136-138 行，从：

```gitignore
# Temporary test scripts
/*.py
!setup.py
```

改为：

```gitignore
# Temporary test scripts in root
/*.py
!setup.py

# But allow scripts directory
!scripts/
```

- [ ] **Step 4: 验证修改**

```bash
tail -8 .gitignore
```

Expected: 显示新添加的 "!scripts/" 规则

- [ ] **Step 5: 测试 .gitignore 规则**

```bash
git status scripts/
```

Expected: 显示 scripts/ 目录下的文件被追踪 (不会被忽略)

- [ ] **Step 6: 删除备份文件**

```bash
rm .gitignore.bak
```

Expected: 无输出表示成功

---

## Task 5: 更新 CLAUDE.md 文档中的脚本路径

**Files:**
- Modify: `CLAUDE.md` (测试命令部分)

- [ ] **Step 1: 查找当前脚本路径引用**

```bash
grep -n "test_auth" CLAUDE.md
```

Expected: 显示包含 test_auth.sh 和 test_auth.ps1 的行号

- [ ] **Step 2: 备份 CLAUDE.md**

```bash
cp CLAUDE.md CLAUDE.md.bak
```

Expected: 无输出表示成功

- [ ] **Step 3: 更新脚本路径**

在 `CLAUDE.md` 中找到测试命令部分，将：

```bash
bash test_auth.sh  # Linux/Mac
.\test_auth.ps1    # Windows PowerShell
```

更新为：

```bash
bash scripts/test_auth.sh  # Linux/Mac
.\scripts\test_auth.ps1    # Windows PowerShell
```

- [ ] **Step 4: 验证修改**

```bash
grep "scripts/test_auth" CLAUDE.md
```

Expected: 显示更新后的路径 (scripts/test_auth.sh 和 scripts\test_auth.ps1)

- [ ] **Step 5: 删除备份文件**

```bash
rm CLAUDE.md.bak
```

Expected: 无输出表示成功

---

## Task 6: 提交项目结构重组变更

**Files:**
- Commit: `scripts/`, `.gitignore`, `CLAUDE.md`

- [ ] **Step 1: 暂存所有变更**

```bash
git add scripts/ .gitignore CLAUDE.md
```

Expected: 无输出表示成功

- [ ] **Step 2: 检查暂存状态**

```bash
git status
```

Expected: 显示 3 个文件重命名到 scripts/, .gitignore 和 CLAUDE.md 已修改

- [ ] **Step 3: 提交变更**

```bash
git commit -m "refactor: reorganize project structure and clean up temp files

- Move utility scripts to scripts/ directory
- Update .gitignore to allow scripts/ tracking
- Update CLAUDE.md with new script paths
- Remove temporary test files and outputs"
```

Expected: 提交成功，显示文件变更统计

- [ ] **Step 4: 验证提交**

```bash
git log --oneline -2
```

Expected: 最新两次提交显示功能更新和结构重组

- [ ] **Step 5: 检查工作区状态**

```bash
git status
```

Expected: "nothing to commit, working tree clean"

---

## Task 7: 验证清理结果

**Files:**
- Test: 项目结构和功能完整性

- [ ] **Step 1: 验证根目录清洁**

```bash
ls *.json *.html *.png *.txt *.log *.sql 2>/dev/null | wc -l
```

Expected: 输出 0 (根目录无临时文件)

- [ ] **Step 2: 验证 scripts 目录结构**

```bash
ls -la scripts/
```

Expected: 显示 3 个文件 (verify_migration.py, test_auth.sh, test_auth.ps1)

- [ ] **Step 3: 验证 .gitignore 规则生效**

```bash
git check-ignore scripts/verify_migration.py; echo $?
```

Expected: 输出 1 (文件不被忽略)

- [ ] **Step 4: 测试 verify_migration.py 脚本**

```bash
python scripts/verify_migration.py
```

Expected: 脚本正常运行 (可能输出验证结果或错误，但不应该是文件路径错误)

- [ ] **Step 5: 检查 tests 目录完整性**

```bash
find tests -name "test_*.py" | wc -l
```

Expected: 输出 16 (所有测试文件保留)

- [ ] **Step 6: 运行测试套件验证功能**

```bash
pytest tests/ -v --tb=short
```

Expected: 测试运行完成 (通过或失败都可以，重要的是测试能运行)

- [ ] **Step 7: 验证 git 历史**

```bash
git log --oneline -5
```

Expected: 显示最近 5 次提交，包含新的两次提交

- [ ] **Step 8: 最终状态检查**

```bash
git status
```

Expected: "On branch main, nothing to commit, working tree clean"

---

## 验收标准检查清单

完成所有任务后，验证以下标准：

- [ ] 根目录不存在 `nhsa_*` 开头的文件
- [ ] 根目录不存在 `*_output.txt` 或 `*.log` 文件  
- [ ] 根目录不存在 `.sql` 备份文件
- [ ] `scripts/` 目录包含 3 个工具脚本
- [ ] `.gitignore` 已更新，包含 `!scripts/` 规则
- [ ] CLAUDE.md 中的脚本路径已更新为 `scripts/`
- [ ] `git status` 显示工作区干净
- [ ] `python scripts/verify_migration.py` 可以正常运行
- [ ] tests 目录包含 16 个测试文件
- [ ] git log 显示两次新提交（功能更新 + 结构重组）

---

## 回滚方案

如果需要回滚任何更改：

```bash
# 回滚最后一次提交（结构重组）
git reset --hard HEAD~1

# 回滚两次提交（功能更新 + 结构重组）
git reset --hard HEAD~2

# 或使用 revert（保留历史）
git revert HEAD
```

注意：由于临时文件已被删除，回滚不会恢复这些文件。如果需要，可以从其他地方重新获取。
