import logging
from fastapi import APIRouter, HTTPException, status, Depends, Query
from typing import List
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.metrics import AlertRule, AlertHistory
from app.schemas.alerts import (
    AlertRuleCreate,
    AlertRuleUpdate,
    AlertRuleResponse,
    AlertHistoryResponse
)

router = APIRouter(prefix="/api/alerts", tags=["alerts"])
logger = logging.getLogger(__name__)

# 常量定义
VALID_CHANNELS = {"email", "dingtalk", "wecom"}


@router.post("/rules", response_model=AlertRuleResponse, status_code=status.HTTP_201_CREATED)
async def create_alert_rule(
    rule: AlertRuleCreate,
    session: AsyncSession = Depends(get_session)
) -> AlertRuleResponse:
    """创建告警规则"""
    try:
        # 验证通知渠道
        invalid_channels = set(rule.channels) - VALID_CHANNELS
        if invalid_channels:
            raise HTTPException(
                status_code=400,
                detail=f"无效的通知渠道: {', '.join(invalid_channels)}"
            )

        # 创建规则
        new_rule = AlertRule(
            rule_name=rule.rule_name,
            metric_name=rule.metric_name,
            condition=rule.condition,
            threshold=rule.threshold,
            duration_seconds=rule.duration_seconds,
            channels=rule.channels,
            enabled=rule.enabled
        )

        session.add(new_rule)
        await session.commit()
        await session.refresh(new_rule)

        logger.info(f"创建告警规则: {new_rule.rule_name} (ID: {new_rule.id})")
        return new_rule

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"创建告警规则失败: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(status_code=500, detail="创建告警规则失败")


@router.get("/rules", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    enabled: bool = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    session: AsyncSession = Depends(get_session)
) -> List[AlertRuleResponse]:
    """列出所有告警规则"""
    try:
        stmt = select(AlertRule)

        if enabled is not None:
            stmt = stmt.where(AlertRule.enabled == enabled)

        stmt = stmt.order_by(AlertRule.created_at.desc())

        # 添加分页
        offset = (page - 1) * page_size
        stmt = stmt.offset(offset).limit(page_size)

        result = await session.execute(stmt)
        rules = result.scalars().all()

        return rules

    except Exception as e:
        logger.error(f"查询告警规则失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询告警规则失败")


@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(
    rule_id: int,
    session: AsyncSession = Depends(get_session)
) -> AlertRuleResponse:
    """获取单个告警规则"""
    try:
        rule = await session.get(AlertRule, rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="告警规则不存在")

        return rule

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"查询告警规则失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询告警规则失败")


@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(
    rule_id: int,
    rule_update: AlertRuleUpdate,
    session: AsyncSession = Depends(get_session)
) -> AlertRuleResponse:
    """更新告警规则"""
    try:
        rule = await session.get(AlertRule, rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="告警规则不存在")

        # 验证通知渠道
        if rule_update.channels:
            invalid_channels = set(rule_update.channels) - VALID_CHANNELS
            if invalid_channels:
                raise HTTPException(
                    status_code=400,
                    detail=f"无效的通知渠道: {', '.join(invalid_channels)}"
                )

        # 更新字段
        update_data = rule_update.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)

        await session.commit()
        await session.refresh(rule)

        logger.info(f"更新告警规则: {rule.rule_name} (ID: {rule.id})")
        return rule

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新告警规则失败: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(status_code=500, detail="更新告警规则失败")


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_alert_rule(
    rule_id: int,
    session: AsyncSession = Depends(get_session)
):
    """删除告警规则"""
    try:
        rule = await session.get(AlertRule, rule_id)

        if not rule:
            raise HTTPException(status_code=404, detail="告警规则不存在")

        await session.delete(rule)
        await session.commit()

        logger.info(f"删除告警规则: {rule.rule_name} (ID: {rule.id})")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除告警规则失败: {e}", exc_info=True)
        await session.rollback()
        raise HTTPException(status_code=500, detail="删除告警规则失败")


@router.get("/history", response_model=List[AlertHistoryResponse])
async def get_alert_history(
    rule_id: int = None,
    limit: int = Query(default=100, ge=1, le=1000),
    session: AsyncSession = Depends(get_session)
) -> List[AlertHistoryResponse]:
    """获取告警历史"""
    try:
        stmt = select(AlertHistory)

        if rule_id is not None:
            stmt = stmt.where(AlertHistory.rule_id == rule_id)

        stmt = stmt.order_by(AlertHistory.triggered_at.desc()).limit(limit)

        result = await session.execute(stmt)
        history = result.scalars().all()

        return history

    except Exception as e:
        logger.error(f"查询告警历史失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="查询告警历史失败")
