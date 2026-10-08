# Streamstats

StreamStats is a local CSV analytics package. Parsing, cleaning, rolling windows, filtering, grouping, stable ordering, and report rendering are separate operations composed by a pipeline. All calculations use in-memory deterministic inputs; no data service or network access is needed.

## Project layout

- `models.py`: package responsibility for `models` operations.
- `parser.py`: package responsibility for `parser` operations.
- `cleaning.py`: package responsibility for `cleaning` operations.
- `windows.py`: package responsibility for `windows` operations.
- `analytics.py`: package responsibility for `analytics` operations.
- `report.py`: package responsibility for `report` operations.
- `pipeline.py`: package responsibility for `pipeline` operations.
- `ordering.py`: package responsibility for `ordering` operations.

## Local development

Use Python 3.12.4 and pytest 7.4.4. Run `python -m pytest -q` from this directory. The package has no runtime dependencies and its tests do not call external services.
