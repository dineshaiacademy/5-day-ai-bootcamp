@echo off
cd /d "%~dp0"
if exist ".venv\Scriptsctivate.bat" call ".venv\Scriptsctivate.bat"
python server\mcp_server.py
pause
