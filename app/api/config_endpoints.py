"""
配置管理 API 端点
"""
import logging
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.models.config import CrawlerConfig
from app.models.job import JobQueue, JobStatus
from app.schemas.config import ConfigCreate, ConfigResponse, ConfigUpdate, ConfigListResponse

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/configs", tags=["配置管理"])


@router.post("", response_model=ConfigResponse, status_code=status.HTTP_201_CREATED)
async def create_config(
    config_data: ConfigCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    创建新的采集配置

    Args:
        config_data: 配置创建数据
        db: 数据库会话

    Returns:
        ConfigResponse: 创建的配置对象

    Raises:
        HTTPException: 422 验证失败
    """
    try:
        # 创建 ORM 对象
        db_config = CrawlerConfig(
            config_name=config_data.config_name,
            target_url=str(config_data.target_url),
            need_login=config_data.need_login,
            auth_profile=config_data.auth_profile,
            login_url=str(config_data.login_url) if config_data.login_url else None,
            input_configs=config_data.input_configs,
            submit_selector=config_data.submit_selector,
            wait_selector=config_data.wait_selector,
            fields_mapping=config_data.fields_mapping,
            pagination_selector=config_data.pagination_selector,
            max_pages=config_data.max_pages,
            is_active=config_data.is_active
        )

        # 插入数据库
        db.add(db_config)
        await db.commit()
        await db.refresh(db_config)

        logger.info(f"配置创建成功: id={db_config.id}, name={db_config.config_name}")

        # 返回配置
        return ConfigResponse.model_validate(db_config)

    except Exception as e:
        await db.rollback()
        logger.error(f"配置创建失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置创建失败: {str(e)}"
        )


@router.get("", response_model=ConfigListResponse)
async def get_configs(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    is_active: Optional[bool] = Query(None, description="是否启用过滤"),
    db: AsyncSession = Depends(get_db)
):
    """
    获取配置列表（分页）

    Args:
        page: 页码（从1开始）
        page_size: 每页大小（1-100）
        is_active: 是否启用过滤（可选）
        db: 数据库会话

    Returns:
        ConfigListResponse: 配置列表响应
    """
    try:
        # 构建查询条件
        query = select(CrawlerConfig)
        if is_active is not None:
            query = query.where(CrawlerConfig.is_active == is_active)

        # 查询总数
        count_query = select(func.count()).select_from(query.subquery())
        result = await db.execute(count_query)
        total = result.scalar()

        # 分页查询
        query = query.order_by(CrawlerConfig.id.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)
        result = await db.execute(query)
        configs = result.scalars().all()

        # 返回响应
        return ConfigListResponse(
            total=total,
            page=page,
            page_size=page_size,
            items=[ConfigResponse.model_validate(config) for config in configs]
        )

    except Exception as e:
        logger.error(f"配置列表查询失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置列表查询失败: {str(e)}"
        )


@router.get("/{config_id}", response_model=ConfigResponse)
async def get_config(config_id: int, db: AsyncSession = Depends(get_db)):
    """
    获取配置详情

    Args:
        config_id: 配置 ID
        db: 数据库会话

    Returns:
        ConfigResponse: 配置对象

    Raises:
        HTTPException: 404 配置不存在
    """
    try:
        # 查询配置
        config = await db.get(CrawlerConfig, config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"配置不存在: id={config_id}"
            )

        # 返回配置
        return ConfigResponse.model_validate(config)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"配置详情查询失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置详情查询失败: {str(e)}"
        )


@router.put("/{config_id}", response_model=ConfigResponse)
async def update_config(
    config_id: int,
    config_data: ConfigUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    更新配置（部分更新）

    Args:
        config_id: 配置 ID
        config_data: 配置更新数据
        db: 数据库会话

    Returns:
        ConfigResponse: 更新后的配置对象

    Raises:
        HTTPException: 404 配置不存在, 422 验证失败
    """
    try:
        # 查询配置
        config = await db.get(CrawlerConfig, config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"配置不存在: id={config_id}"
            )

        # 应用部分更新
        update_data = config_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            # 处理 HttpUrl 类型转换
            if field in ["target_url", "login_url"] and value is not None:
                value = str(value)
            setattr(config, field, value)

        # 提交更新
        await db.commit()
        await db.refresh(config)

        logger.info(f"配置更新成功: id={config_id}")

        # 返回配置
        return ConfigResponse.model_validate(config)

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"配置更新失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置更新失败: {str(e)}"
        )


@router.delete("/{config_id}")
async def delete_config(config_id: int, db: AsyncSession = Depends(get_db)):
    """
    删除配置

    Args:
        config_id: 配置 ID
        db: 数据库会话

    Returns:
        dict: 成功消息

    Raises:
        HTTPException: 404 配置不存在, 409 存在待执行任务
    """
    try:
        # 查询配置
        config = await db.get(CrawlerConfig, config_id)
        if not config:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"配置不存在: id={config_id}"
            )

        # 检查是否有待执行任务
        query = select(func.count()).where(
            JobQueue.config_id == config_id,
            JobQueue.status == JobStatus.PENDING
        )
        result = await db.execute(query)
        pending_count = result.scalar()

        if pending_count > 0:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"配置存在 {pending_count} 个待执行任务，无法删除"
            )

        # 删除配置
        await db.delete(config)
        await db.commit()

        logger.info(f"配置删除成功: id={config_id}")

        # 返回成功消息
        return {"message": f"配置删除成功: id={config_id}"}

    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"配置删除失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置删除失败: {str(e)}"
        )
