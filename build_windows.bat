@echo off
chcp 65001 >nul
setlocal EnableExtensions
cd /d "%~dp0"
echo ==================================================
echo   RMRP Помощник: сборка exe и установщика
echo ==================================================
echo.

rem ---- 1. Python 3.10+ (64-bit)
set "PY="
py -3.12 -c "import sys" >nul 2>&1
if not errorlevel 1 set "PY=py -3.12"
if not defined PY (
  py -3 -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PY=py -3"
)
if not defined PY (
  python -c "import sys" >nul 2>&1
  if not errorlevel 1 set "PY=python"
)
if not defined PY goto nopython
%PY% -c "import sys,struct; sys.exit(0 if sys.version_info>=(3,10) and struct.calcsize('P')==8 else 1)"
if errorlevel 1 goto nopython

rem ---- 2. Окружение сборки (создаётся один раз, лежит в .venv-build)
if not exist ".venv-build\Scripts\python.exe" (
  echo [1/4] Создаю окружение сборки...
  %PY% -m venv .venv-build
  if errorlevel 1 goto fail
)
set "VPY=%CD%\.venv-build\Scripts\python.exe"
echo [1/4] Устанавливаю PyInstaller и Pillow...
"%VPY%" -m pip install --disable-pip-version-check -q pyinstaller==6.16.0 pillow
if errorlevel 1 goto fail

rem ---- 3. Версия, проверки, exe
"%VPY%" -c "import sys;sys.path.insert(0,'app');from rmrp.version import __version__ as v;print(v)" > .ver.tmp
set /p VER=<.ver.tmp
del .ver.tmp >nul 2>&1
if not defined VER goto fail
echo       Версия: %VER%

if /i "%~1"=="/test" (
  echo [2/4] Запускаю тесты...
  "%VPY%" -I -m unittest discover -s tests
  if errorlevel 1 goto fail
  "%VPY%" -I tests\smoke_gui.py
  if errorlevel 1 goto fail
) else (
  echo [2/4] Тесты пропущены ^(запустите build_windows.bat /test, чтобы выполнить их^).
)

rem Адрес репозитория нужен только для автообновления из GitHub Releases. Задайте его так: set GITHUB_REPO=владелец/репозиторий
del app\rmrp\build_info.py >nul 2>&1
if defined GITHUB_REPO echo GITHUB_REPO = '%GITHUB_REPO%'> app\rmrp\build_info.py

echo [3/4] Собираю RMRP_Pomoshnik.exe ^(1–3 минуты^)...
"%VPY%" -m PyInstaller --noconfirm --clean --onefile --windowed --name RMRP_Pomoshnik --icon installer/assets/rmrp.ico --paths app --add-data "app/assets;assets" --add-data "installer/assets/rmrp.ico;assets" app/RMRP_Pomoshnik.pyw
if errorlevel 1 goto fail
if not exist "dist\RMRP_Pomoshnik.exe" goto fail

rem ---- 4. Установщик (Inno Setup 6)
call :findiscc
if not defined ISCC (
  echo       Inno Setup не найден, пробую установить через winget...
  winget install --id JRSoftware.InnoSetup -e --silent --accept-package-agreements --accept-source-agreements >nul 2>&1
  call :findiscc
)
if not defined ISCC goto noinno
echo [4/4] Собираю установщик...
"%ISCC%" "/DMyAppVersion=%VER%" installer\RMRP-Pomoshnik.iss
if errorlevel 1 goto fail

echo.
echo ==================================================
echo   ГОТОВО
echo   Установщик: installer\output\RMRP-Pomoshnik-Setup-%VER%.exe
echo   Просто exe:  dist\RMRP_Pomoshnik.exe
echo ==================================================
explorer "installer\output"
pause
exit /b 0

:findiscc
set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LocalAppData%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LocalAppData%\Programs\Inno Setup 6\ISCC.exe"
exit /b 0

:nopython
echo ОШИБКА: не найден 64-битный Python 3.10 или новее.
echo Установите Python 3.12 с https://www.python.org/downloads/ ^(отметьте «Add python.exe to PATH»^) и запустите файл снова.
pause
exit /b 1

:noinno
echo.
echo exe собран: dist\RMRP_Pomoshnik.exe
echo Для установщика нужен Inno Setup 6: https://jrsoftware.org/isdl.php
echo Установите его и запустите build_windows.bat ещё раз.
pause
exit /b 1

:fail
echo.
echo ОШИБКА: сборка остановлена. Прочитайте сообщения выше.
pause
exit /b 1
