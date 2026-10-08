# Agent benchmark v1 — task catalog (draft)

> **DRAFT — NOT FROZEN.** No coding-agent benchmark has been run.

Tasks: **24** across four local repositories. Draft manifest SHA-256: `b087c4211c5ee9f0e0baa07581a3dc5d9fe8ffb473785fde474673c40ba8b3d2`.

Task labels and their pre-run rationale are recorded in [the label review](agent-benchmark-v1-task-labels.md). Hidden evaluator files and reference fixes are controller-only artifacts; do not include them in agent workspaces or task prompts.

## CONFIGFLOW-01 — configflow

- **Category:** `api_behavior_change`
- **Difficulty:** `easy`
- **Retrieval relevance:** `low`
- **Evaluator:** `CONFIGFLOW-01` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

Parse native booleans unchanged and accept only the textual spellings 1, true, yes, on and 0, false, no, off. Text matching is case-insensitive and ignores surrounding whitespace. Raise ValueError for other values.

## CONFIGFLOW-02 — configflow

- **Category:** `configuration_dependency_change`
- **Difficulty:** `medium`
- **Retrieval relevance:** `medium`
- **Evaluator:** `CONFIGFLOW-02` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

Environment overrides are intended to take precedence over saved configuration, while unspecified settings continue to inherit from defaults. Make settings resolution follow that precedence rule consistently.

## CONFIGFLOW-03 — configflow

- **Category:** `regression_fix`
- **Difficulty:** `easy`
- **Retrieval relevance:** `low`
- **Evaluator:** `CONFIGFLOW-03` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

A zero or negative request timeout can currently enter runtime settings and cause confusing downstream behavior. Reject non-positive timeout values with the package's configuration error.

## CONFIGFLOW-04 — configflow

- **Category:** `security_behavior`
- **Difficulty:** `easy`
- **Retrieval relevance:** `low`
- **Evaluator:** `CONFIGFLOW-04` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

Diagnostic settings may contain credential fields with qualified names such as `database_password` or `service_api_key`. Ensure the shared redaction helper protects those values while preserving ordinary settings.

## CONFIGFLOW-05 — configflow

- **Category:** `cross_file_change`
- **Difficulty:** `medium`
- **Retrieval relevance:** `medium`
- **Evaluator:** `CONFIGFLOW-05` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

Environment keys with multiple double-underscore-separated components must produce the same nested setting hierarchy as explicit dotted-path updates. Correct the shared path behavior so updating one nested setting preserves its sibling settings.

## CONFIGFLOW-06 — configflow

- **Category:** `cross_file_dependency_change`
- **Difficulty:** `medium`
- **Retrieval relevance:** `high`
- **Evaluator:** `CONFIGFLOW-06` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

Named settings profiles can extend a parent profile, which can itself extend another profile. Resolve the inheritance chain before applying child values, deep-merge nested mappings, and retain unrelated parent settings. A missing parent continues to raise KeyError.

## MINISERVICE-01 — miniservice

- **Category:** `single_file_bug_fix`
- **Difficulty:** `easy`
- **Retrieval relevance:** `low`
- **Evaluator:** `MINISERVICE-01` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

Ticket titles should be displayed and searched consistently even when a request contains repeated internal whitespace. Normalize runs of whitespace to a single space when accepting a title.

## MINISERVICE-02 — miniservice

- **Category:** `api_behavior_change`
- **Difficulty:** `medium`
- **Retrieval relevance:** `medium`
- **Evaluator:** `MINISERVICE-02` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

Ticket lifecycle changes must follow the supported workflow. Reject a transition that is not allowed from the current status and leave the ticket unchanged.

## MINISERVICE-03 — miniservice

- **Category:** `cross_file_change`
- **Difficulty:** `medium`
- **Retrieval relevance:** `high`
- **Evaluator:** `MINISERVICE-03` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

Event sequence values must be contiguous per ticket, beginning at 1 for its creation event and increasing by 1 for each update, even when events for other tickets are interleaved.

## MINISERVICE-04 — miniservice

- **Category:** `regression_fix`
- **Difficulty:** `easy`
- **Retrieval relevance:** `medium`
- **Evaluator:** `MINISERVICE-04` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

Malformed or out-of-range pagination values must be returned as client errors by the REST-style façade, while valid integer or numeric-text page and size values continue to work.

## MINISERVICE-05 — miniservice

- **Category:** `api_behavior_change`
- **Difficulty:** `medium`
- **Retrieval relevance:** `medium`
- **Evaluator:** `MINISERVICE-05` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

Ticket tags are returned to API callers as lookup labels. Normalize accepted tags by trimming whitespace and lowercasing them, and reject blank/non-text entries as client errors.

## MINISERVICE-06 — miniservice

- **Category:** `api_behavior_change`
- **Difficulty:** `easy`
- **Retrieval relevance:** `low`
- **Evaluator:** `MINISERVICE-06` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

The REST-style ticket endpoint should accept a numeric identifier supplied as text, as it would arrive from a URL path, and return the matching ticket. Non-numeric identifiers should receive a client error.

## STREAMSTATS-01 — streamstats

- **Category:** `single_file_bug_fix`
- **Difficulty:** `easy`
- **Retrieval relevance:** `medium`
- **Evaluator:** `STREAMSTATS-01` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

An empty measurement in an imported CSV means the value is unknown, not zero. Preserve missing values so they do not bias group summaries.

## STREAMSTATS-02 — streamstats

- **Category:** `missing_function_implementation`
- **Difficulty:** `medium`
- **Retrieval relevance:** `low`
- **Evaluator:** `STREAMSTATS-02` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

Rolling means should average the numeric observations present in each trailing window. Missing values must not count as zero or as an observation; omit a window with no numeric values.

## STREAMSTATS-03 — streamstats

- **Category:** `api_behavior_change`
- **Difficulty:** `easy`
- **Retrieval relevance:** `low`
- **Evaluator:** `STREAMSTATS-03` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

The threshold filter is documented as selecting measurements strictly greater than the configured limit. A value exactly on the boundary must not be included.

## STREAMSTATS-04 — streamstats

- **Category:** `deterministic_regression`
- **Difficulty:** `easy`
- **Retrieval relevance:** `low`
- **Evaluator:** `STREAMSTATS-04` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

Chronological sample ordering must break equal-timestamp ties by group name, as specified by the ordering helper's contract.

## STREAMSTATS-05 — streamstats

- **Category:** `cross_file_change`
- **Difficulty:** `medium`
- **Retrieval relevance:** `medium`
- **Evaluator:** `STREAMSTATS-05` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

The shared data-cleaning step should discard records with negative timestamps as invalid, while retaining valid zero timestamps and known values.

## STREAMSTATS-06 — streamstats

- **Category:** `cross_file_dependency_change`
- **Difficulty:** `medium`
- **Retrieval relevance:** `high`
- **Evaluator:** `STREAMSTATS-06` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

The public analytics pipeline must apply the existing group-name normalization used by direct library callers. Trim surrounding whitespace and ignore case so equivalent labels aggregate together without changing their measurement values.

## ACCESSFLOW-01 — accessflow

- **Category:** `cross_file_change`
- **Difficulty:** `medium`
- **Retrieval relevance:** `high`
- **Evaluator:** `ACCESSFLOW-01` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

Role membership includes transitive parent roles, not only direct parents. Authorization should recognize permissions granted to any ancestor role in the configured role graph.

## ACCESSFLOW-02 — accessflow

- **Category:** `security_behavior`
- **Difficulty:** `medium`
- **Retrieval relevance:** `medium`
- **Evaluator:** `ACCESSFLOW-02` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

When matching grants include both allow and deny decisions for the same request, denial must take precedence. Preserve ordinary allow behavior when no matching denial exists.

## ACCESSFLOW-03 — accessflow

- **Category:** `workflow_behavior_change`
- **Difficulty:** `easy`
- **Retrieval relevance:** `low`
- **Evaluator:** `ACCESSFLOW-03` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

Approval requests should reject unsupported state changes instead of silently accepting them. Valid transitions such as draft to submitted should continue to work.

## ACCESSFLOW-04 — accessflow

- **Category:** `regression_fix`
- **Difficulty:** `medium`
- **Retrieval relevance:** `low`
- **Evaluator:** `ACCESSFLOW-04` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

A time-limited grant must not authorize access when the caller omits the current time. Treat an unverified expiration as ineligible; non-expiring grants remain usable.

## ACCESSFLOW-05 — accessflow

- **Category:** `multi_file_bug_fix`
- **Difficulty:** `medium`
- **Retrieval relevance:** `high`
- **Evaluator:** `ACCESSFLOW-05` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

A delegated resource scope should include the exact resource and its descendants, but must not authorize a sibling whose name merely shares the same character prefix.

## ACCESSFLOW-06 — accessflow

- **Category:** `api_behavior_change`
- **Difficulty:** `easy`
- **Retrieval relevance:** `low`
- **Evaluator:** `ACCESSFLOW-06` (external to agent workspace)
- **Oracle validation:** baseline failed in test body (exit 1); private reference passed (exit 0) twice with deterministic status. **VALID oracle pair.**

**Agent task prompt**

Callers must not be able to mutate the audit snapshot returned by the service, and attempted mutation must not affect later snapshots.

Oracle validity is corpus validation only, not coding-agent performance evidence.
