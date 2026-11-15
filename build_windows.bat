@echo off
rem ============================================================
rem  Сборка установщика RMRP Помощник на этом компьютере.
rem  Запуск: двойной щелчок по файлу.
rem  Необязательно: build_windows.bat владелец/репозиторий
rem  (тогда приложение будет проверять обновления в GitHub Releases этого репозитория).
rem  Результат: installer\output\RMRP-Pomoshnik-Setup-X.Y.Z.exe
rem ============================================================
setlocal EnableExtensions
chcp 65001 >nul
cd /d "%~dp0"

set "PY="
where py >nul 2>&1 && set "PY=py -3"
if not defined PY where python >nul 2>&1 && set "PY=python"
if not defined PY (
  echo [ошибка] Не найден Python 3.10 или новее. Установите его с https://www.python.org/downloads/
  echo          и отметьте галочку "Add python.exe to PATH".
  goto :fail
)

echo [1/5] Зависимости...
%PY% -m pip install --disable-pip-version-check --quiet pyinstaller==6.16.0 pillow
if errorlevel 1 goto :fail

for /f "delims=" %%v in ('%PY% installer\prebuild.py version') do set "VER=%%v"
if not defined VER goto :fail
echo        Версия: %VER%

if not "%~1"=="" (
  %PY% installer\prebuild.py repo %~1
  if errorlevel 1 goto :fail
)

echo [2/5] Сборка EXE (PyInstaller)...
if exist dist\RMRP_Pomoshnik.exe del /q dist\RMRP_Pomoshnik.exe
%PY% -m PyInstaller --noconfirm --clean --onefile --windowed --name RMRP_Pomoshnik ^
  --icon installer\assets\rmrp.ico --paths app ^
  --add-data "app\assets;assets" --add-data "installer\assets\rmrp.ico;assets" ^
  app\RMRP_Pomoshnik.pyw
if errorlevel 1 goto :fail
if not exist dist\RMRP_Pomoshnik.exe goto :fail

echo [3/5] Поиск Inno Setup...
set "ISCC="
for %%p in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe") do (
  if not defined ISCC if exist %%p set "ISCC=%%~p"
)
if not defined ISCC (
  where winget >nul 2>&1
  if not errorlevel 1 (
    echo        Inno Setup не найден, устанавливаю через winget...
    winget install -e --id JRSoftware.InnoSetup --accept-package-agreements --accept-source-agreements
    for %%p in ("%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" "%ProgramFiles%\Inno Setup 6\ISCC.exe" "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe") do (
      if not defined ISCC if exist %%p set "ISCC=%%~p"
    )
  )
)
if not defined ISCC (
  echo [ошибка] Inno Setup 6 не найден. Скачайте его с https://jrsoftware.org/isdl.php , установите и запустите сборку снова.
  goto :fail
)

echo [4/5] Сборка установщика...
"%ISCC%" "/DMyAppVersion=%VER%" installer\RMRP-Pomoshnik.iss
if errorlevel 1 goto :fail

echo [5/5] Контрольная сумма SHA-256...
set "OUT=installer\output\RMRP-Pomoshnik-Setup-%VER%.exe"
if not exist "%OUT%" goto :fail
certutil -hashfile "%OUT%" SHA256

echo.
echo ГОТОВО: %OUT%
explorer /select,"%CD%\%OUT%"
pause
exit /b 0

:fail
echo.
echo Сборка не удалась. Смотрите сообщения выше.
pause
exit /b 1
