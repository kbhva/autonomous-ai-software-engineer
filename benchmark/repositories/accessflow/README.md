# Accessflow

AccessFlow is an in-memory authorization and approval-workflow library. Principals carry roles, a role graph provides inherited membership, grants define scoped allow/deny decisions, a state graph controls workflow, and service methods produce audit records. It requires no identity provider or external database.

## Project layout

- `models.py`: package responsibility for `models` operations.
- `roles.py`: package responsibility for `roles` operations.
- `policy.py`: package responsibility for `policy` operations.
- `workflow.py`: package responsibility for `workflow` operations.
- `errors.py`: package responsibility for `errors` operations.
- `service.py`: package responsibility for `service` operations.
- `delegation.py`: package responsibility for `delegation` operations.
- `audit.py`: package responsibility for `audit` operations.

## Local development

Use Python 3.12.4 and pytest 7.4.4. Run `python -m pytest -q` from this directory. The package has no runtime dependencies and its tests do not call external services.
