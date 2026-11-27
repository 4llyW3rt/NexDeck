# -*- mode: python ; coding: utf-8 -*-
# NexStudio 2.0 PyInstaller tanımı.  Kullanım:  build.bat   (veya: python -m PyInstaller --noconfirm --clean NexStudio.spec)
from PyInstaller.utils.hooks import collect_submodules

hiddenimports = [
    'qrcode', 'PIL', 'PIL.Image', 'PIL.ImageQt',
    'serial', 'serial.tools.list_ports',
    'pycaw.pycaw', 'comtypes', 'comtypes.client',
    'keyboard',
    # Eklentilerin kullandığı kütüphaneler (eklentiler exe içinde değil AppData'dan yüklenir,
    # bu yüzden ihtiyaç duydukları paketler burada açıkça paketlenmeli):
    'obsws_python', 'websocket',
]
hiddenimports += collect_submodules('pycaw')
hiddenimports += collect_submodules('comtypes')
hiddenimports += collect_submodules('obsws_python')

a = Analysis(
    ['src/nexstudio_ui.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/app_icon.ico', '.'),
        ('src/Logo.png', '.'),
        ('src/nexstudio_logo.png', '.'),
        ('src/nircmd.exe', '.'),
        ('src/locales', 'locales'),
        ('src/plugins', 'plugins'),
    ],
    hiddenimports=hiddenimports,
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
    [],
    exclude_binaries=True,
    name='NexStudio',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['src/app_icon.ico'],
    version=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name='NexStudio',
)
