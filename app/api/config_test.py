# app/api/config_test.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.core.database import get_session
from app.schemas.config_test import ConfigTestRequest, ConfigTestResponse
from app.services.executor import PlaywrightExecutor
from app.models.config import CrawlerConfig
from app.models.job import JobQueue, JobStatus
from app.models.result import CrawlerResult

router = APIRouter(prefix="/api/configs", tags=["配置管理"])
logger = logging.getLogger(__name__)


@router.post("/{config_id}/test", response_model=ConfigTestResponse)
async def test_config(
    config_id: int,
    test_request: ConfigTestRequest,
    session: AsyncSession = Depends(get_session)
) -> ConfigTestResponse:
    """测试采集配置"""
    temp_job = None
    original_fields_mapping = None
    original_max_pages = None

    try:
        # 1. 查询现有配置
        result = await session.execute(
            select(CrawlerConfig).where(CrawlerConfig.id == config_id)
        )
        config = result.scalar_one_or_none()

        if not config:
            raise HTTPException(status_code=404, detail=f"配置 {config_id} 不存在")

        # 2. 保存原始配置
        original_fields_mapping = config.fields_mapping
        original_max_pages = config.max_pages

        # 3. 临时修改配置
        config.fields_mapping = test_request.fields_mapping
        config.max_pages = 1  # 测试模式只抓取1页
        await session.flush()

        logger.info(f"临时修改配置 {config_id} 用于测试")

        # 4. 创建临时任务
        temp_job = JobQueue(
            config_id=config_id,
            query_params=test_request.query_params,
            status=JobStatus.PENDING,
            priority=10
        )
        session.add(temp_job)
        await session.flush()

        logger.info(f"创建临时任务: job_id={temp_job.id}")

        # 5. 执行采集
        executor = PlaywrightExecutor()
        await executor.execute_job(temp_job.id, session)

        # 6. 恢复原始配置
        config.fields_mapping = original_fields_mapping
        config.max_pages = original_max_pages
        await session.flush()

        logger.info(f"恢复配置 {config_id} 原始值")

        # 7. 获取结果并统计
        await session.refresh(temp_job)

        if temp_job.status == JobStatus.SUCCESS:
            # 获取结果数据
            result = await session.execute(
                select(CrawlerResult)
                .where(CrawlerResult.job_id == temp_job.id)
                .limit(1)
            )
            result_row = result.scalar_one_or_none()

            if result_row and result_row.extracted_data:
                # 提取样本数据（前3条）
                extracted_data = result_row.extracted_data
                items = extracted_data[:3] if isinstance(extracted_data, list) else []

                # 统计详情状态
                success_count = sum(1 for item in items if item.get("detail_status") == "success")
                failed_count = sum(1 for item in items if item.get("detail_status") == "failed")
                skipped_count = sum(1 for item in items if item.get("detail_status") == "skipped")

                logger.info(f"测试成功: total={len(items)}, success={success_count}, failed={failed_count}, skipped={skipped_count}")

                return ConfigTestResponse(
                    success=True,
                    data={
                        "total_tested": len(items),
                        "success_count": success_count,
                        "failed_count": failed_count,
                        "skipped_count": skipped_count,
                        "sample_items": items
                    },
                    error=None,
                    error_type=None
                )
            else:
                logger.warning("未提取到数据")
                return ConfigTestResponse(
                    success=False,
                    data=None,
                    error="未提取到数据",
                    error_type="execution_error"
                )
        else:
            logger.error(f"任务执行失败: {temp_job.error_msg}")
            return ConfigTestResponse(
                success=False,
                data=None,
                error=temp_job.error_msg or "执行失败",
                error_type="execution_error"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception("配置测试失败")
        return ConfigTestResponse(
            success=False,
            data=None,
            error=str(e),
            error_type="exception"
        )

    finally:
        # 清理临时任务
        if temp_job is not None:
            await session.delete(temp_job)

        # 确保配置恢复（异常情况）
        if original_fields_mapping is not None:
            result = await session.execute(
                select(CrawlerConfig).where(CrawlerConfig.id == config_id)
            )
            config = result.scalar_one_or_none()
            if config:
                config.fields_mapping = original_fields_mapping
                config.max_pages = original_max_pages

        await session.commit()
        logger.info("清理完成")
