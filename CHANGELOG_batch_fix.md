# 更新日志

## [未发布] - 2026-10-21

### 修复
- **[重要]** 修复打包版本 `install.bat` 运行时的 "此时不应有 not" 错误
  - 将所有 `if not exist (...)` 语法改为 `if exist + goto` 风格
  - 修复了 5 个批处理文件的语法问题
  - 确保文件使用 GBK 编码和 CRLF 行尾符
  - 影响文件：
    - `install.bat` - 安装脚本
    - `startup.bat` - 启动脚本
    - `install_browser.bat` - 浏览器安装脚本
    - `init_database.bat` - 数据库初始化脚本
    - `init_config.bat` - 配置初始化脚本

### 新增
- 批处理文件自动修复工具：`scripts/deployment/fix_batch_files.py`
- 批处理文件验证工具：`scripts/deployment/verify_batch_files.py`
- 批处理文件语法测试：`scripts/deployment/test_batch_syntax.py`
- 详细修复文档：`docs/batch_file_syntax_fix.md`
- 修复摘要：`scripts/deployment/FIX_SUMMARY.md`

### 技术细节
- **根本原因**：Windows 批处理解析器在某些环境下对 `if not exist` 语法不兼容
- **解决方案**：使用更兼容的 `if exist + goto` 语法
- **验证方法**：运行 `python scripts/deployment/verify_batch_files.py`
- **打包影响**：无，修复后的文件会自动打包

### 文档更新
- 添加批处理文件修复文档
- 更新打包流程说明
- 添加验证工具使用说明

---

## 历史版本

（此处记录之前的版本更新...）
