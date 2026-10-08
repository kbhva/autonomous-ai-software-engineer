# Agent benchmark v1 — task label review (draft)

This document records the post-audit difficulty and retrieval-relevance judgments. Difficulty reflects the reasoning burden on these small repositories, not observed agent outcomes. Retrieval relevance estimates whether repository context could help; it is not a result metric. The benchmark remains draft and no agent runs informed these labels.

| Task | Difficulty | Retrieval relevance | Rationale |
|---|---|---|---|
| CONFIGFLOW-01 | easy | low | One boolean parser; supported tokens and errors are explicit in the prompt and constants. |
| CONFIGFLOW-02 | medium | medium | Requires tracing settings composition across service, environment, and merge modules; precedence is explicit. |
| CONFIGFLOW-03 | easy | low | One numeric boundary in a validation helper with an existing domain error. |
| CONFIGFLOW-04 | easy | low | Redaction policy is a local helper change; security significance does not make code navigation difficult. |
| CONFIGFLOW-05 | medium | medium | Environment construction and explicit dotted updates share a nested-path helper; sibling preservation matters. |
| CONFIGFLOW-06 | medium | high | Profile resolution must recurse and deep-merge through a chain; relevant behavior is split between profiles and merge modules. The small package and explicit contract do not justify hard. |
| MINISERVICE-01 | easy | low | Deliberate local input-normalization baseline in one validation helper. |
| MINISERVICE-02 | medium | medium | Must enforce the service transition table and preserve ticket state on rejection. |
| MINISERVICE-03 | medium | high | Requires connecting repository-wide event storage with per-ticket reporting across interleaved events. Label raised from medium because the interaction is central to the contract. |
| MINISERVICE-04 | easy | medium | Several invalid values must cross validation and API error mapping, but the supported cases and response are explicit. Relevance raised from low for that integration path. |
| MINISERVICE-05 | medium | medium | Tag validation and normalization must flow through service creation and API error mapping without creating an invalid ticket. |
| MINISERVICE-06 | easy | low | A local API/repository identifier conversion with explicit success and error behavior; difficulty and relevance lowered from medium. |
| STREAMSTATS-01 | easy | medium | The behavior crosses CSV parsing, missing-value cleaning, aggregation, and public reporting; implementation is simple but context helps verify the full effect. Relevance raised from low. |
| STREAMSTATS-02 | medium | low | Rolling-window edge cases require algorithmic care, but the helper is standalone and its contract is in its docstring/prompt. Relevance lowered from medium. |
| STREAMSTATS-03 | easy | low | One comparison boundary in a documented helper; retained as a local easy task. |
| STREAMSTATS-04 | easy | low | One deterministic ordering key backed by the helper docstring; retained as an intentional easy deterministic-output anchor. |
| STREAMSTATS-05 | medium | medium | A shared cleaning rule must be verified through the public pipeline/report; lowered from high because only one shared helper and one consumer path are involved. |
| STREAMSTATS-06 | medium | high | Requires finding and integrating existing group normalization into pipeline composition and preserving aggregation; changed from hard because the repository and contract are small and explicit. |
| ACCESSFLOW-01 | medium | high | Role inheritance must be traversed and used by policy evaluation; a deeper acyclic chain is relevant, while cycles are outside the defined contract. |
| ACCESSFLOW-02 | medium | medium | Policy must combine matching allow/deny grants independently of grant order and preserve ordinary allow; behavior is local to policy evaluation. |
| ACCESSFLOW-03 | easy | low | A documented transition table in one workflow helper; retained as a local state-machine example. |
| ACCESSFLOW-04 | medium | low | Expiration eligibility is a local policy condition; lowered from medium relevance because no cross-module search is needed. |
| ACCESSFLOW-05 | medium | high | Policy delegates resource-scope matching to a helper; exact, descendant, and boundary cases exercise the policy path. |
| ACCESSFLOW-06 | easy | low | Service-to-audit snapshot path is short; the contract is immutable behavior, without prescribing tuple as the implementation. |

Current draft distribution: difficulty **11 easy / 13 medium / 0 hard**; retrieval relevance **11 low / 8 medium / 5 high**. These are pre-run estimates and must not be presented as measured task difficulty or retrieval benefit.
