# CrawlerConfig CRUD API 设计文档

**日期**: 2026-09-23  
**版本**: 1.0  
**状态**: 待审阅

## 1. 概述

为浏览器自动化数据采集平台添加完整的配置（CrawlerConfig）CRUD 操作接口，支持通过 API 管理采集配置，无需直接操作数据库。

### 1.1 目标

- 提供标准的 RESTful API 进行配置管理（创建、读取、更新、删除）
- 使用 Pydantic 进行请求验证和响应序列化
- 支持分页查询和过滤
- 保证数据完整性（字段验证、关联检查）

### 1.2 范围

**包含：**
- 完整的 CRUD API 端点（POST/GET/PUT/DELETE）
- Pydantic Schema 定义
- 字段验证逻辑
- 错误处理
- 基本的单元测试和集成测试

**不包含：**
- 配置版本控制
- 配置导入/导出功能
- 配置模板管理
- 前端界面修改（仅后端 API）

## 2. 架构设计

### 2.1 文件结构

```
app/
├── schemas/
│   └── config.py          # 新增：Pydantic Schema 定义
├── api/
│   ├── endpoints.py       # 现有：登录态和任务执行接口
│   └── config_endpoints.py # 新增：配置 CRUD 路由
└── main.py                # 修改：注册新路由器

tests/
└── test_config_crud.py    # 新增：配置 CRUD 测试
```

### 2.2 技术选型

- **验证层**: Pydantic v2（FastAPI 内置）
- **ORM 层**: SQLAlchemy 2.0（已有）
- **API 风格**: RESTful
- **文档**: 自动生成（Swagger UI）

### 2.3 分层架构

```
┌─────────────────────────────────────┐
│  HTTP Request (JSON)                │
├─────────────────────────────────────┤
│  FastAPI Router                     │
│  - 路由匹配                          │
│  - 参数解析                          │
├─────────────────────────────────────┤
│  Pydantic Schema                    │
│  - 字段验证                          │
│  - 类型转换                          │
├─────────────────────────────────────┤
│  Business Logic                     │
│  - 业务规则检查                      │
│  - 关联数据验证                      │
├─────────────────────────────────────┤
│  SQLAlchemy ORM                     │
│  - 数据库操作                        │
│  - 事务管理                          │
├─────────────────────────────────────┤
│  Database (MySQL)                   │
└─────────────────────────────────────┘
```

## 3. 数据模型设计（Pydantic Schemas）

### 3.1 ConfigBase（基础字段）

```python
class ConfigBase(BaseModel):
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

### 3.2 ConfigCreate（创建请求）

```python
class ConfigCreate(ConfigBase):
    @model_validator(mode='after')
    def validate_auth_profile(self) -> 'ConfigCreate':
        """验证：need_login=True 时 auth_profile 必填"""
        if self.need_login and not self.auth_profile:
            raise ValueError('need_login=True 时必须提供 auth_profile')
        return self
```

### 3.3 ConfigUpdate（更新请求）

```python
class ConfigUpdate(BaseModel):
    # 所有字段可选（部分更新）
    config_name: Optional[str] = Field(None, min_length=1, max_length=100)
    target_url: Optional[HttpUrl] = None
    need_login: Optional[bool] = None
    auth_profile: Optional[str] = Field(None, max_length=50)
    login_url: Optional[HttpUrl] = None
    input_configs: Optional[Dict] = None
    submit_selector: Optional[str] = Field(None, min_length=1, max_length=200)
    wait_selector: Optional[str] = Field(None, min_length=1, max_length=200)
    fields_mapping: Optional[Dict] = None
    pagination_selector: Optional[str] = Field(None, max_length=200)
    max_pages: Optional[int] = Field(None, ge=1)
    is_active: Optional[bool] = None

    @model_validator(mode='after')
    def validate_auth_profile(self) -> 'ConfigUpdate':
        """验证：need_login=True 时 auth_profile 必填"""
        if self.need_login is True and not self.auth_profile:
            raise ValueError('need_login=True 时必须提供 auth_profile')
        return self
```

### 3.4 ConfigResponse（响应）

```python
class ConfigResponse(ConfigBase):
    id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
```

### 3.5 ConfigListResponse（列表响应）

```python
class ConfigListResponse(BaseModel):
    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    items: List[ConfigResponse] = Field(..., description="配置列表")
```

## 4. API 端点设计

### 4.1 创建配置

**端点**: `POST /api/configs`  
**标签**: `配置管理`

**请求体**:
```json
{
  "config_name": "淘宝手机搜索",
  "target_url": "https://www.taobao.com",
  "need_login": true,
  "auth_profile": "taobao",
  "input_configs": {
    "inputs": [
      {
        "selector": "#q",
        "param_key": "keyword",
        "input_type": "text"
      }
    ]
  },
  "submit_selector": "button.btn-search",
  "wait_selector": ".items-list",
  "fields_mapping": {
    "list_selector": ".item",
    "fields": [
      {"name": "title", "selector": ".title", "attr": "text"},
      {"name": "price", "selector": ".price", "attr": "text"}
    ]
  },
  "pagination_selector": ".next-page",
  "max_pages": 5
}
```

**响应**: `201 Created`
```json
{
  "id": 1,
  "config_name": "淘宝手机搜索",
  "target_url": "https://www.taobao.com",
  "need_login": true,
  "auth_profile": "taobao",
  "created_at": "2026-09-23T10:00:00",
  ...
}
```

### 4.2 获取配置列表

**端点**: `GET /api/configs`  
**标签**: `配置管理`

**查询参数**:
- `page` (int, 默认 1): 页码
- `page_size` (int, 默认 20, 最大 100): 每页大小
- `is_active` (bool, 可选): 过滤启用/禁用状态

**响应**: `200 OK`
```json
{
  "total": 50,
  "page": 1,
  "page_size": 20,
  "items": [
    {
      "id": 1,
      "config_name": "淘宝手机搜索",
      ...
    }
  ]
}
```

### 4.3 获取配置详情

**端点**: `GET /api/configs/{config_id}`  
**标签**: `配置管理`

**路径参数**:
- `config_id` (int): 配置 ID

**响应**: `200 OK` / `404 Not Found`
```json
{
  "id": 1,
  "config_name": "淘宝手机搜索",
  ...
}
```

### 4.4 更新配置

**端点**: `PUT /api/configs/{config_id}`  
**标签**: `配置管理`

**路径参数**:
- `config_id` (int): 配置 ID

**请求体** (部分更新示例):
```json
{
  "max_pages": 10,
  "is_active": false
}
```

**响应**: `200 OK` / `404 Not Found`
```json
{
  "id": 1,
  "config_name": "淘宝手机搜索",
  "max_pages": 10,
  "is_active": false,
  ...
}
```

### 4.5 删除配置

**端点**: `DELETE /api/configs/{config_id}`  
**标签**: `配置管理`

**路径参数**:
- `config_id` (int): 配置 ID

**业务规则**:
- 检查是否存在待执行任务（`status=pending`）
- 如果存在，返回 `409 Conflict`
- 否则执行删除，级联删除关联的 `JobQueue` 记录

**响应**: `200 OK` / `404 Not Found` / `409 Conflict`
```json
{
  "status": "success",
  "message": "配置已删除",
  "config_id": 1
}
```

**错误响应（存在待执行任务）**:
```json
{
  "detail": "无法删除：存在 3 个待执行任务，请先处理这些任务"
}
```

## 5. 业务逻辑

### 5.1 创建配置流程

```
1. 接收 JSON 请求
2. Pydantic 验证字段格式
   - URL 格式验证
   - 必填字段检查
   - need_login=True 时验证 auth_profile 非空
3. 创建 CrawlerConfig ORM 对象
4. 插入数据库（自动生成 ID 和 created_at）
5. 返回完整配置（201 Created）
```

### 5.2 更新配置流程

```
1. 查询配置是否存在
   - 不存在 → 返回 404
2. Pydantic 验证更新字段
3. 应用部分更新（只更新提供的字段）
4. 验证 need_login 和 auth_profile 一致性
5. 提交事务
6. 返回更新后的完整配置（200 OK）
```

### 5.3 删除配置流程

```
1. 查询配置是否存在
   - 不存在 → 返回 404
2. 查询关联的待执行任务数量
   SELECT COUNT(*) FROM job_queue 
   WHERE config_id = ? AND status = 'pending'
3. 如果存在待执行任务
   - 返回 409 Conflict，提示任务数量
4. 否则执行删除
   - SQLAlchemy 自动级联删除 JobQueue 记录
5. 返回删除成功消息（200 OK）
```

### 5.4 查询列表流程

```
1. 解析查询参数（page, page_size, is_active）
2. 构建查询条件
   - 如果提供 is_active，添加过滤条件
3. 查询总记录数
4. 分页查询（LIMIT + OFFSET）
5. 返回 ConfigListResponse
```

## 6. 错误处理

### 6.1 错误类型和响应

| 状态码 | 场景 | 响应示例 |
|--------|------|----------|
| 400 Bad Request | 字段验证失败 | `{"detail": [{"loc": ["body", "target_url"], "msg": "invalid URL format"}]}` |
| 400 Bad Request | need_login=True 但 auth_profile 为空 | `{"detail": "need_login=True 时必须提供 auth_profile"}` |
| 404 Not Found | 配置不存在 | `{"detail": "配置不存在: ID=123"}` |
| 409 Conflict | 删除时存在待执行任务 | `{"detail": "无法删除：存在 3 个待执行任务，请先处理这些任务"}` |
| 500 Internal Server Error | 数据库异常 | `{"detail": "服务器内部错误"}` |

### 6.2 日志记录

**记录内容**:
- 操作类型（CREATE/READ/UPDATE/DELETE）
- 配置 ID
- 操作结果（成功/失败）
- 错误详情（包含堆栈信息）

**日志级别**:
- INFO: 正常操作
- WARNING: 业务规则阻止（如删除时存在任务）
- ERROR: 异常情况

## 7. 数据完整性

### 7.1 字段验证

| 字段 | 验证规则 |
|------|----------|
| config_name | 非空，长度 1-100 |
| target_url | 有效的 HTTP/HTTPS URL |
| login_url | 有效的 HTTP/HTTPS URL（可选） |
| auth_profile | 长度 ≤ 50（当 need_login=True 时必填） |
| input_configs | 有效的 JSON 对象 |
| fields_mapping | 有效的 JSON 对象 |
| submit_selector | 非空，长度 1-200 |
| wait_selector | 非空，长度 1-200 |
| pagination_selector | 长度 ≤ 200（可选） |
| max_pages | ≥ 1 |

### 7.2 关联检查

**删除配置时**:
- 检查 `job_queue` 表中是否存在 `status=pending` 的关联任务
- 存在则阻止删除，返回 409 错误

**级联删除**:
- 删除配置时，自动删除所有关联的 `JobQueue` 记录（ORM 配置：`cascade="all, delete-orphan"`）

## 8. 测试策略

### 8.1 单元测试

**Schema 验证测试** (`tests/test_config_schemas.py`):
- ✅ 必填字段缺失时的验证错误
- ✅ URL 格式验证（有效/无效）
- ✅ need_login=True 时 auth_profile 验证
- ✅ max_pages ≥ 1 验证
- ✅ JSON 字段结构验证

**API 端点测试** (`tests/test_config_crud.py`):
- ✅ POST /api/configs - 正常创建
- ✅ POST /api/configs - 字段验证失败（400）
- ✅ GET /api/configs - 空列表
- ✅ GET /api/configs - 分页查询
- ✅ GET /api/configs - is_active 过滤
- ✅ GET /api/configs/{id} - 存在的配置
- ✅ GET /api/configs/{id} - 不存在的配置（404）
- ✅ PUT /api/configs/{id} - 部分更新
- ✅ PUT /api/configs/{id} - 更新不存在的配置（404）
- ✅ DELETE /api/configs/{id} - 正常删除
- ✅ DELETE /api/configs/{id} - 存在待执行任务（409）
- ✅ DELETE /api/configs/{id} - 不存在的配置（404）

### 8.2 集成测试

**完整流程测试**:
1. 创建配置
2. 创建关联任务（JobQueue）
3. 执行任务（验证配置被正确使用）
4. 删除配置（验证级联删除）

### 8.3 手动测试

**Swagger UI 测试** (`http://127.0.0.1:8000/docs`):
- 测试所有端点的正常流程
- 测试各种错误场景
- 验证响应格式和状态码

## 9. 实现清单

### 9.1 开发任务

- [ ] 创建 `app/schemas/config.py`
  - [ ] 定义 ConfigBase
  - [ ] 定义 ConfigCreate（含验证器）
  - [ ] 定义 ConfigUpdate（含验证器）
  - [ ] 定义 ConfigResponse
  - [ ] 定义 ConfigListResponse

- [ ] 创建 `app/api/config_endpoints.py`
  - [ ] POST /api/configs（创建）
  - [ ] GET /api/configs（列表）
  - [ ] GET /api/configs/{id}（详情）
  - [ ] PUT /api/configs/{id}（更新）
  - [ ] DELETE /api/configs/{id}（删除）

- [ ] 修改 `app/main.py`
  - [ ] 导入 config_endpoints 路由器
  - [ ] 注册路由器

- [ ] 创建测试文件
  - [ ] tests/test_config_schemas.py
  - [ ] tests/test_config_crud.py

### 9.2 测试任务

- [ ] 运行单元测试（pytest）
- [ ] 手动测试所有端点（Swagger UI）
- [ ] 验证错误处理
- [ ] 验证日志记录

### 9.3 文档任务

- [ ] 更新 README.md（添加配置管理 API 说明）
- [ ] 提交 git commit

## 10. 未来扩展

**当前设计不包含，但可以在未来添加的功能：**

1. **配置模板**：预定义常用网站的配置模板
2. **配置版本控制**：保留历史版本，支持回滚
3. **配置导入/导出**：JSON 文件导入导出
4. **配置复制**：基于现有配置创建新配置
5. **批量操作**：批量启用/禁用配置
6. **配置验证**：创建后自动运行测试任务验证配置可用性

---

**文档结束**
