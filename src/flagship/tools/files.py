"""File tools constrained to a single resolved repository root."""

import os
from pathlib import Path
from typing import Any

from flagship.types import ToolResult

IGNORED_DIRS = {".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules"}
MAX_READ_BYTES = 200_000


class RepositoryFileTools:
    name = "repository_files"
    description = "List, read, and write files inside the target repository."
    actions = ("list_files", "read_file", "write_file")

    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve(strict=True)
        if not self.root.is_dir():
            raise ValueError("Repository root must be a directory")

    def resolve_path(self, relative_path: str) -> Path:
        if not isinstance(relative_path, str) or not relative_path.strip():
            raise ValueError("A non-empty repository-relative path is required")
        candidate = (self.root / relative_path).resolve(strict=False)
        try:
            candidate.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("Path escapes the target repository") from exc
        return candidate

    def list_files(self, limit: int = 500) -> ToolResult:
        if not isinstance(limit, int) or not 1 <= limit <= 2000:
            return ToolResult("list_files", False, "Invalid file limit", error="limit must be 1..2000")
        paths: list[str] = []
        for directory, dirs, files in os.walk(self.root, followlinks=False):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS and not (Path(directory) / d).is_symlink()]
            for filename in files:
                full = Path(directory) / filename
                try:
                    safe = self.resolve_path(str(full.relative_to(self.root)))
                except ValueError:
                    continue
                if safe.is_file():
                    paths.append(safe.relative_to(self.root).as_posix())
                    if len(paths) >= limit:
                        return ToolResult("list_files", True, f"Listed {len(paths)} files (limit reached)", {"files": paths})
        paths.sort()
        return ToolResult("list_files", True, f"Listed {len(paths)} files", {"files": paths})

    def read_file(self, path: str) -> ToolResult:
        try:
            target = self.resolve_path(path)
            if not target.is_file():
                raise ValueError("Path is not a file")
            content = target.read_bytes()
            if len(content) > MAX_READ_BYTES:
                raise ValueError(f"File exceeds {MAX_READ_BYTES} byte read limit")
            return ToolResult("read_file", True, f"Read {len(content)} bytes", {"path": path, "content": content.decode("utf-8", errors="replace")})
        except (OSError, ValueError) as exc:
            return ToolResult("read_file", False, "Could not read file", error=str(exc))

    def write_file(self, path: str, content: str) -> ToolResult:
        try:
            if not isinstance(content, str):
                raise ValueError("File content must be text")
            target = self.resolve_path(path)
            target.parent.mkdir(parents=True, exist_ok=True)
            # Re-resolve after creating directories to catch a symlink introduced in the path.
            target = self.resolve_path(path)
            # Preserve the exact text payload across platforms (notably Windows newlines).
            with target.open("w", encoding="utf-8", newline="") as stream:
                stream.write(content)
            return ToolResult("write_file", True, f"Wrote {len(content.encode('utf-8'))} bytes", {"path": path})
        except (OSError, ValueError) as exc:
            return ToolResult("write_file", False, "Could not write file", error=str(exc))

    def execute(self, arguments: dict[str, Any]) -> ToolResult:
        action = arguments.get("action")
        if action == "list_files":
            return self.list_files(arguments.get("limit", 500))
        if action == "read_file":
            return self.read_file(arguments.get("path", ""))
        if action == "write_file":
            return self.write_file(arguments.get("path", ""), arguments.get("content", ""))
        return ToolResult("repository_files", False, "Unknown file action", error="Allowed actions: list_files, read_file, write_file")
