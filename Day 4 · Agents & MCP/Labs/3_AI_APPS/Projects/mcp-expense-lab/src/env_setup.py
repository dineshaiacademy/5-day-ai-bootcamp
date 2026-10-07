"""First-run environment setup for the MCP Expense Lab."""
from __future__ import annotations

from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_DIR / ".env"
EXAMPLE_PATH = PROJECT_DIR / ".env.example"

DEFAULT_ENV_TEXT = """# Get a Gemini API key at https://aistudio.google.com/apikey and paste it after the = sign
GEMINI_API_KEY=

# MCP server (the server and the app must agree on these)
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8766
"""


def ensure_env_file() -> bool:
    """Create .env (and .env.example) when missing; never overwrite an existing .env."""
    if ENV_PATH.exists():
        return False
    if not EXAMPLE_PATH.exists():
        EXAMPLE_PATH.write_text(DEFAULT_ENV_TEXT, encoding="utf-8")
    ENV_PATH.write_text(EXAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Created .env at {ENV_PATH}")
    return True
