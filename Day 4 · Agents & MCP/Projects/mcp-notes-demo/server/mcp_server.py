"""
MCP SERVER — Day 4 · Agents & MCP (Dinesh AI Academy)

Run standalone to see it launch as its own process:

    python server/mcp_server.py

You won't see any output — that's correct, not broken. An MCP server
speaks a structured JSON-RPC protocol over stdin/stdout, not human-readable
text. It's meant to be *launched by* a client (client/mcp_client.py, our
Streamlit app, Claude Desktop, Claude Code, ...) — never run and read
directly by a person. Press Ctrl+C to stop it.

This server exposes one small "Notes" capability using all three MCP
primitives, continuing the example from Learning/1-MCP_Server_Basics.ipynb:

    Tool      add_note / list_notes / search_notes / delete_note
              → actions an LLM can ask the server to perform
    Resource  note://all  and  note://{title}
              → read-only data the host can fetch as context — no LLM
                decision required to *read* these, unlike a tool call
    Prompt    summarize_note(title)
              → a reusable, parameterized prompt template the host can
                offer a user, owned by the server instead of copy-pasted
                into every app that wants it

MCPServer (the official Python SDK's high-level server class) turns a plain
Python function into a full MCP primitive using only its type hints (→ the
input schema an LLM sees) and its docstring (→ the description an LLM reads
to decide whether to use it). Write the docstring like you're explaining
the function to someone who can only read one sentence — that sentence is
doing real work.
"""

from __future__ import annotations

from mcp.server import MCPServer

mcp = MCPServer(
    "NotesServer",
    instructions=(
        "Stores and retrieves short study notes for the bootcamp. Use add_note to "
        "save one, list_notes/search_notes to find one, delete_note to remove one, "
        "and the note:// resource to read one (or all of them) in full."
    ),
)

# In-memory only — resets every time this process restarts. A real server
# would swap this dict for a database; nothing else below would need to change.
_notes: dict[str, str] = {}


# ── Tools — actions the LLM can ask this server to perform ─────────────────

@mcp.tool()
def add_note(title: str, content: str) -> str:
    """Save a note under a title. Overwrites any existing note with the same title."""
    _notes[title] = content
    return f"Saved note '{title}' ({len(content)} characters)."


@mcp.tool()
def list_notes() -> list[str]:
    """List the titles of every saved note, alphabetically."""
    return sorted(_notes)


@mcp.tool()
def search_notes(keyword: str) -> list[str]:
    """Search saved notes for a keyword (case-insensitive, matches title or content)."""
    keyword = keyword.lower()
    return sorted(
        title for title, content in _notes.items()
        if keyword in title.lower() or keyword in content.lower()
    )


@mcp.tool()
def delete_note(title: str) -> str:
    """Delete a saved note by title. Safe to call even if the title doesn't exist."""
    existed = _notes.pop(title, None) is not None
    return f"Deleted note '{title}'." if existed else f"No note found with title '{title}'."


# ── Resources — read-only data, fetched by URI, no "action" involved ───────

@mcp.resource("note://all")
def get_all_notes() -> str:
    """A read-only listing of every saved note, title and content."""
    if not _notes:
        return "No notes saved yet."
    return "\n\n".join(f"# {title}\n{content}" for title, content in sorted(_notes.items()))


@mcp.resource("note://{title}")
def get_note(title: str) -> str:
    """Fetch the full content of a single saved note by its title."""
    return _notes.get(title, f"No note found with title '{title}'.")


# ── Prompts — reusable, parameterized templates the host can offer a user ──

@mcp.prompt()
def summarize_note(title: str) -> str:
    """Build a prompt asking an LLM to summarize one saved note in one sentence."""
    content = _notes.get(title, "")
    if not content:
        return f"There is no note titled '{title}' to summarize."
    return f"Summarize the following note in one short sentence:\n\n{content}"


if __name__ == "__main__":
    # Default transport is stdio: read JSON-RPC requests from stdin, write
    # responses to stdout. This is exactly how Claude Desktop, Claude Code,
    # Cursor, and client/mcp_client.py all launch and talk to local servers —
    # and it's why this file never needs to know who its caller is.
    mcp.run()
