# Benchmark isolation and evaluator confidentiality audit

**Decision: NOT SAFE to run an untrusted coding agent. Evaluator confidentiality is not defensible in the current architecture or this host setup.** This audit made no benchmark run, LLM call, corpus/evaluator/reference/RepoMind/experiment change, or security configuration change.

## A. Current trust boundary

### Agent process

`BenchmarkHarness.run` (`src/flagship/benchmark/harness.py`) constructs a CLI invocation and starts it with `subprocess.run(..., cwd=workspace, env=env)`. It runs as the current Windows account (`current desktop account` in this session), with the same user token/ACL access as its parent process. The token inspected here reported Low Mandatory Level and the Administrators group as deny-only; this is not a distinct benchmark account or a per-task identity. No Job Object, restricted token, ACL rewrite, container, or VM is created by the harness.

The agent working directory is the assigned workspace, but cwd is not a filesystem boundary. The CLI gets the workspace path in `--repo`, task text in `--task`, and test command in `--test-command`. The benchmark manifest and evaluator ID are not passed as CLI arguments. These omissions do not prevent absolute paths, parent traversal, or Python filesystem access.

The harness starts from `os.environ.copy()`, adds the shared `FLAGSHIP_*` model/budget/timeouts, prepends the Flagship source path to `PYTHONPATH`, and sets or removes `OPENAI_API_KEY` according to the provided `api_key`. D also gets RepoMind URL and UUID in command arguments and environment. Other inherited variables are retained. The CLI's model client and tool providers run in the same agent process. `MCPClient.for_repository` creates an in-process `MCPServer`, not a lower-privilege child process.

The MCP file tools resolve and reject paths outside the repository root, and avoid symlink traversal. This limits those specific tool calls only. Agent code and public tests execute arbitrary Python and bypass those tools. `PytestTool` invokes Python/pytest with `shell=False`, cwd set to the repository, and no replacement environment; pytest and its children inherit the agent environment and user token. `python -c`, Python scripts, imports, pytest plugins/tests, cwd changes, absolute paths, and child processes are not prevented by `shell=False`.

Task workspaces are copied from the local repository by `materialize_clean_workspace`; the copy retains that repository's `.git` data. This creates an independent checkout but no security boundary. The harness accepts the workspace destination from its caller; no ACL is applied.

### Evaluator process

After the agent subprocess exits, `_run_hidden_evaluator` launches a separate pytest subprocess, but under the same Windows account/token. Its cwd is still the task workspace. Its command includes the absolute controller evaluator path. Its environment is copied from the agent environment, with `PYTHONPATH` prepended by the workspace `src` and `PYTHONDONTWRITEBYTECODE=1` added. It imports and executes task code from that workspace in the same Python interpreter that loads the hidden pytest evaluator. The evaluator file is outside the workspace, but not protected from same-user absolute reads; moreover, code under test runs inside the evaluator process and can inspect that process while the evaluator is loaded.

Thus “agent process terminated before evaluator starts” is true, but it does not make the evaluator process safe: the evaluator deliberately executes agent-controlled Python code after loading hidden tests.

### Controller and storage

The controller/harness runs as the same user and under the same filesystem permissions. The controller source is under `src/flagship`; tasks/manifest and validation results are under `benchmark`; hidden evaluators are under `benchmark/evaluators`; references are under `benchmark/reference_fixes`; repository copies are under `benchmark/repositories` in this checkout. There is no OS-level ACL separation between these paths and the task workspace. `BenchmarkHarness.write_record` appends to a caller-supplied JSONL path without enforcing a controller-only directory. No benchmark sweep controller or isolated output store was found.

## B/C. Escape paths and exact risks

A deterministic fake adversarial subprocess was launched with cwd set to the `configflow` task repository. It attempted only to open paths and read zero bytes; it did not print or expose file contents and used only a fake environment marker. It successfully opened:

- a hidden evaluator file;
- a reference patch;
- the task manifest and validation results;
- another task's repository source;
- controller harness source;
- a file in the user profile outside the project;
- an absolute Windows system file.

The same child successfully opened assigned-repository source and public tests, inherited `PATH`, and read a fake `CONTROLLER_FAKE_SECRET` environment marker. Its process returned 0. `PYTHONPATH` was absent from this probe's parent, but the actual harness explicitly adds it. No real secret or file contents were read. The probe therefore demonstrates the core access risk without disclosing protected content.

Additional risks from code inspection:

- Host environment variables, including any configured API key, pass to the agent. The harness explicitly sets `OPENAI_API_KEY`; `PytestTool` then inherits it. Agent-controlled tests can inspect environment variables.
- D's RepoMind URL/UUID are visible to the agent process and its pytest children. No RepoMind auth secret was configured here. Do not put a service credential in this environment.
- Arbitrary Python filesystem access bypasses MCP path checks, including absolute Windows paths and parent directories.
- The same-user process can access sibling task workspaces and controller files when the OS ACL permits it.
- The agent can launch further subprocesses; the harness does not place the process tree in a Job Object or terminate/revoke all descendants before evaluation.
- The evaluator executes candidate code in its own pytest interpreter. Candidate imports can inspect `sys.modules`, stack frames, pytest state, and file paths, and can attempt to read or tamper with evaluator state. A separate evaluator process by itself is insufficient while candidate code is imported in that process.
- Network policy for a future benchmark worker is not enforced by this harness. This session reports `CODEX_SANDBOX_NETWORK_DISABLED=1`, but the adversarial file/environment probe is not an egress test and does not establish a reliable benchmark worker network boundary.

Process enumeration/injection against unrelated Windows processes was not tested. Windows process ACLs and protected-process restrictions vary; do not claim those threats are prevented.

## D. Windows mechanism availability observed here

| Mechanism | Observation | Security assessment |
|---|---|---|
| Windows Sandbox | `WindowsSandbox.exe` absent. Querying optional-feature state failed with access/COM errors, so feature state is not established. | Not available for this run; cannot rely on it. |
| Docker/container | Docker CLI exists with `desktop-linux` context; `docker info` could not reach a daemon. | No functioning container runtime demonstrated. |
| WSL | `wsl --status` returned access denied. | Not usable from this session. |
| Podman | Command unavailable. | Not installed on PATH. |
| Hyper-V | Hyper-V PowerShell cmdlets unavailable; optional-feature query denied. | VM host capability not established. |
| Windows Job Objects | `win32job` and related pywin32 modules are importable. | Useful for process-tree lifetime/resource limits; not a filesystem, identity, or network sandbox. Alone, insufficient. |
| Restricted tokens / ACLs | `win32security` is importable, but current token is not elevated (Administrators is deny-only). No restricted-token+ACL setup was demonstrated. | Possible Windows engineering path, but not currently established or safe to improvise. |
| Separate Windows account | Current task runs as the desktop user; no separate benchmark identity or task ACLs exist. | Could be provisioned by an administrator, but not available as a ready integration here. |

## E./G. Minimum practical architecture

No change was implemented. There is no reliable isolation mechanism already active in this project environment, and implementing restricted-token/ACL orchestration without an elevated, testable host would create false assurance.

Before running an untrusted agent, provide a disposable worker VM or functioning container/Windows Sandbox with:

1. A per-run identity and a read/write mount containing only the assigned repository and public tests. Do not mount the controller checkout, manifest, evaluator, reference fixes, user profile, credentials, Docker socket, or other task workspaces.
2. No inherited host environment. Use an explicit minimal allowlist. Never place provider credentials in the code-execution worker.
3. Network egress disabled for code/test execution. If model or RepoMind service access is required, use a controller-side broker with fixed operations and strict repository scope; the worker must not receive credentials or unrestricted network access.
4. A killable Job Object/process group inside the VM/container, resource limits, and destruction of the disposable environment after each task.
5. Controller-owned, append-only result storage outside the worker. Transfer only bounded run output and a workspace diff/artifact after the worker is stopped.

**Evaluator confidentiality requires an additional architectural change.** Current hidden tests are pytest modules that execute candidate package code in the same interpreter. A VM boundary protects host files, but it does not keep evaluator logic secret from hostile code already running inside that evaluator process. To make Level 2 confidentiality defensible, evaluation must use an out-of-process candidate interface: keep oracle logic in the controller and have it send bounded requests to an isolated candidate worker (CLI/service/RPC), then inspect only responses. The candidate worker must never load evaluator code or see evaluator paths. This requires adapting the evaluation interface/harness; it cannot be achieved by relocating the existing same-process pytest invocation alone. No evaluator was changed in this phase.

## F./H/I. Implementation and validation

No security implementation or persistent security test was added. A transient Python `-c` subprocess probe was used, with a fake environment marker and zero-byte file opens only. Result: all listed controller-owned/project paths, the profile attachment, and the system file were openable from the simulated agent cwd; the fake environment marker and `PATH` were inherited; assigned repository/public test access also worked. No actual evaluator content, reference content, or real secret was read or printed. This is a **failed isolation test**.

Windows availability checks found no usable Sandbox/container/WSL/Podman environment. The only confirmed available primitive, Job Objects, is not a security sandbox. No LLM or benchmark task was executed.

## J/K/L. Limitations and decision

- Egress behavior of a future worker was not tested; this host's Codex session declares network disabled, but the benchmark harness itself does not enforce egress restrictions.
- Access to unrelated process memory was not tested.
- Restricted-token/ACL or separate-account isolation was not configured or verified.
- The evaluator same-interpreter disclosure remains even if a VM is later provisioned.

**Evaluator confidentiality: not defensible now. Benchmark execution: not safe now.** Do not run the benchmark until a real worker boundary is provisioned and validated, and the evaluator/candidate process boundary is redesigned so hostile candidate code cannot inspect hidden evaluator logic. This does not approve freezing the benchmark.
