# 监控告警系统实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 建立轻量级监控指标收集、存储和告警系统，提供可观测性和主动异常感知能力

**Architecture:** 
- 指标收集器（MetricsCollector）异步缓冲并批量写入 MySQL
- 告警引擎（AlertEngine）定期评估规则并触发多通道通知
- REST API 提供指标查询和告警管理接口

**Tech Stack:** FastAPI, SQLAlchemy, APScheduler, aiohttp, smtplib

---

## Task 1: 数据库模型和迁移

**Files:**
- Create: `app/models/metrics.py`
- Create: `alembic/versions/xxx_add_monitoring_tables.py`
- Modify: `app/models/__init__.py`

- [ ] **Step 1: 创建指标数据模型**

在 `app/models/metrics.py` 创建三个模型类：

```python
from sqlalchemy import Column, Integer, String, Float, JSON, DateTime, Boolean, Text, ForeignKey, Index
from sqlalchemy.orm import relationship
from datetime import datetime
from app.models.base import Base

class MetricsTimeSeries(Base):
    """指标时序数据表"""
    __tablename__ = "metrics_timeseries"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    metric_name = Column(String(100), nullable=False, index=True)
    metric_value = Column(Float, nullable=False)
    labels = Column(JSON, nullable=True)
    timestamp = Column(DateTime, nullable=False, index=True, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_metric_time', 'metric_name', 'timestamp'),
    )

class AlertRule(Base):
    """告警规则表"""
    __tablename__ = "alert_rules"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_name = Column(String(100), nullable=False)
    metric_name = Column(String(100), nullable=False)
    condition = Column(String(10), nullable=False)  # "gt", "lt", "eq", "gte", "lte"
    threshold = Column(Float, nullable=False)
    duration_seconds = Column(Integer, default=60)
    channels = Column(JSON, nullable=False)  # ["email", "dingtalk", "wecom"]
    enabled = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

class AlertHistory(Base):
    """告警历史表"""
    __tablename__ = "alert_history"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    rule_id = Column(Integer, ForeignKey('alert_rules.id'), nullable=False)
    triggered_at = Column(DateTime, nullable=False)
    resolved_at = Column(DateTime, nullable=True)
    alert_message = Column(Text, nullable=False)
    metric_value = Column(Float, nullable=False)
    notify_status = Column(String(20), default="pending")
    notify_error = Column(Text, nullable=True)
    
    rule = relationship("AlertRule", backref="history")
```

- [ ] **Step 2: 更新模型包导入**

在 `app/models/__init__.py` 添加：

```python
from app.models.metrics import MetricsTimeSeries, AlertRule, AlertHistory
```

- [ ] **Step 3: 创建数据库迁移脚本**

运行命令创建迁移：

```bash
alembic revision --autogenerate -m "add monitoring tables"
```

预期输出：创建新的迁移文件 `alembic/versions/xxx_add_monitoring_tables.py`

- [ ] **Step 4: 检查并完善迁移脚本**

打开生成的迁移文件，确认包含以下内容：

```python
def upgrade():
    op.create_table(
        'metrics_timeseries',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('labels', sa.JSON(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_metric_time', 'metrics_timeseries', ['metric_name', 'timestamp'])
    
    op.create_table(
        'alert_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_name', sa.String(100), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('condition', sa.String(10), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=False),
        sa.Column('channels', sa.JSON(), nullable=False),
        sa.Column('enabled', sa.Boolean(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    op.create_table(
        'alert_history',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_id', sa.Integer(), nullable=False),
        sa.Column('triggered_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
        sa.Column('alert_message', sa.Text(), nullable=False),
        sa.Column('metric_value', sa.Float(), nullable=False),
        sa.Column('notify_status', sa.String(20), nullable=False),
        sa.Column('notify_error', sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(['rule_id'], ['alert_rules.id']),
        sa.PrimaryKeyConstraint('id')
    )

def downgrade():
    op.drop_table('alert_history')
    op.drop_table('alert_rules')
    op.drop_index('idx_metric_time', 'metrics_timeseries')
    op.drop_table('metrics_timeseries')
```

- [ ] **Step 5: 执行数据库迁移**

运行命令：

```bash
alembic upgrade head
```

预期输出：`INFO  [alembic.runtime.migration] Running upgrade -> xxx, add monitoring tables`

- [ ] **Step 6: 验证表创建**

连接数据库检查表是否创建成功：

```bash
mysql -u user -p -D dbname -e "SHOW TABLES LIKE '%metrics%'; SHOW TABLES LIKE '%alert%';"
```

预期输出：显示 `metrics_timeseries`, `alert_rules`, `alert_history` 三个表

- [ ] **Step 7: 提交**

```bash
git add app/models/metrics.py app/models/__init__.py alembic/versions/xxx_add_monitoring_tables.py
git commit -m "feat: add monitoring database models and migration"
```

---

## Task 2: 指标收集器服务

**Files:**
- Create: `app/services/metrics_collector.py`

- [ ] **Step 1: 创建指标收集器类**

在 `app/services/metrics_collector.py` 创建：

```python
import asyncio
import logging
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_session
from app.models.metrics import MetricsTimeSeries

logger = logging.getLogger(__name__)

class MetricsCollector:
    """指标收集器 - 单例模式"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, '_initialized'):
            return
        self._initialized = True
        self.buffer: List[MetricsTimeSeries] = []
        self.buffer_lock = asyncio.Lock()
        self.flush_interval = 10  # 每 10 秒刷新一次
        self.buffer_size = 100  # 批量写入阈值
        self.hit_count = 0
        self.miss_count = 0
    
    async def record(
        self, 
        metric_name: str, 
        value: float, 
        labels: Optional[Dict] = None,
        timestamp: Optional[datetime] = None
    ):
        """记录指标（异步缓冲）"""
        metric = MetricsTimeSeries(
            metric_name=metric_name,
            metric_value=value,
            labels=labels or {},
            timestamp=timestamp or datetime.utcnow()
        )
        
        async with self.buffer_lock:
            self.buffer.append(metric)
            
            # 缓冲区满则触发刷新
            if len(self.buffer) >= self.buffer_size:
                await self._flush()
    
    async def _flush(self):
        """刷新缓冲区到数据库"""
        if not self.buffer:
            return
        
        async with self.buffer_lock:
            metrics_to_save = self.buffer[:]
            self.buffer.clear()
        
        try:
            async with get_session() as session:
                session.add_all(metrics_to_save)
                await session.commit()
            logger.debug(f"已刷新 {len(metrics_to_save)} 条指标到数据库")
        except Exception as e:
            logger.error(f"指标刷新失败: {e}")
    
    async def start_background_flush(self):
        """启动后台定时刷新"""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self._flush()
    
    async def query(
        self,
        metric_name: str,
        start_time: datetime,
        end_time: datetime,
        labels: Optional[Dict] = None,
        aggregation: Optional[str] = None  # "avg", "sum", "max", "min"
    ) -> List[Dict]:
        """查询指标数据"""
        async with get_session() as session:
            stmt = select(MetricsTimeSeries).where(
                MetricsTimeSeries.metric_name == metric_name,
                MetricsTimeSeries.timestamp >= start_time,
                MetricsTimeSeries.timestamp <= end_time
            )
            
            # 标签过滤
            if labels:
                for key, value in labels.items():
                    stmt = stmt.where(
                        MetricsTimeSeries.labels[key].astext == str(value)
                    )
            
            result = await session.execute(stmt)
            metrics = result.scalars().all()
            
            # 聚合处理
            if aggregation and metrics:
                if aggregation == "avg":
                    return [{"value": sum(m.metric_value for m in metrics) / len(metrics)}]
                elif aggregation == "sum":
                    return [{"value": sum(m.metric_value for m in metrics)}]
                elif aggregation == "max":
                    return [{"value": max(m.metric_value for m in metrics)}]
                elif aggregation == "min":
                    return [{"value": min(m.metric_value for m in metrics)}]
            
            return [
                {
                    "timestamp": m.timestamp.isoformat(),
                    "value": m.metric_value,
                    "labels": m.labels
                }
                for m in metrics
            ]

# 全局单例
metrics_collector = MetricsCollector()
```

- [ ] **Step 2: 编写单元测试**

创建 `tests/test_metrics_collector.py`:

```python
import pytest
from datetime import datetime, timedelta
from app.services.metrics_collector import metrics_collector

@pytest.mark.asyncio
async def test_record_metric():
    """测试记录指标"""
    await metrics_collector.record(
        "test_metric",
        100.5,
        labels={"test": "true"}
    )
    
    # 验证缓冲区有数据
    assert len(metrics_collector.buffer) > 0

@pytest.mark.asyncio
async def test_query_metric():
    """测试查询指标"""
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    
    # 记录测试数据
    await metrics_collector.record("test_query", 50.0)
    await metrics_collector._flush()
    
    # 查询数据
    results = await metrics_collector.query(
        "test_query",
        one_hour_ago,
        now
    )
    
    assert len(results) > 0
    assert results[0]["value"] == 50.0
```

- [ ] **Step 3: 运行测试**

```bash
pytest tests/test_metrics_collector.py -v
```

预期输出：`2 passed`

- [ ] **Step 4: 提交**

```bash
git add app/services/metrics_collector.py tests/test_metrics_collector.py
git commit -m "feat: add metrics collector service with buffering"
```

---

## Task 3: 告警通知渠道

**Files:**
- Create: `app/services/notifiers.py`
- Modify: `app/core/config.py`

- [ ] **Step 1: 添加配置项**

在 `app/core/config.py` 的 `Settings` 类中添加：

```python
class Settings(BaseSettings):
    # ... 现有配置
    
    # 告警邮件配置
    SMTP_HOST: str = "smtp.example.com"
    SMTP_PORT: int = 587
    SMTP_USE_TLS: bool = True
    SMTP_USER: Optional[str] = None
    SMTP_PASSWORD: Optional[str] = None
    ALERT_EMAIL_FROM: Optional[str] = None
    ALERT_EMAIL_TO: Optional[str] = None
    
    # 钉钉机器人
    DINGTALK_WEBHOOK_URL: Optional[str] = None
    
    # 企业微信机器人
    WECOM_WEBHOOK_URL: Optional[str] = None
```

- [ ] **Step 2: 创建通知器类**

在 `app/services/notifiers.py` 创建：

```python
import logging
import aiohttp
import smtplib
from email.mime.text import MIMEText
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

class EmailNotifier:
    """邮件通知"""
    
    async def send(self, message: str):
        """发送邮件"""
        if not settings.ALERT_EMAIL_FROM or not settings.ALERT_EMAIL_TO:
            logger.warning("邮件配置未设置，跳过发送")
            return
        
        msg = MIMEText(message, 'plain', 'utf-8')
        msg['Subject'] = '【告警】浏览器自动化平台'
        msg['From'] = settings.ALERT_EMAIL_FROM
        msg['To'] = settings.ALERT_EMAIL_TO
        
        try:
            with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as server:
                if settings.SMTP_USE_TLS:
                    server.starttls()
                if settings.SMTP_USER and settings.SMTP_PASSWORD:
                    server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                server.send_message(msg)
            logger.info("邮件通知发送成功")
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            raise

class DingTalkNotifier:
    """钉钉机器人通知"""
    
    async def send(self, message: str):
        """发送钉钉消息"""
        if not settings.DINGTALK_WEBHOOK_URL:
            logger.warning("钉钉 Webhook 未配置，跳过发送")
            return
        
        payload = {
            "msgtype": "text",
            "text": {
                "content": f"【告警】\n{message}"
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.DINGTALK_WEBHOOK_URL, 
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"钉钉通知发送失败: {error_text}")
            logger.info("钉钉通知发送成功")
        except Exception as e:
            logger.error(f"钉钉通知失败: {e}")
            raise

class WeComNotifier:
    """企业微信机器人通知"""
    
    async def send(self, message: str):
        """发送企业微信消息"""
        if not settings.WECOM_WEBHOOK_URL:
            logger.warning("企业微信 Webhook 未配置，跳过发送")
            return
        
        payload = {
            "msgtype": "text",
            "text": {
                "content": f"【告警】\n{message}"
            }
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    settings.WECOM_WEBHOOK_URL,
                    json=payload,
                    timeout=aiohttp.ClientTimeout(total=10)
                ) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        raise Exception(f"企业微信通知发送失败: {error_text}")
            logger.info("企业微信通知发送成功")
        except Exception as e:
            logger.error(f"企业微信通知失败: {e}")
            raise
```

- [ ] **Step 3: 编写测试（使用 mock）**

创建 `tests/test_notifiers.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.notifiers import EmailNotifier, DingTalkNotifier, WeComNotifier

@pytest.mark.asyncio
async def test_email_notifier_success():
    """测试邮件发送成功"""
    with patch('smtplib.SMTP') as mock_smtp:
        mock_server = MagicMock()
        mock_smtp.return_value.__enter__.return_value = mock_server
        
        notifier = EmailNotifier()
        await notifier.send("Test message")
        
        mock_server.send_message.assert_called_once()

@pytest.mark.asyncio
async def test_dingtalk_notifier_success():
    """测试钉钉通知成功"""
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_response = AsyncMock()
        mock_response.status = 200
        mock_post.return_value.__aenter__.return_value = mock_response
        
        notifier = DingTalkNotifier()
        await notifier.send("Test message")
```

- [ ] **Step 4: 运行测试**

```bash
pytest tests/test_notifiers.py -v
```

预期输出：`2 passed`

- [ ] **Step 5: 提交**

```bash
git add app/services/notifiers.py app/core/config.py tests/test_notifiers.py
git commit -m "feat: add alert notification channels (email, dingtalk, wecom)"
```

---

## Task 4: 告警引擎

**Files:**
- Create: `app/services/alert_engine.py`

- [ ] **Step 1: 创建告警引擎类**

在 `app/services/alert_engine.py` 创建：

```python
import logging
from typing import Dict
from datetime import datetime, timedelta
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.metrics import AlertRule, AlertHistory, MetricsTimeSeries
from app.core.database import get_session
from app.services.notifiers import EmailNotifier, DingTalkNotifier, WeComNotifier

logger = logging.getLogger(__name__)

class AlertEngine:
    """告警引擎"""
    
    def __init__(self):
        self.notifiers = {
            "email": EmailNotifier(),
            "dingtalk": DingTalkNotifier(),
            "wecom": WeComNotifier()
        }
    
    async def evaluate_rules(self):
        """评估所有告警规则"""
        async with get_session() as session:
            # 查询启用的规则
            stmt = select(AlertRule).where(AlertRule.enabled == True)
            result = await session.execute(stmt)
            rules = result.scalars().all()
            
            logger.info(f"开始评估 {len(rules)} 条告警规则")
            
            for rule in rules:
                try:
                    await self._evaluate_rule(rule, session)
                except Exception as e:
                    logger.error(f"评估规则 {rule.rule_name} 失败: {e}")
    
    async def _evaluate_rule(self, rule: AlertRule, session: AsyncSession):
        """评估单条规则"""
        # 查询最近 duration_seconds 内的指标数据
        start_time = datetime.utcnow() - timedelta(seconds=rule.duration_seconds)
        
        stmt = select(MetricsTimeSeries).where(
            and_(
                MetricsTimeSeries.metric_name == rule.metric_name,
                MetricsTimeSeries.timestamp >= start_time
            )
        ).order_by(MetricsTimeSeries.timestamp.desc())
        
        result = await session.execute(stmt)
        metrics = result.scalars().all()
        
        if not metrics:
            return
        
        # 判断是否所有数据点都满足条件
        triggered = all(
            self._check_condition(m.metric_value, rule.condition, rule.threshold)
            for m in metrics
        )
        
        if triggered:
            # 检查是否已经存在未解决的告警
            stmt = select(AlertHistory).where(
                and_(
                    AlertHistory.rule_id == rule.id,
                    AlertHistory.resolved_at.is_(None)
                )
            )
            result = await session.execute(stmt)
            existing_alert = result.scalar_one_or_none()
            
            if not existing_alert:
                # 创建新告警
                await self._create_alert(rule, metrics[0], session)
    
    def _check_condition(self, value: float, condition: str, threshold: float) -> bool:
        """检查条件"""
        if condition == "gt":
            return value > threshold
        elif condition == "gte":
            return value >= threshold
        elif condition == "lt":
            return value < threshold
        elif condition == "lte":
            return value <= threshold
        elif condition == "eq":
            return value == threshold
        return False
    
    async def _create_alert(self, rule: AlertRule, metric: MetricsTimeSeries, session: AsyncSession):
        """创建告警"""
        alert_message = (
            f"告警规则 [{rule.rule_name}] 触发\n"
            f"指标: {rule.metric_name}\n"
            f"当前值: {metric.metric_value}\n"
            f"阈值: {rule.condition} {rule.threshold}\n"
            f"时间: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        
        alert = AlertHistory(
            rule_id=rule.id,
            triggered_at=datetime.utcnow(),
            alert_message=alert_message,
            metric_value=metric.metric_value,
            notify_status="pending"
        )
        
        session.add(alert)
        await session.commit()
        
        # 发送通知
        success = await self._send_notifications(rule, alert_message)
        
        # 更新通知状态
        if success:
            alert.notify_status = "sent"
        else:
            alert.notify_status = "failed"
        await session.commit()
        
        logger.info(f"告警已触发: {rule.rule_name}")
    
    async def _send_notifications(self, rule: AlertRule, message: str) -> bool:
        """发送通知到各个通道"""
        success = True
        for channel in rule.channels:
            if channel in self.notifiers:
                try:
                    await self.notifiers[channel].send(message)
                except Exception as e:
                    logger.error(f"告警通知发送失败 ({channel}): {e}")
                    success = False
        return success

# 全局实例
alert_engine = AlertEngine()
```

- [ ] **Step 2: 编写测试**

创建 `tests/test_alert_engine.py`:

```python
import pytest
from datetime import datetime, timedelta
from app.services.alert_engine import AlertEngine
from app.models.metrics import AlertRule, MetricsTimeSeries
from app.core.database import get_session

@pytest.mark.asyncio
async def test_check_condition():
    """测试条件检查"""
    engine = AlertEngine()
    
    assert engine._check_condition(10, "gt", 5) == True
    assert engine._check_condition(10, "lt", 5) == False
    assert engine._check_condition(10, "eq", 10) == True
    assert engine._check_condition(10, "gte", 10) == True
    assert engine._check_condition(10, "lte", 10) == True

@pytest.mark.asyncio
async def test_evaluate_rule_not_triggered():
    """测试规则未触发场景"""
    # 创建测试规则
    async with get_session() as session:
        rule = AlertRule(
            rule_name="Test Rule",
            metric_name="test_metric",
            condition="gt",
            threshold=100.0,
            duration_seconds=60,
            channels=["email"],
            enabled=True
        )
        session.add(rule)
        await session.commit()
        
        # 记录低于阈值的指标
        metric = MetricsTimeSeries(
            metric_name="test_metric",
            metric_value=50.0,
            timestamp=datetime.utcnow()
        )
        session.add(metric)
        await session.commit()
        
        # 评估规则
        engine = AlertEngine()
        await engine._evaluate_rule(rule, session)
        
        # 验证没有创建告警
        from sqlalchemy import select
        stmt = select(AlertHistory).where(AlertHistory.rule_id == rule.id)
        result = await session.execute(stmt)
        alerts = result.scalars().all()
        
        assert len(alerts) == 0
```

- [ ] **Step 3: 运行测试**

```bash
pytest tests/test_alert_engine.py -v
```

预期输出：`2 passed`

- [ ] **Step 4: 提交**

```bash
git add app/services/alert_engine.py tests/test_alert_engine.py
git commit -m "feat: add alert engine with rule evaluation"
```

---

## Task 5: 监控指标 API 端点

**Files:**
- Create: `app/api/metrics.py`
- Create: `app/schemas/metrics.py`
- Modify: `app/main.py`

- [ ] **Step 1: 创建 Pydantic schemas**

在 `app/schemas/metrics.py` 创建：

```python
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime

class MetricQuery(BaseModel):
    metric_name: str
    start_time: datetime
    end_time: datetime
    aggregation: Optional[str] = Field(None, regex="^(avg|sum|max|min)$")

class MetricResponse(BaseModel):
    timestamp: str
    value: float
    labels: Optional[dict] = None

class DashboardData(BaseModel):
    job_success_rate: float
    avg_execution_time: float
    browser_pool_utilization: float
    queue_size: float
```

- [ ] **Step 2: 创建 API 路由**

在 `app/api/metrics.py` 创建：

```python
import asyncio
from fastapi import APIRouter, Query, HTTPException
from datetime import datetime, timedelta
from typing import Optional, List

from app.services.metrics_collector import metrics_collector
from app.schemas.metrics import MetricQuery, MetricResponse, DashboardData

router = APIRouter(prefix="/api/metrics", tags=["监控指标"])

@router.get("/", response_model=List[MetricResponse])
async def query_metrics(
    metric_name: str,
    start_time: Optional[datetime] = Query(None),
    end_time: Optional[datetime] = Query(None),
    aggregation: Optional[str] = Query(None, regex="^(avg|sum|max|min)$")
):
    """查询指标数据"""
    if not start_time:
        start_time = datetime.utcnow() - timedelta(hours=1)
    if not end_time:
        end_time = datetime.utcnow()
    
    try:
        results = await metrics_collector.query(
            metric_name=metric_name,
            start_time=start_time,
            end_time=end_time,
            aggregation=aggregation
        )
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")

@router.get("/dashboard", response_model=DashboardData)
async def get_dashboard_data():
    """获取仪表盘数据（预聚合）"""
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    
    try:
        # 并发查询多个指标
        tasks = [
            metrics_collector.query("job_success_rate_1h", one_hour_ago, now, aggregation="avg"),
            metrics_collector.query("job_execution_time", one_hour_ago, now, aggregation="avg"),
            metrics_collector.query("browser_pool_utilization", one_hour_ago, now, aggregation="avg"),
            metrics_collector.query("job_queue_size", one_hour_ago, now, aggregation="avg"),
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return DashboardData(
            job_success_rate=results[0][0]["value"] if results[0] and not isinstance(results[0], Exception) else 0.0,
            avg_execution_time=results[1][0]["value"] if results[1] and not isinstance(results[1], Exception) else 0.0,
            browser_pool_utilization=results[2][0]["value"] if results[2] and not isinstance(results[2], Exception) else 0.0,
            queue_size=results[3][0]["value"] if results[3] and not isinstance(results[3], Exception) else 0.0
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"查询失败: {e}")
```

- [ ] **Step 3: 注册路由到主应用**

在 `app/main.py` 中添加：

```python
from app.api import metrics

app.include_router(metrics.router)
```

- [ ] **Step 4: 测试 API 端点**

启动服务器并测试：

```bash
# 启动服务
uvicorn app.main:app --reload

# 在另一个终端测试
curl "http://localhost:8000/api/metrics/?metric_name=test_metric"
curl "http://localhost:8000/api/metrics/dashboard"
```

预期输出：返回 JSON 格式的指标数据

- [ ] **Step 5: 提交**

```bash
git add app/api/metrics.py app/schemas/metrics.py app/main.py
git commit -m "feat: add metrics query API endpoints"
```

---

## Task 6: 告警管理 API 端点

**Files:**
- Create: `app/api/alerts.py`
- Create: `app/schemas/alerts.py`
- Modify: `app/main.py`

- [ ] **Step 1: 创建 Pydantic schemas**

在 `app/schemas/alerts.py` 创建：

```python
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime

class AlertRuleCreate(BaseModel):
    rule_name: str = Field(..., min_length=1, max_length=100)
    metric_name: str = Field(..., min_length=1, max_length=100)
    condition: str = Field(..., regex="^(gt|gte|lt|lte|eq)$")
    threshold: float
    duration_seconds: int = Field(60, ge=1, le=3600)
    channels: List[str] = Field(..., min_items=1)
    enabled: bool = True

class AlertRuleResponse(BaseModel):
    id: int
    rule_name: str
    metric_name: str
    condition: str
    threshold: float
    duration_seconds: int
    channels: List[str]
    enabled: bool
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class AlertHistoryResponse(BaseModel):
    id: int
    rule_id: int
    triggered_at: datetime
    resolved_at: Optional[datetime]
    alert_message: str
    metric_value: float
    notify_status: str
    
    class Config:
        from_attributes = True
```

- [ ] **Step 2: 创建 API 路由**

在 `app/api/alerts.py` 创建：

```python
from fastapi import APIRouter, HTTPException, Query
from typing import Optional, List
from sqlalchemy import select

from app.core.database import get_session
from app.models.metrics import AlertRule, AlertHistory
from app.schemas.alerts import AlertRuleCreate, AlertRuleResponse, AlertHistoryResponse

router = APIRouter(prefix="/api/alerts", tags=["告警管理"])

@router.post("/rules", response_model=AlertRuleResponse, status_code=201)
async def create_alert_rule(rule: AlertRuleCreate):
    """创建告警规则"""
    async with get_session() as session:
        db_rule = AlertRule(**rule.dict())
        session.add(db_rule)
        await session.commit()
        await session.refresh(db_rule)
        return db_rule

@router.get("/rules", response_model=List[AlertRuleResponse])
async def list_alert_rules(
    enabled: Optional[bool] = None,
    limit: int = Query(50, ge=1, le=100)
):
    """查询告警规则列表"""
    async with get_session() as session:
        stmt = select(AlertRule).limit(limit)
        
        if enabled is not None:
            stmt = stmt.where(AlertRule.enabled == enabled)
        
        result = await session.execute(stmt)
        return result.scalars().all()

@router.get("/rules/{rule_id}", response_model=AlertRuleResponse)
async def get_alert_rule(rule_id: int):
    """获取单个告警规则"""
    async with get_session() as session:
        stmt = select(AlertRule).where(AlertRule.id == rule_id)
        result = await session.execute(stmt)
        rule = result.scalar_one_or_none()
        
        if not rule:
            raise HTTPException(status_code=404, detail="告警规则不存在")
        
        return rule

@router.put("/rules/{rule_id}", response_model=AlertRuleResponse)
async def update_alert_rule(rule_id: int, rule_update: AlertRuleCreate):
    """更新告警规则"""
    async with get_session() as session:
        stmt = select(AlertRule).where(AlertRule.id == rule_id)
        result = await session.execute(stmt)
        db_rule = result.scalar_one_or_none()
        
        if not db_rule:
            raise HTTPException(status_code=404, detail="告警规则不存在")
        
        for key, value in rule_update.dict().items():
            setattr(db_rule, key, value)
        
        await session.commit()
        await session.refresh(db_rule)
        return db_rule

@router.delete("/rules/{rule_id}", status_code=204)
async def delete_alert_rule(rule_id: int):
    """删除告警规则"""
    async with get_session() as session:
        stmt = select(AlertRule).where(AlertRule.id == rule_id)
        result = await session.execute(stmt)
        rule = result.scalar_one_or_none()
        
        if not rule:
            raise HTTPException(status_code=404, detail="告警规则不存在")
        
        await session.delete(rule)
        await session.commit()

@router.get("/history", response_model=List[AlertHistoryResponse])
async def get_alert_history(
    limit: int = Query(50, ge=1, le=100),
    resolved: Optional[bool] = None
):
    """查询告警历史"""
    async with get_session() as session:
        stmt = select(AlertHistory).order_by(AlertHistory.triggered_at.desc()).limit(limit)
        
        if resolved is not None:
            if resolved:
                stmt = stmt.where(AlertHistory.resolved_at.is_not(None))
            else:
                stmt = stmt.where(AlertHistory.resolved_at.is_(None))
        
        result = await session.execute(stmt)
        return result.scalars().all()
```

- [ ] **Step 3: 注册路由到主应用**

在 `app/main.py` 中添加：

```python
from app.api import alerts

app.include_router(alerts.router)
```

- [ ] **Step 4: 测试 API 端点**

```bash
# 创建告警规则
curl -X POST "http://localhost:8000/api/alerts/rules" \
  -H "Content-Type: application/json" \
  -d '{
    "rule_name": "高任务失败率",
    "metric_name": "job_success_rate_1h",
    "condition": "lt",
    "threshold": 0.8,
    "duration_seconds": 300,
    "channels": ["email"],
    "enabled": true
  }'

# 查询规则列表
curl "http://localhost:8000/api/alerts/rules"

# 查询告警历史
curl "http://localhost:8000/api/alerts/history?limit=10"
```

预期输出：返回 JSON 格式的规则和历史数据

- [ ] **Step 5: 提交**

```bash
git add app/api/alerts.py app/schemas/alerts.py app/main.py
git commit -m "feat: add alert management API endpoints"
```

---

## Task 7: 执行器埋点集成

**Files:**
- Modify: `app/services/executor.py`

- [ ] **Step 1: 在执行器中导入指标收集器**

在 `app/services/executor.py` 顶部添加：

```python
import time
from app.services.metrics_collector import metrics_collector
```

- [ ] **Step 2: 在 execute_job 方法中添加埋点**

修改 `execute_job` 方法，在开始和结束时记录指标：

```python
async def execute_job(self, job_id: int, session: AsyncSession):
    start_time = time.time()
    
    try:
        # ... 现有的执行逻辑
        
        # 成功埋点
        execution_time = time.time() - start_time
        await metrics_collector.record(
            "job_execution_time",
            execution_time,
            labels={"job_id": str(job_id), "config_id": str(config.id), "status": "success"}
        )
        
        await metrics_collector.record(
            "job_data_extraction_count",
            len(extracted_data),
            labels={"config_id": str(config.id)}
        )
        
        return {"status": "success", ...}
        
    except Exception as e:
        # 失败埋点
        execution_time = time.time() - start_time
        await metrics_collector.record(
            "job_execution_time",
            execution_time,
            labels={"job_id": str(job_id), "config_id": str(config.id), "status": "failed"}
        )
        
        await metrics_collector.record(
            "job_retry_count",
            1,
            labels={"job_id": str(job_id), "config_id": str(config.id)}
        )
        
        raise
```

- [ ] **Step 3: 测试埋点功能**

运行一个任务并检查指标是否被记录：

```bash
# 运行服务
uvicorn app.main:app --reload

# 触发任务执行（通过 API 或现有测试）

# 查询指标
curl "http://localhost:8000/api/metrics/?metric_name=job_execution_time"
```

预期输出：返回记录的任务执行时间指标

- [ ] **Step 4: 提交**

```bash
git add app/services/executor.py
git commit -m "feat: integrate metrics collection in executor"
```

---

## Task 8: 调度器集成告警引擎

**Files:**
- Modify: `app/services/scheduler.py`

- [ ] **Step 1: 在调度器中导入告警引擎**

在 `app/services/scheduler.py` 顶部添加：

```python
from app.services.alert_engine import alert_engine
```

- [ ] **Step 2: 添加告警评估定时任务**

在 `start` 方法中添加新的定时任务：

```python
async def start(self):
    # ... 现有任务
    
    # 新增：每 5 分钟评估一次告警规则
    self.scheduler.add_job(
        func=alert_engine.evaluate_rules,
        trigger=IntervalTrigger(minutes=5),
        id='evaluate_alert_rules',
        name='评估告警规则',
        next_run_time=datetime.now() + timedelta(minutes=1)  # 1分钟后首次执行
    )
    
    self.logger.info("告警规则评估任务已添加")
```

- [ ] **Step 3: 测试调度器集成**

启动服务并观察日志：

```bash
uvicorn app.main:app --reload
```

预期输出：日志中显示 "告警规则评估任务已添加" 和定期的评估日志

- [ ] **Step 4: 提交**

```bash
git add app/services/scheduler.py
git commit -m "feat: integrate alert engine into scheduler"
```

---

## Task 9: 主应用集成指标收集器后台任务

**Files:**
- Modify: `app/main.py`

- [ ] **Step 1: 在 lifespan 中启动指标刷新任务**

修改 `app/main.py` 的 `lifespan` 函数：

```python
from contextlib import asynccontextmanager
from app.services.metrics_collector import metrics_collector

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("应用启动中...")
    
    # 启动浏览器池
    await browser_pool.initialize()
    
    # 启动任务调度器
    await scheduler.start()
    
    # 启动指标收集器后台刷新任务
    import asyncio
    flush_task = asyncio.create_task(metrics_collector.start_background_flush())
    logger.info("指标收集器后台任务已启动")
    
    logger.info("应用启动完成")
    
    yield
    
    logger.info("应用关闭中...")
    
    # 停止调度器
    await scheduler.shutdown()
    
    # 刷新剩余指标
    await metrics_collector._flush()
    
    # 取消后台任务
    flush_task.cancel()
    try:
        await flush_task
    except asyncio.CancelledError:
        pass
    
    # 关闭浏览器池
    await browser_pool.shutdown()
    
    logger.info("应用已关闭")
```

- [ ] **Step 2: 测试应用启动和关闭**

```bash
# 启动服务
uvicorn app.main:app --reload

# 观察日志
# 预期看到："指标收集器后台任务已启动"

# Ctrl+C 停止服务
# 预期看到："应用关闭中..." 和 "应用已关闭"
```

- [ ] **Step 3: 提交**

```bash
git add app/main.py
git commit -m "feat: integrate metrics collector background task in lifespan"
```

---

## Task 10: 环境配置和文档

**Files:**
- Create: `.env.example` (更新)
- Create: `docs/monitoring_usage.md`

- [ ] **Step 1: 更新环境变量示例**

在 `.env.example` 中添加：

```bash
# 告警邮件配置
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=alerts@example.com
SMTP_PASSWORD=your-password
ALERT_EMAIL_FROM=alerts@example.com
ALERT_EMAIL_TO=admin@example.com

# 钉钉机器人（可选）
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx

# 企业微信机器人（可选）
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
```

- [ ] **Step 2: 创建使用文档**

创建 `docs/monitoring_usage.md`:

```markdown
# 监控告警系统使用指南

## 概述

监控告警系统提供指标收集、查询和基于规则的告警功能。

## 功能特性

1. **指标收集** - 自动收集任务执行、系统资源等指标
2. **告警规则** - 基于阈值的告警规则配置
3. **多通道通知** - 支持邮件、钉钉、企业微信通知
4. **API 查询** - REST API 查询历史指标数据

## 配置说明

### 环境变量

在 `.env` 文件中配置告警通道：

\`\`\`bash
# 邮件通知（必填项）
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
ALERT_EMAIL_FROM=your-email@gmail.com
ALERT_EMAIL_TO=admin@example.com

# 钉钉通知（可选）
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx
\`\`\`

## 使用示例

### 创建告警规则

\`\`\`bash
curl -X POST "http://localhost:8000/api/alerts/rules" \
  -H "Content-Type: application/json" \
  -d '{
    "rule_name": "任务成功率过低",
    "metric_name": "job_success_rate_1h",
    "condition": "lt",
    "threshold": 0.8,
    "duration_seconds": 300,
    "channels": ["email", "dingtalk"],
    "enabled": true
  }'
\`\`\`

### 查询指标数据

\`\`\`bash
# 查询最近1小时的任务执行时间
curl "http://localhost:8000/api/metrics/?metric_name=job_execution_time&aggregation=avg"

# 获取仪表盘数据
curl "http://localhost:8000/api/metrics/dashboard"
\`\`\`

### 查看告警历史

\`\`\`bash
curl "http://localhost:8000/api/alerts/history?limit=20"
\`\`\`

## 内置指标

### 任务维度
- `job_execution_time` - 任务执行耗时（秒）
- `job_success_rate_1h` - 最近1小时成功率
- `job_retry_count` - 任务重试次数
- `job_data_extraction_count` - 数据提取总量

### 系统维度
- `browser_pool_utilization` - 浏览器池利用率
- `database_connection_pool_size` - 数据库连接数
- `websocket_connections` - WebSocket 连接数

## 告警规则条件

- `gt` - 大于（>）
- `gte` - 大于等于（>=）
- `lt` - 小于（<）
- `lte` - 小于等于（<=）
- `eq` - 等于（==）

## 故障排查

### 告警未发送

1. 检查环境变量配置是否正确
2. 查看应用日志中的错误信息
3. 测试 SMTP/Webhook 连接

### 指标未记录

1. 确认数据库迁移已执行
2. 检查 `metrics_timeseries` 表是否存在
3. 查看应用日志中的指标刷新日志
```

- [ ] **Step 3: 提交**

```bash
git add .env.example docs/monitoring_usage.md
git commit -m "docs: add monitoring configuration and usage guide"
```

---

## Task 11: 集成测试

**Files:**
- Create: `tests/integration/test_monitoring_e2e.py`

- [ ] **Step 1: 编写端到端测试**

创建 `tests/integration/test_monitoring_e2e.py`:

```python
import pytest
import asyncio
from datetime import datetime, timedelta
from app.services.metrics_collector import metrics_collector
from app.services.alert_engine import alert_engine
from app.models.metrics import AlertRule
from app.core.database import get_session

@pytest.mark.asyncio
async def test_monitoring_e2e():
    """端到端测试：记录指标 -> 触发告警 -> 发送通知"""
    
    # Step 1: 记录指标数据
    for i in range(5):
        await metrics_collector.record(
            "test_e2e_metric",
            150.0,  # 超过阈值 100
            labels={"test": "true"}
        )
    
    # 刷新到数据库
    await metrics_collector._flush()
    
    # Step 2: 创建告警规则
    async with get_session() as session:
        rule = AlertRule(
            rule_name="E2E Test Rule",
            metric_name="test_e2e_metric",
            condition="gt",
            threshold=100.0,
            duration_seconds=60,
            channels=["email"],
            enabled=True
        )
        session.add(rule)
        await session.commit()
        rule_id = rule.id
    
    # Step 3: 评估告警规则
    await alert_engine.evaluate_rules()
    
    # Step 4: 验证告警已创建
    async with get_session() as session:
        from sqlalchemy import select
        from app.models.metrics import AlertHistory
        
        stmt = select(AlertHistory).where(AlertHistory.rule_id == rule_id)
        result = await session.execute(stmt)
        alerts = result.scalars().all()
        
        assert len(alerts) > 0
        assert alerts[0].notify_status in ["pending", "sent"]
    
    print("✓ 端到端测试通过")

@pytest.mark.asyncio
async def test_api_integration():
    """测试 API 集成"""
    from fastapi.testclient import TestClient
    from app.main import app
    
    client = TestClient(app)
    
    # 测试查询指标
    response = client.get("/api/metrics/?metric_name=test_metric")
    assert response.status_code == 200
    
    # 测试创建告警规则
    response = client.post(
        "/api/alerts/rules",
        json={
            "rule_name": "API Test Rule",
            "metric_name": "test_metric",
            "condition": "gt",
            "threshold": 50.0,
            "duration_seconds": 60,
            "channels": ["email"],
            "enabled": True
        }
    )
    assert response.status_code == 201
    
    # 测试查询告警规则
    response = client.get("/api/alerts/rules")
    assert response.status_code == 200
    assert len(response.json()) > 0
    
    print("✓ API 集成测试通过")
```

- [ ] **Step 2: 运行集成测试**

```bash
pytest tests/integration/test_monitoring_e2e.py -v -s
```

预期输出：`2 passed`，并显示 "✓ 端到端测试通过" 和 "✓ API 集成测试通过"

- [ ] **Step 3: 提交**

```bash
git add tests/integration/test_monitoring_e2e.py
git commit -m "test: add end-to-end monitoring integration tests"
```

---

## Task 12: 最终验证和文档更新

**Files:**
- Modify: `README.md`

- [ ] **Step 1: 更新 README**

在 `README.md` 中添加监控告警系统说明：

```markdown
## 监控告警系统

本系统内置了完整的监控告警功能：

### 功能特性
- 📊 **指标收集** - 自动收集任务执行、系统资源指标
- 🔔 **智能告警** - 基于阈值的告警规则配置
- 📧 **多通道通知** - 支持邮件、钉钉、企业微信
- 📈 **数据查询** - REST API 查询历史指标

### 快速开始

1. 配置告警通道（在 `.env` 文件中）：
\`\`\`bash
SMTP_HOST=smtp.gmail.com
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-password
ALERT_EMAIL_TO=admin@example.com
\`\`\`

2. 创建告警规则：
\`\`\`bash
curl -X POST "http://localhost:8000/api/alerts/rules" \\
  -H "Content-Type: application/json" \\
  -d '{
    "rule_name": "任务成功率低",
    "metric_name": "job_success_rate_1h",
    "condition": "lt",
    "threshold": 0.8,
    "duration_seconds": 300,
    "channels": ["email"]
  }'
\`\`\`

3. 查看仪表盘数据：
\`\`\`bash
curl "http://localhost:8000/api/metrics/dashboard"
\`\`\`

详细文档：[docs/monitoring_usage.md](docs/monitoring_usage.md)
```

- [ ] **Step 2: 运行完整测试套件**

```bash
pytest tests/ -v
```

预期输出：所有测试通过

- [ ] **Step 3: 手动验证功能**

启动服务并手动测试：

```bash
# 1. 启动服务
uvicorn app.main:app --reload

# 2. 创建告警规则
curl -X POST "http://localhost:8000/api/alerts/rules" \
  -H "Content-Type: application/json" \
  -d '{
    "rule_name": "测试规则",
    "metric_name": "job_execution_time",
    "condition": "gt",
    "threshold": 300,
    "duration_seconds": 60,
    "channels": ["email"],
    "enabled": true
  }'

# 3. 触发任务执行（记录指标）

# 4. 查询指标
curl "http://localhost:8000/api/metrics/dashboard"

# 5. 查看告警历史
curl "http://localhost:8000/api/alerts/history"
```

- [ ] **Step 4: 最终提交**

```bash
git add README.md
git commit -m "docs: update README with monitoring system overview"
```

---

## 验收标准

完成以下检查项后，监控告警系统实施完成：

- [ ] 数据库表已创建（metrics_timeseries, alert_rules, alert_history）
- [ ] 指标收集器正常工作（后台定时刷新）
- [ ] 告警引擎正常评估规则（每5分钟）
- [ ] 邮件/钉钉/企业微信通知可正常发送
- [ ] API 端点可正常查询指标和管理告警规则
- [ ] 执行器埋点正常记录任务指标
- [ ] 所有单元测试和集成测试通过
- [ ] 文档完整且准确

## 后续优化建议

1. 添加前端监控仪表盘（使用 Chart.js 或 ECharts）
2. 支持更多告警通道（Slack、Telegram）
3. 实现告警静默和抑制功能
4. 添加指标数据自动清理（保留最近30天）
5. 支持告警规则模板和批量导入

---

**实施完成后，继续执行下一个计划：安全加固**
