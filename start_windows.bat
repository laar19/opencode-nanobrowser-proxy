@echo off
cd /d "%~dp0"
echo Starting OpenCode Go Proxy...

where uv >nul 2>&1
if %ERRORLEVEL% equ 0 (
    uv run python main.py
    goto :eof
)

if exist "%USERPROFILE%\.local\bin\uv.exe" (
    "%USERPROFILE%\.local\bin\uv.exe" run python main.py
    goto :eof
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" main.py
    goto :eof
)

python main.py
