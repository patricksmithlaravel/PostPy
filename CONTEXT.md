# CONTEXT (v1.3.0)

> **Note:** This context is for PostPy v1.3.0.

# PostPy Project Context

## Project Overview
PostPy is a Python-based API testing and mocking framework. The mock server component allows you to serve static API responses for testing and development purposes.

**Important Limitations:**
- The mock server only supports static responses
- Limited HTTP method support (GET, POST)
- Basic error handling (404, 405)
- No request body validation
- No query parameter handling
- No response headers configuration

## Directory Structure
```
postpy/
├── cli/                    # Command-line interface implementations
│   ├── main.py            # Main CLI entry point
│   └── mock.py            # Mock server CLI commands
├── core/                   # Core functionality
│   ├── mock_server.py     # Mock server implementation
│   ├── loader.py          # Configuration loading
│   └── models.py          # Data models
├── utils/                  # Utility functions
│   ├── config_loader.py   # YAML configuration loading
│   └── __init__.py
└── config/                 # Configuration files
    ├── default_config.yaml # Default mock server config
    └── schema.yaml        # Configuration schema
```

## Key Components

### 1. Mock Server
The mock server is a Flask-based application that serves predefined API endpoints based on a YAML configuration file.

#### Configuration Format
```yaml
endpoints:
  - path: /api/v1/health
    method: GET
    response:
      status: healthy
      version: 1.0.0
    status_code: 200
```
- `endpoints`: List of endpoint definitions.
  - `path`: The URL path. Path parameters (e.g., `{device_id}`) are supported for routing only.
  - `method`: HTTP method (GET, POST).
  - `response`: The static response to return.
    - `status_code`: HTTP status code.
    - `body`: JSON body to return (static).
  - `conditions` (optional): List of conditions for error responses.

#### Features
- Configurable endpoints with static responses
- Support for GET and POST methods
- Path parameter handling for routing
- Custom status codes
- JSON response formatting
- Basic error handling (404, 405)

### 2. Configuration System
The project uses a YAML-based configuration system with:
- Schema validation
- Default configurations
- Static response definitions
- Basic error handling
- Path parameter routing

#### Configuration Examples

1. **Health Check Endpoint**
```yaml
endpoints:
  - path: /api/v1/health
    method: GET
    response:
      status: healthy
      version: 1.0.0
    status_code: 200
```

2. **Device Endpoint**
```yaml
endpoints:
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

3. **Error Response**
```yaml
endpoints:
  - path: /api/v1/devices/invalid_device
    method: GET
    response:
      status_code: 404
      body:
        error: "Device not found"
        message: "The requested device does not exist"
```

## Usage Examples

### Starting the Mock Server
```bash
# Basic usage
postpy mock run mock_config.yaml --host 127.0.0.1 --port 5001 --debug
```

### Testing Endpoints
```bash
# Health check
curl http://127.0.0.1:5001/api/v1/health

# Authentication
curl -X POST http://127.0.0.1:5001/api/v1/auth/token

# Device list
curl http://127.0.0.1:5001/api/v1/devices

# Create device
curl -X POST -H "Content-Type: application/json" -d '{"name": "New Router"}' http://127.0.0.1:5001/api/v1/devices

# Get specific device
curl http://127.0.0.1:5001/api/v1/devices/router1

# Test invalid device (404)
curl http://127.0.0.1:5001/api/v1/devices/invalid_device

# Test invalid method (405)
curl -X PUT http://127.0.0.1:5001/api/v1/devices
```

## Common Issues and Solutions

### 1. Configuration Loading
- Issue: Invalid YAML format
- Solution: Validate YAML syntax
- Prevention: Use a YAML validator

### 2. Port Conflicts
- Issue: Port already in use
- Solution: Use a different port
- Prevention: Check port availability before starting

### 3. Endpoint Not Found
- Issue: 404 errors for expected endpoints
- Solution: Verify endpoint definition in config
- Prevention: Use debug mode to see available endpoints

### 4. Method Not Allowed
- Issue: 405 errors for valid endpoints
- Solution: Check HTTP method in config
- Prevention: Verify method support (GET, POST only)

### 5. Invalid Response Format
- Issue: Invalid JSON responses
- Solution: Check response format in config
- Prevention: Validate response format

## Development Guidelines

### Adding New Features
1. Update the core implementation in `core/`
2. Add CLI commands in `cli/`
3. Update configuration schema if needed
4. Add tests for new functionality
5. Update documentation

### Configuration Updates
1. Modify the schema in `config/schema.yaml`
2. Update default configurations
3. Ensure backward compatibility
4. Add validation rules
5. Update documentation

### Testing
1. Test all defined endpoints
2. Verify error handling
3. Test path parameters
4. Test response formats
5. Test invalid scenarios

## Dependencies
- Flask >= 3.0.0
- Click >= 8.1.0
- PyYAML >= 6.0.0
- Rich >= 13.0.0
- Requests >= 2.31.0
- Python-dotenv >= 1.0.0
- Pydantic >= 2.0.0

## Future Improvements
1. Support for more HTTP methods
2. Request body validation
3. Query parameter handling
4. Response headers configuration
5. Better error handling
6. More configuration options
7. Improved documentation
8. Additional testing tools
9. Request/response logging
10. Performance monitoring 