# Retrieval result artifacts

The reports, per-query JSON results, and manifests below were copied from the known RepoMind project checkout. They document the single-run Experiment 0 vector baseline and Experiment 1 hybrid BM25+dense run summarized in [retrieval-experiment-results.md](../retrieval-experiment-results.md).

These public artifacts preserve reported metrics and run metadata, but the repository does not include the complete evaluation query set, evaluator implementation, or RepoMind source/runtime environment. The recorded hashes and configuration support provenance checks; they are not sufficient for full independent reproduction from a fresh clone.

The hybrid JSON source contained retrieved source excerpts, including email-like addresses. Retrieved excerpt text was omitted from the public JSON artifacts to avoid redistributing corpus text; query, ranking, metric, and latency fields are unchanged. The hybrid manifest records both the original source artifact hash and the hash of this sanitized public artifact. Absolute local result paths in the Markdown reports were replaced with `docs/results/` references. The reported measurements were not recalculated or modified.

These are retrieval results only. They are not autonomous coding-agent benchmark results. The 24-task end-to-end A/B/C/D coding benchmark was **not executed**.
