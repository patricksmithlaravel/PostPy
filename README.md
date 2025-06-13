# PostPy

A powerful Postman-style API testing and automation tool written in Python with a command-line interface. PostPy allows you to define, execute, and test API requests using collection files, with support for environment variables, test assertions, and request history tracking.

## Features

### Core Features
- **HTTP Request Support**
  - All major HTTP methods (GET, POST, PUT, DELETE, PATCH)
  - Custom headers configuration
  - Query parameter support
  - Request body support (JSON, form data, raw payloads)

- **Environment Support**
  - Environment variables via `.env` files
  - Variable substitution using `{{variable}}` syntax
  - Support for multiple environments

- **Request Collections**
  - JSON/YAML collection file format
  - Base URL configuration
  - Named requests with full configuration
  - Test assertions per request

- **Authentication**
  - Basic Authentication
  - Bearer Token
  - API Key (header or query parameter)
  - Custom authentication headers

- **Testing & Assertions**
  - Status code validation
  - Response body content checking
  - JSON field value matching
  - Custom test assertions

- **Request History**
  - Track request execution history
  - Response times
  - Status codes
  - Timestamps

- **Rich CLI Interface**
  - Colored output
  - Formatted tables
  - Syntax-highlighted JSON
  - Progress indicators

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
│   ├── models.py      # Data models
│   ├── executor.py    # Request execution
│   └── loader.py      # Collection loading
├── cli/
│   ├── __init__.py
│   └── main.py        # CLI interface
└── examples/
    ├── api_tests.json # Example collection
    └── .env          # Example environment
```

### Running Tests
```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest
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