"""验证详情配置是否完整"""
import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from app.core.database import get_session
from app.models.config import CrawlerConfig
import json


async def verify():
    async with get_session() as session:
        config = await session.get(CrawlerConfig, 45)
        detail_cfg = config.fields_mapping.get('detail_config', {})

        print("=== Detail Config Verification ===")
        print(f"Enabled: {detail_cfg.get('enabled')}")
        print(f"Button Selector: {detail_cfg.get('button_selector')}")
        print(f"Iframe Selector: {detail_cfg.get('iframe_selector')}")
        print(f"Wait After Click: {detail_cfg.get('wait_after_click')}")
        print(f"Wait Selector: {detail_cfg.get('wait_selector')}")
        print(f"Click Method: {detail_cfg.get('click_method')}")
        print(f"Fields Count: {len(detail_cfg.get('fields', []))}")

        # Check field names
        fields = detail_cfg.get('fields', [])
        print("\nField List:")
        for i, field in enumerate(fields, 1):
            print(f"  {i}. {field.get('name')} -> field_name: {field.get('field_name')}")

        # Verify critical fields
        issues = []
        if not detail_cfg.get('button_selector'):
            issues.append("button_selector missing")
        if not detail_cfg.get('iframe_selector'):
            issues.append("iframe_selector missing")
        if detail_cfg.get('wait_after_click') is None:
            issues.append("wait_after_click missing")
        if len(fields) < 12:
            issues.append(f"Insufficient fields (current: {len(fields)}, expected: 12)")

        # Check if all fields have field_name
        fields_without_name = [f['name'] for f in fields if not f.get('field_name')]
        if fields_without_name:
            issues.append(f"Fields without field_name: {', '.join(fields_without_name)}")

        if issues:
            print("\nIssues Found:")
            for issue in issues:
                print(f"  - {issue}")
            return False
        else:
            print("\nConfig is Complete!")
            return True


if __name__ == "__main__":
    result = asyncio.run(verify())
    sys.exit(0 if result else 1)
