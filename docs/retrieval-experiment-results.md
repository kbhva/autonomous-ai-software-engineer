# Retrieval experiment results

These are one-run retrieval measurements on a frozen 50-query FastAPI corpus with source-level evaluation at K=5. They measure retrieval only; they do not measure coding-agent task success, tokens, or end-to-end coding latency. The reports and machine-readable artifacts are in [`docs/results/`](results/README.md).

The public repository contains the reports, result artifacts, and manifests, but not the complete evaluation query set, evaluator implementation, or RepoMind source/runtime environment. The manifests record hashes and configuration, but those records do not make the experiment fully independently reproducible from a fresh clone. Reproducing it independently is currently limited by those missing inputs. These results do not measure agent token or cost efficiency.

## Experiment 0 — vector retrieval baseline

| Metric | Result |
| --- | ---: |
| Mean Recall@5 | 0.3400 |
| Mean Precision@5 | 0.0920 |
| Mean MRR | 0.3390 |
| Mean nDCG@5 | 0.3031 |
| Mean retrieval latency | 59.277 ms |
| P95 retrieval latency | 68.923 ms |

The run completed 50/50 queries. Latency includes query embedding, database retrieval, and result conversion; it excludes model initialization, warm-up, setup, database/container startup, and ingestion.

## Experiment 1 — hybrid BM25 + dense retrieval

| Metric | Experiment 0 | Experiment 1 | Change |
| --- | ---: | ---: | ---: |
| Mean Recall@5 | 0.3400 | 0.3400 | 0.0000 |
| Mean Precision@5 | 0.0920 | 0.0920 | 0.0000 |
| Mean MRR | 0.3390 | 0.3583 | +0.0193 (+5.70%) |
| Mean nDCG@5 | 0.3031 | 0.3055 | +0.0023 (+0.77%) |
| Mean retrieval latency | 59.277 ms | 2075.356 ms | +2016.079 ms (+3401.12%) |
| P95 retrieval latency | 68.923 ms | 2342.768 ms | +2273.845 ms |

Both runs completed 50/50 queries. Hybrid retrieval modestly improved ranking metrics (MRR and nDCG), but did not improve Recall@5 or Precision@5 and introduced a very large latency cost. It was not an overall improvement under this measured quality/latency trade-off. This is a single measured run, not a statistical performance guarantee.

## Autonomous coding benchmark

**Not executed.** The 24-task benchmark was designed and oracle-validated, but remains a draft and was not run with an LLM. Its Windows execution model did not provide sufficient isolation between candidate code, hidden evaluators, the controller, and the host filesystem/environment. See the [isolation audit](benchmark-isolation-security-audit.md) and [proposed secure architecture](benchmark-secure-evaluation-architecture.md). No A/B/C/D success rates or comparative agent-performance claims are available.
