# 构建脚本修复总结

## 修复日期
2026-10-21

## 问题描述

### 问题1：.env.example 中文注释乱码
- **现象**：运行 `build_release.bat` 后，生成的 `dist/browser-automation-platform/.env.example` 中的中文注释显示为乱码
- **根本原因**：Windows 批处理的 `copy` 命令不保持 UTF-8 编码，会按系统默认编码（GBK）处理文件
- **影响**：用户看到乱码配置文件，影响使用体验

### 问题2：任务队列执行缓慢
- **现象**：执行完一个任务后，长时间不执行下一个任务，大量任务积压
- **根本原因**：配置参数过于保守
  - `MAX_WORKERS=1`：每次只能执行1个任务
  - `DISPATCH_INTERVAL_MINUTES=30`：每30分钟才分发一次任务
- **影响**：1625个任务需要约34天才能完成

## 解决方案

### 问题1：编码乱码修复

**方案**：使用 Python 脚本复制文件，显式指定 UTF-8 编码

**实施步骤**：

1. **创建 UTF-8 复制工具**：`scripts/deployment/copy_utf8_file.py`
   - 使用 `Path.read_text(encoding='utf-8')` 读取
   - 使用 `Path.write_text(..., encoding='utf-8')` 写入
   - 完美保持 UTF-8 BOM 编码

2. **修改构建脚本**：`scripts/deployment/build_release.bat`
   - 将 `copy .env.example ...` 替换为 `%PYTHON% scripts\deployment\copy_utf8_file.py ...`
   - 添加错误检查

**验证结果**：
- ✅ 字节级别完全一致（5231 bytes）
- ✅ UTF-8 BOM 正确保留（efbbbf）
- ✅ 中文内容完整无损

**注意事项**：
- Windows 终端（cmd/bash）显示 UTF-8 文件时会出现乱码，这是**终端显示问题**，不是文件问题
- 在文本编辑器（如 Notepad++、VS Code）中打开可正常显示中文
- Python 应用读取时完全正常

### 问题2：任务执行性能优化

**方案**：调整配置参数，提高并发度和分发频率

**推荐配置**（针对1625个任务）：

```bash
# .env 文件
MAX_WORKERS=5                    # 同时执行5个任务
DISPATCH_INTERVAL_MINUTES=5      # 每5分钟分发一次
```

**性能对比**：

| 配置 | 并发数 | 分发间隔 | 预计总耗时 |
|------|--------|----------|------------|
| 当前（慢） | 1 | 30分钟 | ~812小时（34天） |
| 优化后（快） | 5 | 5分钟 | ~27小时 |
| 提速比 | | | **30倍** |

**文档**：详细说明已保存至 `docs/task_execution_optimization.md`

## 修改文件清单

### 新增文件
1. `scripts/deployment/copy_utf8_file.py` - UTF-8 文件复制工具
2. `docs/task_execution_optimization.md` - 任务执行性能优化指南
3. `docs/build_fixes_summary.md` - 本文档

### 修改文件
1. `scripts/deployment/build_release.bat` - 使用 Python 脚本复制配置文件

## 测试验证

### 编码测试
```bash
# 1. 运行构建脚本
scripts\deployment\build_release.bat

# 2. 检查生成的文件（在文本编辑器中打开）
notepad dist\browser-automation-platform\.env.example

# 预期：中文注释正常显示
```

### 性能测试
```bash
# 1. 编辑 .env 文件
MAX_WORKERS=5
DISPATCH_INTERVAL_MINUTES=5

# 2. 重启服务
startup.bat

# 3. 观察日志
type logs\app.log | findstr "分发"

# 预期：每5分钟分发一批任务，每批最多5个
```

## 后续建议

### 给开发者
1. 建议将 UTF-8 复制工具集成到其他需要处理中文文件的脚本中
2. 考虑在 CLAUDE.md 中添加编码规范说明

### 给用户
1. 首次部署建议从低配置开始（`MAX_WORKERS=2`），观察资源占用后逐步调高
2. 如果目标网站有反爬虫机制，启用 `REQUEST_RATE_LIMIT_ENABLED=true`
3. 定期查看监控看板，及时调整配置参数

## 技术细节

### 为什么 PowerShell Copy-Item 不行？
PowerShell 的 `Copy-Item` 默认按二进制复制，理论上应该保持编码，但实际测试中仍出现问题。可能原因：
- PowerShell 版本差异
- 系统编码设置影响
- BOM 处理不一致

### 为什么选择 Python？
- ✅ 项目已依赖 Python 环境
- ✅ 编码处理明确可控
- ✅ 跨平台兼容性好
- ✅ 易于维护和扩展

### UTF-8 BOM 的作用
- BOM（Byte Order Mark）：`efbbbf`
- 帮助编辑器/应用识别文件编码
- Windows 记事本需要 BOM 才能正确识别 UTF-8
- 建议保留（我们的脚本会自动保留）

## 常见问题

**Q1：终端显示乱码正常吗？**
A：正常。Windows cmd/bash 使用 GBK 编码，显示 UTF-8 文件时会乱码。在编辑器中打开或应用读取时都是正常的。

**Q2：为什么不直接改成 GBK 编码？**
A：GBK 不是标准编码，跨平台兼容性差。UTF-8 是国际标准，Python/FastAPI 默认使用 UTF-8。

**Q3：增加 MAX_WORKERS 后系统卡顿怎么办？**
A：降低并发数或启用请求限流。参考 `docs/task_execution_optimization.md`。

**Q4：修改配置后需要重新打包吗？**
A：不需要。直接修改打包目录下的 `.env` 文件，然后重启服务即可。

**Q5：.env 文件中没有 DISPATCH_INTERVAL_MINUTES 怎么办？**
A：你的 `.env` 文件是旧版本。解决方法：
- **方法1（推荐）**：手动添加缺失的配置项，参考 `docs/env_task_scheduling_snippet.txt`
- **方法2**：备份当前 `.env`，从 `.env.template` 重新生成，然后填入你的实际配置（DATABASE_URL等）
- 详细说明见 `docs/task_execution_optimization.md`
