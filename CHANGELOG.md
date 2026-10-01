# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.4.0] - 2026-10-01

### Security
- Mock server conditions no longer use `eval`. In 1.3.0, a path parameter
  value was pasted into the expression text, so any request to an endpoint
  with `conditions` could run arbitrary Python on the server. Conditions are
  now parsed once against an allow-list of comparisons and boolean logic, and
  parameter values are only ever compared as data.
- Path parameter substitution in mock responses now works on the parsed body
  instead of serialized JSON. A URL value could previously inject extra keys
  into a response or cause a 500 error.
- `postpy mock run --debug` no longer enables Werkzeug's interactive debugger.
- `postpy mock run` warns when the server is bound to a non-loopback host.
- `.env` files are read without `${VAR}` expansion, so a collection cannot pull
  in unrelated environment variables.

### Fixed
- The `postpy` command only exposed `mock`. `run-collection`,
  `show-collection` and `show-history` are now available.
- `run-collection` now runs each request's `tests` and exits with status 1 on
  any failure. Previously assertions were never checked and errors exited 0.
- `show-history` always reported no history because nothing was saved. History
  is now stored per collection.
- The documented `response: {status_code, body}` mock format was served
  literally with status 200. It now sets the status and body as documented.
  The older layout still works.
- `postpy mock init` no longer overwrites an existing file unless `--force` is
  given, and it writes the documented format.
- Rich markup in response bodies or names (e.g. `[/posts]`) no longer crashes
  the CLI or changes its output.
- Malformed `.env` lines, JSON array responses in `json_field_equals`, and
  invalid collection or mock files now produce clear errors instead of
  tracebacks.
- Requests now time out (default 30 s, `--timeout`) instead of hanging.
- Variables are substituted in endpoints, the base URL and nested bodies, not
  only in top-level body fields.
- The version is now reported consistently. `postpy --version`,
  `postpy.__version__`, `setup.py` and `pyproject.toml` previously disagreed.
- The README's `pip install postpy` installed an unrelated PyPI package. It now
  points to GitHub.

### Added
- `PostPy` Python client, as shown in the README, with `get`/`post`/...,
  `load_collection()`, `execute()` and `run()`.
- Mock endpoints support response `headers`, empty bodies, raw text bodies, and
  `PUT`/`PATCH`/`DELETE`.
- Mock config validation at start-up, with field-level messages, and an
  endpoint table in the start-up output.
- JSON 404 and 405 responses from the mock server.
- `json_field_equals` accepts dotted paths such as `data.items.0.id`.
- `base_url` may be a `{{variable}}`. Request methods may be any case. Bodies
  may be JSON arrays.
- `run-collection --quiet` and `--timeout`; `show-history --limit`.
- `python -m postpy`.
- Test suite, GitHub Actions CI (Python 3.9–3.14), and an offline example
  collection for the example mock config.

### Changed
- Python 3.9 or newer is required.
- The example mock config moved to `examples/mock_config.yaml`, and
  `examples/.env` is now `examples/example.env`.
- Mock JSON responses keep the key order from the config file.

### Removed
- `setup.py`; `pyproject.toml` is the only build configuration.
- The unused `postpy.utils.ConfigLoader` and `postpy/config/default_config.yaml`
  and `schema.yaml`, left over from the API emulator removed in 1.2.0.

## [1.3.0] - 2025-06-14

### Added
- Conditional responses for mock endpoints (`conditions` with `when`
  expressions)
- YAML guide and project context documentation

## [1.2.0] - 2025-06-14

### Changed
- Removed API emulator feature and all related code, CLI commands, and documentation
- Project is now focused solely on the mock server for API prototyping and testing

## [1.1.0] - 2024-03-19

### Added
- New mock server feature for rapid API prototyping and testing
- Static response configuration via YAML
- CLI commands for mock server management
- Comprehensive documentation for mock server

### Changed
- Updated project structure to include mock server components
- Enhanced configuration system
- Improved error handling
- Updated dependencies to include Flask for mock server

### Fixed
- Various bug fixes and improvements

## [1.0.0] - 2024-03-18

### Added
- Initial release
- HTTP request support
- Collection management
- Environment variable support
- Basic CLI interface
