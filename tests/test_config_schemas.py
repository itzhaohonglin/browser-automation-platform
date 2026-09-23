import pytest
from pydantic import ValidationError
from app.schemas.config import ConfigBase, ConfigCreate, ConfigUpdate


def test_config_base_required_fields():
    """测试必填字段验证"""
    with pytest.raises(ValidationError) as exc_info:
        ConfigBase(
            config_name="测试配置"
            # 缺少其他必填字段
        )

    errors = exc_info.value.errors()
    required_fields = {err['loc'][0] for err in errors}

    assert 'target_url' in required_fields
    assert 'input_configs' in required_fields
    assert 'submit_selector' in required_fields
    assert 'wait_selector' in required_fields
    assert 'fields_mapping' in required_fields


def test_config_base_valid_data():
    """测试有效数据"""
    config = ConfigBase(
        config_name="测试配置",
        target_url="https://www.example.com",
        input_configs={"inputs": []},
        submit_selector="button.submit",
        wait_selector=".results",
        fields_mapping={"list_selector": ".item", "fields": []}
    )

    assert config.config_name == "测试配置"
    assert str(config.target_url) == "https://www.example.com/"
    assert config.need_login is False
    assert config.max_pages == 1
    assert config.is_active is True


def test_config_create_need_login_without_auth_profile():
    """测试 need_login=True 但缺少 auth_profile"""
    with pytest.raises(ValidationError) as exc_info:
        ConfigCreate(
            config_name="测试配置",
            target_url="https://www.example.com",
            need_login=True,  # 需要登录但没有提供 auth_profile
            input_configs={"inputs": []},
            submit_selector="button",
            wait_selector=".results",
            fields_mapping={"list_selector": ".item", "fields": []}
        )

    assert "need_login=True 时必须提供 auth_profile" in str(exc_info.value)


def test_config_create_need_login_with_auth_profile():
    """测试 need_login=True 且提供 auth_profile"""
    config = ConfigCreate(
        config_name="测试配置",
        target_url="https://www.example.com",
        need_login=True,
        auth_profile="test_profile",
        input_configs={"inputs": []},
        submit_selector="button",
        wait_selector=".results",
        fields_mapping={"list_selector": ".item", "fields": []}
    )

    assert config.need_login is True
    assert config.auth_profile == "test_profile"


def test_config_create_url_validation():
    """测试 URL 格式验证"""
    with pytest.raises(ValidationError) as exc_info:
        ConfigCreate(
            config_name="测试配置",
            target_url="not-a-valid-url",  # 无效 URL
            input_configs={"inputs": []},
            submit_selector="button",
            wait_selector=".results",
            fields_mapping={"list_selector": ".item", "fields": []}
        )

    errors = exc_info.value.errors()
    assert any('url' in str(err).lower() for err in errors)


def test_config_update_partial_fields():
    """测试部分更新（所有字段可选）"""
    update = ConfigUpdate(max_pages=10, is_active=False)

    assert update.max_pages == 10
    assert update.is_active is False
    assert update.config_name is None
    assert update.target_url is None


def test_config_update_need_login_validation():
    """测试更新时 need_login=True 必须提供 auth_profile"""
    with pytest.raises(ValidationError) as exc_info:
        ConfigUpdate(
            need_login=True
            # 缺少 auth_profile
        )

    assert "need_login=True 时必须提供 auth_profile" in str(exc_info.value)


def test_config_update_with_auth_profile():
    """测试更新 need_login 和 auth_profile"""
    update = ConfigUpdate(
        need_login=True,
        auth_profile="new_profile"
    )

    assert update.need_login is True
    assert update.auth_profile == "new_profile"
