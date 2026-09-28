from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class AlertRuleCreate(BaseModel):
    """创建告警规则请求"""
    rule_name: str = Field(..., min_length=1, max_length=100)
    metric_name: str = Field(..., min_length=1, max_length=100)
    condition: str = Field(..., pattern="^(>|>=|<|<=|==|!=)$")
    threshold: float
    duration_seconds: int = Field(default=60, ge=10)
    channels: List[str] = Field(..., min_items=1)
    enabled: bool = Field(default=True)
    silence_duration: int = Field(default=3600, ge=60, description="静默时长（秒）")


class AlertRuleUpdate(BaseModel):
    """更新告警规则请求"""
    rule_name: Optional[str] = Field(None, min_length=1, max_length=100)
    metric_name: Optional[str] = None
    condition: Optional[str] = Field(None, pattern="^(>|>=|<|<=|==|!=)$")
    threshold: Optional[float] = None
    duration_seconds: Optional[int] = Field(None, ge=10)
    channels: Optional[List[str]] = Field(None, min_items=1)
    enabled: Optional[bool] = None
    silence_duration: Optional[int] = Field(None, ge=60, description="静默时长（秒）")


class AlertRuleResponse(BaseModel):
    """告警规则响应"""
    id: int
    rule_name: str
    metric_name: str
    condition: str
    threshold: float
    duration_seconds: int
    channels: List[str]
    enabled: bool
    silence_duration: int
    last_alert_at: Optional[datetime]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AlertHistoryResponse(BaseModel):
    """告警历史响应"""
    id: int
    rule_id: int
    triggered_at: datetime
    resolved_at: Optional[datetime]
    alert_message: str
    metric_value: float
    notify_status: str
    notify_error: Optional[str]

    class Config:
        from_attributes = True
