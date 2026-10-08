import io
import subprocess

from flagship.tools.shell import MAX_OUTPUT_CHARS, PytestTool


def test_only_pytest_commands_allowed(tmp_path):
    try:
        PytestTool(tmp_path, test_command="whoami")
    except ValueError as error:
        assert "Only pytest" in str(error)
    else:
        raise AssertionError("non-pytest command should be rejected")


def test_python_module_pytest_command_is_allowed(tmp_path, monkeypatch):
    seen = {}
    class Process:
        stdout = io.BytesIO(b"ok")
        stderr = io.BytesIO(b"")
        returncode = 0
        def wait(self, timeout=None): return 0
    monkeypatch.setattr("flagship.tools.shell.subprocess.Popen",
                        lambda command, **kwargs: (seen.update(command=command, **kwargs) or Process()))
    result = PytestTool(tmp_path, test_command="python -m pytest -q").execute()
    assert result.success
    assert seen["command"] == ["python", "-m", "pytest", "-q"]
    assert seen["shell"] is False


def test_pytest_timeout_is_structured(tmp_path, monkeypatch):
    class Process:
        stdout = io.BytesIO(b"partial")
        stderr = io.BytesIO(b"waiting")
        returncode = -9
        def wait(self, timeout=None):
            if timeout is not None:
                raise subprocess.TimeoutExpired("pytest", timeout)
        def kill(self): pass
    monkeypatch.setattr("flagship.tools.shell.subprocess.Popen", lambda *a, **kw: Process())
    result = PytestTool(tmp_path, timeout_seconds=1).execute()
    assert not result.success
    assert result.data["timed_out"] is True
    assert "timed out" in result.summary


def test_pytest_output_is_bounded(tmp_path, monkeypatch):
    class Process:
        returncode = 1
        stdout = io.BytesIO(b"x" * (MAX_OUTPUT_CHARS + 10))
        stderr = io.BytesIO(b"y" * (MAX_OUTPUT_CHARS + 10))
        def wait(self, timeout=None): return self.returncode
    monkeypatch.setattr("flagship.tools.shell.subprocess.Popen", lambda *a, **kw: Process())
    result = PytestTool(tmp_path).execute()
    assert len(result.data["stdout"]) == MAX_OUTPUT_CHARS
    assert len(result.data["stderr"]) == MAX_OUTPUT_CHARS
    assert result.data["output_truncated"]


def test_pytest_verification_in_temporary_repository(tmp_path):
    (tmp_path / "test_sample.py").write_text("def test_passes():\n    assert 2 + 2 == 4\n", encoding="utf-8")
    result = PytestTool(tmp_path, timeout_seconds=30, test_command="python -m pytest -q").execute()
    assert result.success, result.data
    assert result.data["returncode"] == 0
