@echo off
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"
title RMRP Pomoshnik - Build 3.1.4

echo ============================================================
echo RMRP Pomoshnik - Windows build
echo ============================================================
echo.

set "PY="
where py >nul 2>&1
if not errorlevel 1 set "PY=py -3"
if not defined PY (
  where python >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY (
  echo ERROR: Python 3.10+ was not found.
  echo Install Python from https://www.python.org/downloads/
  echo During setup enable: Add python.exe to PATH.
  goto :fail
)

%PY% --version
if errorlevel 1 goto :fail

echo [1/6] Installing build dependencies...
%PY% -m pip install --disable-pip-version-check pyinstaller==6.16.0 pillow
if errorlevel 1 goto :fail

echo [2/6] Reading application version...
for /f "delims=" %%v in ('%PY% installer\prebuild.py version') do set "VER=%%v"
if not defined VER (
  echo ERROR: Could not read app version.
  goto :fail
)
echo Version: %VER%

echo [3/6] Building application EXE...
if exist dist\RMRP_Pomoshnik.exe del /q dist\RMRP_Pomoshnik.exe
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name RMRP_Pomoshnik ^
  --icon installer\assets\rmrp.ico --paths app ^
  --add-data "app\assets;assets" --add-data "installer\assets\rmrp.ico;assets" ^
  app\RMRP_Pomoshnik.pyw
if errorlevel 1 goto :fail
if not exist dist\RMRP_Pomoshnik.exe (
  echo ERROR: EXE was not created.
  goto :fail
)

echo [4/6] Locating Inno Setup 6...
set "ISCC="
for %%p in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe") do (
  if not defined ISCC if exist %%p set "ISCC=%%~p"
)
if not defined ISCC (
  echo ERROR: Inno Setup 6 was not found.
  echo Install it from https://jrsoftware.org/isdl.php and run this file again.
  goto :fail
)

echo [5/6] Building installer...
"%ISCC%" "/DMyAppVersion=%VER%" installer\RMRP-Pomoshnik.iss
if errorlevel 1 goto :fail

set "OUT=installer\output\RMRP-Pomoshnik-Setup-%VER%.exe"
if not exist "%OUT%" (
  echo ERROR: Installer output is missing: %OUT%
  goto :fail
)

echo [6/6] Creating update manifest...
%PY% installer\prepare_release.py
if errorlevel 1 goto :fail

echo.
echo BUILD SUCCESSFUL
echo Installer: %OUT%
echo Manifest: release\latest.json
echo.
explorer /select,"%CD%\%OUT%"
pause
exit /b 0

:fail
echo.
echo BUILD FAILED. Copy the error messages above and send them to support.
echo This window will remain open so the error can be read.
pause
exit /b 1
