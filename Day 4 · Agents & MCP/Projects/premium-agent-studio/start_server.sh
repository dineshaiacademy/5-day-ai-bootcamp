#!/usr/bin/env bash
# Double-click / terminal launcher for the standalone MCP server (macOS/Linux).
# Same effect as the sidebar "Launch" button or `python server/mcp_server.py` --
# this just runs it in its own terminal so you can watch it live.

cd "$(dirname "$0")"
if [ -x "../../../venv/bin/python" ]; then
    "../../../venv/bin/python" server/mcp_server.py
else
    python3 server/mcp_server.py
fi
