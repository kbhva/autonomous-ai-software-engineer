"""Translate MCP tool results into provider-neutral structured results."""

import json
from typing import Any

from flagship.types import ToolResult


def encode_tool_result(result: ToolResult) -> str:
    return json.dumps(result.to_dict(), ensure_ascii=False)


def decode_mcp_result(action: str, response: Any) -> ToolResult:
    if getattr(response, "is_error", False):
        message = "; ".join(getattr(item, "text", "MCP tool error") for item in response.content)
        return ToolResult(action, False, "MCP tool returned an error", error=message or "MCP tool returned an error")
    for item in getattr(response, "content", []):
        text = getattr(item, "text", None)
        if not isinstance(text, str):
            continue
        try:
            value = json.loads(text)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict) and {"tool", "success", "summary"}.issubset(value):
            return ToolResult(str(value["tool"]), bool(value["success"]), str(value["summary"]),
                              value.get("data", {}), value.get("error"))
    return ToolResult(action, False, "MCP response did not contain a structured tool result",
                      error="Malformed MCP tool response")
