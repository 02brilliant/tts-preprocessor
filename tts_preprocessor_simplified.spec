# -*- mode: python ; coding: utf-8 -*-
import os
from pathlib import Path


ROOT_DIR = Path(SPECPATH).resolve()
EXECUTABLE_NAME = os.environ.get(
    "TTS_PREPROCESSOR_SIMPLIFIED_EXECUTABLE_NAME",
    "tts_preprocessor_simplified",
)

a = Analysis(
    [str(ROOT_DIR / "bin" / "build_simplified_binary_entrypoint.py")],
    pathex=[str(ROOT_DIR)],
    binaries=[],
    datas=[],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name=EXECUTABLE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
