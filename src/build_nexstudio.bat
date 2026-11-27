@echo off
setlocal
cd /d "%~dp0"

echo ==========================================
echo NexStudio 1.5 Final Build
echo ==========================================

echo [1/3] Gerekli paket kontrolu...
python -m pip show pyinstaller >nul 2>nul
if errorlevel 1 (
    echo PyInstaller bulunamadi, kuruluyor...
    python -m pip install pyinstaller
)

echo [2/3] Eski build klasorleri temizleniyor...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist NexStudio.spec del /q NexStudio.spec

set ADD_DATA_ARGS=
if exist app_icon.ico set ADD_DATA_ARGS=%ADD_DATA_ARGS% --add-data "app_icon.ico;."
if exist Logo.png set ADD_DATA_ARGS=%ADD_DATA_ARGS% --add-data "Logo.png;."
if exist nexstudio_logo.png set ADD_DATA_ARGS=%ADD_DATA_ARGS% --add-data "nexstudio_logo.png;."
if exist logo.png set ADD_DATA_ARGS=%ADD_DATA_ARGS% --add-data "logo.png;."
if exist app_logo.png set ADD_DATA_ARGS=%ADD_DATA_ARGS% --add-data "app_logo.png;."
if exist nircmd.exe set ADD_DATA_ARGS=%ADD_DATA_ARGS% --add-data "nircmd.exe;."
if exist locales set ADD_DATA_ARGS=%ADD_DATA_ARGS% --add-data "locales;locales"
if exist plugins set ADD_DATA_ARGS=%ADD_DATA_ARGS% --add-data "plugins;plugins"

set ICON_ARG=
if exist app_icon.ico set ICON_ARG=--icon "app_icon.ico"

echo [3/3] Exe olusturuluyor...
python -m PyInstaller --noconfirm --clean --onedir --windowed ^
 --name "NexStudio" ^
 %ICON_ARG% ^
 %ADD_DATA_ARGS% ^
 --hidden-import qrcode ^
 --hidden-import PIL ^
 --hidden-import PIL.Image ^
 --hidden-import PIL.ImageQt ^
 --hidden-import serial ^
 --hidden-import serial.tools.list_ports ^
 --hidden-import pycaw.pycaw ^
 --hidden-import comtypes ^
 --hidden-import comtypes.client ^
 --collect-submodules pycaw ^
 --collect-submodules comtypes ^
 "nexstudio_ui.py"

if errorlevel 1 (
    echo.
    echo Build basarisiz oldu.
    pause
    exit /b 1
)

echo.
echo Build tamamlandi: dist\NexStudio\NexStudio.exe
echo Not: Web Kontrolu icin Windows Guvenlik Duvari izin sorarsa Ozel Aglar icin izin ver.
pause
