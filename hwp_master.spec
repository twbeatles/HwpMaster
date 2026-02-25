# -*- mode: python ; coding: utf-8 -*-
"""
HWP Master PyInstaller Spec File
빌드 명령어: pyinstaller hwp_master.spec
"""

import sys
import os
from pathlib import Path

block_cipher = None

# 기본은 관리자 권한을 요구하지 않음. 필요할 때만 환경변수로 켠다.
# 예: set HWP_MASTER_UAC_ADMIN=1
UAC_ADMIN = os.environ.get("HWP_MASTER_UAC_ADMIN", "").strip().lower() in ("1", "true", "yes", "y")

# 프로젝트 루트 경로
ROOT = Path(SPECPATH)

# 데이터 파일
datas = [
    (str(ROOT / 'assets'), 'assets'),
    (str(ROOT / 'README.md'), '.'),
    (str(ROOT / 'PROJECT_AUDIT_PYHWPX.md'), '.'),
]

# 숨겨진 임포트
hiddenimports = [
    'PySide6.QtCore',
    'PySide6.QtGui',
    'PySide6.QtWidgets',
    'openpyxl',
    'pyhwpx',
    'win32com.client',
    'pythoncom',
    # Lazy-loaded pages (importlib in main_window)
    'src.ui.pages.template_page',
    'src.ui.pages.macro_page',
    'src.ui.pages.regex_page',
    'src.ui.pages.style_cop_page',
    'src.ui.pages.table_doctor_page',
    'src.ui.pages.doc_diff_page',
    'src.ui.pages.smart_toc_page',
    'src.ui.pages.watermark_page',
    'src.ui.pages.header_footer_page',
    'src.ui.pages.bookmark_page',
    'src.ui.pages.hyperlink_page',
    'src.ui.pages.image_extractor_page',
    'src.ui.pages.action_console_page',
    # Core extensions used by dynamic action console/capability mapping
    'src.core.action_runner',
    'src.core.capability_mapper',
]

# 제외할 모듈  
excludes = [
    'pandas',
    'numpy',
    'matplotlib',
    'scipy',
    'PIL',
    'tkinter',
    'PyQt5',
    'PyQt6',
    'PySide2',
]

a = Analysis(
    ['main.py'],
    pathex=[str(ROOT), str(ROOT / 'src')],  # src 경로 명시적 추가
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=excludes,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='HWP_Master',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
    uac_admin=UAC_ADMIN,
)
