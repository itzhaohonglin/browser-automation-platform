# 合并环境变量模板文件方案

## 当前问题
- 项目中同时存在 .env.template 和 .env.example
- 两个文件内容应该相同但需要分别维护
- 打包脚本同时复制两个文件

## 解决方案：统一使用 .env.example

### 步骤1：确认 .env.example 是最新的

确保 .env.example 包含所有最新配置项，包括：
- 数据库配置
- 所有服务配置
- **新的请求级限流配置**

### 步骤2：删除 .env.template

```bash
# 删除 .env.template
del .env.template

# 更新 .gitignore（如果有引用）
# 移除 .env.template 相关行
```

### 步骤3：修改打包脚本

编辑 `scripts\deployment\build_release.bat`（第119-133行）：

**修改前**：
```batch
if exist .env.template (
    copy .env.template "dist\browser-automation-platform\.env.template" >nul
    copy .env.template "dist\browser-automation-platform\.env.example" >nul
    echo [OK] Copied .env.template
) else (
    echo [WARN] .env.template not found
)

if exist .env.example (
    copy .env.example "dist\browser-automation-platform\.env.example" >nul
    echo [OK] Copied .env.example (backup)
) else (
    echo [WARN] .env.example not found
)

REM Verify at least one template exists in output
if not exist "dist\browser-automation-platform\.env.template" (
    if not exist "dist\browser-automation-platform\.env.example" (
        echo [ERROR] No config template found in output!
        echo [ERROR] Please ensure .env.template or .env.example exists in project root
        pause
        exit /b 1
    )
)
```

**修改后**（简化）：
```batch
echo [INFO] Copying configuration template...
if exist .env.example (
    copy .env.example "dist\browser-automation-platform\.env.example" >nul
    copy .env.example "dist\browser-automation-platform\.env.template" >nul
    echo [OK] Copied .env.example
) else (
    echo [ERROR] .env.example not found in project root
    pause
    exit /b 1
)
```

### 步骤4：更新文档

在 README.md 和 CLAUDE.md 中统一引用 `.env.example`：
- 安装说明：复制 .env.example 为 .env
- 配置说明：参考 .env.example

### 步骤5：更新 install.bat 客户端脚本

检查 `scripts\deployment\client\install.bat`，确保只引用 `.env.example`。

## 好处

1. **单一数据源** - 只维护一个模板文件
2. **符合标准** - .env.example 是行业约定
3. **简化流程** - 打包和文档都更简单
4. **避免混淆** - 用户不会疑惑该用哪个

## 向后兼容

打包脚本仍然会生成两个文件（.env.example 和 .env.template），
确保旧的安装脚本仍然可以工作。
