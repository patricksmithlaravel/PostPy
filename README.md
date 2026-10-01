# PostPy

PostPy is a Postman-style API testing tool for Python. It runs collections of
HTTP requests with assertions, keeps a request history, and serves mock APIs
from a YAML file. You can drive it from the command line or from Python.

## Features

- Collections of requests in JSON or YAML, with `{{variable}}` placeholders
- Assertions on status codes, response text and JSON fields, with a non-zero
  exit code on failure so collections can run in CI
- Environment files for switching base URLs, tokens and IDs
- Per-collection request history
- A mock server that serves endpoints, headers and conditional responses
  from YAML
- A small Python API (`PostPy`) for scripting the same things

## Installation

PostPy requires Python 3.9 or newer. It is not published on PyPI (the `postpy`
name there belongs to an unrelated project), so install it from GitHub:

```bash
pip install git+https://github.com/patricksmithlaravel/PostPy.git
```

Or from a clone, for development:

```bash
git clone https://github.com/patricksmithlaravel/PostPy.git
cd PostPy
pip install -e ".[dev]"
```

## Quick Start

Start the example mock server in one terminal:

```bash
postpy mock run examples/mock_config.yaml --port 5001
```

Then run the example collection against it in another:

```bash
postpy run-collection examples/mock_api_tests.json --env-file examples/mock.env
```

PostPy prints each request with its status, assertion results and response
body, then a summary such as `8 passed, 0 failed`.

## Collections

### Collection File Format

A collection is a JSON or YAML file:

```json
{
  "collection_name": "My API Tests",
  "base_url": "https://api.example.com",
  "requests": [
    {
      "name": "Get Users",
      "method": "GET",
      "endpoint": "/users",
      "headers": {
        "Authorization": "Bearer {{token}}"
      },
      "query_params": {
        "limit": 10
      },
      "tests": {
        "status_code": 200,
        "contains": ["users"],
        "json_field_equals": {
          "status": "success",
          "users.0.id": 1
        }
      }
    }
  ]
}
```

| Field | Description |
| --- | --- |
| `collection_name` | Display name. |
| `base_url` | Absolute `http(s)` URL, or a `{{variable}}` such as `{{base_url}}`. |
| `requests[].name` | Name used by `--request-name` and `execute()`. |
| `requests[].method` | `GET`, `POST`, `PUT`, `PATCH`, `DELETE`, `HEAD` or `OPTIONS` (any case). |
| `requests[].endpoint` | Path appended to `base_url`, or an absolute URL. |
| `requests[].headers` | Optional header map. |
| `requests[].query_params` | Optional query parameters. A list value repeats the parameter. |
| `requests[].body` | Optional body. Objects and arrays are sent as JSON; a string is sent as-is. |
| `requests[].tests` | Optional assertions, described below. |

### Assertions

| Assertion | Passes when |
| --- | --- |
| `status_code` | The response status equals this value. |
| `contains` | Every listed string appears in the response body. |
| `json_field_equals` | Each field in the JSON response equals the given value. Use dots for nested fields and numbers for list items, e.g. `data.items.0.id`. A key that literally contains a dot is matched first. |

### Variables and Environment Files

`{{name}}` placeholders in `base_url`, `endpoint`, `headers`, `query_params` and
`body` (at any depth) are filled in from an environment file:

```env
# .env
base_url=https://staging.example.com
token=your_auth_token
```

Comments, quoted values and `export` prefixes are supported. Values are taken
literally: `${OTHER}` is not expanded. Placeholders without a matching variable
are sent unchanged.

### CLI Commands

```bash
# Run all requests in a collection
postpy run-collection api_tests.json

# Run with environment variables
postpy run-collection api_tests.json --env-file .env

# Run one request by name
postpy run-collection api_tests.json --request-name "Get Users"

# Hide response bodies and wait at most 10 seconds per request
postpy run-collection api_tests.json --quiet --timeout 10

# Show the requests in a collection
postpy show-collection api_tests.json

# Show the 20 most recent requests run from a collection
postpy show-history api_tests.json --limit 20
```

`run-collection` exits with status 1 if any request cannot be sent or any
assertion fails, so it can gate a CI job.

PostPy keeps history under `~/.postpy/history/` (set `POSTPY_HOME` to move it),
readable only by your user. It records each request's name, method, endpoint
template, status and timing. Headers, bodies and substituted variable values
never reach the disk.

PostPy prints control characters from response bodies and collection fields as
visible `\xNN` escapes, so a response cannot recolor, rewrite or retitle your
terminal or set its clipboard.

A collection decides where requests go, so running one with your environment
file sends your variables to the hosts it names. Review collections from other
people before running them with real credentials.

## Python API

```python
from postpy import PostPy

client = PostPy(environment=".env")  # or a dict, or omit it

# Ad-hoc requests (a requests.Response is returned)
response = client.get("{{base_url}}/users", params={"limit": 10})
print(response.json())

# Collections share the client's variables, cookies and timeout
collection = client.load_collection("api_tests.json")
response = collection.execute("Get Users")

for result in collection.run():
    print(result.request.name, result.passed)
    for assertion in result.assertions:
        print("  ", assertion.name, assertion.passed, assertion.message)
```

`PostPy(timeout=...)` sets the per-request timeout in seconds (default 30).
`client.close()` or `with PostPy() as client:` closes the underlying session.

## Mock Server

The mock server serves endpoints defined in a YAML file.

```bash
# Write a starter config (refuses to overwrite unless --force is given)
postpy mock init mock_config.yaml

# Serve it
postpy mock run mock_config.yaml --host 127.0.0.1 --port 5001
```

On start-up the server validates the whole file and prints its endpoint table.
If the file has an unknown key, an unsupported method or a duplicate route, the
server refuses to start and reports where each problem is.

### Configuration Example

```yaml
endpoints:
  - path: /api/v1/health
    method: GET
    response:
      status_code: 200
      body:
        status: healthy

  - path: /api/v1/devices
    method: POST
    response:
      status_code: 201
      headers:
        Location: /api/v1/devices/router2
      body:
        id: router2

  - path: /api/v1/devices/{device_id}
    method: GET
    response:
      status_code: 200
      body:
        id: "{device_id}"
        name: "Device {device_id}"
    conditions:
      - when: "{device_id} not in ['router1', 'switch1']"
        response:
          status_code: 404
          body:
            error: Device not found
```

- `method` may be `GET`, `POST`, `PUT`, `PATCH` or `DELETE`.
- `response` holds `status_code` (default 200), `body` (any JSON value; omit it
  for an empty response) and optional `headers`.
- `{name}` in a path matches one URL segment. The same placeholder inside
  response strings and header values is replaced with the matched value.
- `conditions` are checked in order and the first one that is true replaces the
  default response.
- Requests that match no endpoint get a JSON 404; a known path with the wrong
  method gets a JSON 405 with an `Allow` header.

See [YAML_GUIDE.md](YAML_GUIDE.md) for the full format, the condition syntax and
more examples.

### Running Safely

[RUNBOOK.md](RUNBOOK.md) has the full procedure: which address and port to
use, handling credentials, running in CI, and what to do if a token leaks.

- The server binds to `localhost` by default. Passing `--host 0.0.0.0` exposes
  it to your network, and PostPy prints a warning when you do.
- `--debug` reloads the server when the config file changes. Werkzeug's
  in-browser debugger stays disabled, because it can run arbitrary code.
- Conditions are parsed against a small allow-list of syntax and are never
  passed to `eval`, so values in the request URL cannot execute code.
- In responses with an HTML or XML `Content-Type`, substituted path values are
  HTML-escaped, so a crafted link cannot inject script into a mocked page.

### Example Requests

With `examples/mock_config.yaml` running on port 5001:

```bash
curl http://127.0.0.1:5001/api/v1/health
curl -X POST http://127.0.0.1:5001/api/v1/auth/token
curl http://127.0.0.1:5001/api/v1/devices
curl -X POST -H "Content-Type: application/json" -d '{"name": "New Router"}' http://127.0.0.1:5001/api/v1/devices
curl http://127.0.0.1:5001/ServicesAPI/API/V1/Device/router1
curl http://127.0.0.1:5001/ServicesAPI/API/V1/Device/unknown   # 404 from a condition
curl -X PUT http://127.0.0.1:5001/api/v1/devices               # 405
```

### Troubleshooting

- **Address already in use:** pick another `--port`. On macOS, port 5000 is
  often taken by AirPlay Receiver.
- **404 for an endpoint you defined:** the `path` and `method` must both match.
  Check the endpoint table printed at start-up.
- **The server will not start:** the validation message lists each problem
  with its location, such as `endpoints[3].method`.

## Development

```bash
pip install -e ".[dev]"
pytest              # tests
black --check .     # formatting
isort --check-only .
mypy                # type checks
```

CI runs all of these on Python 3.9 to 3.14, then builds the package and runs
the example collection against the example mock server.

### Project Structure

```
postpy/
├── __init__.py          # Version and public API
├── __main__.py          # python -m postpy
├── client.py            # PostPy client class
├── cli/
│   ├── main.py          # run-collection, show-collection, show-history
│   ├── mock.py          # mock init, mock run
│   └── output.py        # Escapes control characters before printing
├── config/
│   └── mock_template.yaml  # Written by `postpy mock init`
└── core/
    ├── conditions.py    # Safe condition expressions
    ├── errors.py        # Validation error formatting
    ├── executor.py      # Sends requests, runs assertions
    ├── history.py       # Request history storage
    ├── loader.py        # Collection and .env loading
    ├── mock_server.py   # Mock server and its config schema
    ├── models.py        # Collection data models
    └── runner.py        # Runs collections
examples/                # Sample collections, env files and mock config
tests/                   # pytest suite
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Run the checks under [Development](#development)
4. Open a pull request

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by Postman's collection format
- Built on requests, Flask, Click, Rich and pydantic
