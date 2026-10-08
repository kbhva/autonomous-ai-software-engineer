"""Tool interface, intentionally independent of any agent framework."""

from typing import Any, Protocol

from flagship.types import ToolResult


class Tool(Protocol):
    name: str
    description: str
    actions: tuple[str, ...]

    def execute(self, arguments: dict[str, Any]) -> ToolResult: ...
