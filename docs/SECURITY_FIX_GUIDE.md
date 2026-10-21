# 安全漏洞快速修复指南

本文档提供最关键安全问题的快速修复方案。

---

## 🔴 修复 1: 限制 CORS 配置（最高优先级）

### 修改文件：`app/core/config.py`

添加 CORS 配置：

```python
class Settings(BaseSettings):
    """应用配置类"""
    
    # ... 现有配置 ...
    
    # CORS 配置
    CORS_ORIGINS: str = "http://localhost:8000,http://127.0.0.1:8000"  # 逗号分隔的允许域名
    
    # ... 其他配置 ...
```

### 修改文件：`app/main.py`

替换 CORS 配置：

```python
# 修改前（不安全）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],        # ❌ 危险！
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 修改后（安全）
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS.split(","),  # ✅ 限制特定域名
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-Requested-With"],
    max_age=3600,  # 预检请求缓存时间
)
```

### 更新 `.env` 文件：

```bash
# 开发环境
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000

# 生产环境（替换为实际域名）
# CORS_ORIGINS=https://your-domain.com,https://www.your-domain.com
```

### 更新 `.env.example` 文件：

```bash
# CORS 配置
CORS_ORIGINS=http://localhost:8000,http://127.0.0.1:8000
```

---

## 🔴 修复 2: 添加基本认证（临时方案）

在实现完整的 JWT 认证前，先使用 HTTP Basic Auth 保护 API。

### 创建文件：`app/core/auth.py`

```python
"""
简单的 HTTP Basic Auth 实现（临时方案）

生产环境应使用 JWT 认证
"""
import secrets
from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.core.config import settings

security = HTTPBasic()

def verify_credentials(
    credentials: HTTPBasicCredentials = Depends(security)
) -> str:
    """验证用户名和密码"""
    
    # 从环境变量读取
    correct_username = getattr(settings, 'API_USERNAME', 'admin')
    correct_password = getattr(settings, 'API_PASSWORD', None)
    
    if not correct_password:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="API_PASSWORD 未配置"
        )
    
    # 使用 secrets.compare_digest 防止时序攻击
    username_correct = secrets.compare_digest(
        credentials.username.encode("utf8"),
        correct_username.encode("utf8")
    )
    password_correct = secrets.compare_digest(
        credentials.password.encode("utf8"),
        correct_password.encode("utf8")
    )
    
    if not (username_correct and password_correct):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
            headers={"WWW-Authenticate": "Basic"},
        )
    
    return credentials.username
```

### 修改文件：`app/core/config.py`

添加认证配置：

```python
class Settings(BaseSettings):
    """应用配置类"""
    
    # ... 现有配置 ...
    
    # API 认证配置（临时方案）
    API_USERNAME: str = "admin"
    API_PASSWORD: Optional[str] = None  # 必须在 .env 中设置
    
    # ... 其他配置 ...
```

### 修改文件：`app/api/config_endpoints.py`

添加认证依赖：

```python
from app.core.auth import verify_credentials

# 在需要保护的端点添加依赖
@router.post("", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_config(
    config_data: ConfigCreate,
    db: AsyncSession = Depends(get_db),
    username: str = Depends(verify_credentials)  # ✅ 添加认证
):
    """创建新的采集配置（需要认证）"""
    logger.info(f"用户 {username} 创建配置: {config_data.config_name}")
    # ... 原有代码 ...

@router.delete("/{config_id}")
async def delete_config(
    config_id: int,
    db: AsyncSession = Depends(get_db),
    username: str = Depends(verify_credentials)  # ✅ 添加认证
):
    """删除配置（需要认证）"""
    logger.info(f"用户 {username} 删除配置 ID: {config_id}")
    # ... 原有代码 ...
```

### 修改文件：`app/api/endpoints.py`

添加认证到关键端点：

```python
from app.core.auth import verify_credentials

@router.post("/task/run", tags=["任务执行"])
async def run_task(
    config_id: int = Query(..., description="配置 ID"),
    limit: int = Query(10, ge=1, le=1000, description="最大任务数"),
    db: AsyncSession = Depends(get_db),
    username: str = Depends(verify_credentials)  # ✅ 添加认证
):
    """执行采集任务（需要认证）"""
    logger.info(f"用户 {username} 触发任务执行: config_id={config_id}")
    # ... 原有代码 ...
```

### 更新 `.env` 文件：

```bash
# API 认证配置
API_USERNAME=admin
API_PASSWORD=your_strong_password_here_min_16_chars
```

### 更新 `.env.example` 文件：

```bash
# API 认证配置（临时方案，生产环境应使用 JWT）
API_USERNAME=admin
API_PASSWORD=change_this_to_strong_password
```

---

## 🔴 修复 3: 加密登录态文件

### 创建文件：`app/core/encryption.py`

```python
"""
登录态文件加密工具
"""
import json
from pathlib import Path
from typing import Dict, Optional
from cryptography.fernet import Fernet
import logging

logger = logging.getLogger(__name__)


class AuthStateEncryption:
    """登录态加密存储"""
    
    def __init__(self, key: bytes):
        """
        初始化加密器
        
        Args:
            key: Fernet 加密密钥（32 字节 base64 编码）
        """
        self.cipher = Fernet(key)
    
    def encrypt_file(self, input_file: Path, output_file: Path) -> bool:
        """
        加密登录态文件
        
        Args:
            input_file: 明文 JSON 文件路径
            output_file: 加密文件输出路径
        
        Returns:
            是否成功
        """
        try:
            # 读取明文数据
            with open(input_file, 'r', encoding='utf-8') as f:
                json_data = f.read()
            
            # 加密
            encrypted_data = self.cipher.encrypt(json_data.encode('utf-8'))
            
            # 写入加密文件
            with open(output_file, 'wb') as f:
                f.write(encrypted_data)
            
            # 设置文件权限（仅所有者可读写）
            output_file.chmod(0o600)
            
            logger.info(f"已加密登录态文件: {input_file} -> {output_file}")
            return True
            
        except Exception as e:
            logger.error(f"加密登录态文件失败: {e}", exc_info=True)
            return False
    
    def decrypt_file(self, encrypted_file: Path) -> Optional[Dict]:
        """
        解密登录态文件
        
        Args:
            encrypted_file: 加密文件路径
        
        Returns:
            解密后的 JSON 数据（字典），失败返回 None
        """
        try:
            # 读取加密数据
            with open(encrypted_file, 'rb') as f:
                encrypted_data = f.read()
            
            # 解密
            decrypted_data = self.cipher.decrypt(encrypted_data)
            
            # 解析 JSON
            json_data = json.loads(decrypted_data.decode('utf-8'))
            
            return json_data
            
        except Exception as e:
            logger.error(f"解密登录态文件失败: {e}", exc_info=True)
            return None
    
    @staticmethod
    def generate_key() -> str:
        """生成新的加密密钥"""
        key = Fernet.generate_key()
        return key.decode('ascii')


def migrate_auth_files():
    """
    迁移工具：将现有明文登录态文件加密
    
    使用方法：
        python -c "from app.core.encryption import migrate_auth_files; migrate_auth_files()"
    """
    from app.core.config import settings
    
    # 检查是否配置了加密密钥
    if not hasattr(settings, 'AUTH_ENCRYPTION_KEY') or not settings.AUTH_ENCRYPTION_KEY:
        key = AuthStateEncryption.generate_key()
        print("=" * 60)
        print("首次运行：请将以下密钥添加到 .env 文件")
        print("=" * 60)
        print(f"AUTH_ENCRYPTION_KEY={key}")
        print("=" * 60)
        return
    
    encryptor = AuthStateEncryption(settings.AUTH_ENCRYPTION_KEY.encode('ascii'))
    auth_dir = Path(settings.AUTH_FILES_DIR)
    
    if not auth_dir.exists():
        print(f"auth_files 目录不存在: {auth_dir}")
        return
    
    # 查找所有明文 JSON 文件
    json_files = list(auth_dir.glob("auth_*.json"))
    
    if not json_files:
        print("未找到需要加密的登录态文件")
        return
    
    print(f"找到 {len(json_files)} 个登录态文件，开始加密...")
    
    for json_file in json_files:
        # 生成加密文件路径
        encrypted_file = json_file.with_suffix('.json.enc')
        
        # 加密
        if encryptor.encrypt_file(json_file, encrypted_file):
            # 备份原文件
            backup_file = json_file.with_suffix('.json.bak')
            json_file.rename(backup_file)
            print(f"✓ {json_file.name} -> {encrypted_file.name} (原文件已备份为 .bak)")
        else:
            print(f"✗ {json_file.name} 加密失败")
    
    print("\n加密完成！请妥善保管 AUTH_ENCRYPTION_KEY")
    print("备份文件 (*.bak) 可以在确认加密成功后删除")
```

### 修改文件：`app/core/config.py`

添加加密密钥配置：

```python
class Settings(BaseSettings):
    """应用配置类"""
    
    # ... 现有配置 ...
    
    # 登录态加密配置
    AUTH_ENCRYPTION_KEY: Optional[str] = None  # Fernet 密钥（32字节base64）
    
    # ... 其他配置 ...
```

### 更新 `.env` 文件：

```bash
# 登录态加密密钥（运行迁移脚本后会生成）
# AUTH_ENCRYPTION_KEY=your_generated_key_here
```

### 迁移现有登录态文件：

```bash
# 1. 生成加密密钥
python -c "from app.core.encryption import migrate_auth_files; migrate_auth_files()"

# 2. 将输出的密钥添加到 .env 文件
# AUTH_ENCRYPTION_KEY=xxxxx

# 3. 再次运行迁移脚本进行加密
python -c "from app.core.encryption import migrate_auth_files; migrate_auth_files()"

# 4. 确认加密成功后，删除备份文件
# rm auth_files/*.bak
```

---

## 🟡 修复 4: 添加选择器验证

### 修改文件：`app/schemas/config.py`

添加验证器：

```python
import re
from pydantic import field_validator

class ConfigBase(BaseModel):
    """配置基础 Schema"""
    
    # ... 现有字段 ...
    
    @field_validator('submit_selector', 'wait_selector', 'pagination_selector')
    @classmethod
    def validate_selector(cls, v: str) -> str:
        """验证 CSS 选择器格式"""
        if not v:
            return v
        
        # 只允许安全的选择器字符
        # 允许：字母、数字、空格、. # [ ] = " ' : - > + ~ ( )
        pattern = r'^[a-zA-Z0-9\s\.\#\[\]\=\"\'\:\-\>\+\~\(\)]+$'
        
        if not re.match(pattern, v):
            raise ValueError(
                f'选择器包含不允许的字符: {v}'
            )
        
        # 检查长度
        if len(v) > 500:
            raise ValueError(f'选择器过长: {len(v)} 字符（最大 500）')
        
        return v
    
    @field_validator('target_url', 'login_url')
    @classmethod
    def validate_url_scheme(cls, v: HttpUrl) -> HttpUrl:
        """验证 URL 协议"""
        if v is None:
            return v
        
        scheme = str(v).split('://')[0]
        if scheme not in ['http', 'https']:
            raise ValueError(f'只允许 http/https 协议，当前: {scheme}')
        
        return v
```

---

## 📋 快速修复检查清单

运行以下命令检查修复是否完成：

```bash
# 1. 检查 CORS 配置
grep "allow_origins=\[" app/main.py
# 应该看到：allow_origins=settings.CORS_ORIGINS.split(",")

# 2. 检查是否添加了认证
grep "verify_credentials" app/api/config_endpoints.py
# 应该能找到多个匹配

# 3. 检查环境变量配置
grep "API_PASSWORD" .env
grep "AUTH_ENCRYPTION_KEY" .env
grep "CORS_ORIGINS" .env

# 4. 检查文件权限
ls -la .env
# 应该是：-rw------- (600)

ls -la auth_files/
# 所有文件应该是：-rw------- (600)

# 5. 运行验证
python scripts/verify_connection_pool_config.py
```

---

## ⚠️ 重要提示

1. **立即修改默认密码**
   - 修改 `.env` 中的 `API_PASSWORD`
   - 使用强密码（至少 16 个字符，包含大小写字母、数字、特号）

2. **重启应用使配置生效**
   ```bash
   # 停止应用
   # 重新启动
   python -m app.main
   ```

3. **测试认证是否生效**
   ```bash
   # 未认证应该返回 401
   curl http://localhost:8000/api/configs
   
   # 使用认证应该返回 200
   curl -u admin:your_password http://localhost:8000/api/configs
   ```

4. **备份加密密钥**
   - 将 `AUTH_ENCRYPTION_KEY` 保存到安全位置
   - 丢失密钥将无法解密登录态文件

---

## 📞 需要帮助？

如果在修复过程中遇到问题，请查看：
- `docs/SECURITY_AUDIT_REPORT.md` - 完整安全审计报告
- `CLAUDE.md` - 项目开发指南
- FastAPI 文档: https://fastapi.tiangolo.com/tutorial/security/
