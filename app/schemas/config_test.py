# app/schemas/config_test.py
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class FieldMapping(BaseModel):
    """字段映射"""
    name: str = Field(..., description="字段名称")
    selector: str = Field(..., description="CSS 选择器")
    attr: str = Field(..., description="提取属性：text/href/src")


class DetailConfigTimeout(BaseModel):
    """详情超时配置"""
    click: int = Field(10000, description="点击超时（毫秒）")
    wait_selector: int = Field(5000, description="等待选择器超时（毫秒）")
    iframe_load: Optional[int] = Field(10000, description="iframe 加载超时（毫秒）")
    close: int = Field(5000, description="关闭超时（毫秒）")


class DetailConfigRetry(BaseModel):
    """详情重试配置"""
    max_attempts: int = Field(3, description="最大重试次数")
    delay_seconds: int = Field(2, description="重试延迟（秒）")


class DetailConfig(BaseModel):
    """详情采集配置"""
    enabled: bool = Field(False, description="是否启用详情采集")
    detail_button_selector: Optional[str] = Field(None, description="详情按钮选择器")
    wait_selector: Optional[str] = Field(None, description="详情等待选择器")
    detail_iframe_selector: Optional[str] = Field(None, description="详情iframe选择器")
    fields: List[FieldMapping] = Field(default_factory=list, description="详情字段列表")
    close_method: str = Field("auto", description="关闭方式：click/escape/auto")
    close_selector: Optional[str] = Field(None, description="关闭按钮选择器")
    timeout: DetailConfigTimeout = Field(default_factory=DetailConfigTimeout)
    retry: DetailConfigRetry = Field(default_factory=DetailConfigRetry)


class ConfigTestRequest(BaseModel):
    """配置测试请求"""
    fields_mapping: Dict[str, Any] = Field(..., description="字段映射配置")
    query_params: Dict[str, str] = Field(..., description="查询参数")


class SampleItem(BaseModel):
    """样本数据项"""
    list_data: Dict[str, str] = Field(..., description="列表数据")
    detail_data: Dict[str, str] = Field(default_factory=dict, description="详情数据")
    detail_status: str = Field(..., description="详情状态：success/failed/skipped")
    detail_error: Optional[str] = Field(None, description="详情错误信息")


class ConfigTestResponse(BaseModel):
    """配置测试响应"""
    success: bool = Field(..., description="是否成功")
    data: Optional[Dict[str, Any]] = Field(None, description="测试数据")
    error: Optional[str] = Field(None, description="错误信息")
    error_type: Optional[str] = Field(None, description="错误类型")
