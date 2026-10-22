# 修复 ODBC 驱动程序错误

## 错误信息
```
pyodbc.InterfaceError: ('IM002', '[IM002] [Microsoft][ODBC 驱动程序管理器] 未发现数据源名称并且未指定默认驱动程序 (0) (SQLDriverConnect)')
```

## 问题原因

这个错误表示系统中没有找到 SQL Server ODBC 驱动程序，或者 `DATABASE_URL` 配置中指定的驱动程序名称不正确。

## 解决方案

### 步骤 1: 检查已安装的 ODBC 驱动程序

在 PowerShell 中运行：
```powershell
Get-OdbcDriver | Where-Object {$_.Name -like '*SQL Server*'} | Select-Object Name
```

或在 CMD 中运行：
```cmd
odbcad32
```
打开 ODBC 数据源管理器，查看 "驱动程序" 标签页。

### 步骤 2: 安装 ODBC Driver for SQL Server

如果没有安装驱动程序，需要下载并安装：

**推荐版本（按优先级）：**

1. **ODBC Driver 18 for SQL Server**（最新，推荐）
   - 下载地址：https://go.microsoft.com/fwlink/?linkid=2249006
   - 驱动程序名称：`ODBC Driver 18 for SQL Server`

2. **ODBC Driver 17 for SQL Server**（稳定版）
   - 下载地址：https://go.microsoft.com/fwlink/?linkid=2187214
   - 驱动程序名称：`ODBC Driver 17 for SQL Server`

3. **SQL Server Native Client 11.0**（老版本兼容）
   - 随 SQL Server 安装包一起提供
   - 驱动程序名称：`SQL Server Native Client 11.0`

### 步骤 3: 修改 .env 配置

根据安装的驱动程序版本，修改 `.env` 文件中的 `DATABASE_URL`：

#### 使用 ODBC Driver 18（推荐）
```ini
# 基本配置（本地数据库）
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost/bap?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes

# 远程数据库
DATABASE_URL=mssql+aioodbc://username:password@server_ip:1433/bap?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

#### 使用 ODBC Driver 17
```ini
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost/bap?driver=ODBC+Driver+17+for+SQL+Server
```

#### 使用 SQL Server Native Client 11.0
```ini
DATABASE_URL=mssql+aioodbc://sa:YourPassword@localhost/bap?driver=SQL+Server+Native+Client+11.0
```

### 步骤 4: 配置说明

**URL 格式**：
```
mssql+aioodbc://用户名:密码@服务器地址/数据库名?driver=驱动程序名称&其他参数
```

**重要参数**：
- `driver` - ODBC 驱动程序名称（必须与系统安装的驱动程序名称完全一致）
- `TrustServerCertificate=yes` - 信任服务器证书（ODBC Driver 18 必需）
- `Encrypt=no` - 禁用加密（如果服务器不支持 SSL）

**常见配置示例**：

```ini
# 本地开发环境（SQL Server Express）
DATABASE_URL=mssql+aioodbc://sa:Admin123!@localhost/bap?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes

# 远程服务器（指定端口）
DATABASE_URL=mssql+aioodbc://dbuser:Pass@123@192.168.1.100:1433/bap?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes

# Windows 身份验证（集成安全性）
DATABASE_URL=mssql+aioodbc://@localhost/bap?driver=ODBC+Driver+18+for+SQL+Server&Trusted_Connection=yes&TrustServerCertificate=yes
```

### 步骤 5: 验证配置

创建测试脚本 `test_odbc_connection.py`：

```python
import pyodbc
import sys

def test_connection():
    """测试 ODBC 连接"""
    
    # 从 .env 文件读取配置（需要手动替换）
    connection_string = (
        "DRIVER={ODBC Driver 18 for SQL Server};"
        "SERVER=localhost;"
        "DATABASE=bap;"
        "UID=sa;"
        "PWD=YourPassword;"
        "TrustServerCertificate=yes;"
    )
    
    try:
        print("正在连接数据库...")
        conn = pyodbc.connect(connection_string)
        print("✓ 连接成功！")
        
        cursor = conn.cursor()
        cursor.execute("SELECT @@VERSION")
        row = cursor.fetchone()
        print(f"\nSQL Server 版本:\n{row[0]}")
        
        cursor.close()
        conn.close()
        return True
        
    except pyodbc.Error as e:
        print(f"✗ 连接失败: {e}")
        return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
```

运行测试：
```bash
python test_odbc_connection.py
```

### 步骤 6: 常见问题排查

#### 问题 1: 驱动程序名称不匹配
**症状**：仍然报错 "未发现数据源名称"

**解决**：
1. 确认驱动程序名称完全一致（包括空格和大小写）
2. 在 URL 中使用 `+` 替换空格：`ODBC+Driver+18+for+SQL+Server`

#### 问题 2: SSL/TLS 连接错误（ODBC Driver 18）
**症状**：
```
SSL Provider: The certificate chain was issued by an authority that is not trusted
```

**解决**：
在 URL 中添加 `TrustServerCertificate=yes`

#### 问题 3: 密码包含特殊字符
**症状**：解析错误或认证失败

**解决**：
对密码进行 URL 编码：
```python
from urllib.parse import quote_plus

password = "P@ss&word!"
encoded = quote_plus(password)  # 'P%40ss%26word%21'

DATABASE_URL = f"mssql+aioodbc://sa:{encoded}@localhost/bap?driver=..."
```

#### 问题 4: 32位/64位驱动程序不匹配
**症状**：
```
Architecture mismatch between the Driver and Application
```

**解决**：
- 确保 Python 版本（32位/64位）与 ODBC 驱动程序版本一致
- 推荐：使用 64位 Python + 64位 ODBC Driver

### 步骤 7: 打包版本配置

如果使用打包版本（`dist/browser-automation-platform/`），参考 `docs/package_config_update.md`：

```bash
# 运行安装脚本
install.bat

# 按提示输入数据库连接信息
# 驱动程序名称示例：
# - ODBC Driver 18 for SQL Server
# - ODBC Driver 17 for SQL Server
# - SQL Server Native Client 11.0
```

## 快速参考

| 驱动程序版本 | 下载链接 | URL 中的 driver 参数 |
|------------|---------|---------------------|
| ODBC Driver 18 | [下载](https://go.microsoft.com/fwlink/?linkid=2249006) | `ODBC+Driver+18+for+SQL+Server` |
| ODBC Driver 17 | [下载](https://go.microsoft.com/fwlink/?linkid=2187214) | `ODBC+Driver+17+for+SQL+Server` |
| Native Client 11.0 | 随 SQL Server 安装 | `SQL+Server+Native+Client+11.0` |

## 推荐配置

**生产环境**：
```ini
DATABASE_URL=mssql+aioodbc://username:password@server:1433/bap?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes&Encrypt=yes
```

**开发环境**：
```ini
DATABASE_URL=mssql+aioodbc://sa:Admin123!@localhost/bap?driver=ODBC+Driver+18+for+SQL+Server&TrustServerCertificate=yes
```

## 相关文档

- [数据库连接池优化](database_connection_pool_optimization.md)
- [打包版本配置更新](package_config_update.md)
- [环境变量配置说明](env_config_update.md)
