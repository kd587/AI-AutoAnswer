@echo off
setlocal
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe py -3.11 -m venv .venv
.venv\Scripts\python.exe -m pip install --timeout 120 --retries 3 -i https://pypi.org/simple -r requirements.txt
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m pytest -q
if errorlevel 1 exit /b 1
.venv\Scripts\python.exe -m scripts.smoke_ocr
if errorlevel 1 exit /b 1
call build-mcp.bat
if errorlevel 1 exit /b 1
.venv\Scripts\pyinstaller.exe --noconfirm --clean build.spec
if errorlevel 1 exit /b 1
if not exist dist\AI_AutoAnswer\mcp_runtime mkdir dist\AI_AutoAnswer\mcp_runtime
copy /Y mcp_runtime\windows-mcp-server.exe dist\AI_AutoAnswer\mcp_runtime\windows-mcp-server.exe >nul
if errorlevel 1 exit /b 1
copy /Y licenses\Windows-MCP-LICENSE.md dist\AI_AutoAnswer\mcp_runtime\LICENSE.md >nul
if errorlevel 1 exit /b 1
echo Built dist\AI_AutoAnswer\AI_AutoAnswer.exe
endlocal
