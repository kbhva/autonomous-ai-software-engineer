# Configflow

ConfigFlow is a local CLI configuration package. Settings flow from defaults through a TOML/JSON-like file layer and environment overrides into validated runtime options. The package keeps parsing, precedence, validation, profiles, secret-safe diagnostics, and nested-key manipulation in separate modules so callers can share the same rules.

## Project layout

- `errors.py`: package responsibility for `errors` operations.
- `environment.py`: package responsibility for `environment` operations.
- `merge.py`: package responsibility for `merge` operations.
- `validation.py`: package responsibility for `validation` operations.
- `secrets.py`: package responsibility for `secrets` operations.
- `paths.py`: package responsibility for `paths` operations.
- `profiles.py`: package responsibility for `profiles` operations.
- `service.py`: package responsibility for `service` operations.

## Local development

Use Python 3.12.4 and pytest 7.4.4. Run `python -m pytest -q` from this directory. The package has no runtime dependencies and its tests do not call external services.
