# 系统增强至 9 分设计方案

## 文档信息

- **创建日期**: 2026-09-28
- **设计目标**: 将浏览器自动化平台从 7-7.5 分提升至 9 分
- **实现方案**: 渐进式增强（方案 A）
- **预计开发周期**: 2-3 周
- **技术难度**: 中等

## 执行摘要

本设计方案旨在通过四个维度的系统性增强，将当前浏览器自动化平台从 7-7.5 分（功能完整但稳定性待验证）提升至 9 分（生产就绪级别）。采用渐进式增强策略，最小化外部依赖，优先使用 Python 生态内置工具，确保快速落地和易维护性。

**核心增强领域**：
1. **监控告警系统** - 可观测性和异常感知
2. **安全加固** - 数据保护和访问控制
3. **性能优化** - 吞吐量和资源效率
4. **稳定性提升** - 容错能力和自愈机制

**预期效果**：
- 任务执行效率提升 5-10 倍（通过浏览器池和并发）
- 系统可用性从 ~95% 提升至 >99%
- 任务失败率从 ~5% 降低至 <1%
- 安全性达到企业级标准（加密存储、访问控制、审计日志）

---

## 第一部分：监控告警系统

### 1.1 设计目标

**当前问题**：
- 只有 WebSocket 实时推送，无历史数据追溯
- 缺少性能指标和趋势分析
- 异常发生后无法主动感知，依赖人工巡检

**设计目标**：
- 建立轻量级监控指标收集和存储系统
- 提供基于阈值的智能告警机制
- 支持多种告警通道（邮件、钉钉、企业微信）
- 提供简单的可视化仪表盘

### 1.2 架构设计

#### 核心组件

```
┌─────────────────────────────────────────────────────────┐
│                    应用层（FastAPI）                      │
├─────────────────────────────────────────────────────────┤
│  执行器    │   调度器   │   API 端点   │  WebSocket    │
│ (埋点)    │  (埋点)    │  (埋点)      │  (实时推送)   │
└─────┬───────────┬───────────┬────────────┬──────────────┘
      │           │           │            │
      └───────────┴───────────┴────────────┘
                      │
              ┌───────▼───────┐
              │ MetricsCollector│
              │  (指标收集器)   │
              └───────┬────────┘
                      │
          ┌───────────┴────────────┐
          │                        │
    ┌─────▼──────┐         ┌──────▼─────┐
    │  SQLite    │         │ AlertEngine │
    │ (时序存储) │         │ (告警引擎)  │
    └────────────┘         └──────┬──────┘
                                  │
                    ┌─────────────┴──────────────┐
                    │                            │
            ┌───────▼────────┐          ┌───────▼────────┐
            │  邮件通道       │          │  钉钉/企微     │
            └────────────────┘          └────────────────┘
```

#### 数据模型

**1. 指标时序表（metrics_timeseries）**

```python
class MetricsTimeSeries(Base):
    __tablename__ = "metrics_timeseries"
    
    id: int = Column(Integer, primary_key=True)
    metric_name: str = Column(String(100), nullable=False, index=True)
    metric_value: float = Column(Float, nullable=False)
    labels: dict = Column(JSON, nullable=True)  # {"job_id": 123, "config_id": 45}
    timestamp: datetime = Column(DateTime, nullable=False, index=True)
    
    __table_args__ = (
        Index('idx_metric_time', 'metric_name', 'timestamp'),
    )
```

**2. 告警规则表（alert_rules）**

```python
class AlertRule(Base):
    __tablename__ = "alert_rules"
    
    id: int = Column(Integer, primary_key=True)
    rule_name: str = Column(String(100), nullable=False)
    metric_name: str = Column(String(100), nullable=False)
    condition: str = Column(String(10), nullable=False)  # "gt", "lt", "eq", "gte", "lte"
    threshold: float = Column(Float, nullable=False)
    duration_seconds: int = Column(Integer, default=60)  # 持续多久触发
    channels: list = Column(JSON, nullable=False)  # ["email", "dingtalk", "wecom"]
    enabled: bool = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
```

**3. 告警历史表（alert_history）**

```python
class AlertHistory(Base):
    __tablename__ = "alert_history"
    
    id: int = Column(Integer, primary_key=True)
    rule_id: int = Column(Integer, ForeignKey('alert_rules.id'))
    triggered_at: datetime = Column(DateTime, nullable=False)
    resolved_at: datetime = Column(DateTime, nullable=True)
    alert_message: str = Column(Text, nullable=False)
    metric_value: float = Column(Float, nullable=False)
    notify_status: str = Column(String(20), default="pending")  # "pending", "sent", "failed"
    notify_error: str = Column(Text, nullable=True)
```

### 1.3 关键指标定义

#### 任务维度指标

| 指标名称 | 类型 | 说明 | 标签 |
|---------|------|------|------|
| `job_execution_time` | Gauge | 任务执行耗时（秒） | job_id, config_id, status |
| `job_success_rate_1h` | Gauge | 最近1小时任务成功率 | config_id |
| `job_success_rate_24h` | Gauge | 最近24小时任务成功率 | config_id |
| `job_retry_count` | Counter | 任务重试次数 | job_id, config_id |
| `job_queue_size` | Gauge | 待处理任务数量 | status |
| `job_data_extraction_count` | Counter | 数据提取总量 | config_id |

#### 系统维度指标

| 指标名称 | 类型 | 说明 | 标签 |
|---------|------|------|------|
| `browser_instance_count` | Gauge | 浏览器实例数量 | status (idle/busy) |
| `browser_pool_utilization` | Gauge | 浏览器池利用率 (0-1) | - |
| `database_connection_pool_size` | Gauge | 数据库连接数 | status (checked_in/checked_out) |
| `websocket_connections` | Gauge | WebSocket 活跃连接数 | - |
| `api_request_latency_p50` | Gauge | API 响应时间 P50（毫秒） | endpoint |
| `api_request_latency_p95` | Gauge | API 响应时间 P95（毫秒） | endpoint |
| `api_request_latency_p99` | Gauge | API 响应时间 P99（毫秒） | endpoint |
| `memory_usage_mb` | Gauge | 进程内存使用量（MB） | - |
| `cpu_usage_percent` | Gauge | CPU 使用率（%） | - |

#### 业务维度指标

| 指标名称 | 类型 | 说明 | 标签 |
|---------|------|------|------|
| `page_crawl_speed` | Gauge | 翻页速度（页/分钟） | config_id |
| `auth_session_check_success` | Counter | 登录态有效性检查成功次数 | auth_profile |
| `auth_session_check_failure` | Counter | 登录态失效次数 | auth_profile |
| `config_cache_hit_rate` | Gauge | 配置缓存命中率 | - |

### 1.4 指标收集器实现

```python
# app/services/metrics_collector.py
import asyncio
import time
from typing import Dict, Optional, List
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.core.database import get_session
from app.models.metrics import MetricsTimeSeries

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

### 1.5 告警引擎实现

```python
# app/services/alert_engine.py
from typing import List, Dict
from datetime import datetime, timedelta
from sqlalchemy import select, and_

from app.models.metrics import AlertRule, AlertHistory, MetricsTimeSeries
from app.core.database import get_session

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
            
            for rule in rules:
                await self._evaluate_rule(rule, session)
    
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
                await self._create_alert(rule, metrics[-1], session)
    
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
        await self._send_notifications(rule, alert_message)
        
        # 更新通知状态
        alert.notify_status = "sent"
        await session.commit()
    
    async def _send_notifications(self, rule: AlertRule, message: str):
        """发送通知到各个通道"""
        for channel in rule.channels:
            if channel in self.notifiers:
                try:
                    await self.notifiers[channel].send(message)
                except Exception as e:
                    logger.error(f"告警通知发送失败 ({channel}): {e}")

# 全局实例
alert_engine = AlertEngine()
```

### 1.6 告警通道实现

```python
# app/services/notifiers.py
import aiohttp
import smtplib
from email.mime.text import MIMEText
from app.core.config import settings

class EmailNotifier:
    """邮件通知"""
    
    async def send(self, message: str):
        """发送邮件"""
        msg = MIMEText(message, 'plain', 'utf-8')
        msg['Subject'] = '【告警】浏览器自动化平台'
        msg['From'] = settings.ALERT_EMAIL_FROM
        msg['To'] = settings.ALERT_EMAIL_TO
        
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            if settings.SMTP_USE_TLS:
                server.starttls()
            if settings.SMTP_USER:
                server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.send_message(msg)

class DingTalkNotifier:
    """钉钉机器人通知"""
    
    async def send(self, message: str):
        """发送钉钉消息"""
        webhook_url = settings.DINGTALK_WEBHOOK_URL
        
        payload = {
            "msgtype": "text",
            "text": {
                "content": f"【告警】\n{message}"
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as resp:
                if resp.status != 200:
                    raise Exception(f"钉钉通知发送失败: {await resp.text()}")

class WeComNotifier:
    """企业微信机器人通知"""
    
    async def send(self, message: str):
        """发送企业微信消息"""
        webhook_url = settings.WECOM_WEBHOOK_URL
        
        payload = {
            "msgtype": "text",
            "text": {
                "content": f"【告警】\n{message}"
            }
        }
        
        async with aiohttp.ClientSession() as session:
            async with session.post(webhook_url, json=payload) as resp:
                if resp.status != 200:
                    raise Exception(f"企业微信通知发送失败: {await resp.text()}")
```

### 1.7 API 端点

```python
# app/api/metrics.py
from fastapi import APIRouter, Query
from datetime import datetime, timedelta

router = APIRouter(prefix="/api/metrics", tags=["监控指标"])

@router.get("/")
async def query_metrics(
    metric_name: str,
    start_time: datetime = Query(default_factory=lambda: datetime.utcnow() - timedelta(hours=1)),
    end_time: datetime = Query(default_factory=datetime.utcnow),
    aggregation: Optional[str] = None
):
    """查询指标数据"""
    return await metrics_collector.query(
        metric_name=metric_name,
        start_time=start_time,
        end_time=end_time,
        aggregation=aggregation
    )

@router.get("/dashboard")
async def get_dashboard_data():
    """获取仪表盘数据（预聚合）"""
    now = datetime.utcnow()
    one_hour_ago = now - timedelta(hours=1)
    
    # 并发查询多个指标
    tasks = [
        metrics_collector.query("job_success_rate_1h", one_hour_ago, now, aggregation="avg"),
        metrics_collector.query("job_execution_time", one_hour_ago, now, aggregation="avg"),
        metrics_collector.query("browser_pool_utilization", one_hour_ago, now, aggregation="avg"),
        metrics_collector.query("job_queue_size", one_hour_ago, now, aggregation="avg"),
    ]
    
    results = await asyncio.gather(*tasks)
    
    return {
        "job_success_rate": results[0][0]["value"] if results[0] else 0,
        "avg_execution_time": results[1][0]["value"] if results[1] else 0,
        "browser_pool_utilization": results[2][0]["value"] if results[2] else 0,
        "queue_size": results[3][0]["value"] if results[3] else 0
    }

# app/api/alerts.py
router = APIRouter(prefix="/api/alerts", tags=["告警管理"])

@router.post("/rules")
async def create_alert_rule(rule: AlertRuleCreate):
    """创建告警规则"""
    async with get_session() as session:
        db_rule = AlertRule(**rule.dict())
        session.add(db_rule)
        await session.commit()
        return db_rule

@router.get("/history")
async def get_alert_history(
    limit: int = 50,
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

### 1.8 执行器埋点示例

```python
# app/services/executor.py (修改部分)
class PlaywrightExecutor:
    async def execute_job(self, job_id: int, session: AsyncSession):
        start_time = time.time()
        
        try:
            # ... 执行逻辑
            
            # 成功埋点
            execution_time = time.time() - start_time
            await metrics_collector.record(
                "job_execution_time",
                execution_time,
                labels={"job_id": job_id, "config_id": config.id, "status": "success"}
            )
            
            await metrics_collector.record(
                "job_data_extraction_count",
                len(extracted_data),
                labels={"config_id": config.id}
            )
            
            return {"status": "success", ...}
            
        except Exception as e:
            # 失败埋点
            execution_time = time.time() - start_time
            await metrics_collector.record(
                "job_execution_time",
                execution_time,
                labels={"job_id": job_id, "config_id": config.id, "status": "failed"}
            )
            
            await metrics_collector.record(
                "job_retry_count",
                1,
                labels={"job_id": job_id, "config_id": config.id}
            )
            
            raise
```

### 1.9 配置项

```bash
# .env 新增配置
# 告警邮件配置
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=alerts@example.com
SMTP_PASSWORD=your-password
ALERT_EMAIL_FROM=alerts@example.com
ALERT_EMAIL_TO=admin@example.com

# 钉钉机器人
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx

# 企业微信机器人
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx
```

---

## 第二部分：安全加固

### 2.1 设计目标

**当前安全风险**：
- 登录态文件明文存储（`auth_files/*.json`）
- API 无认证机制，任何人可调用
- 数据库连接信息在 `.env` 明文存储
- WebSocket 无身份验证
- 缺少输入验证和注入防护

**设计目标**：
- 敏感数据加密存储
- 实现 JWT + API Key 双重认证
- 完善输入验证和安全审计
- 达到企业级安全标准

### 2.2 登录态加密存储

#### 加密方案

使用 `cryptography.fernet` 对称加密：
- 加密算法：Fernet (AES-128-CBC + HMAC)
- 密钥管理：从环境变量读取，首次启动自动生成
- 文件格式：`auth_files/auth_{profile}.enc`

#### 实现代码

```python
# app/services/auth_encryption.py
import os
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
import json

class AuthEncryption:
    """登录态加密服务"""
    
    def __init__(self, encryption_key: str):
        """
        初始化加密器
        
        Args:
            encryption_key: Base64 编码的密钥（从环境变量读取）
        """
        self.cipher = Fernet(encryption_key.encode())
    
    def encrypt_auth_file(self, auth_data: dict) -> bytes:
        """加密登录态数据"""
        json_str = json.dumps(auth_data, ensure_ascii=False)
        encrypted = self.cipher.encrypt(json_str.encode('utf-8'))
        return encrypted
    
    def decrypt_auth_file(self, encrypted_data: bytes) -> dict:
        """解密登录态数据"""
        decrypted = self.cipher.decrypt(encrypted_data)
        return json.loads(decrypted.decode('utf-8'))
    
    @staticmethod
    def generate_key() -> str:
        """生成新的加密密钥"""
        return Fernet.generate_key().decode()

# 全局实例
auth_encryption = AuthEncryption(settings.AUTH_ENCRYPTION_KEY)
```

#### 迁移脚本

```python
# scripts/migrate_auth_files.py
"""迁移明文登录态文件到加密格式"""
import os
import json
from pathlib import Path
from app.services.auth_encryption import auth_encryption

def migrate_auth_files():
    auth_dir = Path("auth_files")
    
    for json_file in auth_dir.glob("auth_*.json"):
        enc_file = json_file.with_suffix(".enc")
        
        if enc_file.exists():
            print(f"跳过 {json_file}（已存在加密文件）")
            continue
        
        # 读取明文文件
        with open(json_file, 'r', encoding='utf-8') as f:
            auth_data = json.load(f)
        
        # 加密并保存
        encrypted = auth_encryption.encrypt_auth_file(auth_data)
        with open(enc_file, 'wb') as f:
            f.write(encrypted)
        
        print(f"已加密: {json_file} -> {enc_file}")
        
        # 备份原文件
        backup_file = json_file.with_suffix(".json.bak")
        json_file.rename(backup_file)
        print(f"原文件已备份: {backup_file}")

if __name__ == "__main__":
    migrate_auth_files()
```

#### 执行器集成

```python
# app/services/executor.py (修改 _launch_browser 方法)
async def _launch_browser(self, config: CrawlerConfig):
    if config.need_login:
        # 优先尝试加载加密文件
        enc_file = f"auth_files/auth_{config.auth_profile}.enc"
        json_file = f"auth_files/auth_{config.auth_profile}.json"
        
        if os.path.exists(enc_file):
            with open(enc_file, 'rb') as f:
                encrypted_data = f.read()
            auth_data = auth_encryption.decrypt_auth_file(encrypted_data)
            
            # 写入临时文件供 Playwright 使用
            temp_file = f"auth_files/.temp_{config.auth_profile}.json"
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(auth_data, f)
            
            context = await browser.new_context(storage_state=temp_file)
            
            # 清理临时文件
            os.remove(temp_file)
        elif os.path.exists(json_file):
            # 降级到明文文件（兼容性）
            logger.warning(f"使用明文登录态文件: {json_file}（建议迁移）")
            context = await browser.new_context(storage_state=json_file)
        else:
            raise FileNotFoundError(f"登录态文件不存在: {config.auth_profile}")
    
    return browser, context, playwright
```

### 2.3 API 认证机制

#### JWT 令牌认证

```python
# app/auth/jwt_handler.py
from datetime import datetime, timedelta
from jose import jwt, JWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings

security = HTTPBearer()

def create_access_token(user_id: str, expires_delta: timedelta = None) -> str:
    """创建 JWT 访问令牌"""
    if expires_delta is None:
        expires_delta = timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    
    expire = datetime.utcnow() + expires_delta
    
    payload = {
        "sub": user_id,
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": "access"
    }
    
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)

def verify_token(token: str) -> dict:
    """验证 JWT 令牌"""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"令牌验证失败: {e}"
        )

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """获取当前用户（JWT 依赖注入）"""
    token = credentials.credentials
    payload = verify_token(token)
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌"
        )
    
    return user_id
```

#### API Key 认证

```python
# app/auth/api_key.py
import hashlib
import secrets
from fastapi import Header, HTTPException, status
from sqlalchemy import select

from app.models.api_key import APIKey
from app.core.database import get_session

async def generate_api_key() -> tuple[str, str]:
    """生成 API Key（返回原始 key 和 hash）"""
    raw_key = secrets.token_urlsafe(32)
    key_hash = hashlib.sha256(raw_key.encode()).hexdigest()
    return raw_key, key_hash

async def validate_api_key(x_api_key: str = Header(None)) -> str:
    """验证 API Key（依赖注入）"""
    if not x_api_key:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 API Key（请在 Header 中提供 X-API-Key）"
        )
    
    # 计算 hash
    key_hash = hashlib.sha256(x_api_key.encode()).hexdigest()
    
    # 查询数据库
    async with get_session() as session:
        stmt = select(APIKey).where(
            APIKey.key_hash == key_hash,
            APIKey.is_active == True
        )
        result = await session.execute(stmt)
        api_key = result.scalar_one_or_none()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="无效的 API Key"
            )
        
        # 更新最后使用时间
        api_key.last_used_at = datetime.utcnow()
        await session.commit()
        
        return api_key.name

# 数据库模型
class APIKey(Base):
    __tablename__ = "api_keys"
    
    id: int = Column(Integer, primary_key=True)
    name: str = Column(String(100), nullable=False)  # API Key 名称
    key_hash: str = Column(String(64), unique=True, nullable=False)  # SHA256 hash
    is_active: bool = Column(Boolean, default=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    last_used_at: datetime = Column(DateTime, nullable=True)
    created_by: str = Column(String(100), nullable=True)
```

#### 统一认证依赖

```python
# app/auth/dependencies.py
from fastapi import Depends
from typing import Union

async def require_auth(
    jwt_user: str = Depends(get_current_user, use_cache=False),
) -> str:
    """要求 JWT 认证"""
    return jwt_user

async def require_auth_or_api_key(
    jwt_user: Union[str, None] = Depends(get_current_user, use_cache=False),
    api_key_name: Union[str, None] = Depends(validate_api_key, use_cache=False)
) -> str:
    """要求 JWT 或 API Key 认证（任一即可）"""
    if jwt_user:
        return f"user:{jwt_user}"
    elif api_key_name:
        return f"apikey:{api_key_name}"
    else:
        raise HTTPException(status_code=401, detail="未认证")
```

#### 路由保护

```python
# app/api/endpoints.py (修改示例)
from app.auth.dependencies import require_auth_or_api_key

@app.post("/api/jobs")
async def create_job(
    job: JobCreate,
    current_identity: str = Depends(require_auth_or_api_key)
):
    """创建任务（需要认证）"""
    logger.info(f"任务创建请求来自: {current_identity}")
    # ... 业务逻辑
```

### 2.4 WebSocket 认证

```python
# app/api/websocket.py (修改)
from app.auth.jwt_handler import verify_token

class WebSocketManager:
    async def websocket_endpoint(self, websocket: WebSocket):
        # 从 query 参数获取 token
        token = websocket.query_params.get("token")
        
        if not token:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        try:
            payload = verify_token(token)
            user_id = payload.get("sub")
        except Exception as e:
            logger.warning(f"WebSocket 认证失败: {e}")
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return
        
        # 认证成功，继续处理
        await self.connect(websocket)
        logger.info(f"WebSocket 连接已认证: {user_id}")
        
        # ... 后续逻辑
```

### 2.5 输入验证增强

```python
# app/schemas/job.py (增强)
import re
from pydantic import BaseModel, Field, validator

class JobCreate(BaseModel):
    config_id: int = Field(gt=0, description="配置 ID（必须大于 0）")
    query_params: Dict[str, str] = Field(
        max_length=10,
        description="查询参数（最多 10 个）"
    )
    
    @validator('query_params')
    def validate_params(cls, v):
        """验证查询参数"""
        # 防止参数值过长
        for key, value in v.items():
            if len(key) > 50:
                raise ValueError(f"参数名 {key} 过长（最多 50 字符）")
            if len(value) > 1000:
                raise ValueError(f"参数 {key} 值过长（最多 1000 字符）")
            
            # 防止特殊字符注入
            if re.search(r'[<>\'";`]', value):
                raise ValueError(f"参数 {key} 包含非法字符")
        
        return v
    
    class Config:
        str_strip_whitespace = True  # 自动去除首尾空格
        anystr_lower = False  # 不强制小写

# app/schemas/config.py (增强)
class ConfigCreate(BaseModel):
    config_name: str = Field(min_length=1, max_length=100)
    target_url: HttpUrl  # Pydantic 自动验证 URL 格式
    
    @validator('target_url')
    def validate_target_url(cls, v):
        """验证目标 URL"""
        # 只允许 HTTP/HTTPS 协议
        if v.scheme not in ['http', 'https']:
            raise ValueError("只支持 HTTP/HTTPS 协议")
        
        # 禁止内网地址（可选）
        if settings.BLOCK_INTERNAL_URLS:
            host = v.host
            if host in ['localhost', '127.0.0.1'] or host.startswith('192.168.'):
                raise ValueError("不允许访问内网地址")
        
        return v
```

### 2.6 日志脱敏

```python
# app/core/logging_config.py
import re
import logging

class SensitiveDataFilter(logging.Filter):
    """敏感数据过滤器"""
    
    SENSITIVE_PATTERNS = [
        (r'(password|pwd|secret|token|key|api_key)=([^\s&]+)', r'\1=***'),
        (r'(Authorization:\s*Bearer\s+)([^\s]+)', r'\1***'),
        (r'("password"\s*:\s*")[^"]+(")', r'\1***\2'),
        (r'("api_key"\s*:\s*")[^"]+(")', r'\1***\2'),
    ]
    
    def filter(self, record):
        """过滤日志消息中的敏感信息"""
        if hasattr(record, 'msg') and isinstance(record.msg, str):
            for pattern, replacement in self.SENSITIVE_PATTERNS:
                record.msg = re.sub(pattern, replacement, record.msg, flags=re.IGNORECASE)
        
        return True

# 应用过滤器
logger = logging.getLogger()
logger.addFilter(SensitiveDataFilter())
```

### 2.7 速率限制

```python
# app/middleware/rate_limit.py
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

# app/main.py
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# 使用示例
@app.post("/api/jobs")
@limiter.limit("10/minute")  # 每分钟最多 10 次
async def create_job(...):
    ...

@app.post("/api/auth/login")
@limiter.limit("5/minute")  # 登录接口更严格
async def login(...):
    ...
```

### 2.8 CORS 配置

```python
# app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),  # 从环境变量读取
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    max_age=3600  # 预检请求缓存 1 小时
)
```

### 2.9 安全配置项

```bash
# .env 新增配置
# JWT 配置
JWT_SECRET=your-very-long-random-secret-key-at-least-32-characters
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# 认证加密密钥（首次启动自动生成）
AUTH_ENCRYPTION_KEY=

# CORS 白名单（逗号分隔）
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com

# 速率限制
RATE_LIMIT_ENABLED=true

# 安全选项
BLOCK_INTERNAL_URLS=true
```

### 2.10 安全检查清单

- ✅ 登录态文件加密存储（Fernet AES-128）
- ✅ API 认证机制（JWT + API Key）
- ✅ WebSocket 连接验证（JWT token）
- ✅ 输入验证和长度限制（Pydantic）
- ✅ SQL 注入防护（SQLAlchemy ORM）
- ✅ 速率限制（slowapi）
- ✅ CORS 配置（白名单）
- ✅ 敏感日志脱敏（正则过滤）
- ✅ API Key 安全存储（SHA256 hash）
- ✅ 密钥管理（环境变量）

---

## 第三部分：性能优化

### 3.1 设计目标

**当前性能瓶颈**：
- 每个任务启动/关闭一次浏览器（耗时 2-3 秒）
- 串行执行任务，无并发控制
- 数据库连接池使用默认配置
- 缺少缓存机制，重复查询配置表
- 大量临时变量可能导致内存泄漏

**优化目标**：
- 任务启动时间降低 10 倍（3s → 0.3s）
- 支持 5-10 并发任务执行
- 吞吐量提升 5 倍（1200 → 6000 任务/小时）
- 内存占用降低 40%

### 3.2 浏览器实例池

#### 设计原理

**问题**：每次任务都启动/关闭浏览器进程，开销巨大  
**方案**：维护浏览器进程池，复用浏览器上下文（Context）

```
传统模式（每任务）：
启动浏览器(3s) → 执行任务(5s) → 关闭浏览器(0.5s) = 8.5s

池化模式（首次）：
预热池(一次性 3s) → 获取Context(0.1s) → 执行任务(5s) → 释放Context(0.1s) = 5.2s
              ↓
            后续任务：0.1s + 5s + 0.1s = 5.2s
```

#### 实现代码

```python
# app/services/browser_pool.py
import asyncio
from typing import List, Optional
from playwright.async_api import async_playwright, Browser, BrowserContext
import logging

logger = logging.getLogger(__name__)

class BrowserPool:
    """浏览器实例池"""
    
    def __init__(
        self,
        pool_size: int = 3,
        max_contexts_per_browser: int = 5
    ):
        """
        初始化浏览器池
        
        Args:
            pool_size: 浏览器进程数（默认 3）
            max_contexts_per_browser: 每个浏览器最大上下文数（默认 5）
        """
        self.pool_size = pool_size
        self.max_contexts_per_browser = max_contexts_per_browser
        self.browsers: List[Browser] = []
        self.context_semaphore = asyncio.Semaphore(pool_size * max_contexts_per_browser)
        self.browser_index = 0
        self.lock = asyncio.Lock()
        self.playwright = None
        self._ready = False
    
    async def initialize(self):
        """预热池：启动浏览器进程"""
        logger.info(f"初始化浏览器池（进程数: {self.pool_size}）...")
        
        self.playwright = await async_playwright().start()
        
        for i in range(self.pool_size):
            browser = await self.playwright.chromium.launch(
                headless=True,
                args=[
                    '--disable-blink-features=AutomationControlled',
                    '--no-sandbox',  # Docker 环境需要
                    '--disable-dev-shm-usage',  # 避免共享内存不足
                ]
            )
            self.browsers.append(browser)
            logger.info(f"浏览器 #{i+1} 已启动")
        
        self._ready = True
        logger.info(f"浏览器池初始化完成（总容量: {self.pool_size * self.max_contexts_per_browser}）")
    
    async def acquire_context(
        self,
        auth_profile: Optional[str] = None,
        storage_state: Optional[dict] = None
    ) -> BrowserContext:
        """
        获取浏览器上下文
        
        Args:
            auth_profile: 登录态配置名（可选）
            storage_state: 登录态数据（可选）
        
        Returns:
            BrowserContext 实例
        """
        # 信号量限流
        await self.context_semaphore.acquire()
        
        # 轮询选择浏览器（简单负载均衡）
        async with self.lock:
            browser = self.browsers[self.browser_index % self.pool_size]
            self.browser_index += 1
        
        # 创建上下文
        if storage_state:
            context = await browser.new_context(storage_state=storage_state)
        else:
            context = await browser.new_context()
        
        logger.debug(f"获取浏览器上下文（总使用: {self.pool_size * self.max_contexts_per_browser - self.context_semaphore._value}）")
        
        return context
    
    async def release_context(self, context: BrowserContext):
        """释放上下文"""
        try:
            await context.close()
        except Exception as e:
            logger.warning(f"关闭上下文失败: {e}")
        finally:
            self.context_semaphore.release()
        
        logger.debug(f"释放浏览器上下文（剩余容量: {self.context_semaphore._value}）")
    
    async def get_stats(self) -> dict:
        """获取池统计信息"""
        total = self.pool_size * self.max_contexts_per_browser
        in_use = total - self.context_semaphore._value
        
        return {
            "total": total,
            "in_use": in_use,
            "available": self.context_semaphore._value,
            "utilization": in_use / total if total > 0 else 0
        }
    
    def is_ready(self) -> bool:
        """检查池是否就绪"""
        return self._ready
    
    async def shutdown(self):
        """关闭所有浏览器"""
        logger.info("关闭浏览器池...")
        
        for i, browser in enumerate(self.browsers):
            try:
                await browser.close()
                logger.info(f"浏览器 #{i+1} 已关闭")
            except Exception as e:
                logger.error(f"关闭浏览器 #{i+1} 失败: {e}")
        
        if self.playwright:
            await self.playwright.stop()
        
        self._ready = False
        logger.info("浏览器池已关闭")

# 全局实例
browser_pool = BrowserPool(
    pool_size=settings.BROWSER_POOL_SIZE,
    max_contexts_per_browser=settings.MAX_CONTEXTS_PER_BROWSER
)
```

#### 执行器集成

```python
# app/services/executor.py (修改)
class PlaywrightExecutor:
    def __init__(self, ws_manager=None, browser_pool=None):
        self.ws_manager = ws_manager
        self.browser_pool = browser_pool or globals()['browser_pool']
        self.logger = logger
    
    async def execute_job(self, job_id: int, session: AsyncSession):
        context = None
        page = None
        
        try:
            # ... 查询配置
            
            # 从池获取上下文（替代原有的启动浏览器逻辑）
            if config.need_login:
                # 加载登录态
                storage_state = await self._load_auth_storage(config.auth_profile)
                context = await self.browser_pool.acquire_context(storage_state=storage_state)
            else:
                context = await self.browser_pool.acquire_context()
            
            page = await context.new_page()
            
            # ... 执行任务逻辑
            
        finally:
            if page:
                await page.close()
            
            if context:
                await self.browser_pool.release_context(context)
    
    async def _load_auth_storage(self, auth_profile: str) -> dict:
        """加载登录态数据"""
        enc_file = f"auth_files/auth_{auth_profile}.enc"
        
        with open(enc_file, 'rb') as f:
            encrypted_data = f.read()
        
        return auth_encryption.decrypt_auth_file(encrypted_data)
```

### 3.3 并发任务执行

#### 并发控制器

```python
# app/services/job_executor_service.py
import asyncio
from typing import Set
from sqlalchemy import select
from app.models.job import JobQueue, JobStatus

class JobExecutorService:
    """任务执行服务 - 管理并发"""
    
    def __init__(self, max_concurrent_jobs: int = 5):
        """
        初始化执行服务
        
        Args:
            max_concurrent_jobs: 最大并发任务数（默认 5）
        """
        self.max_concurrent_jobs = max_concurrent_jobs
        self.semaphore = asyncio.Semaphore(max_concurrent_jobs)
        self.executor = PlaywrightExecutor(browser_pool=browser_pool)
        self.running_tasks: Set[asyncio.Task] = set()
        self.lock = asyncio.Lock()
    
    async def execute_job_with_limit(self, job_id: int):
        """带信号量限制的任务执行"""
        task = asyncio.current_task()
        
        async with self.lock:
            self.running_tasks.add(task)
        
        try:
            async with self.semaphore:
                async with get_session() as session:
                    await self.executor.execute_job(job_id, session)
        finally:
            async with self.lock:
                self.running_tasks.discard(task)
    
    async def process_pending_jobs(self):
        """批量处理待执行任务（并发）"""
        # 查询待执行任务
        async with get_session() as session:
            stmt = select(JobQueue).where(
                JobQueue.status == JobStatus.PENDING
            ).order_by(
                JobQueue.created_at.asc()
            ).limit(self.max_concurrent_jobs * 2)  # 取 2 倍防止饥饿
            
            result = await session.execute(stmt)
            pending_jobs = result.scalars().all()
        
        if not pending_jobs:
            return
        
        logger.info(f"发现 {len(pending_jobs)} 个待执行任务，开始并发处理...")
        
        # 并发执行
        tasks = [
            asyncio.create_task(self.execute_job_with_limit(job.id))
            for job in pending_jobs
        ]
        
        # 等待所有任务完成（忽略异常）
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # 统计结果
        success_count = sum(1 for r in results if not isinstance(r, Exception))
        failed_count = len(results) - success_count
        
        logger.info(f"批次执行完成：成功 {success_count}，失败 {failed_count}")
    
    async def wait_all_jobs(self):
        """等待所有正在执行的任务完成（优雅关闭）"""
        if not self.running_tasks:
            return
        
        logger.info(f"等待 {len(self.running_tasks)} 个任务完成...")
        await asyncio.gather(*self.running_tasks, return_exceptions=True)
        logger.info("所有任务已完成")

# 全局实例
job_executor_service = JobExecutorService(
    max_concurrent_jobs=settings.MAX_CONCURRENT_JOBS
)
```

#### 调度器集成

```python
# app/services/scheduler.py (新增)
class TaskScheduler:
    async def start(self):
        # 原有的失败重试任务
        self.scheduler.add_job(...)
        
        # 新增：定期处理待执行任务
        self.scheduler.add_job(
            func=job_executor_service.process_pending_jobs,
            trigger=IntervalTrigger(seconds=30),
            id='process_pending_jobs',
            name='处理待执行任务（并发）',
            next_run_time=datetime.now() + timedelta(seconds=5)
        )
```

### 3.4 数据库连接池优化

```python
# app/core/database.py (优化配置)
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import QueuePool

# 连接池参数调优
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=False,  # 生产环境关闭 SQL 日志
    pool_size=20,              # 连接池大小（默认 5 → 20）
    max_overflow=10,           # 最大溢出连接（默认 10）
    pool_timeout=30,           # 获取连接超时（秒）
    pool_recycle=3600,         # 连接回收时间（1小时，防止 MySQL 8h 超时）
    pool_pre_ping=True,        # 使用前检测连接有效性
    poolclass=QueuePool,
    connect_args={
        "charset": "utf8mb4",
        "connect_timeout": 10,  # MySQL 连接超时
        "autocommit": False,
    },
    # 性能优化
    execution_options={
        "isolation_level": "READ COMMITTED"  # 隔离级别
    }
)

# 监控端点
async def get_db_pool_stats() -> dict:
    """获取数据库连接池统计"""
    pool = engine.pool
    return {
        "size": pool.size(),
        "checked_in": pool.checkedin(),
        "checked_out": pool.checkedout(),
        "overflow": pool.overflow(),
        "total": pool.size() + pool.overflow(),
        "timeout": pool.timeout()
    }
```

### 3.5 配置缓存层

```python
# app/services/config_cache.py
import asyncio
from typing import Dict, Tuple, Optional
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.config import CrawlerConfig

class ConfigCache:
    """配置缓存 - 减少数据库查询"""
    
    def __init__(self, ttl_seconds: int = 300):
        """
        初始化缓存
        
        Args:
            ttl_seconds: 缓存过期时间（默认 5 分钟）
        """
        self.cache: Dict[int, Tuple[CrawlerConfig, datetime]] = {}
        self.ttl = timedelta(seconds=ttl_seconds)
        self.lock = asyncio.Lock()
        self.hit_count = 0
        self.miss_count = 0
    
    async def get(self, config_id: int, session: AsyncSession) -> Optional[CrawlerConfig]:
        """
        获取配置（优先从缓存）
        
        Args:
            config_id: 配置 ID
            session: 数据库会话
        
        Returns:
            配置对象或 None
        """
        # 检查缓存
        async with self.lock:
            if config_id in self.cache:
                config, cached_at = self.cache[config_id]
                if datetime.now() - cached_at < self.ttl:
                    self.hit_count += 1
                    logger.debug(f"配置缓存命中: {config_id}")
                    return config
                else:
                    # 过期，移除
                    del self.cache[config_id]
        
        # 缓存未命中，从数据库加载
        self.miss_count += 1
        logger.debug(f"配置缓存未命中: {config_id}")
        
        stmt = select(CrawlerConfig).where(CrawlerConfig.id == config_id)
        result = await session.execute(stmt)
        config = result.scalar_one_or_none()
        
        if config:
            async with self.lock:
                self.cache[config_id] = (config, datetime.now())
        
        return config
    
    async def invalidate(self, config_id: int):
        """主动失效缓存（配置更新时调用）"""
        async with self.lock:
            if config_id in self.cache:
                del self.cache[config_id]
                logger.debug(f"配置缓存已失效: {config_id}")
    
    async def clear(self):
        """清空所有缓存"""
        async with self.lock:
            self.cache.clear()
            logger.info("配置缓存已清空")
    
    def get_stats(self) -> dict:
        """获取缓存统计"""
        total_requests = self.hit_count + self.miss_count
        hit_rate = self.hit_count / total_requests if total_requests > 0 else 0
        
        return {
            "hit_count": self.hit_count,
            "miss_count": self.miss_count,
            "hit_rate": hit_rate,
            "cached_items": len(self.cache)
        }

# 全局实例
config_cache = ConfigCache(ttl_seconds=settings.CONFIG_CACHE_TTL)
```

#### 执行器集成

```python
# executor.py
async def execute_job(self, job_id: int, session: AsyncSession):
    # 使用缓存获取配置
    config = await config_cache.get(job.config_id, session)
    
    if not config:
        raise ValueError(f"配置不存在: {job.config_id}")
```

#### API 端点集成

```python
# endpoints.py
@app.put("/api/configs/{config_id}")
async def update_config(config_id: int, config_update: ConfigUpdate):
    # 更新配置
    async with get_session() as session:
        # ... 更新逻辑
        await session.commit()
    
    # 清除缓存
    await config_cache.invalidate(config_id)
    
    return {"message": "配置已更新"}
```

### 3.6 数据提取性能优化

#### 浏览器端处理

将 Python 端的过滤逻辑移到浏览器端执行，减少数据传输和处理时间。

```python
# executor.py - _extract_page_data 优化版本
async def _extract_page_data(self, page, fields_mapping):
    """数据提取（浏览器端完成所有处理）"""
    
    container_selector = fields_mapping['list_selector']
    fields = fields_mapping['fields']
    
    # 在浏览器端完成提取和过滤
    page_data = await page.evaluate("""
        (config) => {
            const { containerSelector, fields } = config;
            const result = [];
            
            const containers = document.querySelectorAll(containerSelector);
            
            containers.forEach((container, index) => {
                // 跳过占位行
                if (container.classList.contains('jqgfirstrow')) {
                    return;
                }
                
                const row = {};
                let isValid = false;
                
                fields.forEach(field => {
                    const { name, selector, attr, validationRegex } = field;
                    const element = container.querySelector(selector);
                    let value = '';
                    
                    if (element) {
                        if (attr === 'text') {
                            value = (element.innerText || element.textContent || '').trim();
                        } else {
                            value = (element.getAttribute(attr) || '').trim();
                        }
                    }
                    
                    row[name] = value;
                    
                    // 浏览器端验证（减少无效数据传输）
                    if (validationRegex && value) {
                        const regex = new RegExp(validationRegex);
                        if (regex.test(value)) {
                            isValid = true;
                        }
                    } else if (value.length > 0) {
                        isValid = true;
                    }
                });
                
                // 只添加有效数据
                if (isValid) {
                    result.push(row);
                }
            });
            
            return result;
        }
    """, {
        "containerSelector": container_selector,
        "fields": [
            {
                **field,
                "validationRegex": field.get("validation_regex", "")
            }
            for field in fields
        ]
    })
    
    return page_data
```

### 3.7 内存优化

```python
# executor.py
import gc
from collections import deque

class PlaywrightExecutor:
    def __init__(self, ...):
        # 限制日志缓存大小
        self.console_logs = deque(maxlen=100)  # 最多保留 100 条
    
    async def execute_job(self, job_id: int, session: AsyncSession):
        try:
            # ... 执行逻辑
            
            # 及时释放大对象
            extracted_data = await self._extract_page_data(...)
            await self._save_result(...)
            
            # 显式删除
            del extracted_data
            
        finally:
            # 长时间运行后强制垃圾回收
            if job_id % 100 == 0:  # 每 100 个任务
                gc.collect()
                logger.debug("执行垃圾回收")
```

### 3.8 配置项

```bash
# .env 新增配置
# 浏览器池配置
BROWSER_POOL_SIZE=3
MAX_CONTEXTS_PER_BROWSER=5

# 并发配置
MAX_CONCURRENT_JOBS=5

# 缓存配置
CONFIG_CACHE_TTL=300  # 秒
```

### 3.9 性能监控指标

新增指标（自动记录）：
- `browser_pool_utilization` - 浏览器池利用率
- `browser_context_acquisition_time` - 获取上下文耗时
- `db_connection_pool_size` - 数据库连接池状态
- `config_cache_hit_rate` - 配置缓存命中率
- `concurrent_jobs_count` - 当前并发任务数
- `memory_usage_mb` - 进程内存使用量

### 3.10 性能目标

| 指标 | 优化前 | 优化后 | 提升 |
|------|--------|--------|------|
| 单任务启动时间 | 3s | 0.3s | 10x |
| 并发任务数 | 1 | 5-10 | 5-10x |
| 吞吐量（任务/小时） | ~1200 | ~6000 | 5x |
| 数据库查询 QPS | ~50 | ~200 | 4x |
| 配置查询响应时间 | 50ms | 5ms | 10x |
| 内存占用（10 并发） | ~500MB | ~300MB | -40% |

---

## 第四部分：稳定性提升

### 4.1 设计目标

**当前风险**：
- 异常处理不完善，可能导致任务卡死
- 资源泄漏（浏览器/数据库连接未正确关闭）
- 缺少优雅关闭机制
- WebSocket 断线后无重连机制
- 长时间运行可能累积错误状态
- 缺少健康检查和自愈能力

**稳定性目标**：
- 任务失败率从 ~5% 降低至 <1%
- 资源泄漏频率降至 0
- 支持优雅关闭（成功率 >95%）
- 系统可用性（SLA）从 ~95% 提升至 >99%
- MTTR（平均恢复时间）<5 分钟

### 4.2 分层异常处理

#### 异常类型定义

```python
# app/core/exceptions.py
class BrowserAutomationError(Exception):
    """浏览器自动化基础异常"""
    pass

class AuthenticationError(BrowserAutomationError):
    """登录态失效异常"""
    def __init__(self, auth_profile: str, message: str = "登录态已失效"):
        self.auth_profile = auth_profile
        super().__init__(f"{message}: {auth_profile}")

class ElementNotFoundError(BrowserAutomationError):
    """元素未找到异常"""
    def __init__(self, selector: str, message: str = "元素未找到"):
        self.selector = selector
        super().__init__(f"{message}: {selector}")

class DataExtractionError(BrowserAutomationError):
    """数据提取异常"""
    pass

class ResourceExhaustedError(BrowserAutomationError):
    """资源耗尽异常"""
    pass

class ConfigurationError(BrowserAutomationError):
    """配置错误异常"""
    pass
```

#### 异常处理装饰器

```python
# app/core/decorators.py
import functools
from typing import Callable
import asyncio

def handle_task_exceptions(func: Callable):
    """任务执行异常统一处理"""
    
    @functools.wraps(func)
    async def wrapper(self, job_id: int, session: AsyncSession):
        try:
            return await func(self, job_id, session)
        
        except AuthenticationError as e:
            # 登录态失效 - 标记需要重新登录
            logger.error(f"任务 {job_id} 登录态失效: {e}")
            await self._handle_auth_failure(job_id, session, e.auth_profile)
            
        except ElementNotFoundError as e:
            # 页面结构变化 - 标记配置需要更新
            logger.error(f"任务 {job_id} 元素未找到: {e}")
            await self._handle_config_outdated(job_id, session, e.selector)
            
        except ResourceExhaustedError as e:
            # 资源不足 - 延迟重试
            logger.warning(f"任务 {job_id} 资源不足: {e}")
            await self._delay_retry(job_id, session, delay_seconds=60)
            
        except asyncio.TimeoutError as e:
            # 超时 - 记录并重试
            logger.error(f"任务 {job_id} 执行超时: {e}")
            await self._mark_timeout(job_id, session)
            
        except ConfigurationError as e:
            # 配置错误 - 不重试，需要人工修复
            logger.error(f"任务 {job_id} 配置错误: {e}")
            await self._mark_config_error(job_id, session, str(e))
            
        except Exception as e:
            # 未知异常 - 记录详细信息并重试
            logger.exception(f"任务 {job_id} 执行失败（未知异常）")
            await self._mark_failed(job_id, session, str(e))
    
    return wrapper
```

#### 执行器异常处理方法

```python
# executor.py
class PlaywrightExecutor:
    
    async def _handle_auth_failure(self, job_id: int, session: AsyncSession, auth_profile: str):
        """处理登录态失效"""
        stmt = select(JobQueue).where(JobQueue.id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one()
        
        job.status = JobStatus.FAILED
        job.error_msg = f"登录态失效，需要重新登录: {auth_profile}"
        job.retry_count += 1
        
        await session.commit()
        
        # 发送告警
        await alert_engine.send_alert(
            "auth_failure",
            f"登录态失效: {auth_profile}，任务 #{job_id}"
        )
    
    async def _handle_config_outdated(self, job_id: int, session: AsyncSession, selector: str):
        """处理配置过期"""
        stmt = select(JobQueue).where(JobQueue.id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one()
        
        job.status = JobStatus.FAILED
        job.error_msg = f"页面结构变化，选择器失效: {selector}"
        job.retry_count += 1
        
        await session.commit()
        
        # 发送告警
        await alert_engine.send_alert(
            "config_outdated",
            f"选择器失效: {selector}，任务 #{job_id}"
        )
    
    async def _delay_retry(self, job_id: int, session: AsyncSession, delay_seconds: int):
        """延迟重试"""
        stmt = select(JobQueue).where(JobQueue.id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one()
        
        job.status = JobStatus.PENDING  # 重置为待执行
        job.error_msg = f"资源不足，{delay_seconds}秒后重试"
        
        await session.commit()
        
        # 发送延迟执行任务
        await asyncio.sleep(delay_seconds)
    
    async def _mark_timeout(self, job_id: int, session: AsyncSession):
        """标记超时"""
        stmt = select(JobQueue).where(JobQueue.id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one()
        
        job.status = JobStatus.FAILED
        job.error_msg = "任务执行超时"
        job.retry_count += 1
        
        await session.commit()
    
    async def _mark_config_error(self, job_id: int, session: AsyncSession, error: str):
        """标记配置错误（不重试）"""
        stmt = select(JobQueue).where(JobQueue.id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one()
        
        job.status = JobStatus.FAILED
        job.error_msg = f"配置错误: {error}"
        job.retry_count = 999  # 设置为最大值，阻止自动重试
        
        await session.commit()
    
    async def _mark_failed(self, job_id: int, session: AsyncSession, error: str):
        """标记失败"""
        stmt = select(JobQueue).where(JobQueue.id == job_id)
        result = await session.execute(stmt)
        job = result.scalar_one()
        
        job.status = JobStatus.FAILED
        job.error_msg = error
        job.retry_count += 1
        
        await session.commit()
```

### 4.3 资源管理增强

#### 超时保护

```python
# executor.py
@handle_task_exceptions
async def execute_job(self, job_id: int, session: AsyncSession):
    """执行任务（带超时保护）"""
    
    # 整个任务级别超时
    try:
        async with asyncio.timeout(600):  # 10 分钟超时
            return await self._execute_job_internal(job_id, session)
    except asyncio.TimeoutError:
        raise TimeoutError(f"任务 {job_id} 执行超时（10分钟）")
```

#### 资源清理

```python
async def _execute_job_internal(self, job_id: int, session: AsyncSession):
    """内部执行逻辑（确保资源释放）"""
    context = None
    page = None
    
    try:
        # 获取资源
        context = await self.browser_pool.acquire_context(...)
        page = await context.new_page()
        
        # ... 执行逻辑
        
        return result
    
    finally:
        # 确保资源释放（即使异常也执行）
        if page:
            try:
                await asyncio.wait_for(page.close(), timeout=5)
            except Exception as e:
                logger.warning(f"页面关闭失败: {e}")
        
        if context:
            try:
                await asyncio.wait_for(
                    self.browser_pool.release_context(context),
                    timeout=5
                )
            except Exception as e:
                logger.error(f"上下文释放失败: {e}")
                # 强制清理（避免泄漏）
                try:
                    await context.close()
                except:
                    pass
```

### 4.4 优雅关闭机制

```python
# app/main.py
import signal
from contextlib import asynccontextmanager

shutdown_event = asyncio.Event()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    logger.info("========== 应用启动 ==========")
    
    # 启动组件
    logger.info("初始化浏览器池...")
    await browser_pool.initialize()
    
    logger.info("启动任务调度器...")
    await scheduler.start()
    
    logger.info("启动指标收集器...")
    asyncio.create_task(metrics_collector.start_background_flush())
    
    # 注册信号处理
    def signal_handler(sig, frame):
        logger.warning(f"收到信号 {sig}，开始优雅关闭...")
        shutdown_event.set()
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("========== 应用启动完成 ==========")
    
    yield
    
    # 优雅关闭
    logger.info("========== 应用关闭中 ==========")
    
    # 1. 停止调度器（不再创建新任务）
    logger.info("停止任务调度器...")
    await scheduler.shutdown()
    
    # 2. 等待正在执行的任务（最多等待 30 秒）
    logger.info("等待正在执行的任务完成...")
    try:
        await asyncio.wait_for(
            job_executor_service.wait_all_jobs(),
            timeout=30
        )
        logger.info("所有任务已完成")
    except asyncio.TimeoutError:
        logger.warning("部分任务未完成，强制关闭")
    
    # 3. 刷新指标数据
    logger.info("刷新指标数据...")
    await metrics_collector._flush()
    
    # 4. 关闭浏览器池
    logger.info("关闭浏览器池...")
    await browser_pool.shutdown()
    
    # 5. 关闭 WebSocket 连接
    logger.info("关闭 WebSocket 连接...")
    await websocket_manager.close_all()
    
    # 6. 关闭数据库连接池
    logger.info("关闭数据库连接池...")
    await engine.dispose()
    
    logger.info("========== 应用已关闭 ==========")

app = FastAPI(lifespan=lifespan)
```

#### WebSocket 管理器增强

```python
# websocket.py
class WebSocketManager:
    async def close_all(self):
        """关闭所有连接"""
        if not self.active_connections:
            return
        
        logger.info(f"关闭 {len(self.active_connections)} 个 WebSocket 连接...")
        
        # 发送关闭通知
        await self.broadcast({
            "type": "system",
            "message": "服务器即将关闭，连接将断开"
        })
        
        # 关闭所有连接
        for connection in list(self.active_connections):
            try:
                await connection.close()
            except Exception as e:
                logger.warning(f"关闭 WebSocket 失败: {e}")
        
        self.active_connections.clear()
        logger.info("所有 WebSocket 连接已关闭")
```

### 4.5 健康检查增强

```python
# app/api/health.py
from enum import Enum
from pydantic import BaseModel
from typing import Dict, Optional

class HealthStatus(str, Enum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"

class ComponentHealth(BaseModel):
    status: HealthStatus
    message: str
    latency_ms: Optional[float] = None
    details: Optional[Dict] = None

class HealthCheck(BaseModel):
    status: HealthStatus
    timestamp: datetime
    components: Dict[str, ComponentHealth]

@app.get("/health", response_model=HealthCheck)
async def health_check():
    """综合健康检查"""
    components = {}
    
    # 1. 数据库健康检查
    components["database"] = await check_database_health()
    
    # 2. 浏览器池健康检查
    components["browser_pool"] = await check_browser_pool_health()
    
    # 3. 调度器健康检查
    components["scheduler"] = check_scheduler_health()
    
    # 4. WebSocket 健康检查
    components["websocket"] = check_websocket_health()
    
    # 5. 内存健康检查
    components["memory"] = check_memory_health()
    
    # 综合判断
    overall_status = determine_overall_status(components)
    
    return HealthCheck(
        status=overall_status,
        timestamp=datetime.now(),
        components=components
    )

async def check_database_health() -> ComponentHealth:
    """数据库健康检查"""
    start = time.time()
    
    try:
        async with get_session() as session:
            await session.execute(text("SELECT 1"))
        
        latency = (time.time() - start) * 1000
        
        # 获取连接池状态
        pool_stats = await get_db_pool_stats()
        
        if latency > 1000:
            return ComponentHealth(
                status=HealthStatus.DEGRADED,
                message="数据库响应慢",
                latency_ms=latency,
                details=pool_stats
            )
        
        if pool_stats["checked_out"] / pool_stats["total"] > 0.9:
            return ComponentHealth(
                status=HealthStatus.DEGRADED,
                message="数据库连接池使用率过高",
                latency_ms=latency,
                details=pool_stats
            )
        
        return ComponentHealth(
            status=HealthStatus.HEALTHY,
            message="数据库正常",
            latency_ms=latency,
            details=pool_stats
        )
    
    except Exception as e:
        return ComponentHealth(
            status=HealthStatus.UNHEALTHY,
            message=f"数据库连接失败: {e}"
        )

async def check_browser_pool_health() -> ComponentHealth:
    """浏览器池健康检查"""
    try:
        if not browser_pool.is_ready():
            return ComponentHealth(
                status=HealthStatus.UNHEALTHY,
                message="浏览器池未初始化"
            )
        
        stats = await browser_pool.get_stats()
        utilization = stats['utilization']
        
        if utilization > 0.9:
            return ComponentHealth(
                status=HealthStatus.DEGRADED,
                message=f"浏览器池使用率过高 ({utilization:.0%})",
                details=stats
            )
        
        return ComponentHealth(
            status=HealthStatus.HEALTHY,
            message=f"浏览器池正常 ({stats['in_use']}/{stats['total']})",
            details=stats
        )
    
    except Exception as e:
        return ComponentHealth(
            status=HealthStatus.UNHEALTHY,
            message=f"浏览器池异常: {e}"
        )

def check_scheduler_health() -> ComponentHealth:
    """调度器健康检查"""
    if not scheduler.scheduler.running:
        return ComponentHealth(
            status=HealthStatus.UNHEALTHY,
            message="调度器未运行"
        )
    
    jobs = scheduler.scheduler.get_jobs()
    
    return ComponentHealth(
        status=HealthStatus.HEALTHY,
        message=f"调度器正常 ({len(jobs)} 个任务)",
        details={"job_count": len(jobs)}
    )

def check_websocket_health() -> ComponentHealth:
    """WebSocket 健康检查"""
    conn_count = len(websocket_manager.active_connections)
    
    if conn_count > 100:
        return ComponentHealth(
            status=HealthStatus.DEGRADED,
            message=f"WebSocket 连接数过多 ({conn_count})",
            details={"connection_count": conn_count}
        )
    
    return ComponentHealth(
        status=HealthStatus.HEALTHY,
        message=f"WebSocket 正常 ({conn_count} 连接)",
        details={"connection_count": conn_count}
    )

def check_memory_health() -> ComponentHealth:
    """内存健康检查"""
    import psutil
    
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    memory_percent = process.memory_percent()
    
    if memory_percent > 80:
        return ComponentHealth(
            status=HealthStatus.DEGRADED,
            message=f"内存使用率过高 ({memory_percent:.1f}%)",
            details={"memory_mb": memory_mb, "memory_percent": memory_percent}
        )
    
    return ComponentHealth(
        status=HealthStatus.HEALTHY,
        message=f"内存正常 ({memory_mb:.0f}MB)",
        details={"memory_mb": memory_mb, "memory_percent": memory_percent}
    )

def determine_overall_status(components: Dict[str, ComponentHealth]) -> HealthStatus:
    """综合判断整体状态"""
    if any(c.status == HealthStatus.UNHEALTHY for c in components.values()):
        return HealthStatus.UNHEALTHY
    
    if any(c.status == HealthStatus.DEGRADED for c in components.values()):
        return HealthStatus.DEGRADED
    
    return HealthStatus.HEALTHY

# Kubernetes 探测端点
@app.get("/ready")
async def readiness_probe():
    """就绪探测"""
    if not browser_pool.is_ready():
        raise HTTPException(503, "浏览器池未就绪")
    
    if not scheduler.scheduler.running:
        raise HTTPException(503, "调度器未运行")
    
    return {"status": "ready"}

@app.get("/live")
async def liveness_probe():
    """存活探测"""
    # 简单的存活检查（进程未死锁）
    return {"status": "alive", "timestamp": datetime.now().isoformat()}
```

### 4.6 自动恢复服务

```python
# app/services/recovery_service.py
from datetime import datetime, timedelta

class RecoveryService:
    """自动恢复服务"""
    
    def __init__(self):
        self.scheduler = AsyncIOScheduler()
    
    async def start(self):
        """启动恢复服务"""
        logger.info("启动自动恢复服务...")
        
        # 每 5 分钟检查卡死任务
        self.scheduler.add_job(
            func=self.recover_stuck_jobs,
            trigger=IntervalTrigger(minutes=5),
            id='recover_stuck_jobs',
            name='恢复卡死任务'
        )
        
        # 每 10 分钟检查资源泄漏
        self.scheduler.add_job(
            func=self.check_resource_leaks,
            trigger=IntervalTrigger(minutes=10),
            id='check_resource_leaks',
            name='检查资源泄漏'
        )
        
        self.scheduler.start()
    
    async def recover_stuck_jobs(self):
        """恢复卡死的任务"""
        logger.info("检查卡死任务...")
        
        async with get_session() as session:
            # 查询超过 30 分钟仍在 processing 状态的任务
            stuck_threshold = datetime.now() - timedelta(minutes=30)
            
            stmt = select(JobQueue).where(
                JobQueue.status == JobStatus.PROCESSING,
                JobQueue.updated_at < stuck_threshold
            )
            
            result = await session.execute(stmt)
            stuck_jobs = result.scalars().all()
            
            if not stuck_jobs:
                return
            
            logger.warning(f"发现 {len(stuck_jobs)} 个卡死任务")
            
            for job in stuck_jobs:
                # 重置为 pending 状态
                job.status = JobStatus.PENDING
                job.error_msg = "任务执行超时，已自动重置"
                
                logger.info(f"任务 #{job.id} 已重置")
                
                # 发送告警
                await alert_engine.send_alert(
                    "stuck_job_recovered",
                    f"任务 #{job.id} 卡死已恢复"
                )
            
            await session.commit()
    
    async def check_resource_leaks(self):
        """检查资源泄漏"""
        import psutil
        
        process = psutil.Process()
        
        # 检查文件描述符泄漏
        num_fds = process.num_fds() if hasattr(process, 'num_fds') else 0
        if num_fds > 1000:
            logger.warning(f"文件描述符数量过多: {num_fds}")
            await alert_engine.send_alert(
                "resource_leak",
                f"文件描述符泄漏: {num_fds}"
            )
        
        # 检查内存泄漏
        memory_percent = process.memory_percent()
        if memory_percent > 80:
            logger.warning(f"内存使用率过高: {memory_percent:.1f}%")
            await alert_engine.send_alert(
                "memory_leak",
                f"内存使用率: {memory_percent:.1f}%"
            )

# 全局实例
recovery_service = RecoveryService()
```

### 4.7 结构化日志

```python
# app/core/logging_config.py
import logging
import json
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """JSON 格式日志"""
    
    def format(self, record):
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        # 添加追踪 ID
        if hasattr(record, 'job_id'):
            log_data['job_id'] = record.job_id
        
        if hasattr(record, 'config_id'):
            log_data['config_id'] = record.config_id
        
        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, ensure_ascii=False)

# 配置日志
def setup_logging():
    """配置日志系统"""
    
    # 创建日志目录
    os.makedirs("logs", exist_ok=True)
    
    # JSON 格式（生产环境）
    json_handler = logging.handlers.RotatingFileHandler(
        "logs/app.json.log",
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10,
        encoding='utf-8'
    )
    json_handler.setFormatter(JSONFormatter())
    
    # 人类可读格式（开发环境）
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    ))
    
    # 根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(json_handler)
    root_logger.addHandler(console_handler)
    
    # 添加敏感数据过滤器
    root_logger.addFilter(SensitiveDataFilter())
```

### 4.8 断路器模式

```python
# app/core/circuit_breaker.py
from enum import Enum
import time

class CircuitState(Enum):
    CLOSED = "closed"      # 正常
    OPEN = "open"          # 熔断
    HALF_OPEN = "half_open"  # 半开（尝试恢复）

class CircuitBreaker:
    """断路器 - 防止故障扩散"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        timeout: int = 60,
        success_threshold: int = 2
    ):
        """
        初始化断路器
        
        Args:
            failure_threshold: 失败阈值（连续失败多少次后熔断）
            timeout: 熔断超时（秒，超时后尝试恢复）
            success_threshold: 成功阈值（半开状态需要连续成功多少次才恢复）
        """
        self.failure_threshold = failure_threshold
        self.timeout = timeout
        self.success_threshold = success_threshold
        
        self.failure_count = 0
        self.success_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        """包装函数调用"""
        
        # 如果断路器打开
        if self.state == CircuitState.OPEN:
            # 检查是否可以尝试恢复
            if time.time() - self.last_failure_time > self.timeout:
                self.state = CircuitState.HALF_OPEN
                self.success_count = 0
                logger.info("断路器进入半开状态，尝试恢复")
            else:
                raise Exception(f"断路器已打开，拒绝请求（{self.timeout - int(time.time() - self.last_failure_time)}秒后重试）")
        
        # 执行函数
        try:
            result = await func(*args, **kwargs)
            
            # 成功处理
            if self.state == CircuitState.HALF_OPEN:
                self.success_count += 1
                if self.success_count >= self.success_threshold:
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0
                    logger.info("断路器恢复正常")
            elif self.state == CircuitState.CLOSED:
                self.failure_count = 0  # 重置失败计数
            
            return result
        
        except Exception as e:
            # 失败处理
            self.failure_count += 1
            self.last_failure_time = time.time()
            
            if self.state == CircuitState.HALF_OPEN:
                # 半开状态失败，直接打开
                self.state = CircuitState.OPEN
                logger.error("断路器恢复失败，重新打开")
            elif self.failure_count >= self.failure_threshold:
                # 失败次数达到阈值，打开断路器
                self.state = CircuitState.OPEN
                logger.error(f"断路器打开（连续失败 {self.failure_count} 次）")
            
            raise
    
    def get_state(self) -> dict:
        """获取断路器状态"""
        return {
            "state": self.state.value,
            "failure_count": self.failure_count,
            "success_count": self.success_count
        }

# 使用示例
browser_pool_breaker = CircuitBreaker(
    failure_threshold=3,
    timeout=60,
    success_threshold=2
)

# 在执行器中使用
async def execute_with_breaker(job_id: int, session: AsyncSession):
    return await browser_pool_breaker.call(
        executor.execute_job,
        job_id,
        session
    )
```

### 4.9 稳定性监控指标

新增指标：
- `exception_count_by_type` - 异常类型分布（Counter）
- `stuck_jobs_count` - 卡死任务数量（Gauge）
- `circuit_breaker_state` - 断路器状态（Gauge，0=closed, 1=half_open, 2=open）
- `resource_leak_warnings` - 资源泄漏警告次数（Counter）
- `graceful_shutdown_duration` - 优雅关闭耗时（Histogram）
- `job_recovery_count` - 任务自动恢复次数（Counter）

### 4.10 配置项

```bash
# .env 新增配置
# 恢复服务配置
STUCK_JOB_THRESHOLD_MINUTES=30
RESOURCE_LEAK_CHECK_INTERVAL_MINUTES=10

# 断路器配置
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60
CIRCUIT_BREAKER_SUCCESS_THRESHOLD=2
```

---

## 第五部分：实施计划

### 5.1 实施顺序

**阶段 1：监控告警（第 1 周）**
1. 数据库迁移（metrics 表）
2. 指标收集器实现
3. 告警引擎实现
4. 埋点集成
5. API 端点开发

**阶段 2：安全加固（第 1-2 周）**
1. 登录态加密实现
2. JWT 认证实现
3. API Key 认证实现
4. 输入验证增强
5. 速率限制和 CORS

**阶段 3：性能优化（第 2 周）**
1. 浏览器池实现
2. 并发执行服务实现
3. 数据库连接池优化
4. 配置缓存实现
5. 性能测试和调优

**阶段 4：稳定性提升（第 3 周）**
1. 异常处理完善
2. 优雅关闭机制
3. 健康检查增强
4. 自动恢复服务
5. 断路器实现

**阶段 5：集成测试和文档（第 3 周）**
1. 端到端测试
2. 压力测试
3. 文档更新
4. 部署指南

### 5.2 验收标准

**监控告警**：
- ✅ 所有关键指标正常收集
- ✅ 告警规则生效
- ✅ 通知通道正常工作
- ✅ Dashboard 可视化

**安全加固**：
- ✅ 登录态文件加密存储
- ✅ API 认证通过测试
- ✅ 输入验证覆盖所有端点
- ✅ 无安全漏洞

**性能优化**：
- ✅ 任务启动时间 <0.5s
- ✅ 支持 5 并发任务
- ✅ 吞吐量 >5000 任务/小时
- ✅ 内存占用稳定

**稳定性提升**：
- ✅ 任务失败率 <1%
- ✅ 资源泄漏检测通过
- ✅ 优雅关闭成功率 >95%
- ✅ 健康检查通过

### 5.3 风险评估

**技术风险**：
- 浏览器池可能存在并发竞态条件 → 充分测试
- 加密密钥管理不当 → 使用环境变量 + 文档说明
- 并发任务可能导致数据库死锁 → 使用乐观锁

**业务风险**：
- 迁移期间服务中断 → 灰度发布
- 新功能引入 Bug → 充分测试 + 回滚方案
- 性能优化可能影响稳定性 → 分阶段上线

### 5.4 回滚方案

- 数据库迁移使用 Alembic 支持回滚
- 新功能通过特性开关（Feature Flag）控制
- 保留原有代码路径，确保可快速切换

---

## 附录

### A. 环境变量清单

```bash
# 数据库配置
DATABASE_URL=mysql+aiomysql://user:password@localhost:3306/dbname

# 应用配置
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=false

# JWT 配置
JWT_SECRET=your-very-long-random-secret-key-at-least-32-characters
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=60

# 认证加密密钥
AUTH_ENCRYPTION_KEY=auto-generated

# CORS 白名单
ALLOWED_ORIGINS=http://localhost:3000,https://yourdomain.com

# 速率限制
RATE_LIMIT_ENABLED=true

# 浏览器池配置
BROWSER_POOL_SIZE=3
MAX_CONTEXTS_PER_BROWSER=5

# 并发配置
MAX_CONCURRENT_JOBS=5

# 缓存配置
CONFIG_CACHE_TTL=300

# 告警邮件配置
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USE_TLS=true
SMTP_USER=alerts@example.com
SMTP_PASSWORD=your-password
ALERT_EMAIL_FROM=alerts@example.com
ALERT_EMAIL_TO=admin@example.com

# 钉钉机器人
DINGTALK_WEBHOOK_URL=https://oapi.dingtalk.com/robot/send?access_token=xxx

# 企业微信机器人
WECOM_WEBHOOK_URL=https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=xxx

# 恢复服务配置
STUCK_JOB_THRESHOLD_MINUTES=30

# 断路器配置
CIRCUIT_BREAKER_FAILURE_THRESHOLD=5
CIRCUIT_BREAKER_TIMEOUT=60
```

### B. 数据库迁移

```python
# alembic/versions/xxx_add_metrics_tables.py
def upgrade():
    # 创建指标时序表
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
    
    # 创建告警规则表
    op.create_table(
        'alert_rules',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('rule_name', sa.String(100), nullable=False),
        sa.Column('metric_name', sa.String(100), nullable=False),
        sa.Column('condition', sa.String(10), nullable=False),
        sa.Column('threshold', sa.Float(), nullable=False),
        sa.Column('duration_seconds', sa.Integer(), nullable=False),
        sa.Column('channels', sa.JSON(), nullable=False),
        sa.Column('enabled', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    
    # 创建告警历史表
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
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['rule_id'], ['alert_rules.id'])
    )
    
    # 创建 API Key 表
    op.create_table(
        'api_keys',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('key_hash', sa.String(64), nullable=False),
        sa.Column('is_active', sa.Boolean(), default=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('last_used_at', sa.DateTime(), nullable=True),
        sa.Column('created_by', sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )

def downgrade():
    op.drop_table('api_keys')
    op.drop_table('alert_history')
    op.drop_table('alert_rules')
    op.drop_index('idx_metric_time', 'metrics_timeseries')
    op.drop_table('metrics_timeseries')
```

### C. 依赖包更新

```txt
# requirements.txt 新增
# 已有依赖省略...

# 安全
cryptography==43.0.0
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# 速率限制
slowapi==0.1.9

# 系统监控
psutil==5.9.8

# HTTP 客户端（告警通知）
aiohttp==3.9.5
```

### D. 部署检查清单

部署前检查：
- ✅ 环境变量已配置
- ✅ 数据库迁移已执行
- ✅ 加密密钥已生成
- ✅ 告警通道已测试
- ✅ 浏览器驱动已安装

部署后验证：
- ✅ 健康检查端点正常
- ✅ 监控指标正常收集
- ✅ 任务执行成功
- ✅ 告警通知正常
- ✅ WebSocket 连接正常

---

## 总结

本设计方案通过四个维度的系统性增强，将浏览器自动化平台从当前的 7-7.5 分提升至 9 分（生产就绪级别）：

1. **监控告警系统** - 实现全面的可观测性，支持主动异常感知
2. **安全加固** - 达到企业级安全标准，保护敏感数据和系统访问
3. **性能优化** - 吞吐量提升 5 倍，资源利用率显著提升
4. **稳定性提升** - 任务失败率降至 1% 以下，系统可用性达到 99%+

**核心优势**：
- 渐进式增强，最小化外部依赖
- 易于维护和扩展
- 快速落地（2-3 周）
- 低运维成本

**预期效果**：
- 系统成熟度达到生产级别
- 支持中小规模生产环境（每天数千至上万任务）
- 为未来横向扩展奠定基础
