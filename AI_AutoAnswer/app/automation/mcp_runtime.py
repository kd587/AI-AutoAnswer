"""Locate the private Windows-MCP stdio runtime shipped with the application."""
import sys
from pathlib import Path


TOOLS = "Snapshot,Screenshot,Click,WaitFor,Scroll,DisplayInventory"


class MCPRuntimeManager:
    def command(self) -> tuple[str, list[str]]:
        if getattr(sys, "frozen", False):
            executable = Path(sys.executable).parent / "mcp_runtime" / "windows-mcp-server.exe"
        else:
            executable = Path(__file__).resolve().parents[2] / ".venv-mcp" / "Scripts" / "windows-mcp.exe"
        if not executable.is_file():
            raise RuntimeError(f"Windows-MCP runtime missing: {executable}; run build-mcp.bat")
        return str(executable), ["serve", "--transport", "stdio", "--tools", TOOLS]
