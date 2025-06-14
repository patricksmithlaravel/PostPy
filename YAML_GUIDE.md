# Guide: Writing YAML Files for the PostPy Mock Server (v1.3.0)

> **Note:** This guide is for PostPy v1.3.0.

## Overview

The PostPy mock server uses a YAML configuration file to define all API endpoints and their **static** responses.  
**No variable interpolation** is supported—responses are always returned exactly as written.

---

## Basic Structure

```yaml
endpoints:
  - path: /api/v1/example
    method: GET
    response:
      status_code: 200
      body:
        message: "This is a static response."
```

- `endpoints`: List of endpoint definitions.
- Each endpoint has:
  - `path`: The URL path (e.g., `/api/v1/devices`). Path parameters (e.g., `/api/v1/devices/{device_id}`) are allowed for routing only.
  - `method`: HTTP method (GET, POST, etc.).
  - `response`: The static response to return.
    - `status_code`: HTTP status code (e.g., 200, 404).
    - `body`: The JSON body to return (must be static).

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

### 4. Create Device (POST)

```yaml
- path: /api/v1/devices
  method: POST
  response:
    status_code: 201
    body:
      id: "router2"
      name: "New Router"
      type: "router"
      status: "online"
      message: "Device created successfully"
```

### 5. Device Details (Static Path)

```yaml
- path: /api/v1/devices/router1
  method: GET
  response:
    status_code: 200
    body:
      id: "router1"
      name: "Device router1"
      status: "online"
      type: "router"
      interfaces:
        - name: eth0
          ip: 192.168.1.1
          status: up
        - name: eth1
          ip: 10.0.0.1
          status: up
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

---

## Tips & Best Practices

- **No dynamic content:** All values in `body` must be hardcoded. Do not use `{}` or `{{}}` for variables.
- **Path parameters:** You can use paths like `/api/v1/devices/{device_id}` for routing, but the response must be static (e.g., always return the same body for any `{device_id}`).
- **Multiple endpoints:** To simulate different device IDs, define a separate endpoint for each (e.g., `/api/v1/devices/router1`, `/api/v1/devices/switch1`).
- **Status codes:** Use the correct HTTP status code for each response (e.g., 200 for success, 201 for created, 404 for not found).
- **YAML formatting:** Indentation is important! Use spaces, not tabs.

---

## Troubleshooting

- **404 Not Found:** Make sure the `path` and `method` in your request exactly match an entry in your YAML file.
- **Invalid YAML:** Use a YAML linter or validator if you get syntax errors.
- **No variable substitution:** If you see `{device_id}` or similar in your response, remove it—responses must be static.

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

  - path: /api/v1/devices/router1
    method: GET
    response:
      status_code: 200
      body:
        id: router1
        name: Router 1
        status: online
        type: router
```

---

## Summary

- **All responses are static.**
- **No variable interpolation.**
- **Define each endpoint and response explicitly.**

For more examples, see your project's `mock_config.yaml` or the README. 