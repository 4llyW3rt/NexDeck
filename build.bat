@echo off
setlocal
cd /d "%~dp0"
echo ==========================================
echo  NexStudio 2.0 Build
echo ==========================================

echo [1/3] Paketler kontrol ediliyor...
python -m pip install -q -r requirements.txt pyinstaller
if errorlevel 1 goto :fail

echo [2/3] Eski build klasorleri temizleniyor...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo [3/3] Exe olusturuluyor...
python -m PyInstaller --noconfirm --clean NexStudio.spec
if errorlevel 1 goto :fail

echo.
echo Build tamamlandi: dist\NexStudio\NexStudio.exe
echo Kurulum icin: installer\NexStudio_Setup.iss dosyasini Inno Setup ile derleyin.
if "%1"=="" pause
exit /b 0

:fail
echo.
echo Build basarisiz oldu.
if "%1"=="" pause
exit /b 1
