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
