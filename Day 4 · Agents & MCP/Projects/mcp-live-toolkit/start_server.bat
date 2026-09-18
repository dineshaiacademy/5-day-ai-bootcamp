@echo off
REM Double-click launcher for the standalone MCP server (Windows).
REM Same effect as the sidebar "Launch" button or `python server/mcp_server.py` —
REM this just opens it in its own console window so you can watch it live.

cd /d "%~dp0"
if exist "..\..\..\venv\Scripts\python.exe" (
    "..\..\..\venv\Scripts\python.exe" server\mcp_server.py
) else (
    python server\mcp_server.py
)
pause
