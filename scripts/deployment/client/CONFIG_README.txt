# 配置说明

## 重要提示

首次安装时，`install.bat` 会引导你配置 `.env` 文件。

**新增的重要配置项**（防止被目标网站封禁）：

### 1. 限流控制
```
RATE_LIMIT_ENABLED=true
RATE_LIMIT_WINDOW_MINUTES=60
RATE_LIMIT_MAX_TASKS=100
```

### 2. 智能重试
```
RETRY_MIN_WAIT_MINUTES=60
RETRY_SKIP_IF_PENDING_OVER=100
RETRY_RESPECT_RATE_LIMIT=true
```

### 3. 并发控制
```
MAX_WORKERS=3
```

## 快速参考

详细配置说明请查看 `.env.example` 文件中的注释。

## 配置步骤

1. 运行 `install.bat`
2. 按提示编辑 `.env` 文件
3. 配置数据库连接（必填）
4. 根据需要配置限流参数（推荐）
5. 运行 `startup.bat` 启动服务

## 检查配置

运行 `check_config.bat` 验证配置是否正确。

## 获取帮助

详细文档请参考项目源码中的 `docs/` 目录：
- `docs/package_config_update.md` - 完整配置指南
- `docs/package_config_quick_ref.md` - 快速参考
