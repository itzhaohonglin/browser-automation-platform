import pytest
from pydantic import ValidationError
from app.schemas.config import ConfigBase


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
