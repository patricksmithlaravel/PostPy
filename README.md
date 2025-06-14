# PostPy

PostPy is a powerful Python library for API automation and testing. It provides tools for making HTTP requests, managing collections, and running a mock server for API testing.

## Features

- 🚀 Simple and intuitive API for making HTTP requests
- 📦 Collection management for organizing API endpoints
- 🔄 Environment variable support
- 📝 Comprehensive documentation
- 🛠️ Extensible architecture
- 🧪 Built-in mock server for API prototyping and testing

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package installer)

### Installation Methods

1. **From PyPI**
```bash
pip install postpy
```

2. **From Source**
```bash
git clone https://github.com/yourusername/postpy.git
cd postpy
pip install -e .
```

## Quick Start

### Making HTTP Requests

```python
from postpy import PostPy

# Create a client
client = PostPy()

# Make a request
response = client.get('https://api.example.com/users')
print(response.json())
```

### Using Collections

```python
from postpy import PostPy

# Load a collection
client = PostPy()
collection = client.load_collection('my_api.json')

# Execute a request from the collection
response = collection.execute('Get Users')
print(response.json())
```

## Mock Server

PostPy includes a built-in mock server for rapid API prototyping and testing.

### Features
- Create mock API servers for any REST API
- Define endpoints and static responses in a YAML config file
- Instantly simulate real API behavior for development and testing

### Usage

1. **Create a Mock Server Config**
   ```sh
   postpy mock init mock_config.yaml
   ```
   This generates a template YAML config you can edit.

2. **Run the Mock Server**
   ```sh
   postpy mock run <config_path> [--host HOST] [--port PORT] [--debug]
   ```
   Example:
   ```sh
   postpy mock run mock_config.yaml --host 127.0.0.1 --port 5001 --debug
   ```

3. **Test Endpoints**
   Use `curl` or any HTTP client to test your endpoints as defined in your config.

#### Example Mock Server Config

```yaml
endpoints:
  - path: /api/v1/health
    method: GET
    response:
      status: "healthy"
      version: "1.0.0"
    status_code: 200

  - path: /api/v1/users
    method: GET
    response:
      users:
        - id: 1
          name: "John Doe"
        - id: 2
          name: "Jane Smith"
    status_code: 200

  - path: /api/v1/users
    method: POST
    response:
      message: "User created successfully"
      id: 3
    status_code: 201
```

For more details, see the CLI help:
```sh
postpy mock --help
```

## Documentation

- [API Reference](docs/api.md)
- [Collections Guide](docs/collections.md)
- [Environment Variables](docs/environment.md)

## Usage

### Collection File Format

Create a collection file (e.g., `api_tests.json`):
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
        "limit": "10"
      },
      "tests": {
        "status_code": 200,
        "contains": ["users"],
        "json_field_equals": {
          "status": "success"
        }
      }
    }
  ]
}
```

### Environment File

Create an environment file (e.g., `.env`):
```env
token=your_auth_token
api_key=your_api_key
base_url=https://api.example.com
```

### CLI Commands

1. **Run Collection**
```bash
# Run all requests in a collection
postpy run-collection api_tests.json

# Run with environment variables
postpy run-collection api_tests.json --env-file .env

# Run specific request by name
postpy run-collection api_tests.json --request-name "Get Users"
```

2. **Show Collection Details**
```bash
postpy show-collection api_tests.json
```

3. **View Request History**
```bash
postpy show-history api_tests.json
```

## Package Dependencies

- **Core Dependencies**
  - `click>=8.1.0`: CLI framework
  - `rich>=13.0.0`: Rich text and formatting
  - `requests>=2.31.0`: HTTP client
  - `python-dotenv>=1.0.0`: Environment variable management
  - `pyyaml>=6.0.0`: YAML file support
  - `pydantic>=2.0.0`: Data validation

## Development

### Project Structure
```
postpy/
├── __init__.py
├── core/
│   ├── __init__.py
│   ├── mock_server.py # Mock server implementation
│   ├── loader.py      # Collection loader
│   └── executor.py    # Request executor
├── utils/
│   ├── __init__.py
│   └── config_loader.py
├── cli/
│   ├── __init__.py
│   ├── main.py        # Main CLI
│   └── mock.py        # Mock server CLI
├── config/
│   └── default_config.yaml
└── ...
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- Inspired by Postman's collection format
- Built with Python's rich ecosystem of HTTP and CLI tools 