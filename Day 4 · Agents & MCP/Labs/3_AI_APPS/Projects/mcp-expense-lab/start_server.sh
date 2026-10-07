#!/usr/bin/env bash
cd "$(dirname "$0")"
[ -f ".venv/bin/activate" ] && source ".venv/bin/activate"
python server/mcp_server.py
