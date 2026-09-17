"""A tiny MCP server that manages study notes for the bootcamp."""

from mcp.server import MCPServer

mcp = MCPServer("NotesServer")

# In-memory storage — resets every time the server process restarts.
_notes: dict[str, str] = {}


@mcp.tool()
def add_note(title: str, content: str) -> str:
    """Save a note under a title. Overwrites any existing note with the same title."""
    _notes[title] = content
    return f"Saved note '{title}' ({len(content)} characters)."


@mcp.tool()
def search_notes(keyword: str) -> list[str]:
    """Search saved notes for a keyword (case-insensitive) and return the matching titles."""
    keyword = keyword.lower()
    return [
        title for title, content in _notes.items()
        if keyword in title.lower() or keyword in content.lower()
    ]


@mcp.resource("note://{title}")
def get_note(title: str) -> str:
    """Fetch the full content of a single saved note by its title."""
    return _notes.get(title, f"No note found with title '{title}'.")


if __name__ == "__main__":
    # Default transport is stdio: read requests from stdin, write responses to stdout.
    # This is exactly how Claude Desktop / Claude Code launch local MCP servers.
    mcp.run()
