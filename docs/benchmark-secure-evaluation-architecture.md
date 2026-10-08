# Secure evaluation boundary design

**Status: design only. No benchmark task, evaluator, reference fix, RepoMind code, or experiment was changed. No LLM or A/B/C/D task was run. The benchmark must remain unexecuted and unfrozen.**

## A. Current execution and evaluator interface

`materialize_clean_workspace` copies/clones a repository at its pinned revision and checks the initial Git state. It creates a fresh checkout, not a security boundary. `BenchmarkHarness.run` starts `python -m flagship.cli run` with `cwd=workspace`, the workspace in `--repo`, task text and test command in argv, and an environment copied from the controller. The controller source and other benchmark files are not passed as CLI args, but OS access controls do not confine the process to its cwd.

The CLI creates the model and tool providers in the agent process. In C/D, `MCPClient.for_repository` creates an in-process MCP server. `run_tests` starts pytest/Python with the same user and inherited environment. MCP root checks apply only to the MCP file tools; they do not sandbox Python/pytest.

After the agent subprocess exits, `_run_hidden_evaluator` selects `<evaluator_root>/<evaluator_id>/test_acceptance.py` and starts `python -m pytest -q <absolute evaluator path>`. The evaluator subprocess runs with cwd still set to the candidate workspace, and `PYTHONPATH` includes `<workspace>/src`. It runs under the same Windows account and environment lineage. Pytest loads the hidden evaluator and candidate package in the same interpreter. Its exit code becomes the evaluator result.

The minimum controller API could be `evaluate(task_id, artifact_digest, artifact_location) -> {status, bounded_diagnostics}`. The task ID selects controller-owned evaluation policy; the evaluator never accepts an evaluator path or evaluator code from the worker. Current evaluators directly import/call Python candidate modules, so this API is not a drop-in wrapper: a separate candidate process interface is needed.

## B. Threat model

**Level 1, honest but buggy:** accidental path traversal through provided file tools, unexpected test commands, test hangs, and contaminated outputs. Current application-level checks catch some tool misuse, but do not constrain code run by pytest.

**Level 2, hostile or adversarial candidate code:** absolute and parent-relative reads, environment inspection, child-process creation, cwd changes, network attempts, reading sibling workspaces/controller files, and probing or tampering with evaluator runtime. This is the minimum threat level for benchmark confidentiality.

Protect: evaluator logic/files, reference fixes, manifests/labels, controller source, credentials, unrelated user files, and other task workspaces. Do not promise protection against hypervisor/kernel vulnerabilities or timing side channels; resource exhaustion must be controlled separately.

## C. Isolation options

| Option | Filesystem | Environment/credentials | Network | Process boundary | Windows fit here | Complexity/reproducibility/overhead | Limits |
|---|---|---|---|---|---|---|---|
| **A. Disposable VM** | Separate guest disk; only task input and artifact channel shared | Fresh allowlist; no host credentials | Guest firewall/network-off by default | Separate kernel and process namespace | Windows Sandbox/Hyper-V not verified here; cloud Linux VM is practical | High setup; image snapshot is reproducible; boot/teardown overhead highest | Hypervisor/guest escape risk; does not alone protect evaluator logic if candidate code is loaded into its process |
| **B. Container** | Namespaces/mounts; read-only image and one writable task mount | Explicit environment; no host env or Docker socket | `--network=none` or controlled broker | Process namespace; shared host kernel | Docker CLI exists but daemon is unavailable; Linux CI is a good target | Medium setup; image digest is reproducible; low/medium overhead | Shared kernel and daemon/mount misconfiguration; candidate/evaluator process separation still required |
| **C. Separate processes and OS identities** | DACL/ACL allow only worker identity on task dir; controller dirs deny it | Distinct service accounts and explicit env allowlist | Host firewall policy per worker identity | Separate processes, same kernel; Job Object only for lifetime/resources | Technically possible with admin provisioning; not configured or verified here | High Windows-specific ACL/token/service work; reproducible only with automated provisioning; low runtime overhead | Same-kernel attack surface; ACL/token mistakes; plain subprocess separation provides no isolation |

## D–F. Recommendation and trust boundaries

Use an **ephemeral Linux CI runner/VM** as the trusted controller, and a fresh, unprivileged sandbox worker per agent run. For Level 2, prefer a microVM-backed worker (or a hardened Linux container inside an ephemeral VM); a plain shared-kernel Docker container is a weaker boundary. The worker gets only a clean repository snapshot, public tests, pinned runtime, and tool endpoint. No host mounts, controller checkout, manifest, evaluator, reference files, other workspace, provider key, or broad environment.

Keep model orchestration and provider credentials in the controller. It sends validated, bounded tool requests to the worker; the worker returns untrusted results. The worker may modify its repository and run public tests, but it cannot send arbitrary shell commands to the controller. The controller validates every response and enforces call/time/output budgets. Worker network egress is off.

For evaluation, the controller starts a separate candidate runtime from the returned artifact. The hidden evaluator remains only in a controller-owned evaluator service/process. It calls the candidate through a narrow task-specific RPC or CLI protocol; candidate code executes only in the untrusted candidate process. The evaluator process must never import candidate modules, load candidate plugins, or expose evaluator file paths to the candidate. It returns a bounded status/diagnostic record, not evaluator source or test internals.

The current pytest evaluators directly call Python package APIs, so they cannot safely run unchanged inside the evaluator process. Preserving benchmark semantics requires translating each evaluator’s inputs/assertions into controller-side checks over the candidate RPC interface and validating parity against the same baseline/reference outcomes. That is a design prerequisite, not work performed here.

## G. Model and RepoMind brokers

**Model:** the existing `OpenAIResponsesModel` is constructed inside the CLI agent process, so the current design requires provider access and exposes the API key to that process. Move the orchestration/model call loop to the trusted controller. The controller validates tool calls and dispatches only allowlisted MCP operations to the worker. This keeps keys out of worker environment. Responses/tool output are untrusted input to the controller and must be treated as data, never executed as controller code.

**RepoMind:** D can use a controller-side broker with a fixed per-task repository UUID, query/top-k limits, allowlisted endpoint, and filtered evidence response. The worker receives only the authorized evidence. It gets neither broad RepoMind credentials nor direct service/network access. This is architecturally feasible, but not implemented; current `RepoMindRetriever` is constructed in the CLI process and calls the HTTP endpoint directly.

Benchmark repositories and public tests need no arbitrary network access. A model call does require provider connectivity; D retrieval requires RepoMind connectivity. Broker these capabilities from the controller instead of enabling worker egress.

## H. One-way artifact transfer

1. Worker exports the assigned repository tree after agent exit; the controller kills the worker/process tree before accepting the artifact.
2. Use a bounded archive (for example, tar with normalized POSIX paths) containing only regular files under the assigned repository. Exclude `.git`, caches, virtual environments, sockets, devices, and controller paths. Reject symlinks/hardlinks, absolute paths, `..`, drive prefixes, alternate data streams, case-fold collisions, and unsupported file types.
3. Apply provisional caps appropriate to these small repositories: 50 MiB compressed, 200 MiB expanded, 10,000 files. Reject archives exceeding caps and adjust only after measuring the unchanged baseline repositories.
4. Hash the archive with SHA-256; record digest, task ID, base revision, and worker image digest. Extract into a fresh controller-owned directory using safe path checks. Normalize permissions; do not preserve worker ACLs or executable bits by default.
5. Evaluator receives a read-only extracted snapshot plus a separate writable temp/output area if required. No artifact/evaluator exchange returns to the agent. Destroy worker and temporary evaluation environment after recording bounded results.

An alternative patch artifact is smaller but has its own path/parser hazards; the archive requires strict safe extraction. Neither artifact format is a sandbox by itself.

## I–J. Environment feasibility

This Windows host is not a verified worker host: Windows Sandbox executable absent; optional-feature checks denied; Docker daemon unavailable; WSL access denied; Podman and Hyper-V cmdlets unavailable. Job Objects are present but insufficient alone. Therefore **do not run the benchmark locally on this host**.

Require a reproducible Linux CI environment with ephemeral VM-backed workers. Pin the base image by digest, Python/pytest versions, dependencies, and toolchain. Run each of the eventual 96 agent executions in a clean worker; disable egress; use a broker for model/RepoMind. Store outputs in controller-owned artifact storage. Run evaluator logic in controller services that communicate with isolated candidate processes through task-specific protocols. A dedicated ephemeral VM/runner is preferable to a persistent self-hosted runner.

## K–L. Prototype and adversarial checks

No secure evaluator-boundary implementation was attempted because this host has no verified isolation primitive, and process separation alone is not a boundary. A transient candidate/controller-process diagnostic used only fake sentinels in a temporary directory under the task repository; it removed the directory afterward. Candidate code ran arbitrary Python and **could** read the fake evaluator sentinel by absolute and parent-relative path. A child subprocess could read it too. A fake environment marker was visible when inherited. The test directory was confirmed removed; no real evaluator/reference contents or secrets were used. This was not a full evaluator RPC prototype: it did not instantiate a second evaluator service. It tested whether a separate candidate subprocess under the same user could access controller-owned sentinel paths. It could. The probe did not attempt to hide the fake sentinel with OS permissions and therefore proves process separation alone is insufficient; it does not validate the recommended VM/worker architecture.

This is a **failed process-only prototype**, not a secure design proof. The earlier audit’s zero-byte access probe also confirmed reads were permitted for the real controller paths; it did not read file contents. Legitimate access to assigned files/public tests worked. No filesystem access barrier was demonstrated.

No LLM, benchmark task, A/B/C/D, live RepoMind request, or hidden evaluator run occurred.

## M. Files changed

Only this architecture document was added: `docs/benchmark-secure-evaluation-architecture.md`. No source code or benchmark assets were changed in this phase.

## N–O. Limitations, decisions, and prerequisites

- This host cannot provide a verified disposable worker today.
- The process-only experiment proves separate processes under one user do not block filesystem reads.
- Existing evaluators share an interpreter with candidate code; evaluator confidentiality requires a new candidate/evaluator RPC boundary and semantic parity validation.
- Candidate code may observe the inputs it must process during evaluation and may attempt to infer task behavior. Keep evaluator diagnostics bounded and never return evaluator source/test details.
- A broker and worker protocol introduce new trusted code that needs its own review and adversarial tests.
- Network egress and process-handle attacks were not validated on a future worker because none is available.

**Answers:** (1) No, the current benchmark is not safe on this Windows host. (2) Use an ephemeral Linux CI VM with isolated workers; do not use this local process model. (3) Minimum: trusted controller, per-run disposable worker, no worker secrets/network/mounts, model and RepoMind brokers, one-way hashed artifact transfer, and evaluator-to-candidate RPC that never loads candidate code in the evaluator process. (4) Yes, keep the 24 tasks, revisions, and intended evaluator assertions unchanged; adapt the evaluation interface and verify behavioral parity before any run. No freeze is authorized by this design.
