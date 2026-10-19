@echo off
cd /d "%~dp0"
echo ====================================================
echo  Installing OpenCode Proxy Windows Autostart
echo ====================================================

set "CURRENT_DIR=%~dp0"
set "STARTUP_FOLDER=%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup"
set "STARTUP_VBS=%STARTUP_FOLDER%\opencode_proxy_startup.vbs"

echo [1/3] Creating Startup folder shortcut...
(
echo Set WshShell = CreateObject("WScript.Shell"^)
echo WshShell.CurrentDirectory = "%CURRENT_DIR:~0,-1%"
echo WshShell.Run chr(34^) ^& "%CURRENT_DIR%start_windows_background.vbs" ^& chr(34^), 0, False
echo Set WshShell = Nothing
) > "%STARTUP_VBS%"

echo [2/3] Registering in HKCU Registry Run key...
reg add "HKCU\Software\Microsoft\Windows\CurrentVersion\Run" /v "OpenCodeProxy" /t REG_SZ /d "wscript.exe \"%CURRENT_DIR%start_windows_background.vbs\"" /f >nul 2>&1

echo [3/3] Launching proxy now as a detached background service...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$cmd = 'wscript.exe \"' + (Get-Location).Path + '\start_windows_background.vbs\"'; Invoke-CimMethod -ClassName Win32_Process -MethodName Create -Arguments @{CommandLine = $cmd; CurrentDirectory = (Get-Location).Path} | Out-Null"

echo.
echo ====================================================
echo  Installation complete!
echo  OpenCode Proxy is now running in the background and
echo  will automatically start whenever Windows starts.
echo ====================================================
