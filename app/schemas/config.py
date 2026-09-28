# app/schemas/config.py
from typing import Optional, Dict, List, Union, Any, Annotated
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl, model_validator, field_validator, ConfigDict, field_serializer, SkipValidation


class ConfigBase(BaseModel):
    """配置基础 Schema"""

    config_name: str = Field(..., min_length=1, max_length=100, description="配置名称")
    target_url: HttpUrl = Field(..., description="目标页面 URL")
    need_login: bool = Field(default=False, description="是否需要登录")
    auth_profile: Optional[str] = Field(None, max_length=50, description="登录态标识")
    login_url: Optional[HttpUrl] = Field(None, description="登录页地址")
    input_configs: Annotated[Any, SkipValidation] = Field(..., description="输入框配置（JSON，支持列表或字典）")
    submit_selector: str = Field(..., min_length=1, max_length=200, description="提交按钮选择器")
    wait_selector: str = Field(..., min_length=1, max_length=200, description="等待加载选择器")
    fields_mapping: Dict = Field(..., description="字段映射规则（JSON）")
    pagination_selector: Optional[str] = Field(None, max_length=200, description="下一页按钮选择器")
    max_pages: int = Field(default=1, ge=1, description="最大翻页数")
    is_active: bool = Field(default=True, description="是否启用")

    model_config = ConfigDict(
        # 禁用严格模式，允许Any类型接受任何值
        arbitrary_types_allowed=True,
    )


class ConfigCreate(ConfigBase):
    """创建配置的请求 Schema"""

    @model_validator(mode='after')
    def validate_auth_profile(self) -> 'ConfigCreate':
        """验证：need_login=True 时 auth_profile 必填"""
        if self.need_login and not self.auth_profile:
            raise ValueError('need_login=True 时必须提供 auth_profile')
        return self


class ConfigUpdate(BaseModel):
    """更新配置的请求 Schema（所有字段可选）"""

    config_name: Optional[str] = Field(None, min_length=1, max_length=100, description="配置名称")
    target_url: Optional[HttpUrl] = Field(None, description="目标页面 URL")
    need_login: Optional[bool] = Field(None, description="是否需要登录")
    auth_profile: Optional[str] = Field(None, max_length=50, description="登录态标识")
    login_url: Optional[HttpUrl] = Field(None, description="登录页地址")
    input_configs: Optional[Annotated[Any, SkipValidation]] = Field(None, description="输入框配置（JSON，支持列表或字典）")
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


class ConfigResponse(ConfigBase):
    """配置响应 Schema"""

    id: int = Field(..., description="配置 ID")
    created_at: datetime = Field(..., description="创建时间")

    model_config = ConfigDict(
        from_attributes=True,
        arbitrary_types_allowed=True
    )


class ConfigListResponse(BaseModel):
    """配置列表响应 Schema"""

    total: int = Field(..., description="总记录数")
    page: int = Field(..., description="当前页码")
    page_size: int = Field(..., description="每页大小")
    items: List[ConfigResponse] = Field(..., description="配置列表")
