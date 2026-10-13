@echo off
setlocal
cd /d "%~dp0"
set AI_AUTOANSWER_ONEFILE=1
call build-mcp.bat
if errorlevel 1 exit /b 1
.venv\Scripts\pyinstaller.exe --noconfirm --clean --distpath dist-onefile build.spec
if errorlevel 1 exit /b 1
if not exist dist-onefile\mcp_runtime mkdir dist-onefile\mcp_runtime
copy /Y mcp_runtime\windows-mcp-server.exe dist-onefile\mcp_runtime\windows-mcp-server.exe >nul
if errorlevel 1 exit /b 1
copy /Y licenses\Windows-MCP-LICENSE.md dist-onefile\mcp_runtime\LICENSE.md >nul
if errorlevel 1 exit /b 1
echo Built dist-onefile\AI_AutoAnswer.exe with MCP sidecar
endlocal
