# 打包指南

## 打包前检查

✅ 所有检查项已通过：

- [x] 关键文件完整
- [x] Python依赖已安装
- [x] PyInstaller已安装
- [x] Playwright浏览器已安装（chromium-1134）
- [x] Windows事件循环策略已正确设置
- [x] 配置模板存在

## 开始打包

### 方法1：使用打包脚本（推荐）

```bat
build_release.bat
```

脚本会自动执行以下步骤：
1. 清理旧的构建文件
2. 使用PyInstaller打包应用
3. 复制Playwright浏览器
4. 创建目录结构
5. 复制客户端脚本和配置模板
6. 生成版本信息

### 方法2：手动打包

```bat
# 1. 清理旧构建
rmdir /s /q build dist

# 2. 打包
python -m PyInstaller build.spec

# 3. 复制浏览器（可选，客户端可以后续安装）
# 见 build_release.bat 中的详细步骤
```

## 打包时间

预计需要：**5-10分钟**

取决于：
- CPU性能
- 磁盘速度
- 是否复制Playwright浏览器（约500MB）

## 打包输出

### 目录结构

```
dist/browser-automation-platform/
├── browser-automation-platform.exe    # 主程序
├── _internal/                         # 依赖文件
│   ├── playwright/                    # Playwright依赖
│   │   └── driver/package/.local-browsers/  # 浏览器（如果打包）
│   └── ...
├── static/                            # 前端文件
├── alembic/                          # 数据库迁移
├── alembic.ini                       # 迁移配置
├── auth_files/                       # 登录态目录（空）
├── logs/                             # 日志目录（空）
├── import_data/                      # 数据导入目录
├── .env.template                     # 配置模板
├── startup.bat                       # 启动脚本
├── stop.bat                          # 停止脚本
├── install_playwright.bat            # 安装浏览器脚本
├── import_data.bat                   # 数据导入脚本
└── VERSION.txt                       # 版本信息
```

### 文件大小

- 不含浏览器：约 150-200 MB
- 含浏览器：约 650-700 MB

## 测试打包结果

### 1. 本地测试

```bat
cd dist\browser-automation-platform
startup.bat
```

访问：http://127.0.0.1:8000

### 2. 测试命令行参数

```bat
# 查看帮助
browser-automation-platform.exe --help

# 数据库迁移
browser-automation-platform.exe --migrate

# 安装浏览器
browser-automation-platform.exe --install-browser

# 初始化配置
browser-automation-platform.exe --init-config

# 导入任务
browser-automation-platform.exe --import-jobs import_data\jobs.json
```

## 已知问题和解决方案

### 问题1：NotImplementedError (Windows事件循环)

**已解决** ✅

- 在 `app/main.py` 第13行设置了 `WindowsProactorEventLoopPolicy`
- 在 `app/services/executor.py` 第21行也设置了策略
- 确保在任何异步操作之前设置

### 问题2：详情关闭按钮问题

**已解决** ✅

- 修改为使用 ESC 键关闭详情弹窗
- 关闭后等待2秒确保弹窗完全消失
- 配置中设置 `close_method: "escape"`

### 问题3：详情数据提取0行

**待解决** ⚠️

当前状态：
- 第1条详情：成功提取24条（带分页）
- 第2条详情：0条
- 第3条详情：0条

可能原因：
- 弹窗未完全关闭，影响下一个弹窗打开
- jqGrid数据加载需要更长时间
- 需要增加等待时间或添加显式等待条件

**不影响打包**，这是运行时逻辑问题，可以在打包后继续调试。

## 打包后分发

### 1. 压缩

```bat
# 推荐使用 7-Zip 或 WinRAR
# 压缩 dist\browser-automation-platform\ 目录
```

### 2. 分发清单

必须提供给客户：
- [x] 压缩包（browser-automation-platform.zip）
- [x] 部署文档（docs/deployment_windows.md）
- [x] 配置说明（.env.template 中的注释）
- [x] 快速启动指南（startup.bat 自带说明）

可选文档：
- [ ] API文档（访问 /docs 查看）
- [ ] 配置示例（如NHSA配置）
- [ ] 常见问题FAQ

## 客户端部署步骤（简要）

1. 解压到目标目录（如 `C:\bap\`）
2. 复制 `.env.template` 为 `.env`
3. 编辑 `.env` 配置数据库连接
4. 双击 `startup.bat` 启动
5. 访问 http://127.0.0.1:8000

详见：`docs/deployment_windows.md`

## 注意事项

### 数据库

- 打包程序**不包含**SQL Server
- 客户端需要自行安装SQL Server
- 支持 SQL Server 2016 及以上版本

### 浏览器

如果打包时未包含浏览器：
- 客户端首次运行时执行 `install_playwright.bat`
- 或运行：`browser-automation-platform.exe --install-browser`
- 需要网络连接，下载约500MB

### 配置文件

- `.env` 文件**不会被打包**（包含敏感信息）
- 客户端需要根据 `.env.template` 自行创建
- 必须配置正确的 `DATABASE_URL`

### 防火墙

客户端需要：
- 允许程序访问网络（下载浏览器、访问采集目标站点）
- 开放端口 8000（默认，可在.env中修改）

## 版本管理

当前版本：**v1.0.0**

版本信息存储在：
- `dist/browser-automation-platform/VERSION.txt`
- 包含构建时间、构建主机等信息

## 后续更新

如果代码有更新：

1. 修改代码
2. 测试验证
3. 更新版本号（VERSION.txt）
4. 重新运行 `build_release.bat`
5. 测试新版本
6. 分发给客户

## 技术支持

如遇问题：
1. 检查 `logs/` 目录下的日志文件
2. 查看控制台输出（console模式）
3. 参考 `docs/` 目录下的文档
4. 联系开发团队

---

**最后更新**: 2026-10-11
**状态**: ✅ 可以打包
