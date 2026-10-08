"""Pytest-only command runner with bounded execution and output."""

import shlex
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

from flagship.types import ToolResult

MAX_OUTPUT_CHARS = 20_000


def _drain_bounded(stream: Any, buffer: bytearray, truncation: list[bool]) -> None:
    """Drain a process pipe while retaining only its final bounded byte window."""
    while True:
        chunk = stream.read(4096)
        if not chunk:
            break
        buffer.extend(chunk)
        if len(buffer) > MAX_OUTPUT_CHARS:
            truncation[0] = True
            del buffer[:-MAX_OUTPUT_CHARS]


class PytestTool:
    name = "run_tests"
    description = "Run pytest in the target repository. No other shell commands are allowed."
    actions = ("run_tests",)

    def __init__(self, root: str | Path, timeout_seconds: int = 120, test_command: str | None = None):
        self.root = Path(root).resolve(strict=True)
        self.timeout_seconds = timeout_seconds
        self.test_command = test_command
        if timeout_seconds < 1:
            raise ValueError("timeout_seconds must be positive")
        if test_command:
            parts = shlex.split(test_command, posix=(sys.platform != "win32"))
            executable = Path(parts[0]).name.lower() if parts else ""
            direct_pytest = executable in {"pytest", "pytest.exe"}
            python_module_pytest = (
                executable in {"python", "python.exe", "python3", "python3.exe", "py", "py.exe"}
                and len(parts) >= 3 and parts[1:3] == ["-m", "pytest"]
            )
            if not (direct_pytest or python_module_pytest):
                raise ValueError("Only pytest commands are permitted")

    def execute(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        args = (arguments or {}).get("args", [])
        if not isinstance(args, list) or not all(isinstance(arg, str) for arg in args):
            return ToolResult("run_tests", False, "Invalid pytest arguments", error="args must be a list of strings")
        if self.test_command:
            base = shlex.split(self.test_command, posix=(sys.platform != "win32"))
            command = base + args
        else:
            command = [sys.executable, "-m", "pytest", *args]
        process = subprocess.Popen(command, cwd=self.root, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                   shell=False)
        stdout_buffer, stderr_buffer = bytearray(), bytearray()
        stdout_truncated, stderr_truncated = [False], [False]
        assert process.stdout is not None and process.stderr is not None
        readers = [threading.Thread(target=_drain_bounded, args=(process.stdout, stdout_buffer, stdout_truncated), daemon=True),
                   threading.Thread(target=_drain_bounded, args=(process.stderr, stderr_buffer, stderr_truncated), daemon=True)]
        for reader in readers:
            reader.start()
        try:
            process.wait(timeout=self.timeout_seconds)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
            for reader in readers:
                reader.join()
            return ToolResult("run_tests", False, f"pytest timed out after {self.timeout_seconds}s",
                              {"command": command, "stdout": stdout_buffer.decode(errors="replace"),
                               "stderr": stderr_buffer.decode(errors="replace"), "timed_out": True},
                              error="Test execution timed out")
        for reader in readers:
            reader.join()
        stdout, stderr = stdout_buffer.decode(errors="replace"), stderr_buffer.decode(errors="replace")
        return ToolResult("run_tests", process.returncode == 0,
                          "pytest passed" if process.returncode == 0 else f"pytest exited {process.returncode}",
                          {"command": command, "returncode": process.returncode, "stdout": stdout, "stderr": stderr,
                           "output_truncated": stdout_truncated[0] or stderr_truncated[0]})
