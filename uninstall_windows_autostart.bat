@echo off
cd /d "%~dp0"
echo ====================================================
echo  Uninstalling OpenCode Proxy Windows Autostart
echo ====================================================

set "STARTUP_VBS=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\opencode_proxy_startup.vbs"

if exist "%STARTUP_VBS%" (
    del /f /q "%STARTUP_VBS%"
    echo [1/3] Removed startup folder shortcut.
)

reg delete "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "OpenCodeProxy" /f >nul 2>&1
echo [2/3] Removed HKCU registry key.

call stop_windows.bat
echo [3/3] Stopped active proxy processes.

echo.
echo ====================================================
echo  Uninstallation complete.
echo ====================================================
