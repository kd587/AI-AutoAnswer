"""Thread-owned MCP stdio session; all protocol traffic stays off the Qt thread."""
import asyncio
import threading
from concurrent.futures import TimeoutError as FutureTimeout

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from .mcp_runtime import MCPRuntimeManager


REQUIRED = {"Snapshot", "Screenshot", "Click", "WaitFor", "Scroll", "DisplayInventory"}


class MCPClientManager:
    def __init__(self, runtime: MCPRuntimeManager | None = None):
        self.runtime = runtime or MCPRuntimeManager()
        self.thread = None
        self.loop = None
        self.session = None
        self.shutdown = None
        self.ready = threading.Event()
        self.error = None
        self.tools = set()
        self.pending = None

    def start(self, timeout: float = 30) -> None:
        if self.thread and self.thread.is_alive():
            if not self.ready.wait(timeout):
                raise RuntimeError("Windows-MCP startup timed out")
            if self.error:
                raise RuntimeError(f"Windows-MCP startup failed: {self.error}") from self.error
            return
        command, args = self.runtime.command()
        self.ready.clear()
        self.error = None
        self.thread = threading.Thread(target=self._thread_main, args=(command, args), daemon=True)
        self.thread.start()
        if not self.ready.wait(timeout):
            self.stop()
            raise RuntimeError("Windows-MCP startup timed out")
        if self.error:
            raise RuntimeError(f"Windows-MCP startup failed: {self.error}") from self.error

    def _thread_main(self, command: str, args: list[str]):
        try:
            asyncio.run(self._serve(command, args))
        except BaseException as exc:
            self.error = exc
            self.ready.set()
        finally:
            self.session = None
            self.loop = None

    async def _serve(self, command: str, args: list[str]):
        self.loop = asyncio.get_running_loop()
        self.shutdown = asyncio.Event()
        # The upstream package enables PostHog by default. Keep the embedded
        # local automation runtime offline and avoid sending tool metadata.
        params = StdioServerParameters(command=command, args=args,
                                       env={"POSTHOG_API_KEY": ""})
        async with stdio_client(params) as (reader, writer):
            async with ClientSession(reader, writer) as session:
                await asyncio.wait_for(session.initialize(), 20)
                tools = await asyncio.wait_for(session.list_tools(), 20)
                self.tools = {tool.name for tool in tools.tools}
                missing = REQUIRED - self.tools
                if missing:
                    raise RuntimeError(f"Windows-MCP tools missing: {', '.join(sorted(missing))}")
                self.session = session
                self.ready.set()
                await self.shutdown.wait()

    def call(self, name: str, arguments: dict | None = None, timeout: float = 20):
        if name not in self.tools or self.session is None or self.loop is None:
            raise RuntimeError("Windows-MCP is disconnected or tool unavailable")
        task = asyncio.run_coroutine_threadsafe(
            self.session.call_tool(name, arguments or {}), self.loop)
        self.pending = task
        try:
            result = task.result(timeout)
        except FutureTimeout as exc:
            task.cancel()
            raise RuntimeError(f"Windows-MCP {name} timed out") from exc
        finally:
            self.pending = None
        if result.is_error:
            detail = " ".join(getattr(item, "text", "") for item in result.content)
            raise RuntimeError(f"Windows-MCP {name} failed: {detail[:300]}")
        return result

    def cancel_pending(self):
        if self.pending is not None:
            self.pending.cancel()

    def stop(self):
        self.cancel_pending()
        if self.loop and self.shutdown:
            self.loop.call_soon_threadsafe(self.shutdown.set)
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5)
        self.session = None
