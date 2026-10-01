# PostPy Project Context

## Project Overview

PostPy is a Python API testing and mocking tool with two halves:

- **Collections:** JSON or YAML files of HTTP requests with `{{variable}}`
  placeholders and assertions. They are run from the CLI (`postpy
  run-collection`) or from Python (`PostPy().load_collection(...)`).
- **Mock server:** A Flask app built from a YAML file of endpoints, with path
  parameters, response headers and conditional responses (`postpy mock run`).

The version is defined once, in `postpy/__init__.py`, and read by
`pyproject.toml` and `postpy --version`.

## Directory Structure

```
postpy/
├── __init__.py          # __version__ and public exports (PostPy, Collection, ...)
├── __main__.py          # python -m postpy
├── client.py            # PostPy: ad-hoc requests + load_collection()
├── cli/
│   ├── __init__.py      # Exposes `cli`, the console-script entry point
│   ├── main.py          # run-collection, show-collection, show-history
│   ├── mock.py          # mock init, mock run
│   └── output.py        # printable(): escapes control characters for display
├── config/
│   └── mock_template.yaml  # Starter file written by `postpy mock init`
└── core/
    ├── conditions.py    # AST allow-list evaluator for mock `when` expressions
    ├── errors.py        # Turns pydantic errors into `location: message` lines
    ├── executor.py      # RequestExecutor: substitution, sending, assertions
    ├── history.py       # HistoryStore: JSON-lines history per collection
    ├── loader.py        # CollectionLoader: collections and .env files
    ├── mock_server.py   # Mock config schema (pydantic) and MockServer
    ├── models.py        # Collection, Request, TestAssertion, ...
    └── runner.py        # CollectionRunner and RequestResult
examples/                # Sample collections, env files, mock config
tests/                   # pytest suite
```

## Key Design Points

### Collections

- `CollectionLoader` parses files into pydantic models (`models.py`).
  `base_url` must be an absolute http(s) URL unless it contains `{{...}}`.
- `RequestExecutor` substitutes variables in the base URL, endpoint, headers,
  query parameters and body at any depth, in a single pass. It sends through
  one `requests.Session` with a timeout (default 30 s).
- `run_tests` returns one `AssertionResult` per check. `json_field_equals`
  accepts dotted paths with list indexes.
- `CollectionRunner.iter_run` yields a `RequestResult` per request. Connection
  errors become failed results rather than aborting the run.
- The CLI exits with status 1 if any result fails.
- History lives in `$POSTPY_HOME/history` (default `~/.postpy`), in `0600`
  files. It keeps only the request name, method, endpoint template, status and
  timing.
- Everything the CLI prints from a response or collection goes through
  `cli/output.py:printable()`, which shows control characters as `\xNN`.

### Mock Server

- `load_mock_config` validates the YAML into `MockConfig`/`MockEndpoint`/
  `MockResponse` models. Endpoint keys are strict (`extra="forbid"`).
  Duplicate method and path pairs are rejected.
- Two response layouts are accepted: the envelope form
  `response: {status_code, body, headers}`, and the 1.3 layout with the body
  under `response` and `status_code` beside it. Both are normalized to the
  envelope form.
- `{name}` path segments become Flask `<name>` rules. `{name}` placeholders in
  response strings and headers are substituted on the parsed structure, never
  on serialized JSON.
- `conditions[].when` is compiled by `core/conditions.py` at load time. Only
  literals, path parameters, comparisons and `and`/`or`/`not` are allowed. It
  never calls `eval`.
- Unmatched routes return JSON 404s; wrong methods return JSON 405s with an
  `Allow` header.
- A string body with an HTML or XML `Content-Type` is sent raw, with
  substituted path values HTML-escaped.
- `run()` always passes `use_debugger=False`. With `--debug` it reloads when
  the config file changes.

## Development Guidelines

```bash
pip install -e ".[dev]"
pytest
black --check . && isort --check-only . && mypy
```

- Keep code compatible with Python 3.9 (use `typing.Optional`/`List`, not
  `X | None`, in anything pydantic evaluates).
- Add tests next to the area you change. `tests/conftest.py` provides a live
  echo server, a live example mock server and a collection-file helper.
- If you change a config format, update the template, the examples,
  `YAML_GUIDE.md`, `README.md` and `CHANGELOG.md` together.
  `tests/test_cli.py::test_example_collection_against_example_mock_server`
  keeps the examples working.
- Treat anything taken from an incoming request as data. Never build code,
  JSON text or shell commands from it.

## Possible Future Improvements

1. Matching on query parameters, request headers or request bodies in mock
   conditions
2. Request body validation for mock endpoints
3. Saving values from one response for use in later requests
4. CORS headers for browser clients of the mock server
5. Publishing to PyPI under a distinct name
