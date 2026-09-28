import logging
from datetime import datetime, timedelta, timezone
from typing import List, Optional
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.models.metrics import AlertRule, AlertHistory, MetricsTimeSeries
from app.services.notifiers import EmailNotifier, DingTalkNotifier, WeComNotifier

logger = logging.getLogger(__name__)


class AlertEngine:
    """告警引擎 - 周期性评估告警规则"""

    def __init__(self, ws_manager=None):
        """
        初始化告警引擎

        Args:
            ws_manager: WebSocket 管理器（可选）
        """
        self.email_notifier = EmailNotifier()
        self.dingtalk_notifier = DingTalkNotifier()
        self.wecom_notifier = WeComNotifier()
        self.ws_manager = ws_manager
        self.logger = logger

    async def evaluate_rules(self):
        """评估所有启用的告警规则"""
        self.logger.info("开始评估告警规则...")

        async with get_session() as session:
            # 获取所有启用的告警规则
            rules = await self._get_enabled_rules(session)

            if not rules:
                self.logger.info("没有启用的告警规则")
                return

            self.logger.info(f"发现 {len(rules)} 条启用的告警规则")

            for rule in rules:
                try:
                    await self._evaluate_single_rule(rule, session)
                except Exception as e:
                    self.logger.error(f"评估规则 {rule.rule_name} 时出错: {e}", exc_info=True)

    async def _get_enabled_rules(self, session: AsyncSession) -> List[AlertRule]:
        """获取所有启用的告警规则"""
        stmt = select(AlertRule).where(AlertRule.enabled == True)
        result = await session.execute(stmt)
        return result.scalars().all()

    async def _evaluate_single_rule(self, rule: AlertRule, session: AsyncSession):
        """评估单条告警规则"""
        # 查询最近时间窗口内的指标数据
        end_time = datetime.now(timezone.utc)
        start_time = end_time - timedelta(seconds=rule.duration_seconds)

        metrics = await self._query_metrics(
            session,
            rule.metric_name,
            start_time,
            end_time
        )

        if not metrics:
            self.logger.debug(f"规则 {rule.rule_name}: 没有指标数据")
            return

        # 检查是否触发告警
        latest_metric = metrics[-1]
        should_trigger = self._check_should_trigger(
            latest_metric.metric_value,
            rule.condition,
            rule.threshold
        )

        if should_trigger:
            self.logger.warning(
                f"规则 {rule.rule_name} 触发告警: "
                f"{rule.metric_name}={latest_metric.metric_value} "
                f"{rule.condition} {rule.threshold}"
            )

            # 创建告警历史
            alert = await self._create_alert(rule, latest_metric, session)

            # 发送通知
            await self._send_notifications(rule, alert, latest_metric, session)

            # 广播告警到 WebSocket
            await self._broadcast_alert(rule, alert, latest_metric)

    async def _query_metrics(
        self,
        session: AsyncSession,
        metric_name: str,
        start_time: datetime,
        end_time: datetime
    ) -> List[MetricsTimeSeries]:
        """查询指标数据"""
        stmt = select(MetricsTimeSeries).where(
            MetricsTimeSeries.metric_name == metric_name,
            MetricsTimeSeries.timestamp >= start_time,
            MetricsTimeSeries.timestamp <= end_time
        ).order_by(MetricsTimeSeries.timestamp.asc())

        result = await session.execute(stmt)
        return result.scalars().all()

    def _check_should_trigger(
        self,
        value: float,
        condition: str,
        threshold: float
    ) -> bool:
        """检查是否应该触发告警"""
        epsilon = 1e-9  # 容差

        if condition == ">":
            return value > threshold
        elif condition == ">=":
            return value >= threshold
        elif condition == "<":
            return value < threshold
        elif condition == "<=":
            return value <= threshold
        elif condition == "==":
            return abs(value - threshold) < epsilon
        elif condition == "!=":
            return abs(value - threshold) >= epsilon
        else:
            self.logger.error(f"不支持的条件运算符: {condition}")
            return False

    async def _create_alert(
        self,
        rule: AlertRule,
        metric: MetricsTimeSeries,
        session: AsyncSession
    ) -> AlertHistory:
        """创建告警历史记录"""
        alert_message = (
            f"告警规则: {rule.rule_name}\n"
            f"指标名称: {rule.metric_name}\n"
            f"当前值: {metric.metric_value}\n"
            f"阈值: {rule.threshold}\n"
            f"触发时间: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}"
        )

        alert = AlertHistory(
            rule_id=rule.id,
            triggered_at=datetime.now(timezone.utc),
            alert_message=alert_message,
            metric_value=metric.metric_value,
            notify_status="pending"
        )

        session.add(alert)
        await session.commit()
        await session.refresh(alert)

        return alert

    async def _send_notifications(
        self,
        rule: AlertRule,
        alert: AlertHistory,
        metric: MetricsTimeSeries,
        session: AsyncSession
    ):
        """发送告警通知到所有配置的渠道"""
        message = alert.alert_message
        results = []  # 收集所有渠道结果

        for channel in rule.channels:
            try:
                if channel == "email":
                    await self.email_notifier.send(message)
                elif channel == "dingtalk":
                    await self.dingtalk_notifier.send(message)
                elif channel == "wecom":
                    await self.wecom_notifier.send(message)
                else:
                    self.logger.warning(f"不支持的通知渠道: {channel}")
                    results.append(False)
                    continue

                self.logger.info(f"通知已发送到 {channel}")
                results.append(True)

            except Exception as e:
                self.logger.error(f"发送 {channel} 通知失败: {e}", exc_info=True)
                results.append(False)

        # 统一更新通知状态
        if all(results):
            alert.notify_status = "success"
        elif any(results):
            alert.notify_status = "partial_success"
        else:
            alert.notify_status = "failed"
            alert.notify_error = f"{len(results)} 个渠道全部失败"

        await session.commit()

    async def _broadcast_alert(
        self,
        rule: AlertRule,
        alert: AlertHistory,
        metric: MetricsTimeSeries
    ):
        """
        通过 WebSocket 广播告警

        Args:
            rule: 告警规则
            alert: 告警历史记录
            metric: 触发告警的指标数据
        """
        if not self.ws_manager:
            return

        try:
            message = {
                "type": "alert",
                "alert_id": alert.id,
                "rule_id": rule.id,
                "rule_name": rule.rule_name,
                "metric_name": rule.metric_name,
                "metric_value": metric.metric_value,
                "threshold": rule.threshold,
                "condition": rule.condition,
                "message": alert.alert_message,
                "triggered_at": alert.triggered_at.isoformat(),
                "severity": "warning"  # 可以根据规则配置
            }

            await self.ws_manager.broadcast(message)
            self.logger.info(f"告警 #{alert.id} 已通过 WebSocket 广播")

        except Exception as e:
            self.logger.error(f"WebSocket 广播告警失败: {e}", exc_info=True)


# 全局实例
alert_engine = AlertEngine()
