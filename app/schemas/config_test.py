# app/schemas/config_test.py
from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field, model_validator


class FieldMapping(BaseModel):
    """字段映射"""
    name: str = Field(..., min_length=1, max_length=100, description="字段名称")
    selector: str = Field(..., min_length=1, max_length=500, description="CSS 选择器")
    attr: Literal["text", "href", "src", "value", "title", "alt"] = Field(..., description="提取属性：text/href/src/value/title/alt")


class DetailConfigTimeout(BaseModel):
    """详情超时配置"""
    click: int = Field(10000, ge=1000, le=60000, description="点击超时（毫秒）")
    wait_selector: int = Field(5000, ge=1000, le=30000, description="等待选择器超时（毫秒）")
    iframe_load: Optional[int] = Field(10000, ge=1000, le=60000, description="iframe 加载超时（毫秒）")
    close: int = Field(5000, ge=1000, le=30000, description="关闭超时（毫秒）")


class DetailConfigRetry(BaseModel):
    """详情重试配置"""
    max_attempts: int = Field(3, ge=1, le=10, description="最大重试次数")
    delay_seconds: int = Field(2, ge=1, le=30, description="重试延迟（秒）")


class DetailConfig(BaseModel):
    """详情采集配置"""
    enabled: bool = Field(False, description="是否启用详情采集")
    detail_button_selector: Optional[str] = Field(None, max_length=200, description="详情按钮选择器")
    wait_selector: Optional[str] = Field(None, max_length=200, description="详情等待选择器")
    detail_iframe_selector: Optional[str] = Field(None, max_length=200, description="详情iframe选择器")
    fields: List[FieldMapping] = Field(default_factory=list, description="详情字段列表")
    close_method: Literal["click", "escape", "auto"] = Field("auto", description="关闭方式：click/escape/auto")
    close_selector: Optional[str] = Field(None, max_length=200, description="关闭按钮选择器")
    timeout: DetailConfigTimeout = Field(default_factory=DetailConfigTimeout)
    retry: DetailConfigRetry = Field(default_factory=DetailConfigRetry)

    @model_validator(mode='after')
    def validate_enabled_fields(self):
        """当 enabled=True 时，验证必填字段"""
        if self.enabled:
            if not self.detail_button_selector:
                raise ValueError("当 enabled=True 时，detail_button_selector 不能为空")
            if not self.wait_selector:
                raise ValueError("当 enabled=True 时，wait_selector 不能为空")
            if not self.fields or len(self.fields) == 0:
                raise ValueError("当 enabled=True 时，fields 至少需要一个元素")
            if self.close_method == "click" and not self.close_selector:
                raise ValueError("当 close_method='click' 时，close_selector 不能为空")
        return self


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
