@echo off
setlocal
cd /d "%~dp0"
if not exist .venv-mcp\Scripts\python.exe py -3.13 -m venv .venv-mcp
if errorlevel 1 exit /b 1
.venv-mcp\Scripts\python.exe -m pip install --timeout 120 --retries 3 windows-mcp==0.8.5 "pyinstaller>=6,<7"
if errorlevel 1 exit /b 1
.venv-mcp\Scripts\pyinstaller.exe --noconfirm --clean --distpath mcp_runtime mcp-server.spec
if errorlevel 1 exit /b 1
echo Built mcp_runtime\windows-mcp-server.exe
endlocal
