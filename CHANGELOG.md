# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security
- An explicit `Authorization` header in a collection or a `PostPy` request now
  takes precedence over `~/.netrc`. Previously requests replaced it with the
  `.netrc` credentials for that host, so a test ran as a different user.
  `.netrc` still applies to requests without an `Authorization` header.
- On a redirect to a different host or port, PostPy now forwards only
  standard headers (`Accept`, `Content-Type`, `User-Agent` and similar).
  requests itself drops only `Authorization`, so custom credential headers
  such as `X-API-Key` used to reach the new host. Same-host redirects no
  longer let `~/.netrc` replace an `Authorization` header.
- PostPy no longer adds `~/.netrc` credentials for the target of a redirect to
  a different host or port. requests looked them up for whatever host the
  server named, so a hostile or tampered response could send your requests,
  logged in with your `.netrc` credentials, to any host you have a login for,
  even over plain `http`.
- Requests to loopback addresses (`127.0.0.0/8`, `::1`, `localhost`,
  `*.localhost`) no longer go through `HTTP_PROXY` or `HTTPS_PROXY`. A remote
  proxy cannot reach your machine's loopback interface, so runs against a
  local mock server failed and the proxy saw their credentials. Proxies passed
  explicitly from Python still apply.
- YAML collections can no longer use aliases (`*name`). Nested aliases let a
  file under 1 KB expand into gigabytes when the request is built, so opening
  an untrusted collection could exhaust memory. Mock configs still allow them.
- A mock server bound to a loopback address (`127.0.0.1`, `localhost`, `::1`)
  now answers `421 Misdirected Request` unless the Host header is a loopback
  name. Without the check, a web page using DNS rebinding could read the mock
  server's responses.

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
- The CLI prints control characters from responses and collection files as
  visible `\xNN` escapes. A malicious response could otherwise inject terminal
  escape sequences to rewrite earlier output (for example a fake `PASS`),
  change the window title or set the clipboard.
- Path parameter values substituted into HTML or XML mock responses are
  HTML-escaped, preventing reflected XSS on the mock server's origin.
- Request history files are created owner-only (`0600` in a `0700`
  directory).
- The minimum `requests` version is now 2.32.4, which fixes `.netrc`
  credentials leaking to crafted URLs (CVE-2024-47081).

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
- Invalid collection and mock files now produce messages that say where the
  problem is instead of tracebacks. `.env` lines without `=` are skipped
  instead of crashing the loader, and `json_field_equals` no longer crashes on
  JSON array responses.
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
- Documentation for mock server

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
