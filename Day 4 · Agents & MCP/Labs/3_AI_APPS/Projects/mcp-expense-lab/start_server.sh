#!/usr/bin/env bash
set -e
cd "$(dirname "$0")"
# The four-level path is the lab convention; the five-level path reaches the repo root here.
if [ -f "../../../../venv/bin/activate" ]; then source "../../../../venv/bin/activate"; fi
if [ -f "../../../../../venv/bin/activate" ]; then source "../../../../../venv/bin/activate"; fi
python server/mcp_server.py
