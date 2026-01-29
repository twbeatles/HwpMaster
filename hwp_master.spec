# -*- mode: python ; coding: utf-8 -*-
"""
HWP Master PyInstaller Spec File
빌드 명령어: pyinstaller hwp_master.spec
"""

import sys
from pathlib import Path

block_cipher = None

# 프로젝트 루트 경로
ROOT = Path(SPECPATH)

# 데이터 파일
datas = [
    (str(ROOT / 'assets'), 'assets'),
    (str(ROOT / 'README.md'), '.'),
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
]

# 제외할 모듈  
excludes = [
    'pandas',
    'numpy',
    'matplotlib',
    'scipy',
    'PIL',
    'tkinter',
]

a = Analysis(
    ['main.py'],
    pathex=[str(ROOT)],
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
    console=False,  # GUI 앱이므로 콘솔 숨김
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,  # str(ROOT / 'assets' / 'icons' / 'app.ico') 로 아이콘 지정 가능
)
