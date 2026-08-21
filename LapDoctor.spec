# LapDoctor.spec
#
# PyInstaller build spec for LapDoctor. Run this ON WINDOWS (PyInstaller
# builds for the OS it runs on -- it cannot cross-compile a .exe from
# another OS), from inside the mp/ folder:
#
#   pip install pyinstaller
#   pyinstaller LapDoctor.spec
#
# The finished app will be at: dist/LapDoctor/LapDoctor.exe
# (Or just double-click build_exe.bat, which runs this for you.)

# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['gui.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=['core', 'google.genai'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='LapDoctor',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,       # windowed app -- no black console box behind the GUI
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # icon='icon.ico',   # uncomment and add an .ico file here for a custom app icon
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='LapDoctor',
)
