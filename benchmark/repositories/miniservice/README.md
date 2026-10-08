# Miniservice

MiniService is a framework-free local ticket service. The API façade presents REST-like status/data pairs, while validation, business transitions, an in-memory repository, immutable records, and operational event reporting are separate modules. This keeps behavior testable without a server or external database.

## Project layout

- `errors.py`: package responsibility for `errors` operations.
- `models.py`: package responsibility for `models` operations.
- `validation.py`: package responsibility for `validation` operations.
- `repository.py`: package responsibility for `repository` operations.
- `service.py`: package responsibility for `service` operations.
- `api.py`: package responsibility for `api` operations.
- `reporting.py`: package responsibility for `reporting` operations.

## Local development

Use Python 3.12.4 and pytest 7.4.4. Run `python -m pytest -q` from this directory. The package has no runtime dependencies and its tests do not call external services.
