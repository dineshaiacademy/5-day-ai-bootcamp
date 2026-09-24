@echo off
setlocal
cd /d "%~dp0"
rem The four-level path is the lab convention; the five-level path reaches the repo root here.
if exist "..\..\..\..\venv\Scripts\activate.bat" call "..\..\..\..\venv\Scripts\activate.bat"
if exist "..\..\..\..\..\venv\Scripts\activate.bat" call "..\..\..\..\..\venv\Scripts\activate.bat"
python server\mcp_server.py
