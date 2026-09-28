import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime, timezone
from app.services.executor import PlaywrightExecutor
from app.models.job import JobQueue, JobStatus
from app.models.config import CrawlerConfig


@pytest.mark.asyncio
async def test_executor_records_success_metrics():
    """测试：执行器记录成功任务的指标"""
    executor = PlaywrightExecutor()

    # Mock session
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    # Mock job
    mock_job = MagicMock(spec=JobQueue)
    mock_job.id = 1
    mock_job.config_id = 1
    mock_job.status = JobStatus.PENDING
    mock_job.query_params = {"keyword": "test"}

    # Mock config
    mock_config = MagicMock(spec=CrawlerConfig)
    mock_config.id = 1
    mock_config.config_name = "test_config"
    mock_config.need_login = False
    mock_config.target_url = "http://example.com"
    mock_config.input_configs = None
    mock_config.submit_selector = "#submit"
    mock_config.wait_selector = "#results"
    mock_config.fields_mapping = {"list_selector": ".item", "fields": []}
    mock_config.pagination_selector = None
    mock_config.max_pages = 1

    # Mock database queries
    mock_result_job = MagicMock()
    mock_result_job.scalar_one_or_none = MagicMock(return_value=mock_job)
    mock_result_config = MagicMock()
    mock_result_config.scalar_one_or_none = MagicMock(return_value=mock_config)

    mock_session.execute.side_effect = [mock_result_job, mock_result_config]

    with patch('app.services.executor.metrics_collector') as mock_collector:
        mock_collector.record = AsyncMock()

        # Mock browser automation steps
        with patch.object(executor, '_launch_browser', new_callable=AsyncMock) as mock_launch:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_playwright = MagicMock()
            mock_page = MagicMock()

            mock_launch.return_value = (mock_browser, mock_context, mock_playwright)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_page.on = MagicMock()
            mock_page.goto = AsyncMock()
            mock_page.click = AsyncMock()
            mock_page.wait_for_selector = AsyncMock()
            mock_page.wait_for_function = AsyncMock()
            mock_page.frames = [mock_page]
            mock_page.url = "http://example.com"
            mock_page.close = AsyncMock()
            mock_context.close = AsyncMock()
            mock_browser.close = AsyncMock()
            mock_playwright.stop = AsyncMock()

            with patch('asyncio.sleep', new_callable=AsyncMock):
                with patch.object(executor, '_extract_page_data', new_callable=AsyncMock) as mock_extract:
                    mock_extract.return_value = [{"title": "test"}]

                    with patch.object(executor, '_save_result', new_callable=AsyncMock):
                        result = await executor.execute_job(1, mock_session)

        # 验证返回成功状态
        assert result["status"] == "success"

        # 验证记录了成功率指标
        calls = [call for call in mock_collector.record.call_args_list
                 if 'job_success_rate' in str(call)]
        assert len(calls) > 0, "应该记录 job_success_rate 指标"


@pytest.mark.asyncio
async def test_executor_records_failure_metrics():
    """测试：执行器记录失败任务的指标"""
    executor = PlaywrightExecutor()

    # Mock session
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    # Mock job
    mock_job = MagicMock(spec=JobQueue)
    mock_job.id = 1
    mock_job.config_id = 1
    mock_job.status = JobStatus.PENDING

    # Mock database query to return job
    mock_result = MagicMock()
    mock_result.scalar_one_or_none = MagicMock(return_value=mock_job)
    mock_session.execute.return_value = mock_result

    with patch('app.services.executor.metrics_collector') as mock_collector:
        mock_collector.record = AsyncMock()

        # Mock to raise exception (simulating failure)
        with patch.object(executor, '_launch_browser', side_effect=Exception("Test error")):
            result = await executor.execute_job(1, mock_session)

        # 验证返回失败状态
        assert result["status"] == "failed"

        # 验证记录了失败率指标
        calls = [call for call in mock_collector.record.call_args_list
                 if 'job_failure_rate' in str(call)]
        assert len(calls) > 0, "应该记录 job_failure_rate 指标"


@pytest.mark.asyncio
async def test_executor_records_execution_time():
    """测试：执行器记录执行时间"""
    executor = PlaywrightExecutor()

    # Mock session
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    # Mock job
    mock_job = MagicMock(spec=JobQueue)
    mock_job.id = 1
    mock_job.config_id = 1
    mock_job.status = JobStatus.PENDING
    mock_job.query_params = {"keyword": "test"}

    # Mock config
    mock_config = MagicMock(spec=CrawlerConfig)
    mock_config.id = 1
    mock_config.config_name = "test_config"
    mock_config.need_login = False
    mock_config.target_url = "http://example.com"
    mock_config.input_configs = None
    mock_config.submit_selector = "#submit"
    mock_config.wait_selector = "#results"
    mock_config.fields_mapping = {"list_selector": ".item", "fields": []}
    mock_config.pagination_selector = None
    mock_config.max_pages = 1

    # Mock database queries
    mock_result_job = MagicMock()
    mock_result_job.scalar_one_or_none = MagicMock(return_value=mock_job)
    mock_result_config = MagicMock()
    mock_result_config.scalar_one_or_none = MagicMock(return_value=mock_config)

    mock_session.execute.side_effect = [mock_result_job, mock_result_config]

    with patch('app.services.executor.metrics_collector') as mock_collector:
        mock_collector.record = AsyncMock()

        # Mock browser automation steps
        with patch.object(executor, '_launch_browser', new_callable=AsyncMock) as mock_launch:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_playwright = MagicMock()
            mock_page = MagicMock()

            mock_launch.return_value = (mock_browser, mock_context, mock_playwright)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_page.on = MagicMock()
            mock_page.goto = AsyncMock()
            mock_page.click = AsyncMock()
            mock_page.wait_for_selector = AsyncMock()
            mock_page.wait_for_function = AsyncMock()
            mock_page.frames = [mock_page]
            mock_page.url = "http://example.com"
            mock_page.close = AsyncMock()
            mock_context.close = AsyncMock()
            mock_browser.close = AsyncMock()
            mock_playwright.stop = AsyncMock()

            with patch('asyncio.sleep', new_callable=AsyncMock):
                with patch.object(executor, '_extract_page_data', new_callable=AsyncMock) as mock_extract:
                    mock_extract.return_value = [{"title": "test"}]

                    with patch.object(executor, '_save_result', new_callable=AsyncMock):
                        await executor.execute_job(1, mock_session)

        # 验证记录了执行时间指标
        calls = [call for call in mock_collector.record.call_args_list
                 if 'job_execution_time' in str(call)]
        assert len(calls) > 0, "应该记录 job_execution_time 指标"

        # 验证执行时间是数值类型
        for call in calls:
            args, kwargs = call
            if len(args) >= 2:
                value = args[1]
                assert isinstance(value, (int, float)), "执行时间应该是数值类型"


@pytest.mark.asyncio
async def test_executor_metrics_failure_does_not_break_cleanup():
    """测试：指标记录失败不影响资源清理"""
    executor = PlaywrightExecutor()

    # Mock session
    mock_session = MagicMock()
    mock_session.execute = AsyncMock()
    mock_session.commit = AsyncMock()

    # Mock job
    mock_job = MagicMock(spec=JobQueue)
    mock_job.id = 1
    mock_job.config_id = 1
    mock_job.status = JobStatus.PENDING
    mock_job.query_params = {"keyword": "test"}

    # Mock config
    mock_config = MagicMock(spec=CrawlerConfig)
    mock_config.id = 1
    mock_config.config_name = "test_config"
    mock_config.need_login = False
    mock_config.target_url = "http://example.com"
    mock_config.input_configs = None
    mock_config.submit_selector = "#submit"
    mock_config.wait_selector = "#results"
    mock_config.fields_mapping = {"list_selector": ".item", "fields": []}
    mock_config.pagination_selector = None
    mock_config.max_pages = 1

    # Mock database queries
    mock_result_job = MagicMock()
    mock_result_job.scalar_one_or_none = MagicMock(return_value=mock_job)
    mock_result_config = MagicMock()
    mock_result_config.scalar_one_or_none = MagicMock(return_value=mock_config)

    mock_session.execute.side_effect = [mock_result_job, mock_result_config]

    with patch('app.services.executor.metrics_collector') as mock_collector:
        # Mock 指标记录失败
        mock_collector.record = AsyncMock(side_effect=Exception("Metrics collection error"))

        # Mock browser automation steps
        with patch.object(executor, '_launch_browser', new_callable=AsyncMock) as mock_launch:
            mock_browser = MagicMock()
            mock_context = MagicMock()
            mock_playwright = MagicMock()
            mock_page = MagicMock()

            mock_launch.return_value = (mock_browser, mock_context, mock_playwright)
            mock_context.new_page = AsyncMock(return_value=mock_page)
            mock_page.on = MagicMock()
            mock_page.goto = AsyncMock()
            mock_page.click = AsyncMock()
            mock_page.wait_for_selector = AsyncMock()
            mock_page.wait_for_function = AsyncMock()
            mock_page.frames = [mock_page]
            mock_page.url = "http://example.com"
            mock_page.close = AsyncMock()
            mock_context.close = AsyncMock()
            mock_browser.close = AsyncMock()
            mock_playwright.stop = AsyncMock()

            with patch('asyncio.sleep', new_callable=AsyncMock):
                with patch.object(executor, '_extract_page_data', new_callable=AsyncMock) as mock_extract:
                    mock_extract.return_value = [{"title": "test"}]

                    with patch.object(executor, '_save_result', new_callable=AsyncMock):
                        # 不应该因为指标记录失败而抛出异常
                        result = await executor.execute_job(1, mock_session)

        # 验证任务仍然成功执行
        assert result["status"] == "success"

        # 验证资源清理仍然执行
        mock_page.close.assert_called_once()
        mock_context.close.assert_called_once()
        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()


@pytest.mark.asyncio
async def test_executor_handles_early_failure_without_start_time():
    """测试：在 start_time 初始化前失败不会导致 NameError"""
    executor = PlaywrightExecutor()

    # Mock session that will fail immediately in execute_job
    mock_session = MagicMock()

    # Make session.execute fail before start_time is set
    # This simulates a database connection error before the try block
    mock_session.execute = AsyncMock(side_effect=Exception("Database connection error"))
    mock_session.commit = AsyncMock()

    with patch('app.services.executor.metrics_collector') as mock_collector:
        mock_collector.record = AsyncMock()

        # 应该失败但不会因为 NameError 而崩溃
        result = await executor.execute_job(999, mock_session)

        # 验证返回失败状态
        assert result["status"] == "failed"

        # 验证仍然记录了指标（因为 start_time 在 try 块开始时就设置了）
        # 即使查询失败，start_time 也已经被设置
        assert mock_collector.record.called


