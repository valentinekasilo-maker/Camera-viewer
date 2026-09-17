# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for ANDRO-Vision Launcher
# Build with: pyinstaller installer/launcher.spec
# Output: CameraApp.exe (placed in project root)

import sys
from pathlib import Path

# Resolve paths relative to project root (parent of installer/)
spec_dir = Path(SPECPATH)
project_root = spec_dir.parent
icon_path = str(project_root / "web" / "images" / "branding" / "favicon.ico")

block_cipher = None

a = Analysis(
    [str(spec_dir / "launcher.py")],
    pathex=[str(project_root)],
    binaries=[],
    datas=[],
    hiddenimports=[
        "msvcrt",
        "ctypes",
        "urllib.request",
        "webbrowser",
        "socket",
        "subprocess",
        "threading",
        "shutil",
        "logging",
        "pathlib",
        "platform",
        "tempfile",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude heavy packages not needed by the launcher
        "numpy",
        "cv2",
        "PIL",
        "matplotlib",
        "scipy",
        "pandas",
        "sklearn",
        "tensorflow",
        "torch",
    ],
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
    name="CameraApp",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,           # UPX compression sometimes triggers antivirus; skip it
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,         # Keep console visible so user can see startup status
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=icon_path if Path(icon_path).exists() else None,
    onefile=True,         # Single self-contained EXE
    version=None,
)
