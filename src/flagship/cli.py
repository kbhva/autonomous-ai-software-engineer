"""Local CLI entry point for comparable single-agent and multi-agent runs."""

import argparse
import json
import logging
import os
import sys
from dataclasses import asdict
from enum import Enum

from flagship.agent import CodingAgent
from flagship.agents.messages import TaskRunResult
from flagship.model import OpenAIResponsesModel
from flagship.orchestration import Orchestrator
from flagship.tools import PytestTool, RepositoryFileTools


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="flagship", description="Run a bounded AI coding task in a repository.")
    subparsers = parser.add_subparsers(dest="command", required=True)
    run = subparsers.add_parser("run", help="Run a task in single or multi-agent mode")
    run.add_argument("--mode", choices=("single", "multi", "multi-mcp", "multi-mcp-repomind"), default="single", help="Execution architecture")
    run.add_argument("--task", required=True, help="Task description for the coding agent")
    run.add_argument("--repo", required=True, help="Target repository directory")
    run.add_argument("--test-command", help="Optional pytest command, for example 'pytest -q'")
    run.add_argument("--repository-id", default=os.getenv("REPOMIND_REPOSITORY_ID"),
                     help="Explicit RepoMind repository UUID (required in multi-mcp-repomind mode)")
    run.add_argument("--repomind-base-url", default=os.getenv("REPOMIND_BASE_URL"),
                     help="RepoMind service URL (or REPOMIND_BASE_URL)")
    run.add_argument("--repomind-timeout", type=float, default=float(os.getenv("REPOMIND_TIMEOUT_SECONDS", "15")),
                     help="RepoMind request timeout in seconds")
    run.add_argument("--verbose", action="store_true", help="Log tool audit events (never secrets)")
    return parser


def _json_default(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    raise TypeError(f"Cannot serialize {type(value).__name__}")


def main(argv: list[str] | None = None) -> int:
    raw_argv = list(sys.argv[1:] if argv is None else argv)
    # Keep the original Phase 1 invocation working while documenting the new run subcommand.
    if raw_argv and raw_argv[0] != "run" and raw_argv[0] not in {"-h", "--help"}:
        raw_argv.insert(0, "run")
    args = build_parser().parse_args(raw_argv)
    if args.verbose:
        logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        repo = RepositoryFileTools(args.repo)
        pytest_tool = PytestTool(repo.root, int(os.getenv("FLAGSHIP_TEST_TIMEOUT_SECONDS", "120")), args.test_command)
        tools = [repo, pytest_tool]
        model = OpenAIResponsesModel()
        max_tool_calls = int(os.getenv("FLAGSHIP_MAX_TOOL_CALLS", "20"))
        max_repairs = int(os.getenv("FLAGSHIP_MAX_REPAIR_ATTEMPTS", "2"))
        if args.mode == "single":
            agent_result = CodingAgent(model, tools, max_tool_calls, max_repairs).run(args.task)
            result = TaskRunResult(mode="single", success=agent_result.success,
                                   status="DONE" if agent_result.success else "FAILED",
                                   message=agent_result.message, tool_calls=agent_result.tool_calls,
                                   repair_attempts=agent_result.repair_attempts, audit=agent_result.audit,
                                   tool_latency_ms=sum(entry.latency_ms for entry in agent_result.audit),
                                   tool_errors=sum(not entry.success for entry in agent_result.audit),
                                   input_tokens=(model.input_tokens if model.usage_available else None),
                                   output_tokens=(model.output_tokens if model.usage_available else None),
                                   total_tokens=(model.total_tokens if model.usage_available else None),
                                   single_agent=agent_result)
        elif args.mode == "multi":
            max_coding_attempts = int(os.getenv("FLAGSHIP_MAX_CODING_ATTEMPTS", str(max_repairs + 1)))
            result = Orchestrator(model, tools, max_tool_calls, max_coding_attempts, mode="multi").run(args.task)
        elif args.mode == "multi-mcp":
            from flagship.mcp import MCPClient, MCPToolProvider

            max_coding_attempts = int(os.getenv("FLAGSHIP_MAX_CODING_ATTEMPTS", str(max_repairs + 1)))
            provider = MCPToolProvider(MCPClient.for_repository(
                repo.root, test_timeout=pytest_tool.timeout_seconds, test_command=args.test_command))
            result = Orchestrator(model, provider, max_tool_calls, max_coding_attempts,
                                  mode="multi-mcp").run(args.task)
        else:
            from flagship.mcp import MCPClient, MCPToolProvider
            from flagship.repomind import RepoMindRetriever, RepoMindToolProvider
            from flagship.tools.provider import CompositeToolProvider

            if not args.repository_id:
                raise ValueError("--repository-id or REPOMIND_REPOSITORY_ID is required for multi-mcp-repomind")
            if not args.repomind_base_url:
                raise ValueError("--repomind-base-url or REPOMIND_BASE_URL is required for multi-mcp-repomind")
            mcp_provider = MCPToolProvider(MCPClient.for_repository(
                repo.root, test_timeout=pytest_tool.timeout_seconds, test_command=args.test_command))
            retrieval_provider = RepoMindToolProvider(
                RepoMindRetriever(args.repomind_base_url, args.repomind_timeout), args.repository_id)
            provider = CompositeToolProvider([mcp_provider, retrieval_provider])
            max_coding_attempts = int(os.getenv("FLAGSHIP_MAX_CODING_ATTEMPTS", str(max_repairs + 1)))
            result = Orchestrator(model, provider, max_tool_calls, max_coding_attempts,
                                  mode="multi-mcp-repomind", repository_id=args.repository_id).run(args.task)
    except Exception as exc:
        print(f"Error: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(asdict(result), default=_json_default, indent=2, ensure_ascii=False))
    return 0 if result.success else 1


if __name__ == "__main__":
    raise SystemExit(main())
