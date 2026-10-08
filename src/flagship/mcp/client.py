"""Small official-SDK client facade and MCP-backed ToolProvider."""

import asyncio
from pathlib import Path
from typing import Any

from mcp import Client, StdioServerParameters
from mcp.server import MCPServer
from mcp_types.version import MODERN_PROTOCOL_VERSIONS

from flagship.mcp.tools import decode_mcp_result
from flagship.types import ToolResult


class MCPClient:
    """Synchronous facade over the official SDK's local stdio/in-process client."""

    def __init__(self, target: Any):
        self.target = target

    @classmethod
    def for_repository(cls, root: str | Path, *, test_timeout: int = 120,
                       test_command: str | None = None) -> "MCPClient":
        from flagship.mcp.server import build_repository_server
        from flagship.tools import PytestTool, RepositoryFileTools
        files = RepositoryFileTools(root)
        tests = PytestTool(files.root, test_timeout, test_command)
        return cls(build_repository_server(files, tests))

    def _run(self, coroutine: Any) -> Any:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(coroutine)
        coroutine.close()
        raise RuntimeError("Synchronous MCP facade cannot run inside an active event loop")

    async def _list_tools(self) -> tuple[str, ...]:
        async with Client(self.target, mode=self._mode()) as client:
            response = await client.list_tools()
            return tuple(tool.name for tool in response.tools)

    async def _call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        async with Client(self.target, mode=self._mode()) as client:
            return await client.call_tool(name, arguments=arguments)

    def _mode(self) -> str:
        if isinstance(self.target, MCPServer):
            return MODERN_PROTOCOL_VERSIONS[-1]
        if isinstance(self.target, (StdioServerParameters, str)):
            return "legacy"
        return "legacy"

    def list_tools(self) -> tuple[str, ...]:
        return self._run(self._list_tools())

    def call_tool(self, name: str, arguments: dict[str, Any]) -> Any:
        return self._run(self._call_tool(name, arguments))


class MCPToolProvider:
    """Provider adapter keeps MCP-specific protocol details out of agents."""

    provider_name = "mcp"
    actions = ("list_files", "read_file", "write_file", "run_tests")

    def __init__(self, client: MCPClient):
        self.client = client
        available = set(client.list_tools())
        missing = set(self.actions) - available
        if missing:
            raise RuntimeError(f"MCP server is missing required tools: {', '.join(sorted(missing))}")

    def execute(self, action: str, arguments: dict[str, Any]) -> ToolResult:
        if action not in self.actions:
            return ToolResult(action, False, "Unsupported MCP action", error=f"Unknown action: {action}")
        try:
            response = self.client.call_tool(action, arguments)
            return decode_mcp_result(action, response)
        except Exception as exc:
            return ToolResult(action, False, "MCP call failed", error=f"{type(exc).__name__}: {exc}")
