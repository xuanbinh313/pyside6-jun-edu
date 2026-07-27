# -*- mode: python ; coding: utf-8 -*-

import sys

sys.setrecursionlimit(10000)

a = Analysis(
    ["main.py"],
    pathex=["."],
    binaries=[],
    datas=[
        ("resources", "resources"),
    ],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        "torch",
        "torchvision",
        "torchaudio",
        "paddle",
        "paddleocr",
        "paddlepaddle",
        "paddlepaddle-gpu",
        "google.genai",
        "pytest",
        "unittest",
        "tkinter",
    ],
    noarchive=False,
    optimize=2,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="JunEdu",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
