"""Provider boundary between the agent runtime and repository capabilities."""

from typing import Any, Protocol

from flagship.types import ToolResult


class ToolProvider(Protocol):
    actions: tuple[str, ...]
    provider_name: str

    def execute(self, action: str, arguments: dict[str, Any]) -> ToolResult: ...


class DirectToolProvider:
    """Adapts existing direct tools to the provider interface."""

    provider_name = "direct"

    def __init__(self, tools: list[Any]):
        self.tools = {action: tool for tool in tools for action in tool.actions}
        self.actions = tuple(self.tools)

    def execute(self, action: str, arguments: dict[str, Any]) -> ToolResult:
        tool = self.tools.get(action)
        if tool is None:
            return ToolResult("tool_provider", False, "Tool action unavailable", error=f"Unknown action: {action}")
        return tool.execute({"action": action, **arguments})


class CompositeToolProvider:
    """Routes disjoint actions to existing providers without mixing their protocols."""

    provider_name = "composite"

    def __init__(self, providers: list[ToolProvider]):
        self.providers: dict[str, ToolProvider] = {}
        for provider in providers:
            for action in provider.actions:
                if action in self.providers:
                    raise ValueError(f"Duplicate tool action: {action}")
                self.providers[action] = provider
        self.actions = tuple(self.providers)

    def provider_for(self, action: str) -> str:
        return getattr(self.providers.get(action), "provider_name", self.provider_name)

    def execute(self, action: str, arguments: dict[str, Any]) -> ToolResult:
        provider = self.providers.get(action)
        if provider is None:
            return ToolResult("tool_provider", False, "Tool action unavailable", error=f"Unknown action: {action}")
        return provider.execute(action, arguments)
