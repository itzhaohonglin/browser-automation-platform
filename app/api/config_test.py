# app/api/config_test.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Dict, Any
import logging

from app.core.database import get_db
from app.schemas.config_test import ConfigTestRequest, ConfigTestResponse, SampleItem
from app.services.executor import PlaywrightExecutor
from app.models.config import CrawlerConfig
from app.models.job import JobQueue, JobStatus
from app.models.result import CrawlerResult
from sqlalchemy import select

router = APIRouter(prefix="/api/config-test", tags=["配置测试"])
logger = logging.getLogger(__name__)


@router.post("/test", response_model=ConfigTestResponse)
async def test_config(
    request: ConfigTestRequest,
    session: AsyncSession = Depends(get_db)
) -> ConfigTestResponse:
    """
    测试采集配置

    创建临时任务 → 执行采集（限制 3 条数据）→ 返回示例数据
    """
    temp_job = None
    temp_config = None

    try:
        # Step 1: 创建临时配置
        temp_config = CrawlerConfig(
            config_name="__test_config__",
            target_url="https://code.nhsa.gov.cn/toSearch.html?sysflag=1004",
            need_login=False,
            input_configs=[],
            submit_selector="",
            wait_selector="",
            fields_mapping=request.fields_mapping,
            is_active=False,
            max_pages=1  # 测试模式只抓取1页
        )
        session.add(temp_config)
        await session.flush()

        logger.info(f"创建临时配置: config_id={temp_config.id}")

        # Step 2: 创建临时任务
        temp_job = JobQueue(
            config_id=temp_config.id,
            query_params=request.query_params,
            status=JobStatus.PENDING,
            priority=10
        )
        session.add(temp_job)
        await session.flush()

        logger.info(f"创建临时任务: job_id={temp_job.id}")

        # Step 3: 执行采集
        executor = PlaywrightExecutor()
        await executor.execute_job(temp_job.id, session)

        # Step 4: 获取结果
        await session.refresh(temp_job)

        if temp_job.status == JobStatus.SUCCESS:
            # 从结果表获取数据
            result = await session.execute(
                select(CrawlerResult)
                .where(CrawlerResult.job_id == temp_job.id)
                .limit(1)
            )
            result_row = result.scalar_one_or_none()

            if result_row and result_row.extracted_data:
                # 解析数据
                extracted_data = result_row.extracted_data
                items = extracted_data.get("items", []) if isinstance(extracted_data, dict) else []

                # 限制返回最多3条样本数据
                samples = []
                for item in items[:3]:
                    samples.append(SampleItem(
                        list_data=item.get("list_data", {}),
                        detail_data=item.get("detail_data", {}),
                        detail_status=item.get("detail_status", "skipped"),
                        detail_error=item.get("detail_error")
                    ))

                logger.info(f"测试成功，返回 {len(samples)} 条样本数据")

                return ConfigTestResponse(
                    success=True,
                    data={"samples": [s.model_dump() for s in samples]},
                    error=None,
                    error_type=None
                )
            else:
                logger.warning("未提取到数据")
                return ConfigTestResponse(
                    success=False,
                    data=None,
                    error="未提取到数据",
                    error_type="NO_DATA"
                )
        else:
            logger.error(f"任务执行失败: {temp_job.error_msg}")
            return ConfigTestResponse(
                success=False,
                data=None,
                error=temp_job.error_msg or "执行失败",
                error_type="EXECUTION_ERROR"
            )

    except Exception as e:
        logger.exception("配置测试失败")
        return ConfigTestResponse(
            success=False,
            data=None,
            error=str(e),
            error_type="UNKNOWN_ERROR"
        )

    finally:
        # 清理临时数据
        try:
            if temp_job:
                await session.delete(temp_job)
            if temp_config:
                await session.delete(temp_config)
            await session.commit()
            logger.info("临时数据清理完成")
        except Exception as cleanup_error:
            logger.error(f"清理临时数据失败: {cleanup_error}")
