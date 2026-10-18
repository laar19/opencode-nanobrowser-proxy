@echo off
cd /d "%~dp0"
echo Starting OpenCode Go Proxy...

where uv >nul 2>&1
if %ERRORLEVEL% equ 0 (
    uv run --with fastapi --with uvicorn --with httpx --with python-dotenv python -m opencode_proxy.main
    goto :eof
)

if exist "C:\Users\zurg02\.local\bin\uv.exe" (
    "C:\Users\zurg02\.local\bin\uv.exe" run --with fastapi --with uvicorn --with httpx --with python-dotenv python -m opencode_proxy.main
    goto :eof
)

if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -m opencode_proxy.main
    goto :eof
)

python -m opencode_proxy.main
