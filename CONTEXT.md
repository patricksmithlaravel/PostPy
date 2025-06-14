# CONTEXT (v1.3.0)

> **Note:** This context is for PostPy v1.3.0.

# PostPy Project Context

## Project Overview
PostPy is a Python-based API testing and mocking framework. The mock server component allows you to serve static API responses for testing and development purposes.

**Important Limitation:**
- The mock server only supports static responses. It does not interpolate or substitute variables from the request body, path, or query parameters in the response. All responses must be defined statically in the configuration file.

## Directory Structure
```
postpy/
├── cli/                    # Command-line interface implementations
│   ├── main.py            # Main CLI entry point
│   ├── mock.py            # Mock server CLI commands
│   └── emulator.py        # Emulator CLI commands
├── core/                   # Core functionality
│   ├── mock_server.py     # Mock server implementation (static responses only)
│   ├── emulator.py        # API emulator implementation
│   ├── loader.py          # Configuration loading
│   ├── executor.py        # Request execution
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
  - path: /api/v1/example
    method: GET
    response:
      status_code: 200
      body:
        message: "This is a static response."
```
- `endpoints`: List of endpoint definitions.
  - `path`: The URL path. Path parameters (e.g., `{device_id}`) are supported for routing only, not for response interpolation.
  - `method`: HTTP method (GET, POST, etc.).
  - `response`: The static response to return.
    - `status_code`: HTTP status code.
    - `body`: JSON body to return (static, no variable substitution).
  - `conditions` (optional): List of conditions for error or alternate responses, based on path parameters only.

#### Features
- Configurable endpoints with custom responses
- Support for different HTTP methods
- Path parameter handling
- Custom status codes
- JSON response formatting
- Query parameter support
- Request body validation
- Response headers configuration

### 2. API Emulator
The emulator provides more advanced features for API simulation, including:
- Dynamic response generation
- Template processing
- Request validation
- Error simulation
- Stateful responses
- Conditional responses
- Response delays
- Rate limiting

### 3. Configuration System
The project uses a YAML-based configuration system with:
- Schema validation
- Default configurations
- Environment-specific settings
- Template variables
- Response conditions
- Error scenarios
- Authentication rules
- Rate limiting rules

#### Configuration Examples

1. **Basic Endpoint**
```yaml
endpoints:
  - path: /api/v1/health
    method: GET
    response:
      status: healthy
    status_code: 200
```

2. **Path Parameters**
```yaml
endpoints:
  - path: /api/v1/devices/{device_id}
    method: GET
    response:
      id: "{device_id}"
      name: "Device {device_id}"
    status_code: 200
```

3. **Query Parameters**
```yaml
endpoints:
  - path: /api/v1/search
    method: GET
    response:
      results:
        - name: "Result 1"
          score: 0.95
    status_code: 200
```

4. **Error Responses**
```yaml
endpoints:
  - path: /api/v1/error
    method: GET
    response:
      error: "Not Found"
      message: "Resource not found"
    status_code: 404
```

## Usage Examples

### Starting the Mock Server
```bash
# Basic usage
postpy mock run config.yaml --host 127.0.0.1 --port 6060 --debug

# With custom configuration
postpy mock run netbrain_mock_config.yaml --host 127.0.0.1 --port 5002 --debug

# With specific environment
postpy mock run config.yaml --env production --host 127.0.0.1 --port 6060
```

### Testing Endpoints
```bash
# Health check
curl http://127.0.0.1:6060/api/v1/health

# Authentication
curl -X POST http://127.0.0.1:6060/api/v1/auth/token

# Device list
curl http://127.0.0.1:6060/api/v1/devices

# Specific device
curl http://127.0.0.1:6060/api/v1/devices/router1

# Search with query parameters
curl "http://127.0.0.1:6060/api/v1/search?q=router&limit=10"

# Error endpoint
curl http://127.0.0.1:6060/api/v1/error
```

## Common Issues and Solutions

### 1. Configuration Loading
- Issue: `AttributeError: 'ConfigLoader' object has no attribute 'load_config'`
- Solution: Ensure the `ConfigLoader` class has the `load_config` method implemented
- Prevention: Always validate configuration files before deployment

### 2. Port Conflicts
- Issue: Port already in use
- Solution: Use different ports for different servers (e.g., 5001, 5002, 6060)
- Prevention: Check port availability before starting the server

### 3. Endpoint Not Found
- Issue: 404 errors for expected endpoints
- Solution: Verify the endpoint is defined in the configuration file
- Prevention: Use the debug mode to see available endpoints

### 4. Response Format Issues
- Issue: Invalid JSON responses
- Solution: Check response format in configuration
- Prevention: Validate response format against schema

### 5. Path Parameter Problems
- Issue: Path parameters not being replaced
- Solution: Use correct format in configuration
- Prevention: Test path parameter endpoints

### 6. Server Not Starting
- Issue: Server fails to start
- Solution: Check port availability and permissions
- Prevention: Use debug mode for detailed error messages

## Development Guidelines

### Adding New Features
1. Update the core implementation in `core/`
2. Add CLI commands in `cli/`
3. Update configuration schema if needed
4. Add tests for new functionality
5. Update documentation
6. Add example configurations

### Configuration Updates
1. Modify the schema in `config/schema.yaml`
2. Update default configurations
3. Ensure backward compatibility
4. Add validation rules
5. Update documentation
6. Test with existing configurations

### Testing
1. Use the mock server for API testing
2. Test different response scenarios
3. Verify error handling
4. Test path parameters
5. Test query parameters
6. Test response formats
7. Test error scenarios

## Dependencies
- Flask >= 3.0.0
- Click >= 8.1.0
- PyYAML >= 6.0.0
- Rich >= 13.0.0
- Requests >= 2.31.0
- Python-dotenv >= 1.0.0
- Pydantic >= 2.0.0

## Future Improvements
1. Enhanced template processing
2. Better error handling
3. More configuration options
4. Improved documentation
5. Additional testing tools
6. Web interface for configuration
7. Real-time response modification
8. Request/response logging
9. Performance monitoring
10. Authentication improvements

## Notes
- The mock server and emulator serve different purposes
- Configuration files should be validated before use
- Debug mode provides detailed logging
- Path parameters are supported in endpoint definitions
- Query parameters can be used in responses
- Error scenarios should be tested
- Response formats should be validated
- Server logs should be monitored
- Configuration changes require server restart
- Environment variables can override configuration

# PostPy Project Context

## Project Overview
PostPy is a Python-based API testing and mocking framework that provides tools for creating mock API servers and testing API interactions. The project consists of two main components:

1. **Mock Server**: A configurable Flask-based server that simulates API endpoints
2. **API Emulator**: A more advanced server that can generate dynamic responses based on templates

## Directory Structure
```
postpy/
├── cli/                    # Command-line interface implementations
│   ├── main.py            # Main CLI entry point
│   ├── mock.py            # Mock server CLI commands
│   └── emulator.py        # Emulator CLI commands
├── core/                   # Core functionality
│   ├── mock_server.py     # Mock server implementation
│   ├── emulator.py        # API emulator implementation
│   ├── loader.py          # Configuration loading
│   ├── executor.py        # Request execution
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
  # Health check endpoint
  - path: /api/v1/health
    method: GET
    response:
      status: healthy
      version: 1.0.0
    status_code: 200

  # Authentication endpoint
  - path: /api/v1/auth/token
    method: POST
    response:
      token: "mock-jwt-token-123"
      expires_in: 3600
    status_code: 200

  # Device endpoints with path parameters
  - path: /api/v1/devices/{device_id}
    method: GET
    response:
      id: "{device_id}"
      name: "Device {device_id}"
      status: "online"
    status_code: 200
```

#### Features
- Configurable endpoints with custom responses
- Support for different HTTP methods
- Path parameter handling
- Custom status codes
- JSON response formatting
- Query parameter support
- Request body validation
- Response headers configuration

### 2. API Emulator
The emulator provides more advanced features for API simulation, including:
- Dynamic response generation
- Template processing
- Request validation
- Error simulation
- Stateful responses
- Conditional responses
- Response delays
- Rate limiting

### 3. Configuration System
The project uses a YAML-based configuration system with:
- Schema validation
- Default configurations
- Environment-specific settings
- Template variables
- Response conditions
- Error scenarios
- Authentication rules
- Rate limiting rules

#### Configuration Examples

1. **Basic Endpoint**
```yaml
endpoints:
  - path: /api/v1/health
    method: GET
    response:
      status: healthy
    status_code: 200
```

2. **Path Parameters**
```yaml
endpoints:
  - path: /api/v1/devices/{device_id}
    method: GET
    response:
      id: "{device_id}"
      name: "Device {device_id}"
    status_code: 200
```

3. **Query Parameters**
```yaml
endpoints:
  - path: /api/v1/search
    method: GET
    response:
      results:
        - name: "Result 1"
          score: 0.95
    status_code: 200
```

4. **Error Responses**
```yaml
endpoints:
  - path: /api/v1/error
    method: GET
    response:
      error: "Not Found"
      message: "Resource not found"
    status_code: 404
```

## Usage Examples

### Starting the Mock Server
```bash
# Basic usage
postpy mock run config.yaml --host 127.0.0.1 --port 6060 --debug

# With custom configuration
postpy mock run netbrain_mock_config.yaml --host 127.0.0.1 --port 5002 --debug

# With specific environment
postpy mock run config.yaml --env production --host 127.0.0.1 --port 6060
```

### Testing Endpoints
```bash
# Health check
curl http://127.0.0.1:6060/api/v1/health

# Authentication
curl -X POST http://127.0.0.1:6060/api/v1/auth/token

# Device list
curl http://127.0.0.1:6060/api/v1/devices

# Specific device
curl http://127.0.0.1:6060/api/v1/devices/router1

# Search with query parameters
curl "http://127.0.0.1:6060/api/v1/search?q=router&limit=10"

# Error endpoint
curl http://127.0.0.1:6060/api/v1/error
```

## Common Issues and Solutions

### 1. Configuration Loading
- Issue: `AttributeError: 'ConfigLoader' object has no attribute 'load_config'`
- Solution: Ensure the `ConfigLoader` class has the `load_config` method implemented
- Prevention: Always validate configuration files before deployment

### 2. Port Conflicts
- Issue: Port already in use
- Solution: Use different ports for different servers (e.g., 5001, 5002, 6060)
- Prevention: Check port availability before starting the server

### 3. Endpoint Not Found
- Issue: 404 errors for expected endpoints
- Solution: Verify the endpoint is defined in the configuration file
- Prevention: Use the debug mode to see available endpoints

### 4. Response Format Issues
- Issue: Invalid JSON responses
- Solution: Check response format in configuration
- Prevention: Validate response format against schema

### 5. Path Parameter Problems
- Issue: Path parameters not being replaced
- Solution: Use correct format in configuration
- Prevention: Test path parameter endpoints

### 6. Server Not Starting
- Issue: Server fails to start
- Solution: Check port availability and permissions
- Prevention: Use debug mode for detailed error messages

## Development Guidelines

### Adding New Features
1. Update the core implementation in `core/`
2. Add CLI commands in `cli/`
3. Update configuration schema if needed
4. Add tests for new functionality
5. Update documentation
6. Add example configurations

### Configuration Updates
1. Modify the schema in `config/schema.yaml`
2. Update default configurations
3. Ensure backward compatibility
4. Add validation rules
5. Update documentation
6. Test with existing configurations

### Testing
1. Use the mock server for API testing
2. Test different response scenarios
3. Verify error handling
4. Test path parameters
5. Test query parameters
6. Test response formats
7. Test error scenarios

## Dependencies
- Flask >= 3.0.0
- Click >= 8.1.0
- PyYAML >= 6.0.0
- Rich >= 13.0.0
- Requests >= 2.31.0
- Python-dotenv >= 1.0.0
- Pydantic >= 2.0.0

## Future Improvements
1. Enhanced template processing
2. Better error handling
3. More configuration options
4. Improved documentation
5. Additional testing tools
6. Web interface for configuration
7. Real-time response modification
8. Request/response logging
9. Performance monitoring
10. Authentication improvements

## Notes
- The mock server and emulator serve different purposes
- Configuration files should be validated before use
- Debug mode provides detailed logging
- Path parameters are supported in endpoint definitions
- Query parameters can be used in responses
- Error scenarios should be tested
- Response formats should be validated
- Server logs should be monitored
- Configuration changes require server restart
- Environment variables can override configuration 