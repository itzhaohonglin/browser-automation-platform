# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller 打包配置文件

使用方法：
    pyinstaller build.spec

打包完成后：
    可执行文件位于 dist/browser-automation-platform/ 目录
"""

import sys
from pathlib import Path

block_cipher = None

# 项目根目录
ROOT_DIR = Path.cwd()

# conda 环境的依赖 DLL 位于 Library\bin，PyInstaller 不会自动搜索该目录，
# 缺失会导致打包后的 exe 运行时 "ImportError: DLL load failed"（如 _ctypes → ffi.dll）
CONDA_BIN_DIR = Path(sys.prefix) / "Library" / "bin"
CONDA_DLL_NAMES = [
    "ffi.dll",             # _ctypes
    "libbz2.dll",          # _bz2
    "liblzma.dll",         # _lzma
    "sqlite3.dll",         # _sqlite3
    "libexpat.dll",        # pyexpat
    "libssl-3-x64.dll",    # _ssl
    "libcrypto-3-x64.dll", # _ssl / _hashlib
]
conda_binaries = [
    (str(CONDA_BIN_DIR / name), ".")
    for name in CONDA_DLL_NAMES
    if (CONDA_BIN_DIR / name).exists()
]

a = Analysis(
    ['app/main.py'],
    pathex=[str(ROOT_DIR)],
    binaries=conda_binaries,
    datas=[
        # 前端静态文件
        ('static', 'static'),

        # 数据库迁移文件
        ('alembic', 'alembic'),
        ('alembic.ini', '.'),

        # 配置模板
        ('.env.example', '.'),
        ('.env.template', '.'),

        # 客户端功能脚本（--init-config / --import-jobs 调用）
        ('scripts/init_nhsa_registration_config.py', 'scripts'),
        ('scripts/batch_import_registration_jobs.py', 'scripts'),

        # 文档（可选，仅打包存在的文件）
        ('README.md', '.'),
        ('docs/deployment_windows.md', 'docs'),
    ],
    hiddenimports=[
        # Uvicorn 相关
        'uvicorn',
        'uvicorn.logging',
        'uvicorn.loops',
        'uvicorn.loops.auto',
        'uvicorn.protocols',
        'uvicorn.protocols.http',
        'uvicorn.protocols.http.auto',
        'uvicorn.protocols.http.h11_impl',
        'uvicorn.protocols.websockets',
        'uvicorn.protocols.websockets.auto',
        'uvicorn.protocols.websockets.wsproto_impl',
        'uvicorn.lifespan',
        'uvicorn.lifespan.on',

        # FastAPI 相关
        'fastapi',
        'starlette',
        'starlette.responses',
        'starlette.staticfiles',
        'starlette.websockets',

        # Playwright
        'playwright',
        'playwright.__main__',  # --install-browser 参数调用 playwright CLI 入口
        'playwright.async_api',
        'playwright._impl',
        'playwright._impl._api_structures',
        'playwright._impl._browser',
        'playwright._impl._browser_context',
        'playwright._impl._page',
        'playwright._impl._network',
        'playwright.sync_api',

        # 数据库相关
        'sqlalchemy',
        'sqlalchemy.ext.asyncio',
        'sqlalchemy.ext.asyncio.engine',
        'sqlalchemy.ext.asyncio.session',
        'sqlalchemy.dialects.mssql',
        'sqlalchemy.dialects.mssql.pyodbc',
        'sqlalchemy.connectors.aioodbc',
        'aiomysql',
        'aioodbc',
        'pyodbc',
        'pymysql',
        'alembic',
        'alembic.context',  # alembic/env.py 为数据文件，其内部导入需手动声明
        'sqlalchemy.pool',  # 同上，env.py 运行时需要

        # 异步相关
        'asyncio',
        'asyncio.windows_events',  # Windows 平台必需

        # APScheduler
        'apscheduler',
        'apscheduler.schedulers.asyncio',
        'apscheduler.triggers.interval',

        # 其他依赖
        'pydantic',
        'pydantic_settings',
        'email_validator',
        'websockets',
        'typing_extensions',
        'aiohttp',
        'aiohttp.client',
        'aiohttp.connector',
        'smtplib',
        'email.mime.text',
        'email.mime.multipart',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'pytest',
        'unittest',
        'test',
        'tests',
        'setuptools',
        'pip',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher
)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='browser-automation-platform',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,  # 保留控制台窗口，方便查看日志
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='static/icon.ico'  # 可选：添加应用图标
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='browser-automation-platform'
)

# 如果遇到目录被占用问题，可以手动删除 dist/ 和 build/ 目录后重新打包
