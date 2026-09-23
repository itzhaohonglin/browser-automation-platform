# CrawlerConfig CRUD API 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为浏览器自动化数据采集平台添加完整的配置 CRUD API（创建、读取、更新、删除）

**Architecture:** 使用 FastAPI + Pydantic Schema 实现 RESTful API，通过 SQLAlchemy ORM 操作数据库。分层架构：API Router → Pydantic 验证 → 业务逻辑 → ORM → 数据库。

**Tech Stack:** FastAPI 0.115.0, Pydantic v2, SQLAlchemy 2.0.35, pytest

---

## 文件结构规划

**新增文件：**
- `app/schemas/__init__.py` - schemas 包初始化
- `app/schemas/config.py` - 配置相关的 Pydantic Schema
- `app/api/config_endpoints.py` - 配置 CRUD 路由
- `tests/test_config_crud.py` - 配置 CRUD API 测试

**修改文件：**
- `app/main.py` - 注册新路由器

---

## Task 1: 创建 Schemas 包结构

**Files:**
- Create: `app/schemas/__init__.py`

- [ ] **Step 1: 创建 schemas 目录**

```bash
mkdir -p app/schemas
```

- [ ] **Step 2: 创建包初始化文件**

在 `app/schemas/__init__.py` 写入：

```python
# app/schemas/__init__.py
"""Pydantic schemas for request/response validation"""
```

- [ ] **Step 3: 验证目录结构**

运行：`ls -la app/schemas/`

预期输出：包含 `__init__.py` 文件

- [ ] **Step 4: 提交**

```bash
git add app/schemas/__init__.py
git commit -m "chore: create schemas package structure"
```

---

## Task 2: 实现配置 Pydantic Schemas（第 1 部分 - 基础类）

**Files:**
- Create: `app/schemas/config.py`

- [ ] **Step 1: 编写测试 - ConfigBase 基本验证**

创建 `tests/test_config_schemas.py`：

```python
import pytest
from pydantic import ValidationError
from app.schemas.config import ConfigBase


def test_config_base_required_fields():
    """测试必填字段验证"""
    with pytest.raises(ValidationError) as exc_info:
        ConfigBase(
            config_name="测试配置"
            # 缺少其他必填字段
        )
    
    errors = exc_info.value.errors()
    required_fields = {err['loc'][0] for err in errors}
    
    assert 'target_url' in required_fields
    assert 'input_configs' in required_fields
    assert 'submit_selector' in required_fields
    assert 'wait_selector' in required_fields
    assert 'fields_mapping' in required_fields


def test_config_base_valid_data():
    """测试有效数据"""
    config = ConfigBase(
        config_name="测试配置",
        target_url="https://www.example.com",
        input_configs={"inputs": []},
        submit_selector="button.submit",
        wait_selector=".results",
        fields_mapping={"list_selector": ".item", "fields": []}
    )
    
    assert config.config_name == "测试配置"
    assert str(config.target_url) == "https://www.example.com/"
    assert config.need_login is False
    assert config.max_pages == 1
    assert config.is_active is True
```

- [ ] **Step 2: 运行测试验证失败**

运行：`pytest tests/test_config_schemas.py::test_config_base_required_fields -v`

预期：FAIL - "No module named 'app.schemas.config'"

- [ ] **Step 3: 实现 ConfigBase**

创建 `app/schemas/config.py`：

```python
# app/schemas/config.py
from typing import Optional, Dict
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, ConfigDict


class ConfigBase(BaseModel):
    """配置基础 Schema"""
    
    config_name: str = Field(..., min_length=1, max_length=100, description="配置名称")
    target_url: HttpUrl = Field(..., description="目标页面 URL")
    need_login: bool = Field(default=False, description="是否需要登录")
    auth_profile: Optional[str] = Field(None, max_length=50, description="登录态标识")
    login_url: Optional[HttpUrl] = Field(None, description="登录页地址")
    input_configs: Dict = Field(..., description="输入框配置（JSON）")
    submit_selector: str = Field(..., min_length=1, max_length=200, description="提交按钮选择器")
    wait_selector: str = Field(..., min_length=1, max_length=200, description="等待加载选择器")
    fields_mapping: Dict = Field(..., description="字段映射规则（JSON）")
    pagination_selector: Optional[str] = Field(None, max_length=200, description="下一页按钮选择器")
    max_pages: int = Field(default=1, ge=1, description="最大翻页数")
    is_active: bool = Field(default=True, description="是否启用")
```

- [ ] **Step 4: 运行测试验证通过**

运行：`pytest tests/test_config_schemas.py -v`

预期：PASS - 所有测试通过

- [ ] **Step 5: 提交**

```bash
git add app/schemas/config.py tests/test_config_schemas.py
git commit -m "feat: add ConfigBase schema with validation"
```

---

## Task 3: 实现 ConfigCreate Schema（带验证器）

**Files:**
- Modify: `app/schemas/config.py`
- Modify: `tests/test_config_schemas.py`

- [ ] **Step 1: 编写测试 - auth_profile 验证**

在 `tests/test_config_schemas.py` 添加：

```python
from app.schemas.config import ConfigCreate


def test_config_create_need_login_without_auth_profile():
    """测试 need_login=True 但缺少 auth_profile"""
    with pytest.raises(ValidationError) as exc_info:
        ConfigCreate(
            config_name="测试配置",
            target_url="https://www.example.com",
            need_login=True,  # 需要登录但没有提供 auth_profile
            input_configs={"inputs": []},
            submit_selector="button",
            wait_selector=".results",
            fields_mapping={"list_selector": ".item", "fields": []}
        )
    
    assert "need_login=True 时必须提供 auth_profile" in str(exc_info.value)


def test_config_create_need_login_with_auth_profile():
    """测试 need_login=True 且提供 auth_profile"""
    config = ConfigCreate(
        config_name="测试配置",
        target_url="https://www.example.com",
        need_login=True,
        auth_profile="test_profile",
        input_configs={"inputs": []},
        submit_selector="button",
        wait_selector=".results",
        fields_mapping={"list_selector": ".item", "fields": []}
    )
    
    assert config.need_login is True
    assert config.auth_profile == "test_profile"


def test_config_create_url_validation():
    """测试 URL 格式验证"""
    with pytest.raises(ValidationError) as exc_info:
        ConfigCreate(
            config_name="测试配置",
            target_url="not-a-valid-url",  # 无效 URL
            input_configs={"inputs": []},
            submit_selector="button",
            wait_selector=".results",
            fields_mapping={"list_selector": ".item", "fields": []}
        )
    
    errors = exc_info.value.errors()
    assert any('url' in str(err).lower() for err in errors)
```

- [ ] **Step 2: 运行测试验证失败**

运行：`pytest tests/test_config_schemas.py::test_config_create_need_login_without_auth_profile -v`

预期：FAIL - "No module named 'ConfigCreate'"

- [ ] **Step 3: 实现 ConfigCreate**

在 `app/schemas/config.py` 添加：

```python
from pydantic import model_validator


class ConfigCreate(ConfigBase):
    """创建配置的请求 Schema"""
    
    @model_validator(mode='after')
    def validate_auth_profile(self) -> 'ConfigCreate':
        """验证：need_login=True 时 auth_profile 必填"""
        if self.need_login and not self.auth_profile:
            raise ValueError('need_login=True 时必须提供 auth_profile')
        return self
```

- [ ] **Step 4: 运行测试验证通过**

运行：`pytest tests/test_config_schemas.py -v -k "test_config_create"`

预期：PASS - 所有 ConfigCreate 测试通过

- [ ] **Step 5: 提交**

```bash
git add app/schemas/config.py tests/test_config_schemas.py
git commit -m "feat: add ConfigCreate schema with auth_profile validation"
```

---

## Task 4: 实现 ConfigUpdate Schema

**Files:**
- Modify: `app/schemas/config.py`
- Modify: `tests/test_config_schemas.py`

- [ ] **Step 1: 编写测试 - 部分更新验证**

在 `tests/test_config_schemas.py` 添加：

```python
from app.schemas.config import ConfigUpdate


def test_config_update_partial_fields():
    """测试部分更新（所有字段可选）"""
    update = ConfigUpdate(max_pages=10, is_active=False)
    
    assert update.max_pages == 10
    assert update.is_active is False
    assert update.config_name is None
    assert update.target_url is None


def test_config_update_need_login_validation():
    """测试更新时 need_login=True 必须提供 auth_profile"""
    with pytest.raises(ValidationError) as exc_info:
        ConfigUpdate(
            need_login=True
            # 缺少 auth_profile
        )
    
    assert "need_login=True 时必须提供 auth_profile" in str(exc_info.value)


def test_config_update_with_auth_profile():
    """测试更新 need_login 和 auth_profile"""
    update = ConfigUpdate(
        need_login=True,
        auth_profile="new_profile"
    )
    
    assert update.need_login is True
    assert update.auth_profile == "new_profile"
```

- [ ] **Step 2: 运行测试验证失败**

运行：`pytest tests/test_config_schemas.py::test_config_update_partial_fields -v`

预期：FAIL - "No module named 'ConfigUpdate'"

- [ ] **Step 3: 实现 ConfigUpdate**

在 `app/schemas/config.py` 添加：

```python
class ConfigUpdate(BaseModel):
    """更新配置的请求 Schema（所有字段可选）"""
    
    config_name: Optional[str] = Field(None, min_length=1, max_length=100, description="配置名称")
    target_url: Optional[HttpUrl] = Field(None, description="目标页面 URL")
    need_login: Optional[bool] = Field(None, description="是否需要登录")
    auth_profile: Optional[str] = Field(None, max_length=50, description="登录态标识")
    login_url: Optional[HttpUrl] = Field(None, description="登录页地址")
    input_configs: Optional[Dict] = Field(None, description="输入框配置（JSON）")
    submit_selector: Optional[str] = Field(None, min_length=1, max_length=200, description="提交按钮选择器")
    wait_selector: Optional[str] = Field(None, min_length=1, max_length=200, description="等待加载选择器")
    fields_mapping: Optional[Dict] = Field(None, description="字段映射规则（JSON）")
    pagination_selector: Optional[str] = Field(None, max_length=200, description="下一页按钮选择器")
    max_pages: Optional[int] = Field(None, ge=1, description="最大翻页数")
    is_active: Optional[bool] = Field(None, description="是否启用")
    
    @model_validator(mode='after')
    def validate_auth_profile(self) -> 'ConfigUpdate':
        """验证：need_login=True 时 auth_profile 必填"""
        if self.need_login is True and not self.auth_profile:
            raise ValueError('need_login=True 时必须提供 auth_profile')
        return self
```

- [ ] **Step 4: 运行测试验证通过**

运行：`pytest tests/test_config_schemas.py -v -k "test_config_update"`

预期：PASS - 所有 ConfigUpdate 测试通过

- [ ] **Step 5: 提交**

```bash
git add app/schemas/config.py tests/test_config_schemas.py
git commit -m "feat: add ConfigUpdate schema for partial updates"
```

---

## Task 5: 实现 ConfigResponse 和 ConfigListResponse

**Files:**
- Modify: `app/schemas/config.py`
- Modify: `tests/test_config_schemas.py`

- [ ] **Step 1: 编写测试 - 响应 Schema**

在 `tests/test_config_schemas.py` 添加：

```python
from datetime import datetime
from app.schemas.config import ConfigResponse, ConfigListResponse
from app.models.config import CrawlerConfig


def test_config_response_from_orm():
    """测试从 ORM 模型创建响应"""
    # 模拟 ORM 对象
    class MockConfig:
        id = 1
        config_name = "测试配置"
        target_url = "https://www.example.com"
        need_login = False
        auth_profile = None
        login_url = None
        input_configs = {"inputs": []}
        submit_selector = "button"
        wait_selector = ".results"
        fields_mapping = {"list_selector": ".item", "fields": []}
        pagination_selector = None
        max_pages = 1
        is_active = True
        created_at = datetime(2026, 9, 23, 10, 0, 0)
    
    response = ConfigResponse.model_validate(MockConfig())
    
    assert response.id == 1
    assert response.config_name == "测试配置"
    assert response.created_at == datetime(2026, 9, 23, 10, 0, 0)


def test_config_list_response():
    """测试列表响应"""
    list_response = ConfigListResponse(
        total=100,
        page=1,
        page_size=20,
        items=[]
    )
    
    assert list_response.total == 100
    assert list_response.page == 1
    assert list_response.page_size == 20
    assert len(list_response.items) == 0
```

- [ ] **Step 2: 运行测试验证失败**

运行：`pytest tests/test_config_schemas.py::test_config_response_from_orm -v`

预期：FAIL - "No module named 'ConfigResponse'"

- [ ] **Step 3: 实现响应 Schemas**

在 `app/schemas/config.py` 添加：

```python
from typing import List


class ConfigResponse(ConfigBase):
    """配置响应 Schema"""
    
    id: int = Field(..., description="配置 ID")
    created_at: datetime = Field(..., description="创建时间")
    
    model_config = ConfigDict(from_attributes=True)


class ConfigListResponse(BaseModel):
    """配置列表响应 Schema"""
    
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    items: List[ConfigResponse] = Field(..., description="配置列表")
```

- [ ] **Step 4: 运行测试验证通过**

运行：`pytest tests/test_config_schemas.py -v`

预期：PASS - 所有 Schema 测试通过

- [ ] **Step 5: 提交**

```bash
git add app/schemas/config.py tests/test_config_schemas.py
git commit -m "feat: add ConfigResponse and ConfigListResponse schemas"
```

---

## Task 6: 实现创建配置端点（POST）

**Files:**
- Create: `app/api/config_endpoints.py`
- Create: `tests/test_config_crud.py`

- [ ] **Step 1: 编写测试 - 创建配置成功**

创建 `tests/test_config_crud.py`：

```python
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.main import app
from app.models.config import CrawlerConfig
from app.core.database import get_db


@pytest.fixture
async def client():
    """测试客户端"""
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def db_session():
    """测试数据库 session"""
    async for session in get_db():
        yield session


@pytest.mark.asyncio
async def test_create_config_success(client: AsyncClient, db_session: AsyncSession):
    """测试创建配置成功"""
    payload = {
        "config_name": "测试配置",
        "target_url": "https://www.example.com",
        "need_login": False,
        "input_configs": {"inputs": [{"selector": "#q", "param_key": "keyword"}]},
        "submit_selector": "button.submit",
        "wait_selector": ".results",
        "fields_mapping": {
            "list_selector": ".item",
            "fields": [
                {"name": "title", "selector": ".title", "attr": "text"}
            ]
        },
        "max_pages": 5
    }
    
    response = await client.post("/api/configs", json=payload)
    
    assert response.status_code == 201
    data = response.json()
    
    assert data["config_name"] == "测试配置"
    assert data["max_pages"] == 5
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_create_config_validation_error(client: AsyncClient):
    """测试创建配置字段验证失败"""
    payload = {
        "config_name": "测试配置",
        "target_url": "invalid-url",  # 无效 URL
        "input_configs": {},
        "submit_selector": "button",
        "wait_selector": ".results",
        "fields_mapping": {}
    }
    
    response = await client.post("/api/configs", json=payload)
    
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_create_config_need_login_without_profile(client: AsyncClient):
    """测试 need_login=True 但缺少 auth_profile"""
    payload = {
        "config_name": "测试配置",
        "target_url": "https://www.example.com",
        "need_login": True,  # 缺少 auth_profile
        "input_configs": {"inputs": []},
        "submit_selector": "button",
        "wait_selector": ".results",
        "fields_mapping": {"list_selector": ".item", "fields": []}
    }
    
    response = await client.post("/api/configs", json=payload)
    
    assert response.status_code == 422
    assert "auth_profile" in response.text.lower()
```

- [ ] **Step 2: 运行测试验证失败**

运行：`pytest tests/test_config_crud.py::test_create_config_success -v`

预期：FAIL - "404 Not Found" (路由不存在)

- [ ] **Step 3: 实现创建配置端点**

创建 `app/api/config_endpoints.py`：

```python
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.config import CrawlerConfig
from app.schemas.config import ConfigCreate, ConfigResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/configs", tags=["配置管理"])


@router.post("", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_config(
    config_data: ConfigCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    创建新的采集配置
    
    Args:
        config_data: 配置数据
        db: 数据库 session
    
    Returns:
        创建的配置（包含 ID 和创建时间）
    """
    logger.info(f"创建配置: {config_data.config_name}")
    
    try:
        # 创建 ORM 对象
        config = CrawlerConfig(
            config_name=config_data.config_name,
            target_url=str(config_data.target_url),
            need_login=config_data.need_login,
            auth_profile=config_data.auth_profile,
            login_url=str(config_data.login_url) if config_data.login_url else None,
            input_configs=config_data.input_configs,
            submit_selector=config_data.submit_selector,
            wait_selector=config_data.wait_selector,
            fields_mapping=config_data.fields_mapping,
            pagination_selector=config_data.pagination_selector,
            max_pages=config_data.max_pages,
            is_active=config_data.is_active
        )
        
        db.add(config)
        await db.commit()
        await db.refresh(config)
        
        logger.info(f"配置创建成功: ID={config.id}")
        
        return config
        
    except Exception as e:
        await db.rollback()
        logger.error(f"创建配置失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="创建配置失败"
        )
```

- [ ] **Step 4: 注册路由器到 main.py**

在 `app/main.py` 中添加导入和注册：

```python
# 在文件顶部添加导入
from app.api.config_endpoints import router as config_router

# 在 app.include_router(router) 之后添加
app.include_router(config_router)
```

- [ ] **Step 5: 运行测试验证通过**

运行：`pytest tests/test_config_crud.py -v -k "test_create_config"`

预期：PASS - 所有创建配置测试通过

- [ ] **Step 6: 提交**

```bash
git add app/api/config_endpoints.py app/main.py tests/test_config_crud.py
git commit -m "feat: add POST /api/configs endpoint for creating configs"
```

---

## Task 7: 实现获取配置列表端点（GET /api/configs）

**Files:**
- Modify: `app/api/config_endpoints.py`
- Modify: `tests/test_config_crud.py`

- [ ] **Step 1: 编写测试 - 获取配置列表**

在 `tests/test_config_crud.py` 添加：

```python
@pytest.mark.asyncio
async def test_get_configs_empty_list(client: AsyncClient):
    """测试获取空配置列表"""
    response = await client.get("/api/configs")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] >= 0
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert isinstance(data["items"], list)


@pytest.mark.asyncio
async def test_get_configs_with_pagination(client: AsyncClient):
    """测试分页查询"""
    response = await client.get("/api/configs?page=2&page_size=10")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["page"] == 2
    assert data["page_size"] == 10


@pytest.mark.asyncio
async def test_get_configs_filter_by_active(client: AsyncClient):
    """测试按 is_active 过滤"""
    response = await client.get("/api/configs?is_active=true")
    
    assert response.status_code == 200
    data = response.json()
    
    # 验证所有返回的配置都是激活状态
    for item in data["items"]:
        assert item["is_active"] is True
```

- [ ] **Step 2: 运行测试验证失败**

运行：`pytest tests/test_config_crud.py::test_get_configs_empty_list -v`

预期：FAIL - "404 Not Found"

- [ ] **Step 3: 实现获取配置列表端点**

在 `app/api/config_endpoints.py` 添加：

```python
from app.schemas.config import ConfigListResponse
from fastapi import Query
from sqlalchemy import func


@router.get("", response_model=ConfigListResponse)
async def get_configs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    is_active: Optional[bool] = Query(None, description="过滤启用/禁用状态"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取配置列表（支持分页和过滤）
    
    Args:
        page: 页码（从 1 开始）
        page_size: 每页大小（最大 100）
        is_active: 过滤条件（可选）
        db: 数据库 session
    
    Returns:
        配置列表（含分页信息）
    """
    logger.info(f"查询配置列表: page={page}, page_size={page_size}, is_active={is_active}")
    
    try:
        # 构建查询条件
        stmt = select(CrawlerConfig)
        if is_active is not None:
            stmt = stmt.where(CrawlerConfig.is_active == is_active)
        
        # 查询总数
        count_stmt = select(func.count(CrawlerConfig.id))
        if is_active is not None:
            count_stmt = count_stmt.where(CrawlerConfig.is_active == is_active)
        
        total_result = await db.execute(count_stmt)
        total = total_result.scalar() or 0
        
        # 分页查询
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size).order_by(CrawlerConfig.id.desc())
        
        result = await db.execute(stmt)
        configs = result.scalars().all()
        
        logger.info(f"查询到 {len(configs)} 条配置，总数 {total}")
        
        return ConfigListResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=configs
        )
        
    except Exception as e:
        logger.error(f"查询配置列表失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="查询配置列表失败"
        )
```

- [ ] **Step 4: 运行测试验证通过**

运行：`pytest tests/test_config_crud.py -v -k "test_get_configs"`

预期：PASS - 所有列表查询测试通过

- [ ] **Step 5: 提交**

```bash
git add app/api/config_endpoints.py tests/test_config_crud.py
git commit -m "feat: add GET /api/configs endpoint with pagination and filtering"
```

---

## Task 8: 实现获取配置详情端点（GET /api/configs/{id}）

**Files:**
- Modify: `app/api/config_endpoints.py`
- Modify: `tests/test_config_crud.py`

- [ ] **Step 1: 编写测试 - 获取配置详情**

在 `tests/test_config_crud.py` 添加：

```python
@pytest.mark.asyncio
async def test_get_config_by_id_success(client: AsyncClient, db_session: AsyncSession):
    """测试获取配置详情成功"""
    # 先创建一个配置
    config = CrawlerConfig(
        config_name="测试配置",
        target_url="https://www.example.com",
        input_configs={"inputs": []},
        submit_selector="button",
        wait_selector=".results",
        fields_mapping={"list_selector": ".item", "fields": []}
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    
    # 获取配置详情
    response = await client.get(f"/api/configs/{config.id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["id"] == config.id
    assert data["config_name"] == "测试配置"


@pytest.mark.asyncio
async def test_get_config_by_id_not_found(client: AsyncClient):
    """测试获取不存在的配置"""
    response = await client.get("/api/configs/999999")
    
    assert response.status_code == 404
    assert "不存在" in response.json()["detail"]
```

- [ ] **Step 2: 运行测试验证失败**

运行：`pytest tests/test_config_crud.py::test_get_config_by_id_success -v`

预期：FAIL - "404 Not Found"

- [ ] **Step 3: 实现获取配置详情端点**

在 `app/api/config_endpoints.py` 添加：

```python
@router.get("/{config_id}", response_model=ConfigResponse)
async def get_config(
    config_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    获取指定配置的详情
    
    Args:
        config_id: 配置 ID
        db: 数据库 session
    
    Returns:
        配置详情
    
    Raises:
        HTTPException: 配置不存在时返回 404
    """
    logger.info(f"查询配置详情: ID={config_id}")
    
    try:
        stmt = select(CrawlerConfig).where(CrawlerConfig.id == config_id)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()
        
        if not config:
            logger.warning(f"配置不存在: ID={config_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"配置不存在: ID={config_id}"
            )
        
        logger.info(f"查询配置成功: ID={config_id}, name={config.config_name}")
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询配置详情失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="查询配置详情失败"
        )
```

- [ ] **Step 4: 运行测试验证通过**

运行：`pytest tests/test_config_crud.py -v -k "test_get_config_by_id"`

预期：PASS - 所有详情查询测试通过

- [ ] **Step 5: 提交**

```bash
git add app/api/config_endpoints.py tests/test_config_crud.py
git commit -m "feat: add GET /api/configs/{id} endpoint for config details"
```

---

## Task 9: 实现更新配置端点（PUT /api/configs/{id}）

**Files:**
- Modify: `app/api/config_endpoints.py`
- Modify: `tests/test_config_crud.py`

- [ ] **Step 1: 编写测试 - 更新配置**

在 `tests/test_config_crud.py` 添加：

```python
@pytest.mark.asyncio
async def test_update_config_partial(client: AsyncClient, db_session: AsyncSession):
    """测试部分更新配置"""
    # 先创建配置
    config = CrawlerConfig(
        config_name="原始配置",
        target_url="https://www.example.com",
        input_configs={"inputs": []},
        submit_selector="button",
        wait_selector=".results",
        fields_mapping={"list_selector": ".item", "fields": []},
        max_pages=1
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    
    # 更新部分字段
    update_data = {
        "max_pages": 10,
        "is_active": False
    }
    
    response = await client.put(f"/api/configs/{config.id}", json=update_data)
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["max_pages"] == 10
    assert data["is_active"] is False
    assert data["config_name"] == "原始配置"  # 未更新的字段保持不变


@pytest.mark.asyncio
async def test_update_config_not_found(client: AsyncClient):
    """测试更新不存在的配置"""
    update_data = {"max_pages": 10}
    
    response = await client.put("/api/configs/999999", json=update_data)
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_config_validation_error(client: AsyncClient, db_session: AsyncSession):
    """测试更新配置验证错误"""
    # 先创建配置
    config = CrawlerConfig(
        config_name="测试配置",
        target_url="https://www.example.com",
        input_configs={"inputs": []},
        submit_selector="button",
        wait_selector=".results",
        fields_mapping={"list_selector": ".item", "fields": []}
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    
    # 尝试设置 need_login=True 但不提供 auth_profile
    update_data = {"need_login": True}
    
    response = await client.put(f"/api/configs/{config.id}", json=update_data)
    
    assert response.status_code == 422
```

- [ ] **Step 2: 运行测试验证失败**

运行：`pytest tests/test_config_crud.py::test_update_config_partial -v`

预期：FAIL - "404 Not Found"

- [ ] **Step 3: 实现更新配置端点**

在 `app/api/config_endpoints.py` 添加：

```python
from app.schemas.config import ConfigUpdate


@router.put("/{config_id}", response_model=ConfigResponse)
async def update_config(
    config_id: int,
    config_data: ConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    更新配置（支持部分更新）
    
    Args:
        config_id: 配置 ID
        config_data: 更新数据（只更新提供的字段）
        db: 数据库 session
    
    Returns:
        更新后的完整配置
    
    Raises:
        HTTPException: 配置不存在时返回 404
    """
    logger.info(f"更新配置: ID={config_id}")
    
    try:
        # 查询配置
        stmt = select(CrawlerConfig).where(CrawlerConfig.id == config_id)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()
        
        if not config:
            logger.warning(f"配置不存在: ID={config_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"配置不存在: ID={config_id}"
            )
        
        # 应用部分更新
        update_dict = config_data.model_dump(exclude_unset=True)
        
        # 处理 URL 字段（转换为字符串）
        if 'target_url' in update_dict and update_dict['target_url']:
            update_dict['target_url'] = str(update_dict['target_url'])
        if 'login_url' in update_dict and update_dict['login_url']:
            update_dict['login_url'] = str(update_dict['login_url'])
        
        for key, value in update_dict.items():
            setattr(config, key, value)
        
        await db.commit()
        await db.refresh(config)
        
        logger.info(f"配置更新成功: ID={config_id}")
        
        return config
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"更新配置失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新配置失败"
        )
```

- [ ] **Step 4: 运行测试验证通过**

运行：`pytest tests/test_config_crud.py -v -k "test_update_config"`

预期：PASS - 所有更新配置测试通过

- [ ] **Step 5: 提交**

```bash
git add app/api/config_endpoints.py tests/test_config_crud.py
git commit -m "feat: add PUT /api/configs/{id} endpoint for updating configs"
```

---

## Task 10: 实现删除配置端点（DELETE /api/configs/{id}）

**Files:**
- Modify: `app/api/config_endpoints.py`
- Modify: `tests/test_config_crud.py`

- [ ] **Step 1: 编写测试 - 删除配置**

在 `tests/test_config_crud.py` 添加：

```python
from app.models.job import JobQueue, JobStatus


@pytest.mark.asyncio
async def test_delete_config_success(client: AsyncClient, db_session: AsyncSession):
    """测试删除配置成功"""
    # 创建配置
    config = CrawlerConfig(
        config_name="待删除配置",
        target_url="https://www.example.com",
        input_configs={"inputs": []},
        submit_selector="button",
        wait_selector=".results",
        fields_mapping={"list_selector": ".item", "fields": []}
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    
    # 删除配置
    response = await client.delete(f"/api/configs/{config.id}")
    
    assert response.status_code == 200
    data = response.json()
    
    assert data["status"] == "success"
    assert data["config_id"] == config.id
    
    # 验证配置已被删除
    stmt = select(CrawlerConfig).where(CrawlerConfig.id == config.id)
    result = await db_session.execute(stmt)
    deleted_config = result.scalar_one_or_none()
    
    assert deleted_config is None


@pytest.mark.asyncio
async def test_delete_config_not_found(client: AsyncClient):
    """测试删除不存在的配置"""
    response = await client.delete("/api/configs/999999")
    
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_delete_config_with_pending_jobs(client: AsyncClient, db_session: AsyncSession):
    """测试删除配置时存在待执行任务"""
    # 创建配置
    config = CrawlerConfig(
        config_name="有任务的配置",
        target_url="https://www.example.com",
        input_configs={"inputs": []},
        submit_selector="button",
        wait_selector=".results",
        fields_mapping={"list_selector": ".item", "fields": []}
    )
    db_session.add(config)
    await db_session.commit()
    await db_session.refresh(config)
    
    # 创建待执行任务
    job = JobQueue(
        config_id=config.id,
        query_params={"keyword": "test"},
        status=JobStatus.PENDING
    )
    db_session.add(job)
    await db_session.commit()
    
    # 尝试删除配置
    response = await client.delete(f"/api/configs/{config.id}")
    
    assert response.status_code == 409  # Conflict
    assert "待执行任务" in response.json()["detail"]
```

- [ ] **Step 2: 运行测试验证失败**

运行：`pytest tests/test_config_crud.py::test_delete_config_success -v`

预期：FAIL - "404 Not Found"

- [ ] **Step 3: 实现删除配置端点**

在 `app/api/config_endpoints.py` 添加：

```python
from app.models.job import JobQueue, JobStatus


@router.delete("/{config_id}")
async def delete_config(
    config_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    删除配置
    
    业务规则：
    - 如果存在待执行任务（status=pending），返回 409 Conflict
    - 否则删除配置，级联删除所有关联的 JobQueue 记录
    
    Args:
        config_id: 配置 ID
        db: 数据库 session
    
    Returns:
        删除成功消息
    
    Raises:
        HTTPException: 配置不存在时返回 404，存在待执行任务时返回 409
    """
    logger.info(f"删除配置: ID={config_id}")
    
    try:
        # 查询配置
        stmt = select(CrawlerConfig).where(CrawlerConfig.id == config_id)
        result = await db.execute(stmt)
        config = result.scalar_one_or_none()
        
        if not config:
            logger.warning(f"配置不存在: ID={config_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"配置不存在: ID={config_id}"
            )
        
        # 检查是否存在待执行任务
        count_stmt = select(func.count(JobQueue.id)).where(
            JobQueue.config_id == config_id,
            JobQueue.status == JobStatus.PENDING
        )
        count_result = await db.execute(count_stmt)
        pending_count = count_result.scalar() or 0
        
        if pending_count > 0:
            logger.warning(f"配置有待执行任务，无法删除: ID={config_id}, pending_jobs={pending_count}")
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"无法删除：存在 {pending_count} 个待执行任务，请先处理这些任务"
            )
        
        # 删除配置（级联删除 JobQueue 记录）
        await db.delete(config)
        await db.commit()
        
        logger.info(f"配置删除成功: ID={config_id}")
        
        return {
            "status": "success",
            "message": "配置已删除",
            "config_id": config_id
        }
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"删除配置失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除配置失败"
        )
```

- [ ] **Step 4: 运行测试验证通过**

运行：`pytest tests/test_config_crud.py -v -k "test_delete_config"`

预期：PASS - 所有删除配置测试通过

- [ ] **Step 5: 提交**

```bash
git add app/api/config_endpoints.py tests/test_config_crud.py
git commit -m "feat: add DELETE /api/configs/{id} endpoint with pending jobs check"
```

---

## Task 11: 运行完整测试套件

**Files:**
- Test: `tests/test_config_schemas.py`
- Test: `tests/test_config_crud.py`

- [ ] **Step 1: 运行所有 Schema 测试**

运行：`pytest tests/test_config_schemas.py -v`

预期：PASS - 所有 Schema 验证测试通过

- [ ] **Step 2: 运行所有 CRUD API 测试**

运行：`pytest tests/test_config_crud.py -v`

预期：PASS - 所有 CRUD API 测试通过

- [ ] **Step 3: 运行覆盖率报告**

运行：`pytest tests/test_config*.py --cov=app/schemas/config --cov=app/api/config_endpoints --cov-report=term`

预期：覆盖率 > 80%

- [ ] **Step 4: 检查代码质量**

运行：`python -m flake8 app/schemas/config.py app/api/config_endpoints.py --max-line-length=120`

预期：无语法错误或风格问题

- [ ] **Step 5: 提交测试结果**

如果所有测试通过，无需额外提交。如果有问题，修复后提交：

```bash
git add tests/
git commit -m "test: verify all CRUD tests pass"
```

---

## Task 12: 手动测试和文档更新

**Files:**
- Modify: `README.md`
- Manual: Swagger UI 测试

- [ ] **Step 1: 启动开发服务器**

运行：`uvicorn app.main:app --reload`

预期：服务器启动成功，访问 http://127.0.0.1:8000

- [ ] **Step 2: 访问 Swagger UI**

打开浏览器：http://127.0.0.1:8000/docs

预期：看到"配置管理"分组，包含 5 个端点

- [ ] **Step 3: 手动测试创建配置**

在 Swagger UI 中测试 `POST /api/configs`，使用以下 JSON：

```json
{
  "config_name": "百度搜索测试",
  "target_url": "https://www.baidu.com",
  "input_configs": {
    "inputs": [
      {
        "selector": "#kw",
        "param_key": "keyword",
        "input_type": "text"
      }
    ]
  },
  "submit_selector": "#su",
  "wait_selector": "#content_left",
  "fields_mapping": {
    "list_selector": ".c-container",
    "fields": [
      {"name": "title", "selector": "h3 a", "attr": "text"},
      {"name": "url", "selector": "h3 a", "attr": "href"}
    ]
  },
  "max_pages": 3
}
```

预期：返回 201，包含 ID 和 created_at

- [ ] **Step 4: 手动测试其他端点**

依次测试：
- GET /api/configs（列表）
- GET /api/configs/{id}（详情）
- PUT /api/configs/{id}（更新）
- DELETE /api/configs/{id}（删除）

预期：所有端点正常工作

- [ ] **Step 5: 更新 README.md**

在 `README.md` 的 API 文档部分添加：

```markdown
### 配置管理 API

#### 创建配置
- **端点**: `POST /api/configs`
- **说明**: 创建新的采集配置
- **请求体**: 见 Swagger UI `/docs` 中的 Schema 定义

#### 获取配置列表
- **端点**: `GET /api/configs`
- **参数**: `page` (int), `page_size` (int), `is_active` (bool)
- **说明**: 分页查询配置列表，支持按激活状态过滤

#### 获取配置详情
- **端点**: `GET /api/configs/{config_id}`
- **说明**: 获取指定配置的完整信息

#### 更新配置
- **端点**: `PUT /api/configs/{config_id}`
- **说明**: 更新配置（支持部分更新）

#### 删除配置
- **端点**: `DELETE /api/configs/{config_id}`
- **说明**: 删除配置（如存在待执行任务则拒绝删除）
```

- [ ] **Step 6: 提交文档更新**

```bash
git add README.md
git commit -m "docs: add configuration management API documentation"
```

---

## 实现计划自审

### Spec 覆盖检查

- ✅ **创建配置**: Task 6 实现 POST /api/configs
- ✅ **获取列表**: Task 7 实现 GET /api/configs（含分页和过滤）
- ✅ **获取详情**: Task 8 实现 GET /api/configs/{id}
- ✅ **更新配置**: Task 9 实现 PUT /api/configs/{id}
- ✅ **删除配置**: Task 10 实现 DELETE /api/configs/{id}（含待执行任务检查）
- ✅ **字段验证**: Task 2-5 实现 Pydantic Schemas（URL、必填字段、auth_profile 验证）
- ✅ **错误处理**: 所有端点包含 404/409/500 错误处理和日志记录
- ✅ **测试**: Task 2-10 每个功能都有对应的测试

### 占位符检查

无 TBD、TODO 或"类似于 Task N"等占位符。

### 类型一致性检查

- ConfigBase、ConfigCreate、ConfigUpdate、ConfigResponse - 字段名称和类型一致
- API 端点参数和返回类型与 Schema 匹配
- 测试中使用的字段名称与 Schema 一致

---

**实现计划完成！准备执行。**
