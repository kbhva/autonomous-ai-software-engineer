# Retrieval Benchmark v1

## 1. Experiment Configuration

- RepoMind 0.1.0; Python 3.12.0; model `sentence-transformers/all-MiniLM-L6-v2` (384 dimensions, cuda:0).
- Evaluator K=5 from its unchanged CLI default. The general `TOP_K=20` setting is not used by this evaluator.
- PostgreSQL: PostgreSQL 17.11 (Debian 17.11-1.pgdg12+2) on x86_64-pc-linux-gnu, compiled by gcc (Debian 12.2.0-14+deb12u1) 12.2.0, 64-bit; pgvector extension: 0.8.6; database image digest: `sha256:cf134a767f474095eeba57e0117be8e568e011a63f33fbf252f14c9b760f8e6f`.
- Chunking: --ast: Python AST-aware; fixed-size chunking for other supported text; one chunk per commit. Warm-up: one complete evaluator-defined retrieval request, excluded from query metrics.

## 2. Frozen Benchmark

- Dataset: `eval/eval_set_v1_clean.jsonl`; SHA-256 `095ab6ad618aa26bcfd49022f7044fa095dc46c1b34085e899d83298acee171d`.
- 50 queries; 70 evidence annotations; 68 unique query/source ground-truth references. Duplicate evidence annotations occur only in RMV1-022 (`fastapi\routing.py`) and RMV1-035 (`fastapi\dependencies\utils.py`); each collapses to one source label in metrics.
- FastAPI commit `c3f316b7e814667e8ee81e03a7330d00ee61e45c`; repository key `repomind-fastapi-clean-v1`; UUID `b9e734ef-1538-579f-afce-520e5007a1cc`.

## 3. Repository Corpus

- Files processed: 2877; source documents: 2944; chunks: 15374; commits: 250; ingest failures: 0; reported skips: 0.
- Documents: 2694 file documents and 250 commit documents. Empty/whitespace candidates ignored by ingestion: 183.
- Ingested exactly once into the fresh isolated database. No corpus changes occurred during retrieval.

## 4. Evaluation Method

- Source-level relevance: top-k chunks are projected to unique first-seen source ranks. Duplicate chunks from one source do not add another gain.
- K=5. Recall and Precision use the evaluator's source projection; MRR uses the first relevant projected rank; nDCG uses binary source-level gains.
- Query success rate counts successful vector-search calls. Evidence-complete rate separately counts queries with every labeled source returned.
- Retrieval latency includes query embedding, database retrieval, and result conversion. It excludes model initialization, warm-up, session/setup, container/database startup, and ingestion.

## 5. Aggregate Results

| Measure | Result |
|---|---:|
| Queries completed successfully | 50/50 |
| Query success rate | 100.0% |
| Evidence-complete rate | 24.0% |
| Mean Recall@5 | 0.3400 |
| Mean Precision@5 | 0.0920 |
| Mean MRR | 0.3390 |
| Mean nDCG@5 | 0.3031 |

## 6. Category Results

| Category | Queries | Success | Recall | Precision | MRR | nDCG | Evidence complete |
|---|---:|---:|---:|---:|---:|---:|---:|
| Symbol lookup | 8 | 8 | 0.1250 | 0.0250 | 0.0417 | 0.0625 | 12.5% |
| Class lookup | 5 | 5 | 0.4000 | 0.0800 | 0.4000 | 0.4000 | 40.0% |
| Configuration/dependency | 5 | 5 | 0.2000 | 0.0400 | 0.0400 | 0.0774 | 20.0% |
| API/routing | 6 | 6 | 0.0000 | 0.0000 | 0.0000 | 0.0000 | 0.0% |
| Behavior | 8 | 8 | 0.3750 | 0.1250 | 0.3958 | 0.3266 | 12.5% |
| Cross-file | 7 | 7 | 0.2857 | 0.1143 | 0.3571 | 0.2857 | 14.3% |
| Architecture/documentation | 6 | 6 | 0.5000 | 0.1667 | 0.7500 | 0.5377 | 16.7% |
| History | 5 | 5 | 1.0000 | 0.2000 | 0.8500 | 0.8861 | 100.0% |

## 7. Latency Results

- Count: 50; mean: 59.28 ms; median: 58.36 ms; p95 nearest-rank: 68.92 ms; min: 49.27 ms; max: 97.94 ms.
- Measured boundary: query embedding + database retrieval + result conversion. Excluded: model initialization, warm-up, session/setup, database/container startup, and ingestion.

## 8. Failure Analysis

- Zero relevant sources retrieved: 28 queries: `RMV1-001, RMV1-002, RMV1-003, RMV1-005, RMV1-006, RMV1-007, RMV1-008, RMV1-009, RMV1-010, RMV1-011, RMV1-014, RMV1-015, RMV1-016, RMV1-018, RMV1-019, RMV1-020, RMV1-021, RMV1-022, RMV1-023, RMV1-024, RMV1-025, RMV1-028, RMV1-032, RMV1-033, RMV1-035, RMV1-036, RMV1-038, RMV1-041`.
- Partial recall: 10 queries.
- Successful queries above the observed p95 threshold: 2 (strictly greater than nearest-rank p95).
- Retrieval/service errors: 0.
- Per-query missing sources, failed calls, and latency values are in the result artifact.

## 9. Reproducibility

- Per-query and aggregate result artifact: `docs/results/retrieval-benchmark-v1.json`.
- Reproducibility manifest: `docs/results/retrieval-benchmark-v1-manifest.json`.
- Run interval: 2026-10-08T13:47:20Z – 2026-10-08T13:47:30Z UTC. Evaluator SHA-256: `f7490a5b6050c1a0099fc4e911a5cc8123801e762342c0d5c8650999efdb7e36`; metric implementation SHA-256: `1bc5bd7955a8ea00b4f9e1d0e2ae272a9b7eb3228c9c1ad89053b5a1deeaa7e5`.
- Benchmark and source revisions, corpus counts, runtime/database/model configuration, warm-up, metric definitions, and evaluator fingerprints are captured in the manifest.

## 10. Limitations

- This is one local run on one temporary corpus/database and hardware configuration; it is not a statistical performance guarantee.
- K=5 is the evaluator CLI default. The result is source-level after projection of at most five retrieved chunks; duplicate chunks can leave fewer than five unique sources.
- Failure analysis reports observed top-k misses and does not infer an unobserved rank beyond K.

## 11. Conclusion

This single run completed 50 of 50 retrieval requests. Mean Recall@5 was 0.34 and mean nDCG@5 was 0.30313941887208623; median latency was 58.35950000073353 ms. Interpret these measurements only for this frozen corpus and configuration; no architecture comparison or post-result optimization was performed.
