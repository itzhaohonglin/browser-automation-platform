"""
Integration tests for Config CRUD API endpoints
"""
import pytest
import asyncio
from fastapi.testclient import TestClient
from sqlalchemy import select
from app.main import app
from app.core.database import get_session
from app.models.job import JobQueue, JobStatus


@pytest.fixture(scope="function")
def client():
    """Create a test client for each test function"""
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def sample_config_payload():
    """Sample config payload for testing"""
    return {
        "config_name": "测试百度搜索",
        "target_url": "https://www.baidu.com",
        "need_login": False,
        "input_configs": {
            "inputs": [
                {"selector": "#kw", "param_key": "keyword"}
            ]
        },
        "submit_selector": "#su",
        "wait_selector": "#content_left",
        "fields_mapping": {
            "list_selector": ".result",
            "fields": [
                {"name": "title", "selector": "h3 a"},
                {"name": "url", "selector": "h3 a", "attr": "href"}
            ]
        },
        "max_pages": 3
    }


# ============= Task 6: POST /api/configs (创建配置) =============

def test_create_config_success(client, sample_config_payload):
    """测试成功创建配置"""
    response = client.post("/api/configs", json=sample_config_payload)

    assert response.status_code == 201
    data = response.json()

    # 验证返回数据结构
    assert data["id"] is not None
    assert data["config_name"] == "测试百度搜索"
    assert data["target_url"] == "https://www.baidu.com/"
    assert data["need_login"] is False
    assert data["auth_profile"] is None
    assert data["input_configs"] == sample_config_payload["input_configs"]
    assert data["submit_selector"] == "#su"
    assert data["wait_selector"] == "#content_left"
    assert data["fields_mapping"] == sample_config_payload["fields_mapping"]
    assert data["max_pages"] == 3
    assert data["is_active"] is True
    assert "created_at" in data


def test_create_config_invalid_url(client):
    """测试 URL 验证失败"""
    payload = {
        "config_name": "测试配置",
        "target_url": "not-a-valid-url",  # 无效 URL
        "need_login": False,
        "input_configs": {"inputs": []},
        "submit_selector": "button",
        "wait_selector": ".results",
        "fields_mapping": {"list_selector": ".item", "fields": []}
    }

    response = client.post("/api/configs", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


def test_create_config_need_login_without_auth_profile(client):
    """测试 need_login=True 但缺少 auth_profile 返回 422"""
    payload = {
        "config_name": "测试配置",
        "target_url": "https://www.example.com",
        "need_login": True,  # 需要登录但没有提供 auth_profile
        "input_configs": {"inputs": []},
        "submit_selector": "button",
        "wait_selector": ".results",
        "fields_mapping": {"list_selector": ".item", "fields": []}
    }

    response = client.post("/api/configs", json=payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    # 验证错误消息包含 auth_profile 相关信息
    error_msg = str(data["detail"]).lower()
    assert "auth_profile" in error_msg or "need_login" in error_msg


# ============= Task 7: GET /api/configs (列表查询) =============

def test_get_configs_list_success(client, sample_config_payload):
    """测试成功获取配置列表"""
    # 创建两个配置
    client.post("/api/configs", json=sample_config_payload)

    payload2 = sample_config_payload.copy()
    payload2["config_name"] = "测试配置2"
    client.post("/api/configs", json=payload2)

    # 获取列表
    response = client.get("/api/configs")

    assert response.status_code == 200
    data = response.json()

    # 验证响应结构
    assert "total" in data
    assert "page" in data
    assert "page_size" in data
    assert "items" in data
    assert data["page"] == 1
    assert data["page_size"] == 20
    assert data["total"] >= 2
    assert len(data["items"]) >= 2


def test_get_configs_list_with_pagination(client, sample_config_payload):
    """测试分页参数"""
    # 创建多个配置
    for i in range(5):
        payload = sample_config_payload.copy()
        payload["config_name"] = f"测试配置{i}"
        client.post("/api/configs", json=payload)

    # 测试第一页
    response = client.get("/api/configs?page=1&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2

    # 测试第二页
    response = client.get("/api/configs?page=2&page_size=2")
    assert response.status_code == 200
    data = response.json()
    assert data["page"] == 2


def test_get_configs_list_filter_by_is_active(client, sample_config_payload):
    """测试 is_active 过滤"""
    # 创建启用的配置
    payload_active = sample_config_payload.copy()
    payload_active["config_name"] = "启用配置"
    payload_active["is_active"] = True
    client.post("/api/configs", json=payload_active)

    # 创建禁用的配置
    payload_inactive = sample_config_payload.copy()
    payload_inactive["config_name"] = "禁用配置"
    payload_inactive["is_active"] = False
    client.post("/api/configs", json=payload_inactive)

    # 查询启用的配置
    response = client.get("/api/configs?is_active=true")
    assert response.status_code == 200
    data = response.json()
    assert all(item["is_active"] is True for item in data["items"])

    # 查询禁用的配置
    response = client.get("/api/configs?is_active=false")
    assert response.status_code == 200
    data = response.json()
    assert all(item["is_active"] is False for item in data["items"])


# ============= Task 8: GET /api/configs/{config_id} (详情查询) =============

def test_get_config_detail_success(client, sample_config_payload):
    """测试成功获取配置详情"""
    # 创建配置
    create_response = client.post("/api/configs", json=sample_config_payload)
    config_id = create_response.json()["id"]

    # 获取详情
    response = client.get(f"/api/configs/{config_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == config_id
    assert data["config_name"] == sample_config_payload["config_name"]
    assert data["target_url"] == "https://www.baidu.com/"


def test_get_config_detail_not_found(client):
    """测试配置不存在返回 404"""
    response = client.get("/api/configs/999999")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "不存在" in data["detail"]


# ============= Task 9: PUT /api/configs/{config_id} (更新配置) =============

def test_update_config_success(client, sample_config_payload):
    """测试成功更新配置"""
    # 创建配置
    create_response = client.post("/api/configs", json=sample_config_payload)
    config_id = create_response.json()["id"]

    # 更新配置
    update_payload = {
        "config_name": "更新后的配置名称",
        "max_pages": 5,
        "is_active": False
    }
    response = client.put(f"/api/configs/{config_id}", json=update_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == config_id
    assert data["config_name"] == "更新后的配置名称"
    assert data["max_pages"] == 5
    assert data["is_active"] is False
    # 验证未更新的字段保持不变
    assert data["target_url"] == "https://www.baidu.com/"


def test_update_config_partial_update(client, sample_config_payload):
    """测试部分更新配置"""
    # 创建配置
    create_response = client.post("/api/configs", json=sample_config_payload)
    config_id = create_response.json()["id"]

    # 只更新一个字段
    update_payload = {"is_active": False}
    response = client.put(f"/api/configs/{config_id}", json=update_payload)

    assert response.status_code == 200
    data = response.json()
    assert data["is_active"] is False
    # 其他字段不变
    assert data["config_name"] == sample_config_payload["config_name"]


def test_update_config_not_found(client):
    """测试更新不存在的配置返回 404"""
    update_payload = {"config_name": "测试"}
    response = client.put("/api/configs/999999", json=update_payload)

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "不存在" in data["detail"]


def test_update_config_invalid_validation(client, sample_config_payload):
    """测试更新时验证失败"""
    # 创建配置
    create_response = client.post("/api/configs", json=sample_config_payload)
    config_id = create_response.json()["id"]

    # 尝试设置 need_login=True 但不提供 auth_profile
    update_payload = {
        "need_login": True
        # 缺少 auth_profile
    }
    response = client.put(f"/api/configs/{config_id}", json=update_payload)

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data


# ============= Task 10: DELETE /api/configs/{config_id} (删除配置) =============

def test_delete_config_success(client, sample_config_payload):
    """测试成功删除配置"""
    # 创建配置
    create_response = client.post("/api/configs", json=sample_config_payload)
    config_id = create_response.json()["id"]

    # 删除配置
    response = client.delete(f"/api/configs/{config_id}")

    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert str(config_id) in data["message"]

    # 验证配置已被删除
    get_response = client.get(f"/api/configs/{config_id}")
    assert get_response.status_code == 404


def test_delete_config_not_found(client):
    """测试删除不存在的配置返回 404"""
    response = client.delete("/api/configs/999999")

    assert response.status_code == 404
    data = response.json()
    assert "detail" in data
    assert "不存在" in data["detail"]


def test_delete_config_with_pending_jobs(client, sample_config_payload):
    """测试删除有待执行任务的配置返回 409"""
    # 创建配置
    create_response = client.post("/api/configs", json=sample_config_payload)
    config_id = create_response.json()["id"]

    # 直接在数据库中创建待执行任务
    async def create_pending_job():
        async for session in get_session():
            try:
                job = JobQueue(
                    config_id=config_id,
                    query_params={"keyword": "测试"},
                    status=JobStatus.PENDING
                )
                session.add(job)
                await session.commit()
            finally:
                await session.close()
                break

    # 运行异步函数
    asyncio.run(create_pending_job())

    # 尝试删除配置
    response = client.delete(f"/api/configs/{config_id}")

    assert response.status_code == 409
    data = response.json()
    assert "detail" in data
    assert "待执行任务" in data["detail"]

