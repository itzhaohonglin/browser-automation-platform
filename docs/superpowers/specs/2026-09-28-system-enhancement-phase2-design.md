# 浏览器自动化平台系统增强设计文档（第二阶段）

**文档版本**: V1.0  
**创建日期**: 2026-09-28  
**设计目标**: 将系统评分从7.5分提升到8.5分  
**实施方式**: 分阶段实施（A方案）

---

## 一、改进背景

### 1.1 当前系统评估

**优势：**
- ✅ 架构设计扎实（8/10）：配置驱动、异步架构、分层清晰
- ✅ 核心功能完整（7.5/10）：登录态管理、任务调度、WebSocket实时推送、告警系统
- ✅ 代码质量中等偏上（7/10）：错误处理完善、日志规范、资源清理正确

**不足：**
- ❌ 测试覆盖不足（-1.5分）：根目录47个临时测试脚本，测试流程不规范
- ❌ 技术债务明显（-0.5分）：大量未跟踪文件，代码库管理混乱
- ❌ 生产就绪度一般（-0.5分）：串行执行、硬编码配置、缺少性能优化

### 1.2 改进目标

按优先级顺序进行5项改进：

1. **代码库清理** - 删除47个临时脚本，规范项目结构
2. **测试规范化** - 关键路径覆盖（50%），建立测试数据工厂
3. **配置灵活化** - 将硬编码参数（超时时间、过滤规则）移到数据库配置
4. **并发能力** - 多进程池方案，支持2-5个并发任务
5. **监控增强** - 基础性能指标（CPU/内存/浏览器资源/任务队列）

---

## 二、总体架构设计

### 2.1 架构演进

**当前架构：**
```
FastAPI (主进程)
  ├── WebSocket Manager (实时推送)
  ├── Task Scheduler (调度器)
  └── Playwright Executor (串行执行)
```

**改进后架构：**
```
FastAPI (主进程)
  ├── WebSocket Manager (实时推送)
  ├── Task Scheduler (增强调度器)
  ├── Process Pool Manager (新增 - 进程池管理)
  │   ├── Worker Process 1 (Playwright Executor)
  │   ├── Worker Process 2 (Playwright Executor)
  │   └── Worker Process N (可配置 1-10)
  ├── System Monitor (新增 - 系统资源监控)
  └── Config Manager (增强 - 动态配置加载)
```

### 2.2 核心改进点

| 改进项 | 方案 | 预期效果 |
|--------|------|----------|
| 代码清理 | 删除根目录47个 `*.py` 临时脚本 | 项目结构清爽，易维护 |
| 配置灵活化 | 数据库新增 `timeout_config`, `extraction_config` 字段 | 无需改代码调整参数 |
| 并发执行 | `ProcessPoolExecutor` 多进程池 | 吞吐量提升2-3倍 |
| 监控增强 | 集成 `psutil` 监控系统资源 | 实时掌握系统健康状态 |
| 测试补充 | 关键路径测试用例 | 核心功能回归测试 |

---

## 三、数据模型设计

### 3.1 增强 CrawlerConfig 模型

```python
# app/models/config.py 新增字段

class CrawlerConfig(Base):
    # ... 现有字段 ...
    
    # 超时配置（新增）
    timeout_config: Mapped[Optional[dict]] = mapped_column(
        JSON, 
        nullable=True,
        comment="超时配置 {page_load: 30000, wait_selector: 15000, ...}"
    )
    
    # 提取规则配置（新增）
    extraction_config: Mapped[Optional[dict]] = mapped_column(
        JSON,
        nullable=True, 
        comment="提取规则 {filters: [...], wait_times: {...}, retry: {...}}"
    )
    
    # 优先级（新增）
    priority: Mapped[int] = mapped_column(
        Integer,
        default=5,
        nullable=False,
        comment="任务优先级 1-10，数字越大优先级越高"
    )
```

### 3.2 timeout_config 结构

```json
{
  "page_load": 30000,           // 页面加载超时（毫秒）
  "wait_selector": 15000,       // 元素等待超时
  "navigation": 30000,          // 页面跳转超时
  "click": 10000,               // 点击操作超时
  "data_stabilization": 2000    // 数据稳定等待时间（新增）
}
```

**设计说明：**
- 如果 `timeout_config` 为 `null`，使用默认值
- 支持部分覆盖：只配置需要修改的字段
- 单位统一为毫秒

### 3.3 extraction_config 结构

```json
{
  "filters": [
    {
      "type": "regex",          // 过滤器类型：regex/length/empty
      "field_index": 1,         // 字段索引（从0开始）
      "pattern": "^[A-Z0-9]{5,}",  // 正则表达式
      "action": "keep"          // 动作：keep保留 / drop丢弃
    }
  ],
  "wait_times": {
    "before_extraction": 3000,  // 提取前等待
    "after_click": 1000,        // 点击后等待
    "between_pages": 2000       // 翻页间隔
  },
  "retry": {
    "max_attempts": 2,          // 最大重试次数
    "delay_seconds": 3          // 重试延迟（秒）
  }
}
```

**过滤器类型说明：**

| type | 参数 | 说明 | 示例 |
|------|------|------|------|
| `regex` | `pattern`, `action` | 正则匹配 | 保留编码格式正确的行 |
| `length` | `min_length`, `max_length`, `action` | 长度过滤 | 丢弃空字符串 |
| `empty` | `action` | 空值过滤 | 丢弃空白行 |

### 3.4 系统配置表（新增）

```python
# app/models/system_config.py (新建)

class SystemConfig(Base):
    """系统配置表 - 存储运行时参数"""
    
    __tablename__ = "system_configs"
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    config_key: Mapped[str] = mapped_column(
        String(100), 
        unique=True, 
        nullable=False,
        comment="配置键"
    )
    config_value: Mapped[str] = mapped_column(
        String(500), 
        nullable=False,
        comment="配置值"
    )
    description: Mapped[Optional[str]] = mapped_column(
        String(200),
        comment="配置说明"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, 
        onupdate=func.now(),
        comment="更新时间"
    )
```

**预设配置项：**

| config_key | 默认值 | 说明 |
|------------|--------|------|
| `max_concurrent_workers` | `3` | 最大并发进程数 |
| `worker_memory_limit_mb` | `512` | 单进程内存限制（MB）|
| `queue_warning_threshold` | `50` | 队列积压告警阈值 |

### 3.5 性能指标扩展

**新增指标类型：**

| metric_name | 说明 | 单位 | 采集频率 |
|-------------|------|------|----------|
| `system_cpu_usage` | CPU使用率 | % | 10秒 |
| `system_memory_usage` | 内存使用量 | MB | 10秒 |
| `browser_process_count` | 浏览器进程数 | 个 | 10秒 |
| `queue_pending_count` | 待处理任务数 | 个 | 10秒 |
| `worker_idle_time` | 工作进程空闲时间 | 秒 | 事件触发 |

---

## 四、核心组件设计

### 4.1 进程池管理器（新增）

```python
# app/services/process_pool_manager.py (新建)

from concurrent.futures import ProcessPoolExecutor
import asyncio

class ProcessPoolManager:
    """管理多进程并发执行"""
    
    def __init__(self, max_workers: int = 3, ws_manager=None):
        """
        初始化进程池
        
        Args:
            max_workers: 最大工作进程数（1-10）
            ws_manager: WebSocket管理器（用于状态推送）
        """
        self.max_workers = max_workers
        self.ws_manager = ws_manager
        self.executor = ProcessPoolExecutor(max_workers=max_workers)
        self.active_jobs = {}  # {job_id: Future}
        self.logger = logging.getLogger(__name__)
        
    async def submit_job(self, job_id: int) -> asyncio.Future:
        """
        提交任务到进程池
        
        Args:
            job_id: 任务ID
            
        Returns:
            异步Future对象
        """
        if len(self.active_jobs) >= self.max_workers:
            raise RuntimeError("进程池已满，无可用槽位")
        
        loop = asyncio.get_event_loop()
        future = loop.run_in_executor(
            self.executor,
            self._execute_in_process,
            job_id
        )
        
        self.active_jobs[job_id] = future
        self.logger.info(f"任务 #{job_id} 已提交到进程池")
        
        # 任务完成后清理
        future.add_done_callback(lambda f: self.active_jobs.pop(job_id, None))
        
        return future
    
    def _execute_in_process(self, job_id: int):
        """
        在子进程中执行任务（静态方法，可序列化）
        
        注意：子进程中需要重新创建事件循环和数据库连接
        """
        # 创建新的事件循环
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            # 执行任务
            from app.services.executor import PlaywrightExecutor
            executor = PlaywrightExecutor()
            
            result = loop.run_until_complete(
                self._run_job(executor, job_id)
            )
            return result
        finally:
            loop.close()
    
    async def _run_job(self, executor, job_id: int):
        """异步执行单个任务"""
        from app.core.database import get_session
        
        async with get_session() as session:
            return await executor.execute_job(job_id, session)
    
    async def get_status(self) -> dict:
        """获取进程池状态"""
        return {
            "max_workers": self.max_workers,
            "active_jobs": len(self.active_jobs),
            "available_slots": self.max_workers - len(self.active_jobs),
            "job_ids": list(self.active_jobs.keys())
        }
    
    async def resize(self, new_max_workers: int):
        """
        动态调整进程池大小
        
        Args:
            new_max_workers: 新的最大工作进程数
        """
        if not 1 <= new_max_workers <= 10:
            raise ValueError("并发数必须在1-10之间")
        
        self.logger.info(f"调整进程池大小: {self.max_workers} -> {new_max_workers}")
        
        # 等待当前任务完成
        if self.active_jobs:
            await asyncio.gather(*self.active_jobs.values(), return_exceptions=True)
        
        # 关闭旧进程池
        self.executor.shutdown(wait=True)
        
        # 创建新进程池
        self.max_workers = new_max_workers
        self.executor = ProcessPoolExecutor(max_workers=new_max_workers)
        self.active_jobs.clear()
    
    async def shutdown(self):
        """优雅关闭进程池"""
        self.logger.info("正在关闭进程池...")
        
        # 等待所有任务完成
        if self.active_jobs:
            await asyncio.gather(*self.active_jobs.values(), return_exceptions=True)
        
        self.executor.shutdown(wait=True)
        self.logger.info("进程池已关闭")
```

**设计要点：**
- ✅ 进程隔离：每个进程独立运行浏览器，崩溃不影响其他
- ✅ 资源管理：通过 `active_jobs` 跟踪任务状态
- ✅ 动态调整：支持运行时修改并发数
- ✅ 优雅关闭：等待任务完成后再关闭

### 4.2 增强型调度器

```python
# app/services/scheduler.py 修改

class TaskScheduler:
    """任务调度器 - 负责定时补跑失败任务和分发待处理任务"""
    
    # 调度配置常量
    RETRY_INTERVAL_MINUTES = 1
    FIRST_RUN_DELAY_MINUTES = 1
    MAX_RETRY_COUNT = 3
    BATCH_SIZE = 100
    
    # 任务分发配置（新增）
    DISPATCH_INTERVAL_SECONDS = 5  # 每5秒检查一次待处理任务
    
    def __init__(self, ws_manager=None, pool_manager=None):
        """
        初始化调度器
        
        Args:
            ws_manager: WebSocket管理器
            pool_manager: 进程池管理器（新增）
        """
        self.scheduler = AsyncIOScheduler(...)
        self.ws_manager = ws_manager
        self.pool_manager = pool_manager  # 新增
        self.logger = logger
    
    async def start(self):
        """启动调度器"""
        self.logger.info("正在启动任务调度器...")
        
        # 现有任务：重试失败任务
        self.scheduler.add_job(
            func=self.retry_failed_jobs,
            trigger=IntervalTrigger(minutes=self.RETRY_INTERVAL_MINUTES),
            id='retry_failed_jobs',
            name='重试失败任务'
        )
        
        # 现有任务：评估告警规则
        self.scheduler.add_job(
            func=self.evaluate_alerts,
            trigger=IntervalTrigger(minutes=5),
            id='evaluate_alerts',
            name='评估告警规则'
        )
        
        # 新增任务：分发待处理任务
        self.scheduler.add_job(
            func=self.dispatch_pending_jobs,
            trigger=IntervalTrigger(seconds=self.DISPATCH_INTERVAL_SECONDS),
            id='dispatch_pending_jobs',
            name='分发待处理任务'
        )
        
        self.scheduler.start()
        self.logger.info("任务调度器启动成功")
    
    async def dispatch_pending_jobs(self):
        """
        调度待处理任务到进程池（新增方法）
        
        逻辑：
        1. 查询 pending 状态的任务，按优先级排序
        2. 检查进程池可用槽位
        3. 提交任务到进程池执行
        """
        try:
            # 检查可用槽位
            status = await self.pool_manager.get_status()
            available_slots = status['available_slots']
            
            if available_slots == 0:
                return  # 进程池已满，等待下次调度
            
            # 查询待处理任务
            async with get_session() as session:
                stmt = select(JobQueue).where(
                    JobQueue.status == JobStatus.PENDING
                ).order_by(
                    JobQueue.priority.desc(),   # 高优先级优先
                    JobQueue.created_at.asc()   # 同优先级按创建时间
                ).limit(available_slots)
                
                result = await session.execute(stmt)
                pending_jobs = result.scalars().all()
                
                if not pending_jobs:
                    return
                
                self.logger.info(
                    f"发现 {len(pending_jobs)} 个待处理任务，"
                    f"可用槽位 {available_slots}"
                )
                
                # 提交任务到进程池
                for job in pending_jobs:
                    try:
                        await self.pool_manager.submit_job(job.id)
                        self.logger.info(f"任务 #{job.id} 已提交到进程池")
                        
                        # 广播任务开始
                        if self.ws_manager:
                            await self.ws_manager.broadcast({
                                "type": "log",
                                "level": "info",
                                "msg": f"任务 #{job.id} 开始执行"
                            })
                    
                    except Exception as e:
                        self.logger.error(f"提交任务 #{job.id} 失败: {e}")
        
        except Exception as e:
            self.logger.error(f"分发任务时出错: {e}", exc_info=True)
    
    # ... 保留现有的 retry_failed_jobs() 和 evaluate_alerts() 方法 ...
```

**调度策略：**
- 每5秒检查一次待处理任务
- 按优先级（priority字段）排序
- 只提交与可用槽位数相等的任务
- 避免过度提交导致任务堆积

### 4.3 系统资源监控器（新增）

```python
# app/services/system_monitor.py (新建)

import psutil
import logging
from typing import Dict
from datetime import datetime
from sqlalchemy import select, func

from app.core.database import get_session
from app.models.job import JobQueue, JobStatus

logger = logging.getLogger(__name__)

class SystemMonitor:
    """系统资源监控器"""
    
    def __init__(self):
        """初始化监控器"""
        self.process = psutil.Process()
        self.logger = logger
    
    async def collect_metrics(self) -> Dict:
        """
        收集系统指标
        
        Returns:
            指标字典
        """
        try:
            # CPU 使用率（1秒采样）
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用（主进程）
            memory_info = self.process.memory_info()
            memory_mb = memory_info.rss / 1024 / 1024
            
            # 浏览器进程数（查找 chromium 进程）
            browser_count = 0
            for proc in psutil.process_iter(['name']):
                try:
                    if 'chromium' in proc.info['name'].lower():
                        browser_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
            # 任务队列统计
            async with get_session() as session:
                pending_count = await session.scalar(
                    select(func.count()).where(
                        JobQueue.status == JobStatus.PENDING
                    )
                )
                
                processing_count = await session.scalar(
                    select(func.count()).where(
                        JobQueue.status == JobStatus.PROCESSING
                    )
                )
            
            return {
                "cpu_percent": cpu_percent,
                "memory_mb": memory_mb,
                "browser_processes": browser_count,
                "queue_pending": pending_count,
                "queue_processing": processing_count,
                "timestamp": datetime.now().isoformat()
            }
        
        except Exception as e:
            self.logger.error(f"收集指标失败: {e}", exc_info=True)
            return {}
    
    async def record_metrics(self):
        """
        记录指标到数据库
        
        定时任务调用此方法，将指标持久化
        """
        metrics = await self.collect_metrics()
        
        if not metrics:
            return
        
        from app.services.metrics_collector import metrics_collector
        
        try:
            await metrics_collector.record(
                "system_cpu_usage", 
                metrics['cpu_percent']
            )
            await metrics_collector.record(
                "system_memory_usage", 
                metrics['memory_mb']
            )
            await metrics_collector.record(
                "browser_process_count", 
                metrics['browser_processes']
            )
            await metrics_collector.record(
                "queue_pending_count", 
                metrics['queue_pending']
            )
            
            self.logger.debug(f"系统指标已记录: CPU={metrics['cpu_percent']:.1f}%, "
                            f"内存={metrics['memory_mb']:.0f}MB")
        
        except Exception as e:
            self.logger.error(f"记录指标失败: {e}", exc_info=True)
    
    async def check_health(self) -> Dict:
        """
        健康检查
        
        Returns:
            健康状态字典
        """
        metrics = await self.collect_metrics()
        
        warnings = []
        
        # CPU使用率告警（>80%）
        if metrics.get('cpu_percent', 0) > 80:
            warnings.append(f"CPU使用率过高: {metrics['cpu_percent']:.1f}%")
        
        # 内存使用告警（>1GB）
        if metrics.get('memory_mb', 0) > 1024:
            warnings.append(f"内存占用过高: {metrics['memory_mb']:.0f}MB")
        
        # 浏览器进程泄漏告警（>10个）
        if metrics.get('browser_processes', 0) > 10:
            warnings.append(f"浏览器进程过多: {metrics['browser_processes']}个")
        
        # 任务队列积压告警（>50个）
        if metrics.get('queue_pending', 0) > 50:
            warnings.append(f"任务队列积压: {metrics['queue_pending']}个")
        
        return {
            "status": "healthy" if not warnings else "warning",
            "warnings": warnings,
            "metrics": metrics
        }

# 全局单例
system_monitor = SystemMonitor()
```

**监控指标说明：**

| 指标 | 正常范围 | 告警阈值 | 处理建议 |
|------|----------|----------|----------|
| CPU使用率 | 0-60% | >80% | 降低并发数或优化代码 |
| 内存占用 | <500MB | >1GB | 检查内存泄漏 |
| 浏览器进程数 | ≤并发数 | >10 | 检查进程清理逻辑 |
| 队列积压 | <20 | >50 | 增加并发数或优化执行速度 |

---

## 五、执行器改造

### 5.1 动态配置加载

```python
# app/services/executor.py 新增方法

class PlaywrightExecutor:
    
    def _load_timeouts(self, config: CrawlerConfig) -> dict:
        """
        加载超时配置（支持自定义覆盖）
        
        Args:
            config: 配置对象
            
        Returns:
            超时配置字典（毫秒）
        """
        # 默认超时配置
        default_timeouts = {
            "page_load": 30000,
            "wait_selector": 15000,
            "navigation": 30000,
            "click": 10000,
            "data_stabilization": 2000
        }
        
        # 合并自定义配置（部分覆盖）
        if config.timeout_config:
            default_timeouts.update(config.timeout_config)
        
        self.logger.info(f"加载超时配置: {default_timeouts}")
        return default_timeouts
    
    def _load_extraction_config(self, config: CrawlerConfig) -> dict:
        """
        加载提取配置
        
        Args:
            config: 配置对象
            
        Returns:
            提取配置字典
        """
        default_config = {
            "filters": [],
            "wait_times": {
                "before_extraction": 3000,
                "after_click": 1000,
                "between_pages": 2000
            },
            "retry": {
                "max_attempts": 2,
                "delay_seconds": 3
            }
        }
        
        if config.extraction_config:
            # 深度合并配置
            if 'filters' in config.extraction_config:
                default_config['filters'] = config.extraction_config['filters']
            if 'wait_times' in config.extraction_config:
                default_config['wait_times'].update(
                    config.extraction_config['wait_times']
                )
            if 'retry' in config.extraction_config:
                default_config['retry'].update(
                    config.extraction_config['retry']
                )
        
        self.logger.info(f"加载提取配置: 过滤器数量={len(default_config['filters'])}")
        return default_config
```

### 5.2 智能过滤器实现

```python
# app/services/executor.py 新增方法

def _apply_filters(self, data: List[Dict], filters: List[Dict]) -> List[Dict]:
    """
    应用数据过滤规则
    
    Args:
        data: 原始数据列表
        filters: 过滤规则列表
        
    Returns:
        过滤后的数据列表
    """
    if not filters:
        return data
    
    filtered = []
    
    for row_idx, row in enumerate(data):
        keep = True
        
        for filter_rule in filters:
            filter_type = filter_rule.get('type')
            field_index = filter_rule.get('field_index', 0)
            action = filter_rule.get('action', 'keep')
            
            # 获取字段值
            values = list(row.values())
            if field_index >= len(values):
                self.logger.warning(
                    f"行 {row_idx}: 字段索引 {field_index} 超出范围"
                )
                continue
            
            field_value = values[field_index]
            
            # 应用过滤逻辑
            if filter_type == 'regex':
                import re
                pattern = filter_rule.get('pattern', '')
                matches = bool(re.match(pattern, field_value))
                
                if action == 'keep' and not matches:
                    keep = False
                    break
                elif action == 'drop' and matches:
                    keep = False
                    break
            
            elif filter_type == 'length':
                min_len = filter_rule.get('min_length', 0)
                max_len = filter_rule.get('max_length', 999999)
                length = len(field_value)
                
                if not (min_len <= length <= max_len):
                    keep = False
                    break
            
            elif filter_type == 'empty':
                is_empty = not field_value.strip()
                
                if action == 'drop' and is_empty:
                    keep = False
                    break
                elif action == 'keep' and not is_empty:
                    keep = False
                    break
        
        if keep:
            filtered.append(row)
    
    self.logger.info(
        f"过滤完成: 原始数据 {len(data)} 条 -> 过滤后 {len(filtered)} 条"
    )
    return filtered
```

### 5.3 重试机制改进

```python
# app/services/executor.py 修改数据提取逻辑

async def _extract_with_retry(
    self,
    target_frame,
    fields_mapping: dict,
    retry_config: dict
) -> List[Dict]:
    """
    带重试的数据提取
    
    Args:
        target_frame: 页面或Frame对象
        fields_mapping: 字段映射规则
        retry_config: 重试配置
        
    Returns:
        提取的数据列表
    """
    max_attempts = retry_config.get('max_attempts', 2)
    delay = retry_config.get('delay_seconds', 3)
    
    for attempt in range(max_attempts):
        try:
            self.logger.info(f"=== 第 {attempt + 1} 次提取尝试 ===")
            
            # 提取数据
            data = await self._extract_page_data(target_frame, fields_mapping)
            
            if len(data) > 0:
                self.logger.info(
                    f"第 {attempt + 1} 次提取成功，获得 {len(data)} 条数据"
                )
                return data
            
            # 无数据时重试
            if attempt < max_attempts - 1:
                self.logger.warning(
                    f"第 {attempt + 1} 次提取无数据，{delay}秒后重试..."
                )
                await asyncio.sleep(delay)
        
        except Exception as e:
            self.logger.error(f"第 {attempt + 1} 次提取失败: {e}")
            if attempt < max_attempts - 1:
                await asyncio.sleep(delay)
            else:
                raise
    
    return []
```

### 5.4 execute_job 方法改造

```python
# app/services/executor.py 修改核心方法

async def execute_job(self, job_id: int, session: AsyncSession) -> Dict:
    """执行单个任务（使用动态配置）"""
    
    # ... 前置代码保持不变 ...
    
    # 加载配置
    timeouts = self._load_timeouts(config)
    extraction_cfg = self._load_extraction_config(config)
    
    # 使用动态超时配置
    await page.goto(
        config.target_url,
        timeout=timeouts['page_load'],  # 动态配置
        wait_until='networkidle'
    )
    
    # 数据稳定等待
    await asyncio.sleep(timeouts['data_stabilization'] / 1000)
    
    # ... iframe处理逻辑 ...
    
    # 使用配置化等待时间
    wait_times = extraction_cfg['wait_times']
    await asyncio.sleep(wait_times['before_extraction'] / 1000)
    
    # 使用重试机制提取数据
    raw_data = await self._extract_with_retry(
        target_frame,
        config.fields_mapping,
        extraction_cfg['retry']
    )
    
    # 应用过滤器
    filtered_data = self._apply_filters(raw_data, extraction_cfg['filters'])
    
    # ... 后续保存逻辑保持不变 ...
```

---

## 六、API接口设计

### 6.1 系统配置API

```python
# app/api/system_config.py (新建)

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_session
from app.models.system_config import SystemConfig

router = APIRouter(prefix="/api/system", tags=["系统配置"])

@router.get("/config")
async def get_system_configs(session: AsyncSession = Depends(get_session)):
    """获取所有系统配置"""
    stmt = select(SystemConfig)
    result = await session.execute(stmt)
    configs = result.scalars().all()
    
    return {
        "configs": [
            {
                "key": c.config_key,
                "value": c.config_value,
                "description": c.description,
                "updated_at": c.updated_at.isoformat() if c.updated_at else None
            }
            for c in configs
        ]
    }

@router.get("/config/{key}")
async def get_system_config(
    key: str,
    session: AsyncSession = Depends(get_session)
):
    """获取单个系统配置"""
    stmt = select(SystemConfig).where(SystemConfig.config_key == key)
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="配置项不存在")
    
    return {
        "key": config.config_key,
        "value": config.config_value,
        "description": config.description
    }

@router.put("/config/{key}")
async def update_system_config(
    key: str,
    value: str,
    session: AsyncSession = Depends(get_session)
):
    """
    动态更新系统配置
    
    支持热更新的配置项：
    - max_concurrent_workers: 触发进程池重新初始化
    """
    stmt = select(SystemConfig).where(SystemConfig.config_key == key)
    result = await session.execute(stmt)
    config = result.scalar_one_or_none()
    
    if not config:
        raise HTTPException(status_code=404, detail="配置项不存在")
    
    old_value = config.config_value
    config.config_value = value
    await session.commit()
    
    # 热更新：如果是并发数配置，通知进程池管理器
    if key == "max_concurrent_workers":
        from app.main import pool_manager
        try:
            await pool_manager.resize(int(value))
        except Exception as e:
            # 回滚数据库
            config.config_value = old_value
            await session.commit()
            raise HTTPException(
                status_code=500,
                detail=f"进程池调整失败: {str(e)}"
            )
    
    return {
        "message": "配置更新成功",
        "key": key,
        "old_value": old_value,
        "new_value": value
    }

@router.get("/metrics/realtime")
async def get_realtime_metrics():
    """获取实时系统指标"""
    from app.services.system_monitor import system_monitor
    
    metrics = await system_monitor.collect_metrics()
    return metrics

@router.get("/health/check")
async def health_check():
    """系统健康检查"""
    from app.services.system_monitor import system_monitor
    
    health = await system_monitor.check_health()
    return health
```

### 6.2 进程池管理API

```python
# app/api/endpoints.py 新增

@router.get("/pool/status")
async def get_pool_status():
    """获取进程池状态"""
    from app.main import pool_manager
    
    status = await pool_manager.get_status()
    return {
        "max_workers": status['max_workers'],
        "active_jobs": status['active_jobs'],
        "available_slots": status['available_slots'],
        "job_ids": status['job_ids']
    }

@router.post("/pool/resize")
async def resize_pool(max_workers: int):
    """
    动态调整进程池大小
    
    Args:
        max_workers: 新的最大工作进程数（1-10）
    """
    if not 1 <= max_workers <= 10:
        raise HTTPException(
            status_code=400,
            detail="并发数必须在1-10之间"
        )
    
    from app.main import pool_manager
    
    try:
        await pool_manager.resize(max_workers)
        return {
            "message": f"进程池已调整为 {max_workers} 个工作进程",
            "max_workers": max_workers
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"调整进程池失败: {str(e)}"
        )
```

---

## 七、测试策略

### 7.1 测试范围（关键路径覆盖）

**测试目标：50%覆盖率，重点测试核心业务流程**

| 测试类别 | 测试用例 | 优先级 |
|----------|----------|--------|
| 任务执行 | 成功执行、失败重试、超时处理 | P0 |
| 并发执行 | 多任务并发、进程池状态 | P0 |
| 配置加载 | 超时配置、过滤规则 | P1 |
| 数据过滤 | 正则过滤、长度过滤、空值过滤 | P1 |
| 系统监控 | 指标收集、健康检查 | P2 |

### 7.2 核心测试用例

```python
# tests/test_core_flow.py (新建)

import pytest
import asyncio
from app.services.executor import PlaywrightExecutor
from app.models.job import JobQueue, JobStatus

@pytest.mark.asyncio
async def test_job_execution_success(test_session, sample_config, sample_job):
    """测试任务执行成功流程"""
    executor = PlaywrightExecutor()
    
    # 执行任务
    result = await executor.execute_job(sample_job.id, test_session)
    
    # 验证结果
    assert result['status'] == 'success'
    assert result['extracted_count'] > 0
    assert 'execution_time' in result
    
    # 验证数据库状态
    await test_session.refresh(sample_job)
    assert sample_job.status == JobStatus.SUCCESS

@pytest.mark.asyncio
async def test_job_execution_retry(test_session, failing_job):
    """测试失败重试机制"""
    executor = PlaywrightExecutor()
    
    result = await executor.execute_job(failing_job.id, test_session)
    
    # 验证失败标记
    assert result['status'] == 'failed'
    assert 'error' in result
    
    # 验证重试计数
    await test_session.refresh(failing_job)
    assert failing_job.status == JobStatus.FAILED
    assert failing_job.retry_count == 1

@pytest.mark.asyncio
async def test_concurrent_execution(test_session, multiple_jobs):
    """测试并发执行"""
    from app.services.process_pool_manager import ProcessPoolManager
    
    pool = ProcessPoolManager(max_workers=2)
    
    # 提交多个任务
    futures = []
    for job in multiple_jobs[:3]:
        future = await pool.submit_job(job.id)
        futures.append(future)
    
    # 等待完成
    results = await asyncio.gather(*futures, return_exceptions=True)
    
    # 验证至少有2个任务成功
    success_count = sum(
        1 for r in results 
        if isinstance(r, dict) and r.get('status') == 'success'
    )
    assert success_count >= 2
    
    # 清理进程池
    await pool.shutdown()

@pytest.mark.asyncio
async def test_config_flexibility(test_session, custom_timeout_config):
    """测试配置灵活性"""
    executor = PlaywrightExecutor()
    
    # 加载自定义超时配置
    timeouts = executor._load_timeouts(custom_timeout_config)
    
    # 验证自定义值生效
    assert timeouts['page_load'] == 60000  # 自定义值
    assert timeouts['click'] == 10000      # 默认值（未覆盖）

@pytest.mark.asyncio
async def test_data_filtering():
    """测试数据过滤"""
    executor = PlaywrightExecutor()
    
    raw_data = [
        {"code": "ABC12345", "name": "测试"},
        {"code": "invalid", "name": "无效"},
        {"code": "XYZ67890", "name": "正常"},
        {"code": "", "name": "空编码"}
    ]
    
    # 正则过滤器：保留编码格式正确的行
    filters = [{
        "type": "regex",
        "field_index": 0,
        "pattern": "^[A-Z0-9]{5,}",
        "action": "keep"
    }]
    
    filtered = executor._apply_filters(raw_data, filters)
    
    assert len(filtered) == 2
    assert filtered[0]['code'] == "ABC12345"
    assert filtered[1]['code'] == "XYZ67890"

@pytest.mark.asyncio
async def test_system_monitoring():
    """测试系统监控"""
    from app.services.system_monitor import SystemMonitor
    
    monitor = SystemMonitor()
    metrics = await monitor.collect_metrics()
    
    # 验证指标完整性
    assert 'cpu_percent' in metrics
    assert 'memory_mb' in metrics
    assert 'browser_processes' in metrics
    assert 'queue_pending' in metrics
    
    # 验证数据有效性
    assert metrics['cpu_percent'] >= 0
    assert metrics['memory_mb'] > 0

@pytest.mark.asyncio
async def test_pool_status():
    """测试进程池状态"""
    from app.services.process_pool_manager import ProcessPoolManager
    
    pool = ProcessPoolManager(max_workers=3)
    status = await pool.get_status()
    
    assert status['max_workers'] == 3
    assert status['active_jobs'] == 0
    assert status['available_slots'] == 3
    
    await pool.shutdown()
```

### 7.3 测试数据工厂

```python
# tests/conftest.py 补充

import pytest
from app.models.config import CrawlerConfig
from app.models.job import JobQueue, JobStatus

@pytest.fixture
async def sample_config(test_session):
    """示例配置（基本配置）"""
    config = CrawlerConfig(
        config_name="测试配置",
        target_url="https://example.com",
        need_login=False,
        input_configs={"inputs": []},
        submit_selector=".submit",
        wait_selector=".result",
        fields_mapping={"title": ".title text"},
        priority=5
    )
    test_session.add(config)
    await test_session.commit()
    await test_session.refresh(config)
    return config

@pytest.fixture
async def custom_timeout_config(test_session):
    """自定义超时配置"""
    config = CrawlerConfig(
        config_name="自定义超时配置",
        target_url="https://example.com",
        need_login=False,
        input_configs={"inputs": []},
        submit_selector=".submit",
        wait_selector=".result",
        fields_mapping={"title": ".title text"},
        timeout_config={
            "page_load": 60000,  # 自定义60秒
            "data_stabilization": 5000  # 自定义5秒
        },
        extraction_config={
            "filters": [
                {
                    "type": "regex",
                    "field_index": 0,
                    "pattern": "^TEST",
                    "action": "keep"
                }
            ]
        }
    )
    test_session.add(config)
    await test_session.commit()
    await test_session.refresh(config)
    return config

@pytest.fixture
async def sample_job(test_session, sample_config):
    """示例任务"""
    job = JobQueue(
        config_id=sample_config.id,
        query_params={"keyword": "test"},
        status=JobStatus.PENDING,
        priority=5
    )
    test_session.add(job)
    await test_session.commit()
    await test_session.refresh(job)
    return job

@pytest.fixture
async def failing_job(test_session, sample_config):
    """会失败的任务（用于测试重试）"""
    job = JobQueue(
        config_id=sample_config.id,
        query_params={"invalid": "params"},  # 无效参数
        status=JobStatus.PENDING,
        retry_count=0
    )
    test_session.add(job)
    await test_session.commit()
    await test_session.refresh(job)
    return job

@pytest.fixture
async def multiple_jobs(test_session, sample_config):
    """多个任务（用于并发测试）"""
    jobs = []
    for i in range(5):
        job = JobQueue(
            config_id=sample_config.id,
            query_params={"keyword": f"test{i}"},
            status=JobStatus.PENDING,
            priority=5 - i  # 不同优先级
        )
        test_session.add(job)
        jobs.append(job)
    
    await test_session.commit()
    for job in jobs:
        await test_session.refresh(job)
    return jobs
```

---

## 八、前端看板集成

### 8.1 新增功能模块

**系统监控面板：**
- CPU使用率实时曲线图
- 内存占用趋势图
- 浏览器进程数统计
- 任务队列积压情况

**进程池控制面板：**
- 当前进程池状态（最大进程数/活跃任务数/可用槽位）
- 动态调整并发数滑块（1-10）
- 进程池重启按钮

### 8.2 WebSocket消息扩展

```javascript
// static/app.js 新增部分

// 系统监控面板类
class SystemMetricsPanel {
    constructor() {
        this.cpuChart = null;
        this.memoryChart = null;
        this.maxDataPoints = 20;  // 保留最近20个数据点
        this.initCharts();
    }
    
    initCharts() {
        // CPU使用率图表
        const cpuCtx = document.getElementById('cpuChart').getContext('2d');
        this.cpuChart = new Chart(cpuCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: 'CPU使用率 (%)',
                    data: [],
                    borderColor: 'rgb(75, 192, 192)',
                    backgroundColor: 'rgba(75, 192, 192, 0.2)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: { 
                        beginAtZero: true, 
                        max: 100,
                        ticks: {
                            callback: function(value) {
                                return value + '%';
                            }
                        }
                    }
                },
                plugins: {
                    legend: { display: true },
                    tooltip: { mode: 'index', intersect: false }
                }
            }
        });
        
        // 内存使用图表
        const memCtx = document.getElementById('memoryChart').getContext('2d');
        this.memoryChart = new Chart(memCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [{
                    label: '内存占用 (MB)',
                    data: [],
                    borderColor: 'rgb(255, 99, 132)',
                    backgroundColor: 'rgba(255, 99, 132, 0.2)',
                    tension: 0.4,
                    fill: true
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: { 
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return value + ' MB';
                            }
                        }
                    }
                },
                plugins: {
                    legend: { display: true },
                    tooltip: { mode: 'index', intersect: false }
                }
            }
        });
    }
    
    updateMetrics(metrics) {
        const now = new Date().toLocaleTimeString();
        
        // 更新CPU图表
        this.cpuChart.data.labels.push(now);
        this.cpuChart.data.datasets[0].data.push(metrics.cpu_percent);
        
        // 保持最近N个数据点
        if (this.cpuChart.data.labels.length > this.maxDataPoints) {
            this.cpuChart.data.labels.shift();
            this.cpuChart.data.datasets[0].data.shift();
        }
        
        this.cpuChart.update('none');  // 无动画更新，性能更好
        
        // 更新内存图表
        this.memoryChart.data.labels.push(now);
        this.memoryChart.data.datasets[0].data.push(metrics.memory_mb);
        
        if (this.memoryChart.data.labels.length > this.maxDataPoints) {
            this.memoryChart.data.labels.shift();
            this.memoryChart.data.datasets[0].data.shift();
        }
        
        this.memoryChart.update('none');
        
        // 更新统计卡片
        document.getElementById('cpu-usage').textContent = 
            `${metrics.cpu_percent.toFixed(1)}%`;
        document.getElementById('memory-usage').textContent = 
            `${metrics.memory_mb.toFixed(0)} MB`;
        document.getElementById('browser-count').textContent = 
            metrics.browser_processes;
        document.getElementById('queue-pending').textContent = 
            metrics.queue_pending;
        
        // 高亮告警状态
        this.updateWarningState(metrics);
    }
    
    updateWarningState(metrics) {
        const cpuCard = document.getElementById('cpu-card');
        const memoryCard = document.getElementById('memory-card');
        const queueCard = document.getElementById('queue-card');
        
        // CPU告警（>80%）
        if (metrics.cpu_percent > 80) {
            cpuCard.classList.add('warning');
        } else {
            cpuCard.classList.remove('warning');
        }
        
        // 内存告警（>1GB）
        if (metrics.memory_mb > 1024) {
            memoryCard.classList.add('warning');
        } else {
            memoryCard.classList.remove('warning');
        }
        
        // 队列告警（>50）
        if (metrics.queue_pending > 50) {
            queueCard.classList.add('warning');
        } else {
            queueCard.classList.remove('warning');
        }
    }
}

// WebSocket消息处理增强
function handleWebSocketMessage(data) {
    const messageType = data.type;
    
    if (messageType === 'metrics') {
        // 新增：系统指标推送
        metricsPanel.updateMetrics(data.data);
    } else if (messageType === 'progress') {
        updateJobProgress(data.data);
    } else if (messageType === 'log') {
        appendLog(data.level, data.msg);
    } else if (messageType === 'alert') {
        handleAlert(data.data);
    }
}

// 进程池状态监控
async function loadPoolStatus() {
    try {
        const response = await fetch('/api/pool/status');
        const status = await response.json();
        
        document.getElementById('pool-max-workers').textContent = 
            status.max_workers;
        document.getElementById('pool-active').textContent = 
            status.active_jobs;
        document.getElementById('pool-available').textContent = 
            status.available_slots;
        
        // 更新活跃任务列表
        const jobList = document.getElementById('active-jobs-list');
        jobList.innerHTML = status.job_ids
            .map(id => `<li>任务 #${id}</li>`)
            .join('');
    } catch (error) {
        console.error('加载进程池状态失败:', error);
    }
}

// 动态调整并发数
async function adjustConcurrency(newValue) {
    try {
        const response = await fetch('/api/pool/resize', {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify({max_workers: parseInt(newValue)})
        });
        
        if (response.ok) {
            const result = await response.json();
            showNotification(result.message, 'success');
            loadPoolStatus();
        } else {
            const error = await response.json();
            showNotification(error.detail, 'error');
        }
    } catch (error) {
        showNotification('调整并发数失败', 'error');
        console.error(error);
    }
}

// 初始化
document.addEventListener('DOMContentLoaded', function() {
    // 初始化监控面板
    window.metricsPanel = new SystemMetricsPanel();
    
    // 加载进程池状态
    loadPoolStatus();
    
    // 定时刷新进程池状态（每10秒）
    setInterval(loadPoolStatus, 10000);
    
    // 并发数滑块事件
    const slider = document.getElementById('concurrency-slider');
    const valueDisplay = document.getElementById('concurrency-value');
    
    slider.addEventListener('input', function() {
        valueDisplay.textContent = this.value;
    });
    
    slider.addEventListener('change', function() {
        adjustConcurrency(this.value);
    });
});
```

### 8.3 HTML界面增强

```html
<!-- static/index.html 新增部分 -->

<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>浏览器自动化平台 - 监控看板</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js"></script>
    <link rel="stylesheet" href="/static/style.css">
</head>
<body>
    <div class="container">
        <h1>浏览器自动化平台监控看板</h1>
        
        <!-- 系统监控面板 -->
        <section class="metrics-panel">
            <h2>系统监控</h2>
            <div class="metrics-grid">
                <div class="metric-card" id="cpu-card">
                    <label>CPU使用率</label>
                    <span class="metric-value" id="cpu-usage">0%</span>
                </div>
                <div class="metric-card" id="memory-card">
                    <label>内存占用</label>
                    <span class="metric-value" id="memory-usage">0 MB</span>
                </div>
                <div class="metric-card">
                    <label>浏览器进程</label>
                    <span class="metric-value" id="browser-count">0</span>
                </div>
                <div class="metric-card" id="queue-card">
                    <label>队列积压</label>
                    <span class="metric-value" id="queue-pending">0</span>
                </div>
            </div>
            
            <!-- 图表区域 -->
            <div class="charts-container">
                <div class="chart-wrapper">
                    <h3>CPU使用率趋势</h3>
                    <canvas id="cpuChart"></canvas>
                </div>
                <div class="chart-wrapper">
                    <h3>内存占用趋势</h3>
                    <canvas id="memoryChart"></canvas>
                </div>
            </div>
        </section>
        
        <!-- 进程池控制面板 -->
        <section class="pool-control">
            <h2>并发控制</h2>
            <div class="pool-status">
                <div class="status-item">
                    <label>最大进程数:</label>
                    <span id="pool-max-workers">3</span>
                </div>
                <div class="status-item">
                    <label>活跃任务:</label>
                    <span id="pool-active">0</span>
                </div>
                <div class="status-item">
                    <label>可用槽位:</label>
                    <span id="pool-available">3</span>
                </div>
            </div>
            
            <div class="pool-adjust">
                <label for="concurrency-slider">调整并发数:</label>
                <input type="range" 
                       id="concurrency-slider" 
                       min="1" 
                       max="10" 
                       value="3" 
                       step="1">
                <span id="concurrency-value">3</span>
            </div>
            
            <div class="active-jobs">
                <h3>活跃任务列表</h3>
                <ul id="active-jobs-list">
                    <li>暂无活跃任务</li>
                </ul>
            </div>
        </section>
        
        <!-- 原有的任务监控面板保持不变 -->
        <!-- ... -->
    </div>
    
    <script src="/static/app.js"></script>
</body>
</html>
```

### 8.4 样式补充

```css
/* static/style.css 新增部分 */

.metrics-panel {
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
    gap: 15px;
    margin-bottom: 30px;
}

.metric-card {
    background: #f8f9fa;
    padding: 20px;
    border-radius: 6px;
    text-align: center;
    transition: all 0.3s ease;
}

.metric-card label {
    display: block;
    font-size: 14px;
    color: #666;
    margin-bottom: 10px;
}

.metric-card .metric-value {
    display: block;
    font-size: 28px;
    font-weight: bold;
    color: #333;
}

.metric-card.warning {
    background: #fff3cd;
    border: 2px solid #ffc107;
    animation: pulse 2s infinite;
}

@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.8; }
}

.charts-container {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
    gap: 20px;
}

.chart-wrapper {
    background: #f8f9fa;
    padding: 15px;
    border-radius: 6px;
}

.chart-wrapper h3 {
    font-size: 16px;
    margin-bottom: 15px;
    color: #333;
}

.pool-control {
    background: #fff;
    border-radius: 8px;
    padding: 20px;
    margin-bottom: 20px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

.pool-status {
    display: flex;
    justify-content: space-around;
    margin-bottom: 20px;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 6px;
}

.status-item {
    text-align: center;
}

.status-item label {
    display: block;
    font-size: 14px;
    color: #666;
    margin-bottom: 5px;
}

.status-item span {
    display: block;
    font-size: 24px;
    font-weight: bold;
    color: #007bff;
}

.pool-adjust {
    display: flex;
    align-items: center;
    gap: 15px;
    padding: 15px;
    background: #f8f9fa;
    border-radius: 6px;
    margin-bottom: 20px;
}

.pool-adjust input[type="range"] {
    flex: 1;
    height: 6px;
}

.pool-adjust span {
    font-size: 20px;
    font-weight: bold;
    min-width: 30px;
    text-align: center;
}

.active-jobs {
    padding: 15px;
    background: #f8f9fa;
    border-radius: 6px;
}

.active-jobs h3 {
    font-size: 16px;
    margin-bottom: 10px;
}

.active-jobs ul {
    list-style: none;
    padding: 0;
    margin: 0;
}

.active-jobs li {
    padding: 8px;
    background: #fff;
    border-radius: 4px;
    margin-bottom: 5px;
}
```

---

## 九、数据库迁移

### 9.1 迁移脚本

```python
# alembic/versions/xxx_add_flexible_config_and_monitoring.py

"""添加灵活配置和监控支持

Revision ID: xxx
Revises: yyy
Create Date: 2026-09-28
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

def upgrade():
    # 1. crawler_configs 表新增字段
    
    # 添加 timeout_config 字段
    op.add_column('crawler_configs', 
        sa.Column('timeout_config', sa.JSON(), nullable=True, 
                  comment='超时配置 JSON')
    )
    
    # 添加 extraction_config 字段
    op.add_column('crawler_configs',
        sa.Column('extraction_config', sa.JSON(), nullable=True,
                  comment='提取规则配置 JSON')
    )
    
    # 添加 priority 字段
    op.add_column('crawler_configs',
        sa.Column('priority', sa.Integer(), nullable=False, 
                  server_default='5', comment='任务优先级 1-10')
    )
    
    # 2. 创建 system_configs 表
    op.create_table('system_configs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('config_key', sa.String(100), nullable=False, 
                  comment='配置键'),
        sa.Column('config_value', sa.String(500), nullable=False,
                  comment='配置值'),
        sa.Column('description', sa.String(200), nullable=True,
                  comment='配置说明'),
        sa.Column('updated_at', sa.DateTime(), nullable=True,
                  comment='更新时间'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('config_key')
    )
    
    # 3. 插入默认系统配置
    op.execute("""
        INSERT INTO system_configs (config_key, config_value, description)
        VALUES 
        ('max_concurrent_workers', '3', '最大并发进程数'),
        ('worker_memory_limit_mb', '512', '单进程内存限制(MB)'),
        ('queue_warning_threshold', '50', '队列积压告警阈值')
    """)
    
    # 4. job_queue 表新增 priority 字段（如果不存在）
    try:
        op.add_column('job_queue',
            sa.Column('priority', sa.Integer(), nullable=False,
                      server_default='5', comment='任务优先级')
        )
    except:
        pass  # 字段可能已存在

def downgrade():
    # 回滚操作
    op.drop_column('crawler_configs', 'priority')
    op.drop_column('crawler_configs', 'extraction_config')
    op.drop_column('crawler_configs', 'timeout_config')
    op.drop_table('system_configs')
    
    try:
        op.drop_column('job_queue', 'priority')
    except:
        pass
```

---

## 十、部署方案

### 10.1 分阶段部署计划

#### 第一阶段：代码清理 + 配置灵活化（1天）

**步骤：**
1. 备份当前数据库
   ```bash
   mysqldump -u root -p browser_automation > backup_$(date +%Y%m%d).sql
   ```

2. 删除临时脚本
   ```bash
   # 预览要删除的文件
   git ls-files --others --exclude-standard "*.py" | grep -v "^app/" | grep -v "^tests/"
   
   # 确认后删除
   find . -maxdepth 1 -name "*.py" -type f -delete
   
   # 更新 .gitignore
   echo "/*.py" >> .gitignore
   echo "!setup.py" >> .gitignore
   ```

3. 运行数据库迁移
   ```bash
   alembic upgrade head
   ```

4. 验证配置灵活性
   ```bash
   # 通过API测试配置加载
   curl http://localhost:8000/api/system/config
   ```

5. 重启服务
   ```bash
   systemctl restart browser-automation
   ```

#### 第二阶段：并发能力 + 测试补充（2-3天）

**步骤：**
1. 安装新依赖
   ```bash
   pip install psutil
   pip freeze > requirements.txt
   ```

2. 更新代码
   - 添加进程池管理器
   - 改造调度器
   - 补充测试用例

3. 配置环境变量
   ```bash
   # .env 新增
   MAX_CONCURRENT_WORKERS=3
   WORKER_MEMORY_LIMIT_MB=512
   ```

4. 运行测试
   ```bash
   pytest tests/test_core_flow.py -v
   ```

5. 重启服务并压力测试
   ```bash
   # 提交10个任务测试并发
   for i in {1..10}; do
       curl -X POST http://localhost:8000/api/jobs \
            -H "Content-Type: application/json" \
            -d '{"config_id": 1, "query_params": {"keyword": "test'$i'"}}'
   done
   ```

#### 第三阶段：监控增强（1-2天）

**步骤：**
1. 前端资源更新
   ```bash
   # 下载 Chart.js（或使用CDN）
   curl -o static/chart.min.js https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.umd.min.js
   ```

2. 启动系统监控器
   - 调度器中添加监控任务
   - WebSocket推送监控数据

3. 配置告警阈值
   ```sql
   UPDATE system_configs 
   SET config_value = '50' 
   WHERE config_key = 'queue_warning_threshold';
   ```

4. 前端测试
   - 打开 `http://localhost:8000/static/index.html`
   - 验证CPU/内存图表实时更新
   - 测试并发数动态调整

### 10.2 回滚方案

**如果出现问题，按以下步骤回滚：**

1. 回滚数据库
   ```bash
   alembic downgrade -1
   ```

2. 恢复代码
   ```bash
   git revert HEAD
   ```

3. 重启服务
   ```bash
   systemctl restart browser-automation
   ```

### 10.3 验收标准

| 验收项 | 标准 | 验证方法 |
|--------|------|----------|
| 代码清理 | 根目录无 `*.py` 临时文件 | `ls *.py` 返回空 |
| 配置灵活化 | 可通过API修改超时配置 | 调用 PUT `/api/system/config/{key}` |
| 并发执行 | 3个任务同时执行 | 查看进程池状态API |
| 监控指标 | CPU/内存数据每10秒更新 | 观察前端图表 |
| 测试覆盖 | 核心测试通过率100% | `pytest tests/test_core_flow.py` |

---

## 十一、预期效果

### 11.1 量化指标

| 指标 | 改进前 | 改进后 | 提升幅度 |
|------|--------|--------|----------|
| 系统评分 | 7.5分 | 8.5分 | +1分 |
| 吞吐量 | 1任务/次 | 3任务/次 | +200% |
| 配置修改 | 需改代码 | API动态修改 | 效率提升100% |
| 测试覆盖率 | ~30% | ~50% | +20% |
| 项目文件数 | 69个临时文件 | 0个 | 代码库清爽 |
| 监控指标数 | 2个 | 6个 | +300% |

### 11.2 质量提升

**工程化：**
- ✅ 项目结构规范，无临时文件
- ✅ 测试流程完善，核心路径覆盖
- ✅ 文档完整，易于维护

**可扩展性：**
- ✅ 配置驱动，新增参数无需改代码
- ✅ 并发可调，适应不同负载需求
- ✅ 监控完善，快速定位问题

**生产就绪度：**
- ✅ 资源监控：CPU/内存/进程数实时掌控
- ✅ 容错能力：进程隔离，单任务崩溃不影响全局
- ✅ 运维友好：动态配置、健康检查、告警机制

---

## 十二、风险与应对

### 12.1 技术风险

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 进程池序列化问题 | 任务提交失败 | 确保执行函数可序列化，使用顶层函数 |
| 数据库连接池耗尽 | 并发数过高导致连接不足 | 限制最大并发数≤10，配置连接池大小 |
| 浏览器进程泄漏 | 内存占用持续增长 | 监控浏览器进程数，超阈值告警 |
| WebSocket断线 | 监控数据推送中断 | 前端自动重连机制 |

### 12.2 兼容性风险

**Windows平台特殊处理：**
```python
# 确保 Windows 使用正确的事件循环策略
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
```

**数据库兼容性：**
- MySQL 5.7+：JSON字段支持
- PostgreSQL 9.4+：JSONB字段支持

### 12.3 运维风险

| 风险 | 应对措施 |
|------|----------|
| 配置错误导致系统不可用 | 配置验证 + 回滚机制 |
| 并发数调整过大导致OOM | 限制最大并发数≤10 |
| 监控数据量过大 | 定期清理历史数据（保留7天）|

---

## 十三、后续优化方向

完成本次改进后，系统评分预计达到8.5分。未来可进一步优化：

1. **分布式部署**（9.0分目标）
   - 多机器部署，共享任务队列
   - Redis作为消息队列
   - 负载均衡

2. **智能调度**（9.5分目标）
   - 基于历史数据预测任务耗时
   - 动态调整并发策略
   - 优先级算法优化

3. **完整监控体系**（10分目标）
   - Prometheus + Grafana集成
   - 分布式追踪（OpenTelemetry）
   - 性能分析工具

---

## 十四、总结

本设计文档详细阐述了将浏览器自动化平台从7.5分提升到8.5分的完整方案，采用分阶段实施策略，平衡了开发效率和系统稳定性。

**核心亮点：**
1. ✅ 工程化：清理技术债务，建立测试规范
2. ✅ 配置化：所有参数可配置，无需改代码
3. ✅ 并发化：多进程池，吞吐量提升2-3倍
4. ✅ 可观测：完善监控体系，实时掌握系统状态

**实施周期：4-6天**
**预期效果：评分+1分，吞吐量+200%**

---

**文档结束**
