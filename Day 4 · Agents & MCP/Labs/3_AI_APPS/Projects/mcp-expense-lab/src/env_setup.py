"""First-run environment setup for the MCP Expense Lab."""
from __future__ import annotations

import logging
import os
from pathlib import Path

from dotenv import set_key

PROJECT_DIR = Path(__file__).resolve().parents[1]
ENV_PATH = PROJECT_DIR / ".env"
EXAMPLE_PATH = PROJECT_DIR / ".env.example"

DEFAULT_ENV_TEXT = """# ── Which LLM the app starts with: gemini | lmstudio ───────────────────────
DEFAULT_PROVIDER=gemini

# ── LLM: Google Gemini (get a free key at https://aistudio.google.com/apikey) ──
GEMINI_API_KEY=
GEMINI_MODEL=gemini-3.6-flash

# ── LLM: LM Studio (local, no key — fallback when Gemini fails) ────────────
LOCAL_LLM_BASE_URL=http://localhost:1234/v1
LMSTUDIO_MODEL=qwen2.5-7b-instruct

# ── MCP server (server and client must agree on these) ─────────────────────
MCP_SERVER_HOST=127.0.0.1
MCP_SERVER_PORT=8766
"""

logger = logging.getLogger(__name__)


def ensure_env_file() -> bool:
    """Create the project's .env and .env.example without overwriting .env."""
    if ENV_PATH.exists():
        return False
    EXAMPLE_PATH.parent.mkdir(parents=True, exist_ok=True)
    if EXAMPLE_PATH.exists():
        ENV_PATH.write_text(EXAMPLE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        EXAMPLE_PATH.write_text(DEFAULT_ENV_TEXT, encoding="utf-8")
        ENV_PATH.write_text(DEFAULT_ENV_TEXT, encoding="utf-8")
    message = f"Created .env at {ENV_PATH}"
    logger.info(message)
    print(message)
    return True


def save_env_value(key: str, value: str) -> None:
    """Persist one setting in .env and make it available to this process."""
    ensure_env_file()
    set_key(str(ENV_PATH), key, value, quote_mode="never")
    os.environ[key] = value
