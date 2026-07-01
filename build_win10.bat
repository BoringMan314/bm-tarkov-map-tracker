@echo off
setlocal EnableExtensions
cd /d "%~dp0"

if not exist "go.mod" (
  echo [build_win10] FAIL: missing go.mod ^(run from repo root^)
  goto :end_fail
)

set "EXE_NAME=bm-tarkov-map-tracker.exe"
set "ROOT_EXE=%~dp0%EXE_NAME%"
set "OUT_EXE=%~dp0bin\%EXE_NAME%"

echo [build_win10] Wails v3 Win10/amd64: %ROOT_EXE% ^(from bin^)

taskkill /F /IM "%EXE_NAME%" /T >nul 2>&1

if exist "%ROOT_EXE%" del /f /q "%ROOT_EXE%" 2>nul

where go >nul 2>&1
if errorlevel 1 (
  echo [build_win10] FAIL: go not in PATH ^(install Go 1.22+^)
  goto :end_fail
)

where wails3 >nul 2>&1
if errorlevel 1 (
  echo [build_win10] FAIL: wails3 not in PATH
  echo [build_win10] install: go install github.com/wailsapp/wails/v3/cmd/wails3@latest
  goto :end_fail
)

if not exist "icons\icon.ico" (
  echo [build_win10] FAIL: missing icons\icon.ico
  echo [build_win10] run once: python tools\sync_root_assets.py
  goto :end_fail
)

if not exist "icons\icon.png" (
  echo [build_win10] FAIL: missing icons\icon.png
  echo [build_win10] run once: python tools\sync_root_assets.py
  goto :end_fail
)

if not exist "points\exfil-pmc.png" (
  echo [build_win10] FAIL: missing points\exfil-pmc.png
  echo [build_win10] run once: python tools\sync_root_assets.py
  goto :end_fail
)

if not exist "maps\woods_tarkov.dev_A.png" (
  echo [build_win10] FAIL: missing maps\woods_tarkov.dev_A.png
  echo [build_win10] run once: python tools\sync_root_assets.py
  goto :end_fail
)

if not exist "maps\woods_tarkov.dev_B.svg" (
  if not exist "maps\woods_tarkov.dev_B.png" (
    echo [build_win10] FAIL: missing maps\woods_tarkov.dev_B.svg or .png
    echo [build_win10] run once: python tools\sync_root_assets.py
    goto :end_fail
  )
)

if not exist "maps\factory_eftarkov.com.png" (
  echo [build_win10] FAIL: missing maps\factory_eftarkov.com.png
  echo [build_win10] run once: python tools\sync_root_assets.py
  goto :end_fail
)

echo [build_win10] using:
go version
wails3 version

echo [build_win10] sync root assets (icons/maps/points)
python tools\sync_root_assets.py
if errorlevel 1 (
  echo [build_win10] FAIL: sync_root_assets.py
  goto :end_fail
)

echo [build_win10] sync root i18n
python tools\sync_root_i18n.py
if errorlevel 1 (
  echo [build_win10] FAIL: sync_root_i18n.py
  goto :end_fail
)

go mod tidy
if errorlevel 1 (
  echo [build_win10] FAIL: go mod tidy
  goto :end_fail
)

if exist "sync_version.go" (
  go run sync_version.go
  if errorlevel 1 (
    echo [build_win10] FAIL: sync_version.go
    goto :end_fail
  )
)

wails3 build GOOS=windows GOARCH=amd64
set "BUILD_RC=%ERRORLEVEL%"
if not "%BUILD_RC%"=="0" (
  echo [build_win10] FAIL: wails3 build
  goto :end_fail
)

if not exist "%OUT_EXE%" (
  echo [build_win10] FAIL: missing %OUT_EXE%
  goto :end_fail
)

copy /Y "%OUT_EXE%" "%ROOT_EXE%" >nul
if errorlevel 1 (
  echo [build_win10] FAIL: copy to repo root
  goto :end_fail
)

if not exist "%ROOT_EXE%" (
  echo [build_win10] FAIL: missing %ROOT_EXE%
  goto :end_fail
)

echo [build_win10] OK: %ROOT_EXE%
goto :end_ok

:end_fail
if /i "%~1"=="nopause" exit /b 1
echo.
pause
exit /b 1

:end_ok
if /i "%~1"=="nopause" exit /b 0
echo.
pause
exit /b 0
