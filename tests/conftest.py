"""
Pytest configuration file
"""
import sys
from pathlib import Path
import pytest

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


@pytest.fixture(scope="session")
def event_loop_policy():
    """Set event loop policy for Windows（Proactor 支持子进程，Playwright 需要）"""
    if sys.platform == "win32":
        import asyncio
        return asyncio.WindowsProactorEventLoopPolicy()
