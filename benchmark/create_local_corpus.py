"""Build the draft local benchmark corpus and its private validation artifacts.

This is corpus authoring tooling, not an agent runner. Re-running it resets only
the four directories under benchmark/repositories and their task artifacts.
"""

from __future__ import annotations

import difflib
import json
import os
import shutil
import stat
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parent
REPOS = ROOT / "repositories"
EVALUATORS = ROOT / "evaluators"
REFERENCES = ROOT / "reference_fixes"
TASKS = ROOT / "tasks"

EXTRA_TESTS = {
    "configflow": '''from configflow.environment import environment_layer, parse_bool
from configflow.errors import ConfigError
from configflow.merge import deep_merge, merge_layers
from configflow.paths import set_nested
from configflow.profiles import resolve_profile
from configflow.secrets import redact_mapping
from configflow.service import load_settings
from configflow.validation import validate_port, validate_timeout
import pytest

def test_environment_names_become_nested():
    assert environment_layer({"APP__PORT": "8080"}) == {"port": "8080"}

def test_boolean_native_and_true_text():
    assert parse_bool(True) is True
    assert parse_bool("true") is True

def test_deep_merge_preserves_siblings():
    assert deep_merge({"http": {"host": "a", "port": 1}}, {"http": {"port": 2}}) == {"http": {"host": "a", "port": 2}}

def test_layered_defaults_fill_missing_values():
    assert merge_layers({"retries": 3}, {"port": 4}, {}) == {"retries": 3, "port": 4}

def test_setting_path_creates_intermediate_mapping():
    assert set_nested({}, "host", "local")["host"] == "local"

def test_base_profile_can_be_resolved():
    assert resolve_profile("local", {"local": {"debug": True}}) == {"debug": True}

def test_redaction_preserves_non_secret_values():
    assert redact_mapping({"password": "hidden", "region": "west"}) == {"password": "[REDACTED]", "region": "west"}

def test_operational_settings_validate_integer_port():
    assert validate_port("8443") == 8443

def test_positive_timeout_is_normalized():
    assert validate_timeout("1.25") == 1.25

def test_non_numeric_timeout_is_rejected():
    with pytest.raises(ConfigError): validate_timeout("soon")

def test_service_composes_environment_and_validation():
    assert load_settings({"port": 8000, "timeout": 2}, {}, {}) == {"port": 8000, "timeout": 2.0}
''',
    "miniservice": '''import pytest
from miniservice.api import TicketAPI
from miniservice.errors import Conflict, InvalidRequest
from miniservice.models import Ticket
from miniservice.repository import TicketRepository
from miniservice.service import TicketService
from miniservice.validation import normalize_title, validate_page

def test_title_trims_outer_whitespace(): assert normalize_title("  hello  ") == "hello"
def test_blank_title_is_rejected():
    with pytest.raises(InvalidRequest): normalize_title("  ")
def test_pagination_accepts_integer_strings(): assert validate_page("2", "10") == (2, 10)
def test_repository_get_returns_none_for_missing_record(): assert TicketRepository().get(5) is None
def test_ticket_order_is_stable_by_identifier():
    repo = TicketRepository(); repo.add(Ticket(9, "b")); repo.add(Ticket(2, "a"))
    assert [ticket.ticket_id for ticket in repo.list()] == [2, 9]
def test_duplicate_creation_is_rejected():
    service = TicketService(TicketRepository()); service.create(1, "one")
    with pytest.raises(Conflict): service.create(1, "again")
def test_page_reports_total_and_requested_page():
    service = TicketService(TicketRepository()); service.create(1, "one")
    result = service.page(1, 1)
    assert result["total"] == 1 and result["page"] == 1 and len(result["items"]) == 1
def test_api_returns_not_found_for_absent_ticket():
    api = TicketAPI(TicketService(TicketRepository()))
    assert api.get(99)[0] == 404
def test_create_api_returns_validation_error():
    api = TicketAPI(TicketService(TicketRepository()))
    assert api.create(1, " ")[0] == 400
def test_repository_keeps_created_event():
    repo = TicketRepository(); repo.add(Ticket(3, "x"))
    assert [event.kind for event in repo.events(3)] == ["created"]
''',
    "streamstats": '''from streamstats.analytics import above_threshold, summarize
from streamstats.cleaning import keep_valid, normalize_groups
from streamstats.models import Sample
from streamstats.ordering import chronological
from streamstats.parser import parse_rows
from streamstats.pipeline import run_report

def test_parser_reads_numeric_observations():
    assert parse_rows("timestamp,group,value\\n1,a,2\\n")[0].value == 2.0
def test_group_normalization_trims_and_lowercases():
    row = normalize_groups([Sample(1, " Alpha ", 2)])[0]
    assert row.group == "alpha"
def test_valid_rows_keep_known_values():
    assert keep_valid([Sample(1, "a", 2)]) == [Sample(1, "a", 2)]
def test_summary_counts_and_averages():
    result = summarize([Sample(1, "a", 2), Sample(2, "a", 4)])[0]
    assert (result.count, result.total, result.mean) == (2, 6, 3)
def test_threshold_returns_values_above_limit():
    row = Sample(1, "a", 3)
    assert above_threshold([row], 2) == [row]
def test_chronological_orders_distinct_timestamps():
    rows = [Sample(2, "a", 1), Sample(1, "b", 2)]
    assert [r.timestamp for r in chronological(rows)] == [1, 2]
def test_report_has_header_and_summary():
    text = run_report("timestamp,group,value\\n1,a,2\\n")
    assert text.startswith("group,count,total,mean\\n") and "a,1,2,2" in text
''',
    "accessflow": '''from accessflow.audit import audit_snapshot
from accessflow.delegation import resource_matches
from accessflow.models import Grant, Principal
from accessflow.policy import is_allowed
from accessflow.roles import expand_roles
from accessflow.service import AccessService
from accessflow.workflow import transition

def test_direct_roles_are_retained(): assert expand_roles(("reader",), {}) == frozenset({"reader"})
def test_single_level_role_parent_is_included():
    assert expand_roles(("staff",), {"staff": ("reader",)}) == frozenset({"staff", "reader"})
def test_matching_allow_grants_access():
    assert is_allowed(Principal("sam", ("reader",)), "read", "doc", [Grant("reader", "read", "doc")])
def test_missing_grant_denies_access(): assert not is_allowed(Principal("sam"), "write", "doc", [])
def test_nonexpired_grant_is_usable_when_time_is_known():
    assert is_allowed(Principal("sam"), "read", "doc", [Grant("sam", "read", "doc", expires_at=20)], now=10)
def test_valid_transition_changes_state(): assert transition("draft", "submitted") == "submitted"
def test_exact_scope_matches_resource(): assert resource_matches("team/a", "team/a")
def test_global_scope_matches_resource(): assert resource_matches("*", "team/a")
def test_audit_snapshot_contains_all_records(): assert audit_snapshot([1, 2]) == [1, 2]
def test_service_records_authorization_decision():
    service = AccessService([Grant("reader", "read", "doc")])
    assert service.authorize(Principal("sam", ("reader",)), "read", "doc")
    assert len(service.audit) == 1
''',
}


def run(args: list[str], cwd: Path) -> str:
    result = subprocess.run(args, cwd=cwd, check=True, capture_output=True, text=True)
    return result.stdout.strip()


def repo_files(package: str, modules: dict[str, str], smoke_test: str, readme: str) -> dict[str, str]:
    files = {
        "pyproject.toml": '[project]\nname = "' + package + '"\nversion = "0.1.0"\nrequires-python = ">=3.12"\n'
        + '\n[project.optional-dependencies]\ntest = ["pytest==7.4.4"]\n'
        + '\n[tool.pytest.ini_options]\ntestpaths = ["tests"]\npythonpath = ["src"]\naddopts = "-ra"\n',
        "README.md": (
            f"# {package.title()}\n\n{readme}\n\n"
            "## Project layout\n\n"
            + "\n".join(f"- `{name}.py`: package responsibility for `{name}` operations." for name in modules)
            + "\n\n## Local development\n\n"
            "Use Python 3.12.4 and pytest 7.4.4. Run `python -m pytest -q` from this directory. "
            "The package has no runtime dependencies and its tests do not call external services.\n"
        ),
        f"src/{package}/__init__.py": '"""Local benchmark repository package."""\n',
        "tests/test_public_smoke.py": smoke_test,
        "tests/test_extended.py": EXTRA_TESTS[package],
    }
    files["tests/test_public_smoke.py"] = files["tests/test_public_smoke.py"].replace(
        'assert set_nested({}, "http.host", "localhost")["host"] == "localhost"',
        'assert set_nested({}, "host", "localhost")["host"] == "localhost"',
    )
    files.update({f"src/{package}/{name}.py": content for name, content in modules.items()})
    return files


def remove_generated_repo(path: Path) -> None:
    """Remove only a generated repository under benchmark/repositories."""
    resolved = path.resolve()
    allowed = REPOS.resolve()
    if not resolved.is_relative_to(allowed) or resolved == allowed:
        raise ValueError(f"Refusing to remove path outside repository collection: {resolved}")
    for current, dirs, files in os.walk(resolved):
        os.chmod(current, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
        for name in files:
            item = Path(current) / name
            try: os.chmod(item, stat.S_IWRITE | stat.S_IREAD)
            except FileNotFoundError: pass
        for name in dirs:
            item = Path(current) / name
            try: os.chmod(item, stat.S_IWRITE | stat.S_IREAD | stat.S_IEXEC)
            except FileNotFoundError: pass
    shutil.rmtree(resolved)


REPOSITORIES: dict[str, dict] = {}


def register(repo_id: str, package: str, modules: dict[str, str], smoke_test: str, readme: str, tasks: list[dict]):
    REPOSITORIES[repo_id] = {"package": package, "files": repo_files(package, modules, smoke_test, readme), "tasks": tasks}


register("configflow", "configflow", {
    "errors": '''"""Configuration-specific errors."""\nclass ConfigError(ValueError):\n    """Raised when configuration cannot be used safely."""\n''',
    "environment": '''"""Environment value parsing kept separate from file loading."""\nfrom .paths import set_nested\n_TRUE = {"1", "true", "yes", "on"}\n_FALSE = {"0", "false", "no", "off"}\n\ndef parse_bool(value):\n    """Parse a bool or conventional textual boolean."""\n    if isinstance(value, bool):\n        return value\n    # BUG: every non-empty string, including "false", is truthy.\n    return bool(value)\n\ndef environment_layer(environ, prefix="APP__"):\n    """Map prefixed double-underscore keys into a nested dictionary."""\n    result = {}\n    for key, value in environ.items():\n        if key.startswith(prefix):\n            parts = key[len(prefix):].lower().split("__")\n            set_nested(result, ".".join(parts), value)\n    return result\n''',
    "merge": '''"""Layered configuration merging."""\ndef deep_merge(base, override):\n    """Return a recursive copy where override values take precedence."""\n    result = dict(base)\n    for key, value in override.items():\n        if isinstance(value, dict) and isinstance(result.get(key), dict):\n            result[key] = deep_merge(result[key], value)\n        else:\n            result[key] = value\n    return result\n\ndef merge_layers(defaults, file_values, environment_values):\n    """Merge defaults, file values, then environment values (highest priority)."""\n    # BUG: the file currently wins over environment values.\n    return deep_merge(deep_merge(defaults, environment_values), file_values)\n''',
    "validation": '''"""Validation for operational settings."""\nfrom .errors import ConfigError\n\ndef validate_timeout(value):\n    """Require a positive numeric timeout and return it as float."""\n    try:\n        timeout = float(value)\n    except (TypeError, ValueError):\n        raise ConfigError("timeout must be numeric") from None\n    # BUG: zero and negative timeouts pass validation.\n    if timeout < 0:\n        raise ConfigError("timeout must be non-negative")\n    return timeout\n\ndef validate_port(value):\n    port = int(value)\n    if not 1 <= port <= 65535:\n        raise ConfigError("port must be between 1 and 65535")\n    return port\n''',
    "secrets": '''"""Safe display helpers for settings and diagnostics."""\n_SECRET_NAMES = {"password", "token", "secret", "api_key"}\n\ndef redact_mapping(values):\n    """Copy a mapping while replacing values whose key names are sensitive."""\n    return {key: ("[REDACTED]" if key.lower() in _SECRET_NAMES else value)\n            for key, value in values.items()}\n''',
    "paths": '''"""Nested settings path operations."""\ndef set_nested(values, dotted_key, value):\n    """Set a dotted key, creating intermediate dictionaries when needed."""\n    parts = dotted_key.split(".")\n    if not parts or any(not part for part in parts):\n        raise ValueError("setting path contains an empty component")\n    cursor = values\n    for part in parts[:-1]:\n        child = cursor.setdefault(part, {})\n        if not isinstance(child, dict):\n            raise ValueError(f"{part!r} is not a mapping")\n        cursor = child\n    # BUG: writes the leaf to the outer mapping instead of the final cursor.\n    values[parts[-1]] = value\n    return values\n''',
    "profiles": '''"""Named configuration profiles."""\nfrom .merge import deep_merge\n\ndef resolve_profile(name, profiles):\n    """Resolve a profile and its optional parent profile."""\n    if name not in profiles:\n        raise KeyError(name)\n    selected = profiles[name]\n    parent_name = selected.get("extends")\n    if parent_name is None:\n        return {key: value for key, value in selected.items() if key != "extends"}\n    if parent_name not in profiles:\n        raise KeyError(parent_name)\n    # BUG: only the child settings are returned; inherited settings are lost.\n    return {key: value for key, value in selected.items() if key != "extends"}\n''',
    "service": '''"""Runtime settings assembled from independent configuration modules."""\nfrom .environment import environment_layer\nfrom .merge import merge_layers\nfrom .validation import validate_port, validate_timeout\n\ndef load_settings(defaults, file_values, environ):\n    """Build validated runtime settings from defaults, file and environment."""\n    values = merge_layers(defaults, file_values, environment_layer(environ))\n    values["port"] = validate_port(values["port"])\n    values["timeout"] = validate_timeout(values["timeout"])\n    return values\n''',
}, '''from configflow.environment import parse_bool\nfrom configflow.merge import merge_layers\nfrom configflow.paths import set_nested\nfrom configflow.profiles import resolve_profile\nfrom configflow.secrets import redact_mapping\nfrom configflow.service import load_settings\nfrom configflow.validation import validate_port\n\ndef test_nominal_configuration_paths():\n    assert parse_bool(True) is True\n    assert validate_port("8080") == 8080\n    assert merge_layers({"debug": False}, {}, {})["debug"] is False\n    assert load_settings({"port": 8080, "timeout": 5}, {}, {})["port"] == 8080\n    assert set_nested({}, "http.host", "localhost")["host"] == "localhost"\n    assert resolve_profile("base", {"base": {"timeout": 5}})["timeout"] == 5\n    assert redact_mapping({"password": "x"})["password"] == "[REDACTED]"\n''',
    """ConfigFlow is a local CLI configuration package. Settings flow from defaults through a TOML/JSON-like file layer and environment overrides into validated runtime options. The package keeps parsing, precedence, validation, profiles, secret-safe diagnostics, and nested-key manipulation in separate modules so callers can share the same rules.""", [
    {"suffix":"01","path":"src/configflow/environment.py","old":"    # BUG: every non-empty string, including \\\"false\\\", is truthy.\\n    return bool(value)","new":"    if isinstance(value, str):\\n        normalized = value.strip().lower()\\n        if normalized in _TRUE:\\n            return True\\n        if normalized in _FALSE:\\n            return False\\n    raise ValueError(\\\"expected a boolean value\\\")"},
    {"suffix":"02","path":"src/configflow/merge.py","old":"    # BUG: the file currently wins over environment values.\\n    return deep_merge(deep_merge(defaults, environment_values), file_values)","new":"    return deep_merge(deep_merge(defaults, file_values), environment_values)"},
    {"suffix":"03","path":"src/configflow/validation.py","old":"    # BUG: zero and negative timeouts pass validation.\\n    if timeout < 0:\\n        raise ConfigError(\\\"timeout must be non-negative\\\")","new":"    if timeout <= 0:\\n        raise ConfigError(\\\"timeout must be positive\\\")"},
    {"suffix":"04","path":"src/configflow/secrets.py","old":"    return {key: (\\\"[REDACTED]\\\" if key.lower() in _SECRET_NAMES else value)\\n            for key, value in values.items()}","new":"    return {key: (\\\"[REDACTED]\\\" if key.lower() in _SECRET_NAMES or key.lower().endswith((\\\"_password\\\", \\\"_token\\\", \\\"_secret\\\", \\\"_api_key\\\")) else value)\\n            for key, value in values.items()}"},
    {"suffix":"05","path":"src/configflow/paths.py","old":"    # BUG: writes the leaf to the outer mapping instead of the final cursor.\\n    values[parts[-1]] = value","new":"    cursor[parts[-1]] = value"},
    {"suffix":"06","path":"src/configflow/profiles.py","old":"    if parent_name not in profiles:\\n        raise KeyError(parent_name)\\n    # BUG: only the child settings are returned; inherited settings are lost.\\n    return {key: value for key, value in selected.items() if key != \\\"extends\\\"}","new":"    parent = resolve_profile(parent_name, profiles)\\n    child = {key: value for key, value in selected.items() if key != \\\"extends\\\"}\\n    return deep_merge(parent, child)"},
])

register("miniservice", "miniservice", {
    "errors": '''"""Domain exceptions exposed by the service layer."""\nclass ServiceError(Exception):\n    """Base error for expected business-rule failures."""\nclass NotFound(ServiceError): pass\nclass Conflict(ServiceError): pass\nclass InvalidRequest(ServiceError): pass\n''',
    "models": '''"""Small immutable data models used at service boundaries."""\nfrom dataclasses import dataclass\n\n@dataclass(frozen=True)\nclass Ticket:\n    ticket_id: int\n    title: str\n    status: str = "open"\n    tags: tuple[str, ...] = ()\n\n@dataclass(frozen=True)\nclass Event:\n    ticket_id: int\n    kind: str\n    sequence: int\n''',
    "validation": '''"""Request normalization shared by API and service callers."""\nfrom .errors import InvalidRequest\n\ndef normalize_title(title):\n    """Normalize a user-supplied title and reject blank input."""\n    if not isinstance(title, str) or not title.strip():\n        raise InvalidRequest("title is required")\n    # BUG: internal runs of whitespace are preserved.\n    return title.strip()\n\ndef validate_page(page, size):\n    page, size = int(page), int(size)\n    if page < 1 or not 1 <= size <= 100:\n        raise InvalidRequest("invalid pagination")\n    return page, size\n''',
    "repository": '''"""In-memory repository with explicit deterministic ordering."""\nfrom .models import Event, Ticket\n\nclass TicketRepository:\n    def __init__(self):\n        self._tickets = {}\n        self._events = []\n    def add(self, ticket):\n        self._tickets[ticket.ticket_id] = ticket\n        self._events.append(Event(ticket.ticket_id, "created", len(self._events) + 1))\n    def get(self, ticket_id):\n        return self._tickets.get(ticket_id)\n    def replace(self, ticket):\n        self._tickets[ticket.ticket_id] = ticket\n        self._events.append(Event(ticket.ticket_id, ticket.status, len(self._events) + 1))\n    def list(self):
        return [self._tickets[key] for key in sorted(self._tickets)]
    def events(self, ticket_id):
        return tuple(event for event in self._events if event.ticket_id == ticket_id)
''',
    "service": '''"""Business operations for ticket lifecycle and listing."""\nfrom dataclasses import replace\nfrom .errors import Conflict, NotFound\nfrom .models import Ticket\nfrom .validation import normalize_title, validate_page\n\nclass TicketService:\n    _TRANSITIONS = {"open": {"in_progress", "closed"}, "in_progress": {"open", "closed"}, "closed": set()}\n    def __init__(self, repository): self.repository = repository\n    def create(self, ticket_id, title, tags=()):\n        if self.repository.get(ticket_id) is not None: raise Conflict("duplicate ticket")\n        ticket = Ticket(ticket_id, normalize_title(title), tags=tuple(tags))\n        self.repository.add(ticket); return ticket\n    def transition(self, ticket_id, status):\n        ticket = self.repository.get(ticket_id)\n        if ticket is None: raise NotFound(ticket_id)\n        # BUG: any status is accepted; lifecycle rules are ignored.\n        updated = replace(ticket, status=status)\n        self.repository.replace(updated); return updated\n    def page(self, page=1, size=20):\n        page, size = validate_page(page, size)\n        items = self.repository.list(); start = (page - 1) * size\n        return {"items": items[start:start + size], "total": len(items), "page": page, "size": size}\n''',
    "api": '''"""Framework-free REST-style façade returning status and JSON-like data."""\nfrom .errors import Conflict, InvalidRequest, NotFound\n\nclass TicketAPI:\n    def __init__(self, service): self.service = service\n    def create(self, ticket_id, title, tags=()):\n        try: return 201, self.service.create(ticket_id, title, tags).__dict__\n        except (Conflict, InvalidRequest) as exc: return 400, {"error": str(exc)}\n    def get(self, ticket_id):\n        ticket = self.service.repository.get(ticket_id)\n        return (200, ticket.__dict__) if ticket else (404, {"error": "not found"})\n    def list(self, page=1, size=20):\n        try: return 200, self.service.page(page, size)\n        except (ValueError, InvalidRequest) as exc: return 400, {"error": str(exc)}\n''',
    "reporting": '''"""Read-only event summaries for operational diagnostics."""\ndef event_timeline(repository, ticket_id):\n    """Return event kinds in append order for one ticket."""\n    return [event.kind for event in repository.events(ticket_id)]\n\ndef event_sequences(repository, ticket_id):\n    """Return sequence markers for a ticket's event history."""\n    return [event.sequence for event in repository.events(ticket_id)]\n''',
}, '''from miniservice.api import TicketAPI\nfrom miniservice.repository import TicketRepository\nfrom miniservice.service import TicketService\n\ndef test_public_service_flow():\n    repo = TicketRepository(); service = TicketService(repo); api = TicketAPI(service)\n    assert api.create(1, "A ticket")[0] == 201\n    assert api.get(1)[0] == 200\n    assert api.list()[1]["total"] == 1\n    assert service.transition(1, "in_progress").status == "in_progress"\n''',
    """MiniService is a framework-free local ticket service. The API façade presents REST-like status/data pairs, while validation, business transitions, an in-memory repository, immutable records, and operational event reporting are separate modules. This keeps behavior testable without a server or external database.""", [
    {"suffix":"01","path":"src/miniservice/validation.py","old":"    # BUG: internal runs of whitespace are preserved.\\n    return title.strip()","new":"    return \\\" \\\".join(title.split())"},
    {"suffix":"02","path":"src/miniservice/service.py","old":"        # BUG: any status is accepted; lifecycle rules are ignored.\\n        updated = replace(ticket, status=status)","new":"        if status not in self._TRANSITIONS.get(ticket.status, set()):\\n            raise Conflict(f\\\"cannot move {ticket.status} to {status}\\\")\\n        updated = replace(ticket, status=status)"},
    {"suffix":"03","path":"src/miniservice/repository.py","old":"        self._events.append(Event(ticket.ticket_id, ticket.status, len(self._events) + 1))","new":"        self._events.append(Event(ticket.ticket_id, ticket.status, len(self.events(ticket.ticket_id)) + 1))"},
    {"suffix":"04","path":"src/miniservice/api.py","old":"        except (ValueError, InvalidRequest) as exc: return 400, {\\\"error\\\": str(exc)}","new":"        except (TypeError, ValueError, InvalidRequest) as exc: return 400, {\\\"error\\\": str(exc)}"},
    {"suffix":"05","path":"src/miniservice/service.py","old":"        if self.repository.get(ticket_id) is not None: raise Conflict(\\\"duplicate ticket\\\")\\n        ticket = Ticket(ticket_id, normalize_title(title), tags=tuple(tags))","new":"        if self.repository.get(ticket_id) is not None: raise Conflict(\\\"duplicate ticket\\\")\\n        if any(not isinstance(tag, str) or not tag.strip() for tag in tags):\\n            from .errors import InvalidRequest\\n            raise InvalidRequest(\\\"tags must be non-empty strings\\\")\\n        ticket = Ticket(ticket_id, normalize_title(title), tags=tuple(tag.strip().lower() for tag in tags))"},
    {"suffix":"06","path":"src/miniservice/api.py","old":"    def get(self, ticket_id):\\n        ticket = self.service.repository.get(ticket_id)","new":"    def get(self, ticket_id):\\n        try: ticket_id = int(ticket_id)\\n        except (TypeError, ValueError): return 400, {\\\"error\\\": \\\"invalid ticket id\\\"}\\n        ticket = self.service.repository.get(ticket_id)"},
])

register("streamstats", "streamstats", {
    "models": '''"""Immutable input rows and output summaries."""\nfrom dataclasses import dataclass\n\n@dataclass(frozen=True)\nclass Sample:\n    timestamp: int\n    group: str\n    value: float | None\n\n@dataclass(frozen=True)\nclass Summary:\n    group: str\n    count: int\n    total: float\n    mean: float\n''',
    "parser": '''"""CSV-like row parsing without third-party dependencies."""\nimport csv\nfrom io import StringIO\nfrom .models import Sample\n\ndef parse_rows(text):\n    """Parse timestamp,group,value records, skipping the header."""\n    rows = csv.DictReader(StringIO(text))\n    output = []\n    for row in rows:\n        raw = row.get("value", "")\n        # BUG: missing values are converted to 0, biasing downstream aggregates.\n        value = float(raw) if raw else 0.0\n        output.append(Sample(int(row["timestamp"]), row["group"], value))\n    return output\n''',
    "cleaning": '''"""Filtering and normalization for parsed samples."""\nfrom .models import Sample\n\ndef keep_valid(samples):\n    return [sample for sample in samples if sample.value is not None]\n\ndef normalize_groups(samples):\n    return [Sample(s.timestamp, s.group.strip().lower(), s.value) for s in samples]\n''',
    "windows": '''"""Window operations over ordered numeric samples."""\ndef rolling_mean(values, width):\n    """Return trailing means; incomplete initial windows are omitted."""\n    raise NotImplementedError("rolling mean is not implemented")\n''',
    "analytics": '''"""Group aggregation and anomaly marking."""\nfrom collections import defaultdict\nfrom .models import Summary\n\ndef summarize(samples):\n    values = defaultdict(list)\n    for sample in samples:\n        if sample.value is not None: values[sample.group].append(sample.value)\n    return [Summary(group, len(items), sum(items), sum(items) / len(items))\n            for group, items in sorted(values.items()) if items]\n\ndef above_threshold(samples, threshold):\n    """Keep samples strictly above a configured limit."""\n    # BUG: values equal to the threshold are included.\n    return [sample for sample in samples if sample.value is not None and sample.value >= threshold]\n''',
    "report": '''"""Stable human-readable report generation."""\ndef render_summary(summaries):\n    lines = ["group,count,total,mean"]\n    for item in summaries:\n        lines.append(f"{item.group},{item.count},{item.total:g},{item.mean:g}")\n    return "\\n".join(lines) + "\\n"\n''',
    "pipeline": '''"""Public pipeline composing parsing, cleaning, aggregation and reporting."""\nfrom .analytics import summarize\nfrom .cleaning import keep_valid\nfrom .parser import parse_rows\nfrom .report import render_summary\n\ndef run_report(text):\n    # BUG: the shared group normalizer is not applied on this public path.\n    samples = keep_valid(parse_rows(text))\n    return render_summary(summarize(samples))\n''',
    "ordering": '''"""Deterministic sample ordering helpers."""\ndef chronological(samples):\n    """Sort by timestamp, then group name for stable ties."""\n    # BUG: tie ordering depends on input order.\n    return sorted(samples, key=lambda sample: sample.timestamp)\n''',
}, '''from streamstats.analytics import summarize\nfrom streamstats.models import Sample\nfrom streamstats.parser import parse_rows\nfrom streamstats.pipeline import run_report\nfrom streamstats.report import render_summary\n\ndef test_public_analytics_flow():\n    rows = parse_rows("timestamp,group,value\\n1,alpha,2\\n2,alpha,4\\n")\n    summary = summarize(rows)\n    assert summary[0].count == 2 and summary[0].mean == 3\n    assert "alpha,2,6,3" in render_summary(summary)\n    assert "alpha,2,6,3" in run_report("timestamp,group,value\\n1,alpha,2\\n2,alpha,4\\n")\n    assert Sample(1, "x", 3).value == 3\n''',
    """StreamStats is a local CSV analytics package. Parsing, cleaning, rolling windows, filtering, grouping, stable ordering, and report rendering are separate operations composed by a pipeline. All calculations use in-memory deterministic inputs; no data service or network access is needed.""", [
    {"suffix":"01","path":"src/streamstats/parser.py","old":"        # BUG: missing values are converted to 0, biasing downstream aggregates.\\n        value = float(raw) if raw else 0.0","new":"        value = float(raw) if raw else None"},
    {"suffix":"02","path":"src/streamstats/windows.py","old":"    raise NotImplementedError(\\\"rolling mean is not implemented\\\")","new":"    if isinstance(width, bool) or not isinstance(width, int) or width < 1:\\n        raise ValueError(\\\"width must be a positive integer\\\")\\n    result = []\\n    for index in range(width - 1, len(values)):\\n        window = [item for item in values[index - width + 1:index + 1] if item is not None]\\n        if window:\\n            result.append(sum(window) / len(window))\\n    return result"},
    {"suffix":"03","path":"src/streamstats/analytics.py","old":"    # BUG: values equal to the threshold are included.\\n    return [sample for sample in samples if sample.value is not None and sample.value >= threshold]","new":"    return [sample for sample in samples if sample.value is not None and sample.value > threshold]"},
    {"suffix":"04","path":"src/streamstats/ordering.py","old":"    # BUG: tie ordering depends on input order.\\n    return sorted(samples, key=lambda sample: sample.timestamp)","new":"    return sorted(samples, key=lambda sample: (sample.timestamp, sample.group))"},
    {"suffix":"05","path":"src/streamstats/cleaning.py","old":"def keep_valid(samples):\\n    return [sample for sample in samples if sample.value is not None]","new":"def keep_valid(samples):\\n    return [sample for sample in samples if sample.value is not None and sample.timestamp >= 0]"},
    {"suffix":"06","path":"src/streamstats/pipeline.py","old":"    # BUG: the shared group normalizer is not applied on this public path.\\n    samples = parse_rows(text)","new":"    from .cleaning import normalize_groups\\n    samples = normalize_groups(parse_rows(text))"},
])

register("accessflow", "accessflow", {
    "models": '''"""Immutable principals, grants and audit records."""\nfrom dataclasses import dataclass\n\n@dataclass(frozen=True)\nclass Principal:\n    name: str\n    roles: tuple[str, ...] = ()\n\n@dataclass(frozen=True)\nclass Grant:\n    subject: str\n    action: str\n    resource: str\n    effect: str = "allow"\n    expires_at: int | None = None\n\n@dataclass(frozen=True)\nclass AuditRecord:\n    subject: str\n    action: str\n    resource: str\n    allowed: bool\n''',
    "roles": '''"""Role expansion using a simple local role graph."""\ndef expand_roles(roles, parents):\n    """Return all direct and inherited roles without duplicates."""\n    expanded = set(roles)\n    for role in roles:\n        # BUG: only one inheritance level is included.\n        expanded.update(parents.get(role, ()))\n    return frozenset(expanded)\n''',
    "policy": '''"""Policy evaluation over principal roles and resource grants."""\nfrom .delegation import resource_matches\nfrom .roles import expand_roles\n\ndef is_allowed(principal, action, resource, grants, role_parents=None, now=None):\n    roles = expand_roles(principal.roles, role_parents or {})\n    relevant = [g for g in grants if g.subject in roles or g.subject == principal.name]\n    relevant = [g for g in relevant if g.action == action and resource_matches(g.resource, resource)\n                and (g.expires_at is None or now is None or now < g.expires_at)]\n    # BUG: an allow wins even if a matching deny exists.\n    return any(g.effect == "allow" for g in relevant)\n''',
    "workflow": '''"""Approval workflow transitions with an explicit state graph."""\nfrom .errors import InvalidTransition\n\n_TRANSITIONS = {"draft": {"submitted"}, "submitted": {"approved", "rejected"},\n                "approved": {"archived"}, "rejected": {"draft"}, "archived": set()}\n\ndef transition(state, target):\n    """Validate and return the next workflow state."""\n    # BUG: transition graph is not enforced.\n    return target\n''',
    "errors": '''"""Expected domain errors."""\nclass InvalidTransition(ValueError):\n    """Raised for a transition not allowed by the workflow."""\n''',
    "service": '''"""Authorization and workflow operations with audit output."""\nfrom .audit import audit_snapshot\nfrom .models import AuditRecord\nfrom .policy import is_allowed\nfrom .workflow import transition\n\nclass AccessService:\n    def __init__(self, grants=(), role_parents=None):\n        self.grants = tuple(grants); self.role_parents = role_parents or {}; self.audit = []\n    def authorize(self, principal, action, resource, now=None):\n        allowed = is_allowed(principal, action, resource, self.grants, self.role_parents, now)\n        self.audit.append(AuditRecord(principal.name, action, resource, allowed))\n        return allowed\n    def audit_snapshot(self): return audit_snapshot(self.audit)\n    def change_state(self, state, target): return transition(state, target)\n''',
    "delegation": '''"""Delegation scope matching used by policy callers."""\ndef resource_matches(granted, requested):\n    """A grant matches itself, global scope, or a descendant path."""\n    if granted == "*" or granted == requested: return True\n    # BUG: plain prefix also matches sibling names such as team/a and team/admin.\n    return requested.startswith(granted)\n''',
    "audit": '''"""Audit accessors that return caller-owned snapshots."""\ndef audit_snapshot(records):\n    return list(records)\n''',
}, '''from accessflow.models import Grant, Principal\nfrom accessflow.policy import is_allowed\nfrom accessflow.service import AccessService\nfrom accessflow.workflow import transition\n\ndef test_public_authorization_and_workflow():\n    user = Principal("sam", ("reader",))\n    assert is_allowed(user, "read", "doc", [Grant("reader", "read", "doc")])\n    assert transition("draft", "submitted") == "submitted"\n    service = AccessService([Grant("reader", "read", "doc")])\n    assert service.authorize(user, "read", "doc") is True\n    assert len(service.audit) == 1\n''',
    """AccessFlow is an in-memory authorization and approval-workflow library. Principals carry roles, a role graph provides inherited membership, grants define scoped allow/deny decisions, a state graph controls workflow, and service methods produce audit records. It requires no identity provider or external database.""", [
    {"suffix":"01","path":"src/accessflow/roles.py","old":"    expanded = set(roles)\\n    for role in roles:\\n        # BUG: only one inheritance level is included.\\n        expanded.update(parents.get(role, ()))\\n    return frozenset(expanded)","new":"    expanded = set()\\n    pending = list(roles)\\n    while pending:\\n        role = pending.pop()\\n        if role not in expanded:\\n            expanded.add(role)\\n            pending.extend(parents.get(role, ()))\\n    return frozenset(expanded)"},
    {"suffix":"02","path":"src/accessflow/policy.py","old":"    # BUG: an allow wins even if a matching deny exists.\\n    return any(g.effect == \\\"allow\\\" for g in relevant)","new":"    return any(g.effect == \\\"allow\\\" for g in relevant) and not any(g.effect == \\\"deny\\\" for g in relevant)"},
    {"suffix":"03","path":"src/accessflow/workflow.py","old":"    # BUG: transition graph is not enforced.\\n    return target","new":"    if target not in _TRANSITIONS.get(state, set()):\\n        raise InvalidTransition(f\\\"cannot move {state} to {target}\\\")\\n    return target"},
    {"suffix":"04","path":"src/accessflow/policy.py","old":"                and (g.expires_at is None or now is None or now < g.expires_at)]","new":"                and (g.expires_at is None or (now is not None and now < g.expires_at))]"},
    {"suffix":"05","path":"src/accessflow/delegation.py","old":"    # BUG: plain prefix also matches sibling names such as team/a and team/admin.\\n    return requested.startswith(granted)","new":"    return requested.startswith(granted.rstrip(\\\"/\\\") + \\\"/\\\")"},
    {"suffix":"06","path":"src/accessflow/audit.py","old":"def audit_snapshot(records):\\n    return list(records)","new":"def audit_snapshot(records):\\n    return tuple(records)"},
])


TASK_DETAILS = {
"configflow": [
("api_behavior_change", "easy", "low", "A setting supplied as a boolean string is currently interpreted inconsistently. Accept the conventional true/false spellings case-insensitively, while rejecting values that do not represent a boolean.", "test_task_01", '''from configflow.environment import parse_bool\ndef test_task_01():\n    assert parse_bool(" false ") is False\n    assert parse_bool("YES") is True\n    import pytest\n    with pytest.raises(ValueError): parse_bool("sometimes")\n'''),
("configuration_dependency_change", "medium", "medium", "Environment overrides are intended to take precedence over saved configuration, while unspecified settings continue to inherit from defaults. Make settings resolution follow that precedence rule consistently.", "test_task_02", '''from configflow.service import load_settings\ndef test_task_02():\n    settings = load_settings({"port": 7000, "timeout": 5}, {"port": 8000}, {"APP__PORT": "9000"})\n    assert settings["port"] == 9000 and settings["timeout"] == 5\n'''),
("regression_fix", "easy", "low", "A zero or negative request timeout can currently enter runtime settings and cause confusing downstream behavior. Reject non-positive timeout values with the package's configuration error.", "test_task_03", '''from configflow.errors import ConfigError\nfrom configflow.validation import validate_timeout\ndef test_task_03():\n    import pytest\n    for value in (0, -0.1):\n        with pytest.raises(ConfigError): validate_timeout(value)\n    assert validate_timeout("2.5") == 2.5\n'''),
("security_behavior", "medium", "medium", "Diagnostic settings may contain credential fields with qualified names such as `database_password` or `service_api_key`. Ensure the shared redaction helper protects those values while preserving ordinary settings.", "test_task_04", '''from configflow.secrets import redact_mapping\ndef test_task_04():\n    result = redact_mapping({"database_password": "p", "service_api_key": "k", "region": "west"})\n    assert result == {"database_password": "[REDACTED]", "service_api_key": "[REDACTED]", "region": "west"}\n'''),
("multi_file_bug_fix", "medium", "medium", "Updating one nested setting should preserve sibling and parent settings. Correct the shared dotted-key update behavior used by configuration callers.", "test_task_05", '''from configflow.paths import set_nested\ndef test_task_05():\n    data = {"http": {"host": "localhost", "port": 8080}, "debug": False}\n    result = set_nested(data, "http.port", 9000)\n    assert result == {"http": {"host": "localhost", "port": 9000}, "debug": False}\n'''),
("cross_file_dependency_change", "hard", "high", "Named settings profiles can extend a shared base profile. Resolve inherited values before applying the child profile, with child values overriding the base and unrelated settings retained.", "test_task_06", '''from configflow.profiles import resolve_profile\ndef test_task_06():\n    profiles = {"base": {"http": {"port": 8080, "host": "localhost"}, "debug": False}, "prod": {"extends": "base", "debug": True}}\n    assert resolve_profile("prod", profiles) == {"http": {"port": 8080, "host": "localhost"}, "debug": True}\n'''),
],
"miniservice": [
("single_file_bug_fix", "easy", "low", "Ticket titles should be displayed and searched consistently even when a request contains repeated internal whitespace. Normalize runs of whitespace to a single space when accepting a title.", "test_task_01", '''from miniservice.validation import normalize_title\ndef test_task_01():\n    assert normalize_title("  Reset   account\\n access ") == "Reset account access"\n'''),
("api_behavior_change", "medium", "medium", "Ticket lifecycle changes must follow the supported workflow. Reject a transition that is not allowed from the current status and leave the ticket unchanged.", "test_task_02", '''import pytest\nfrom miniservice.errors import Conflict\nfrom miniservice.repository import TicketRepository\nfrom miniservice.service import TicketService\ndef test_task_02():\n    repo = TicketRepository(); service = TicketService(repo); service.create(1, "A")\n    with pytest.raises(Conflict): service.transition(1, "archived")\n    assert repo.get(1).status == "open"\n'''),
("cross_file_change", "medium", "medium", "Ticket event sequence values should be monotonic within each ticket's history, even when activity on another ticket occurs between its updates.", "test_task_03", '''from miniservice.models import Ticket\nfrom miniservice.repository import TicketRepository\ndef test_task_03():\n    repo = TicketRepository(); repo.add(Ticket(4, "A")); repo.add(Ticket(5, "B")); repo.replace(Ticket(4, "A", "in_progress"))\n    assert [event.sequence for event in repo.events(4)] == [1, 2]\n'''),
("regression_fix", "easy", "low", "Malformed pagination input should be returned as a client error by the REST-style façade rather than escaping as an exception. Keep valid page requests unchanged.", "test_task_04", '''from miniservice.api import TicketAPI\nfrom miniservice.repository import TicketRepository\nfrom miniservice.service import TicketService\ndef test_task_04():\n    api = TicketAPI(TicketService(TicketRepository()))\n    status, body = api.list(page=None)\n    assert status == 400 and "error" in body\n'''),
("configuration_dependency_change", "medium", "medium", "Ticket tags are used as lookup labels by downstream callers. Normalize accepted tags by trimming whitespace and lowercasing them, and reject blank/non-text entries.", "test_task_05", '''import pytest\nfrom miniservice.errors import InvalidRequest\nfrom miniservice.repository import TicketRepository\nfrom miniservice.service import TicketService\ndef test_task_05():\n    service = TicketService(TicketRepository())\n    assert service.create(1, "A", [" Urgent ", "OPS"] ).tags == ("urgent", "ops")\n    with pytest.raises(InvalidRequest): service.create(2, "B", ["  "])\n'''),
("api_behavior_change", "medium", "medium", "The REST-style ticket endpoint should accept a numeric identifier supplied as text, as it would arrive from a URL path, and return the matching ticket. Non-numeric identifiers should receive a client error.", "test_task_06", '''from miniservice.api import TicketAPI\nfrom miniservice.repository import TicketRepository\nfrom miniservice.service import TicketService\ndef test_task_06():\n    service = TicketService(TicketRepository()); service.create(12, "A")\n    api = TicketAPI(service)\n    assert api.get("12")[0] == 200\n    assert api.get("bad")[0] == 400\n'''),
],
"streamstats": [
("single_file_bug_fix", "easy", "low", "An empty measurement in an imported CSV means the value is unknown, not zero. Preserve missing values so they do not bias group summaries.", "test_task_01", '''from streamstats.parser import parse_rows\ndef test_task_01():\n    rows = parse_rows("timestamp,group,value\\n1,a,\\n2,a,4\\n")\n    assert rows[0].value is None and rows[1].value == 4\n'''),
("missing_function_implementation", "medium", "medium", "Rolling means should average the numeric observations present in each trailing window. Missing values must not count as zero or as an observation; omit a window with no numeric values.", "test_task_02", '''from streamstats.windows import rolling_mean\ndef test_task_02():\n    assert rolling_mean([2.0, None, 6.0, None], 2) == [2.0, 6.0, 6.0]\n'''),
("api_behavior_change", "easy", "low", "The threshold filter is documented as selecting measurements strictly greater than the configured limit. A value exactly on the boundary must not be included.", "test_task_03", '''from streamstats.analytics import above_threshold\nfrom streamstats.models import Sample\ndef test_task_03():\n    rows = [Sample(1, "a", 5), Sample(2, "a", 5.1)]\n    assert above_threshold(rows, 5) == [rows[1]]\n'''),
("deterministic_regression", "easy", "low", "Reports must be stable when samples share a timestamp. Order ties by group name so equivalent input data produces the same output ordering.", "test_task_04", '''from streamstats.models import Sample\nfrom streamstats.ordering import chronological\ndef test_task_04():\n    rows = [Sample(1, "z", 1), Sample(1, "a", 2)]\n    assert [row.group for row in chronological(rows)] == ["a", "z"]\n'''),
("cross_file_change", "medium", "high", "The shared data-cleaning step should discard records with negative timestamps as invalid, while retaining valid zero timestamps and known values.", "test_task_05", '''from streamstats.cleaning import keep_valid\nfrom streamstats.models import Sample\ndef test_task_05():\n    rows = [Sample(-1, "a", 2), Sample(0, "a", 3), Sample(1, "a", None)]\n    assert keep_valid(rows) == [rows[1]]\n'''),
("cross_file_dependency_change", "hard", "high", "The public analytics pipeline must apply the same group-name normalization as direct library callers so equivalent labels do not split one summary into separate groups.", "test_task_06", '''from streamstats.pipeline import run_report\ndef test_task_06():\n    report = run_report("timestamp,group,value\\n1, Alpha ,2\\n2,alpha,4\\n")\n    assert "alpha,2,6,3" in report and " Alpha ,1,2,2" not in report\n'''),
],
"accessflow": [
("cross_file_change", "medium", "high", "Role membership includes transitive parent roles, not only direct parents. Authorization should recognize permissions granted to any ancestor role in the configured role graph.", "test_task_01", '''from accessflow.models import Grant, Principal\nfrom accessflow.policy import is_allowed\ndef test_task_01():\n    user = Principal("sam", ("operator",))\n    parents = {"operator": ("staff",), "staff": ("reader",)}\n    assert is_allowed(user, "read", "doc", [Grant("reader", "read", "doc")], parents)\n'''),
("security_behavior", "medium", "medium", "When matching grants include both allow and deny decisions for the same request, denial must take precedence. Preserve ordinary allow behavior when no matching denial exists.", "test_task_02", '''from accessflow.models import Grant, Principal\nfrom accessflow.policy import is_allowed\ndef test_task_02():\n    user = Principal("sam", ("reader",))\n    grants = [Grant("reader", "read", "doc", "allow"), Grant("sam", "read", "doc", "deny")]\n    assert is_allowed(user, "read", "doc", grants) is False\n'''),
("workflow_behavior_change", "easy", "low", "Approval requests should reject unsupported state changes instead of silently accepting them. Valid transitions such as draft to submitted should continue to work.", "test_task_03", '''import pytest\nfrom accessflow.errors import InvalidTransition\nfrom accessflow.workflow import transition\ndef test_task_03():\n    assert transition("draft", "submitted") == "submitted"\n    with pytest.raises(InvalidTransition): transition("draft", "approved")\n'''),
("regression_fix", "medium", "medium", "A time-limited grant must not authorize access when the caller omits the current time. Treat an unverified expiration as ineligible; non-expiring grants remain usable.", "test_task_04", '''from accessflow.models import Grant, Principal\nfrom accessflow.policy import is_allowed\ndef test_task_04():\n    user = Principal("sam")\n    assert not is_allowed(user, "read", "doc", [Grant("sam", "read", "doc", expires_at=500)])\n    assert is_allowed(user, "read", "doc", [Grant("sam", "read", "doc")])\n'''),
("multi_file_bug_fix", "medium", "high", "A delegated resource scope should include the exact resource and its descendants, but must not match a sibling whose name merely shares the same character prefix.", "test_task_05", '''from accessflow.delegation import resource_matches\ndef test_task_05():\n    assert resource_matches("team/a", "team/a/item")\n    assert resource_matches("team/a", "team/a")\n    assert not resource_matches("team/a", "team/admin")\n'''),
("api_behavior_change", "easy", "low", "Audit consumers need a stable snapshot they cannot mutate accidentally. Return an immutable sequence from the audit snapshot helper.", "test_task_06", '''from accessflow.audit import audit_snapshot\ndef test_task_06():\n    result = audit_snapshot([1, 2])\n    assert result == (1, 2) and isinstance(result, tuple)\n'''),
]}

TASK_DETAILS["configflow"][4] = (
    "cross_file_change", "medium", "medium",
    "Multi-level environment settings should preserve each component of the setting name and remain consistent with explicit nested updates. Correct the behavior so configuration consumers receive the intended hierarchy.",
    "test_task_05", '''from configflow.environment import environment_layer
from configflow.paths import set_nested
def test_task_05():
    assert environment_layer({"APP__HTTP__PORT": "9000"}) == {"http": {"port": "9000"}}
    data = {"http": {"host": "localhost", "port": 8080}, "debug": False}
    assert set_nested(data, "http.port", 9000) == {"http": {"host": "localhost", "port": 9000}, "debug": False}
''')
TASK_DETAILS["miniservice"][2] = (
    "cross_file_change", "medium", "medium",
    "Ticket event sequence values should be monotonic within each ticket's history, even when activity on another ticket occurs between its updates.",
    "test_task_03", '''from miniservice.models import Ticket
from miniservice.reporting import event_sequences
from miniservice.repository import TicketRepository
def test_task_03():
    repo = TicketRepository(); repo.add(Ticket(4, "A")); repo.add(Ticket(5, "B")); repo.replace(Ticket(4, "A", "in_progress"))
    assert event_sequences(repo, 4) == [1, 2]
''')
TASK_DETAILS["miniservice"][4] = (
    "api_behavior_change", "medium", "medium",
    "Ticket tags are returned to API callers as lookup labels. Normalize accepted tags by trimming whitespace and lowercasing them, and reject blank/non-text entries as client errors.",
    "test_task_05", '''from miniservice.api import TicketAPI
from miniservice.repository import TicketRepository
from miniservice.service import TicketService
def test_task_05():
    api = TicketAPI(TicketService(TicketRepository()))
    status, body = api.create(1, "A", [" Urgent ", "OPS"])
    assert status == 201 and body["tags"] == ("urgent", "ops")
    assert api.create(2, "B", ["  "])[0] == 400
''')
TASK_DETAILS["streamstats"][5] = (
    "cross_file_dependency_change", "hard", "high",
    "The public analytics pipeline must apply the same group-name normalization as direct library callers so equivalent labels do not split one summary into separate groups.",
    "test_task_06", '''from streamstats.pipeline import run_report
def test_task_06():
    report = run_report("timestamp,group,value\\n1, Alpha ,2\\n2,alpha,4\\n")
    assert "alpha,2,6,3" in report and " Alpha ,1,2,2" not in report
''')
TASK_DETAILS["accessflow"][4] = (
    "multi_file_bug_fix", "medium", "high",
    "A delegated resource scope should include the exact resource and its descendants, but must not authorize a sibling whose name merely shares the same character prefix.",
    "test_task_05", '''from accessflow.models import Grant, Principal
from accessflow.policy import is_allowed
def test_task_05():
    user = Principal("sam", ("reader",))
    grant = [Grant("reader", "read", "team/a")]
    assert is_allowed(user, "read", "team/a/item", grant)
    assert not is_allowed(user, "read", "team/admin", grant)
''')
TASK_DETAILS["accessflow"][5] = (
    "api_behavior_change", "easy", "low",
    "Audit consumers need a stable snapshot they cannot mutate accidentally. Return an immutable sequence from the service's audit snapshot interface.",
    "test_task_06", '''from accessflow.models import Grant, Principal
from accessflow.service import AccessService
def test_task_06():
    service = AccessService([Grant("reader", "read", "doc")])
    service.authorize(Principal("sam", ("reader",)), "read", "doc")
    result = service.audit_snapshot()
    assert len(result) == 1 and isinstance(result, tuple)
''')
REPOSITORIES["streamstats"]["tasks"][5].update(
    old="    # BUG: the shared group normalizer is not applied on this public path.\\n    samples = keep_valid(parse_rows(text))",
    new="    from .cleaning import normalize_groups\\n    samples = normalize_groups(keep_valid(parse_rows(text)))",
)

for _repo_id, _rows in TASK_DETAILS.items():
    for _row, (_category, _difficulty, _relevance, _description, _test_name, _evaluator) in zip(REPOSITORIES[_repo_id]["tasks"], _rows, strict=True):
        _row.update(category=_category, difficulty=_difficulty, relevance=_relevance,
                    description=_description, test_name=_test_name, evaluator=_evaluator)


def create() -> dict:
    for root in (REPOS, EVALUATORS, REFERENCES, TASKS): root.mkdir(parents=True, exist_ok=True)
    repo_meta = {}
    manifest_tasks = []
    for repo_id, spec in REPOSITORIES.items():
        repo = REPOS / repo_id
        if repo.exists(): remove_generated_repo(repo)
        repo.mkdir(parents=True)
        for relative, text in spec["files"].items():
            target = repo / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            text = "\n".join(line for line in text.splitlines() if "# BUG:" not in line) + "\n"
            target.write_text(text, encoding="utf-8", newline="\n")
        run(["git", "init", "-q"], repo)
        run(["git", "add", "."], repo)
        subprocess.run(["git", "-c", "user.name=Benchmark Author", "-c", "user.email=benchmark@example.invalid",
                        "commit", "-qm", f"Baseline for local benchmark: {repo_id}"], cwd=repo, check=True)
        revision = run(["git", "rev-parse", "HEAD"], repo)
        repo_meta[repo_id] = {"source": repo.relative_to(ROOT.parent).as_posix(), "revision": revision,
                              "package": spec["package"], "task_count": len(spec["tasks"])}
        for row in spec["tasks"]:
            task_id = f"{repo_id.upper()}-{row['suffix']}"
            evaluator_dir = EVALUATORS / task_id
            evaluator_dir.mkdir(parents=True, exist_ok=True)
            evaluator_file = evaluator_dir / "test_acceptance.py"
            evaluator_file.write_text(row["evaluator"], encoding="utf-8", newline="\n")
            reference_dir = REFERENCES / task_id
            reference_target = reference_dir / row["path"]
            reference_target.parent.mkdir(parents=True, exist_ok=True)
            baseline = (repo / row["path"]).read_text(encoding="utf-8")
            old = row["old"].encode("utf-8").decode("unicode_escape")
            old = "\n".join(line for line in old.splitlines() if "# BUG:" not in line)
            new = row["new"].encode("utf-8").decode("unicode_escape")
            if baseline.count(old) != 1:
                raise ValueError(f"Expected one reference hunk for {task_id}; found {baseline.count(old)}")
            fixed = baseline.replace(old, new)
            reference_target.write_text(fixed, encoding="utf-8", newline="\n")
            patch = "".join(difflib.unified_diff(baseline.splitlines(True), fixed.splitlines(True),
                                                   fromfile=f"a/{row['path']}", tofile=f"b/{row['path']}"))
            (reference_dir / "fix.patch").write_text(patch, encoding="utf-8", newline="\n")
            manifest_tasks.append({
                "task_id": task_id, "repository_id": repo_id,
                "repository_source": repo.relative_to(ROOT.parent).as_posix(), "repository_revision": revision,
                "task_category": row["category"], "task_description": row["description"],
                "difficulty": row["difficulty"], "retrieval_relevance": row["relevance"],
                "evaluator_id": task_id,
                "evaluator_command": "python -m pytest -q <controller-evaluator-root>/<evaluator_id>/test_acceptance.py",
                "test_name": row["test_name"], "test_command": "python -m pytest -q",
                "timeout_seconds": 90, "setup_requirements": ["Python ==3.12.4", "pytest ==7.4.4"],
                "expected_evaluation_method": "hidden_pytest_exit_code_zero",
                "independent_from_other_tasks": True, "network_required": False,
            })
    draft = {"schema_version": 1, "status": "draft_not_frozen", "repositories": repo_meta,
             "run_configuration": {"python": "3.12+", "platform": "record at validation/run time",
                                   "variants": ["single", "multi", "multi-mcp", "multi-mcp-repomind"]},
             "tasks": manifest_tasks}
    (TASKS / "manifest.draft.json").write_text(json.dumps(draft, indent=2, ensure_ascii=False) + "\n",
                                               encoding="utf-8", newline="\n")
    return draft


if __name__ == "__main__":
    built = create()
    print(json.dumps({"repositories": len(built["repositories"]), "tasks": len(built["tasks"])}, indent=2))
