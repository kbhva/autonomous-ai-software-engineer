"""MCP server exposing only the existing repository tools."""

import argparse
import os
from typing import Any

from mcp.server import MCPServer

from flagship.tools import PytestTool, RepositoryFileTools
from flagship.mcp.tools import encode_tool_result


def build_repository_server(files: Any, tests: Any) -> MCPServer:
    """Register existing tool implementations; no filesystem logic is duplicated."""
    server = MCPServer("flagship-repository", instructions="Repository-root-scoped file and pytest tools.")

    @server.tool()
    def list_files(limit: int = 500) -> str:
        """List repository files, excluding generated/dependency directories."""
        return encode_tool_result(files.list_files(limit))

    @server.tool()
    def read_file(path: str) -> str:
        """Read a UTF-8 text file by repository-relative path."""
        return encode_tool_result(files.read_file(path))

    @server.tool()
    def write_file(path: str, content: str) -> str:
        """Write a UTF-8 text file within the configured repository root."""
        return encode_tool_result(files.write_file(path, content))

    @server.tool()
    def run_tests(args: list[str] | None = None) -> str:
        """Run pytest only; arbitrary shell commands are not supported."""
        return encode_tool_result(tests.execute({"args": args or []}))

    return server


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run the local Flagship repository MCP server.")
    parser.add_argument("--repo", required=True, help="Repository root exposed by this server")
    parser.add_argument("--test-command", help="Optional pytest command")
    parser.add_argument("--test-timeout", type=int, default=int(os.getenv("FLAGSHIP_TEST_TIMEOUT_SECONDS", "120")))
    args = parser.parse_args(argv)
    files = RepositoryFileTools(args.repo)
    tests = PytestTool(files.root, args.test_timeout, args.test_command)
    build_repository_server(files, tests).run(transport="stdio")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
