# Guide: Writing YAML Files for the PostPy Mock Server

## Overview

The PostPy mock server reads a YAML file that lists API endpoints and the
responses they return. `postpy mock init <file>` writes a commented starter
file, and `postpy mock run <file>` validates and serves it.

---

## Basic Structure

```yaml
endpoints:
  - path: /api/v1/example
    method: GET
    response:
      status_code: 200
      headers:
        X-Request-Id: abc123
      body:
        message: "This is a response."
```

- `endpoints`: List of endpoint definitions.
- Each endpoint has:
  - `path`: The URL path. Must start with `/`. May contain path parameters
    such as `/api/v1/devices/{device_id}`.
  - `method`: `GET` (the default), `POST`, `PUT`, `PATCH` or `DELETE`. Case
    does not matter.
  - `response`: What to send back.
    - `status_code`: HTTP status code, 100–599. Defaults to 200.
    - `body`: Any YAML value (mapping, list, string, number, boolean). It is
      sent as JSON. Leave it out to send an empty body, e.g. for a 204.
    - `headers`: Optional map of response headers.
  - `conditions`: Optional list of alternative responses. See
    [Conditional Responses](#conditional-responses).

Each `method` and `path` pair may appear only once. Other top-level keys are
ignored, so you can use them to hold YAML anchors (see
[Reusing Responses](#reusing-responses)).

---

## Path Parameters

`{name}` in a path matches exactly one URL segment (anything except `/`).
Wherever `{name}` appears inside a response string or header value, it is
replaced with the value from the URL:

```yaml
- path: /api/v1/devices/{device_id}
  method: GET
  response:
    body:
      id: "{device_id}"
      name: "Device {device_id}"
```

`GET /api/v1/devices/router7` returns `{"id": "router7", "name": "Device router7"}`.

- Replacement happens inside the parsed response, so a URL value containing
  quotes or braces is returned as plain text and cannot alter the response
  structure.
- Placeholders that do not name a path parameter are left as written.
- Replaced values are always strings. Quote a placeholder that makes up a whole
  value (`id: "{device_id}"`), because an unquoted `{device_id}` is YAML for a
  mapping.
- Werkzeug converters are available: `{int:item_id}` only matches digits and
  gives conditions an integer, and `{path:rest}` matches across slashes.

A fixed path such as `/api/v1/devices/router1` takes priority over
`/api/v1/devices/{device_id}`, so you can mix specific responses with a
general one.

---

## Conditional Responses

`conditions` let one endpoint return different responses depending on its path
parameters. They are checked in order. The first one whose `when` expression
is true replaces the default `response`; if none match, the default is used.

```yaml
- path: /api/v1/devices/{device_id}
  method: GET
  response:
    status_code: 200
    body:
      id: "{device_id}"
  conditions:
    - when: "{device_id} == 'locked'"
      response:
        status_code: 403
        body:
          error: "Device is locked"
    - when: "{device_id} not in ['router1', 'switch1']"
      response:
        status_code: 404
        body:
          error: "Device {device_id} not found"
```

The `when` expression supports:

| Syntax | Example |
| --- | --- |
| Path parameters, with or without braces | `{device_id}`, `device_id` |
| Literals | `'router1'`, `42`, `True`, `None` |
| Lists, tuples and sets of literals | `['a', 'b']` |
| Comparisons | `==`, `!=`, `<`, `<=`, `>`, `>=`, `in`, `not in`, including chains such as `1 < {n} <= 5` |
| Boolean logic | `and`, `or`, `not`, parentheses |

Anything else, such as function calls, attribute access, indexing or
arithmetic, is rejected when the server starts, as is a reference to a path
parameter the endpoint does not have. Path parameter values are only ever
compared as data and never run as code. A comparison between incompatible
types (for example a string with `>`) is simply false.

---

## Example: Common Patterns

### 1. Health Check Endpoint

```yaml
- path: /api/v1/health
  method: GET
  response:
    status_code: 200
    body:
      status: healthy
      version: 1.0.0
```

### 2. Authentication Endpoint

```yaml
- path: /api/v1/auth/token
  method: POST
  response:
    status_code: 200
    body:
      token: "mock-jwt-token-123"
      expires_in: 3600
```

### 3. List Devices

```yaml
- path: /api/v1/devices
  method: GET
  response:
    status_code: 200
    body:
      devices:
        - id: router1
          name: Router 1
          status: online
          type: router
        - id: switch1
          name: Switch 1
          status: online
          type: switch
```

### 4. Create Device (POST) with a Header

```yaml
- path: /api/v1/devices
  method: POST
  response:
    status_code: 201
    headers:
      Location: /api/v1/devices/router2
    body:
      id: "router2"
      name: "New Router"
      message: "Device created successfully"
```

### 5. Delete With No Body

```yaml
- path: /api/v1/devices/{device_id}
  method: DELETE
  response:
    status_code: 204
```

### 6. Error Response

```yaml
- path: /api/v1/devices/invalid_device
  method: GET
  response:
    status_code: 404
    body:
      error: "Device not found"
      message: "The requested device does not exist"
```

### 7. Plain Text Instead of JSON

A string `body` is sent as raw text when `headers` sets a non-JSON
`Content-Type`:

```yaml
- path: /metrics
  method: GET
  response:
    headers:
      Content-Type: text/plain
    body: "requests_total 42\n"
```

### Reusing Responses

```yaml
x-not-found: &not_found
  status_code: 404
  body:
    error: Not found

endpoints:
  - path: /api/v1/users/{user_id}
    response:
      body: {id: "{user_id}"}
    conditions:
      - when: "{user_id} not in ['1', '2']"
        response: *not_found
```

---

## Older Response Format

Configs written for PostPy 1.3 and earlier put the body directly under
`response` and the status code beside it. This still works:

```yaml
- path: /api/v1/health
  method: GET
  response:
    status: healthy
  status_code: 200
```

A `response` mapping is read in the new form only when its keys are some of
`status_code`, `body` and `headers` and include `status_code` or `body`.
Anything else is treated as a body in the older form. New configs should use
the form shown in [Basic Structure](#basic-structure).

---

## Built-in Error Responses

- A request that matches no endpoint gets a JSON `404`:
  `{"error": "Not Found", "message": "No mock endpoint matches GET /path"}`.
- A request to a known path with an unconfigured method gets a JSON `405`,
  with the allowed methods in the body and in the `Allow` header.

---

## Tips & Best Practices

- **Validate early:** `postpy mock run` checks the whole file before it starts
  and names the endpoint and field of every problem, such as
  `endpoints[3].method: unsupported method 'FETCH'`.
- **Status codes:** Use the right code for each response (200 for success, 201
  for created, 204 for no content, 404 for not found).
- **YAML formatting:** Indentation matters. Use spaces, not tabs.
- **Debug mode:** `--debug` reloads the server whenever you save the config
  file.

---

## Troubleshooting

- **404 Not Found:** The `path` and `method` in your request must match an
  entry exactly. The table printed at start-up lists every endpoint.
- **405 Method Not Allowed:** The path exists, but not for that method.
- **Invalid YAML:** The error includes the line and column of the problem.
- **`Extra inputs are not permitted`:** A key is misspelled or at the wrong
  level, e.g. `headers` placed beside `response` instead of inside it.
- **A placeholder is returned literally:** Check that the name in braces
  matches the name in `path`.

---

## Example: Full Minimal Config

```yaml
endpoints:
  - path: /api/v1/health
    method: GET
    response:
      status_code: 200
      body:
        status: healthy

  - path: /api/v1/devices
    method: GET
    response:
      status_code: 200
      body:
        devices:
          - id: router1
            name: Router 1
            status: online
            type: router

  - path: /api/v1/devices/{device_id}
    method: GET
    response:
      status_code: 200
      body:
        id: "{device_id}"
        name: "Device {device_id}"
    conditions:
      - when: "{device_id} != 'router1'"
        response:
          status_code: 404
          body:
            error: Device not found
```

For a larger example, see `examples/mock_config.yaml` in the repository.
