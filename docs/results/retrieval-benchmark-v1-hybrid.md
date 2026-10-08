# Hybrid Retrieval Benchmark v1 — Experiment 1

## Experiment setup

- **Experiment 0:** vector-only retrieval (frozen baseline).
- **Experiment 1:** hybrid BM25 + dense retrieval.
- Hybrid alpha: **0.5**; K: **5**; queries: 50.
- No benchmark-driven hyperparameter tuning was performed.
- Benchmark SHA-256: `095ab6ad618aa26bcfd49022f7044fa095dc46c1b34085e899d83298acee171d`.
- FastAPI commit: `c3f316b7e814667e8ee81e03a7330d00ee61e45c`.
- Repository identity key: `repomind-fastapi-clean-v1`; derived UUID: `b9e734ef-1538-579f-afce-520e5007a1cc`.
- Model: `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions, `cuda:0`).
- Warm-up used the synthetic query `Synthetic warm-up probe for repository retrieval behavior.` and was excluded from latency.

## Aggregate comparison

| Metric | Experiment 0 vector | Experiment 1 hybrid | Absolute delta (E1 − E0) | Relative change |
|---|---:|---:|---:|---:|
| mean_recall_at_5 | 0.3400 | 0.3400 | +0.0000 | +0.00% |
| mean_precision_at_5 | 0.0920 | 0.0920 | +0.0000 | +0.00% |
| mean_mrr | 0.3390 | 0.3583 | +0.0193 | +5.70% |
| mean_ndcg_at_5 | 0.3031 | 0.3055 | +0.0023 | +0.77% |
| mean_latency_ms | 59.2770 | 2075.3560 | +2016.0790 | +3401.12% |
| median_latency_ms | 58.3595 | 2137.5365 | +2079.1770 | +3562.71% |
| p95_latency_ms | 68.9228 | 2342.7681 | +2273.8453 | +3299.12% |

## Category results

| Category | Queries | E0 Recall@5 | E1 Recall@5 | Recall delta | E1 Precision@5 | E1 MRR | E1 nDCG@5 |
|---|---:|---:|---:|---:|---:|---:|---:|
| api_routing | 6 | 0.0000 | 0.0000 | +0.0000 | 0.0000 | 0.0000 | 0.0000 |
| architecture_docs | 6 | 0.5000 | 0.5000 | +0.0000 | 0.1667 | 0.7222 | 0.5243 |
| behavior | 8 | 0.3750 | 0.3750 | +0.0000 | 0.1250 | 0.4792 | 0.3650 |
| class_lookup | 5 | 0.4000 | 0.4000 | +0.0000 | 0.0800 | 0.4000 | 0.4000 |
| configuration_dependency | 5 | 0.2000 | 0.0000 | -0.2000 | 0.0000 | 0.0000 | 0.0000 |
| cross_file | 7 | 0.2857 | 0.2857 | +0.0000 | 0.1143 | 0.4762 | 0.3066 |
| history | 5 | 1.0000 | 1.0000 | +0.0000 | 0.2000 | 0.7333 | 0.8000 |
| symbol_lookup | 8 | 0.1250 | 0.2500 | +0.1250 | 0.0500 | 0.0938 | 0.1327 |

Category-level comparisons for all metrics are in the JSON artifact.

## Experiment 1 latency

- Mean: 2075.3560 ms; median: 2137.5365 ms; nearest-rank p95: 2342.7681 ms; min/max: 1784.2055/2437.8076 ms.

## Completion and failures

- Query attempts: 50; successful: 50; service errors: 0.
- Full recall: 11; partial recall: 12; zero recall: 27.
- Unusually high latency (strictly above nearest-rank p95): 2.
- Zero-recall query IDs: RMV1-002, RMV1-003, RMV1-005, RMV1-006, RMV1-007, RMV1-008, RMV1-009, RMV1-010, RMV1-011, RMV1-014, RMV1-015, RMV1-016, RMV1-017, RMV1-018, RMV1-019, RMV1-020, RMV1-021, RMV1-022, RMV1-023, RMV1-024, RMV1-025, RMV1-028, RMV1-032, RMV1-035, RMV1-036, RMV1-038, RMV1-041.
- Partial-recall query IDs: RMV1-026, RMV1-027, RMV1-029, RMV1-030, RMV1-033, RMV1-034, RMV1-037, RMV1-039, RMV1-040, RMV1-042, RMV1-044, RMV1-045.
- High-latency query IDs: RMV1-004, RMV1-006.
- Service errors: [].

## Corpus and runtime

- Candidates: 2877; empty/whitespace ignored: 183; documents: 2944; chunks: 15374; commits: 250; ingest failures/skips: 0/0.
- Database: PostgreSQL 17.11 (Debian 17.11-1.pgdg12+2) on x86_64-pc-linux-gnu, compiled by gcc (Debian 12.2.0-14+deb12u1) 12.2.0, 64-bit; pgvector 0.8.6.
- Python 3.12.0; Windows-11-10.0.26200-SP0.

## Reproducibility and interpretation

Per-query ranks, evidence, metrics, category deltas, and exact runtime fingerprints are in `results/retrieval-benchmark-v1-hybrid.json` and `results/retrieval-benchmark-v1-hybrid-manifest.json`. Metrics use the unchanged Experiment 0 source-level projection and definitions. Results are reported as observed; no post-result tuning or retrieval reruns were performed.
