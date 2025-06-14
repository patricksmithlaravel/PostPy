"""
Mock server implementation.
"""
import yaml
from pathlib import Path
from flask import Flask, request, jsonify
from ..utils.config_loader import ConfigLoader

class MockServer:
    """Mock API server for testing."""
    
    def __init__(self, config_path):
        """Initialize the mock server with a configuration file.
        
        Args:
            config_path (str): Path to the configuration file
        """
        self.app = Flask(__name__)
        self.config = self._load_config(config_path)
        self._setup_routes()
    
    def _load_config(self, config_path):
        """Load the server configuration from a YAML file.
        
        Args:
            config_path (str): Path to the configuration file
            
        Returns:
            dict: Server configuration
        """
        with open(config_path, 'r') as f:
            return yaml.safe_load(f)
    
    def _evaluate_condition(self, condition, params):
        """Evaluate a condition string with the given parameters.
        
        Args:
            condition (str): Condition string to evaluate
            params (dict): Parameters to use in evaluation
            
        Returns:
            bool: True if condition is met, False otherwise
        """
        try:
            # Replace parameters in condition
            for key, value in params.items():
                condition = condition.replace(f"{{{key}}}", f"'{value}'")
            return eval(condition)
        except Exception:
            return False
    
    def _setup_routes(self):
        """Set up the Flask routes based on the configuration."""
        for endpoint in self.config.get('endpoints', []):
            path = endpoint.get('path')
            method = endpoint.get('method', 'GET').upper()
            response = endpoint.get('response', {})
            status_code = endpoint.get('status_code', 200)
            conditions = endpoint.get('conditions', [])
            
            def create_handler(resp, code, conds):
                def handler(**kwargs):
                    # Check conditions if any
                    if conds and kwargs:
                        for condition in conds:
                            if self._evaluate_condition(condition['when'], kwargs):
                                return jsonify(condition['response']), condition['status_code']
                    
                    # Replace path parameters in response
                    if kwargs:
                        import json
                        resp_str = json.dumps(resp)
                        for key, value in kwargs.items():
                            resp_str = resp_str.replace(f"{{{key}}}", str(value))
                        return jsonify(json.loads(resp_str)), code
                    return jsonify(resp), code
                return handler
            
            # Convert path parameters to Flask format
            flask_path = path.replace('{', '<').replace('}', '>')
            
            self.app.add_url_rule(
                flask_path,
                endpoint=f"{method}_{path}",
                methods=[method],
                view_func=create_handler(response, status_code, conditions)
            )
    
    def run(self, host='localhost', port=5000, debug=False):
        """Run the mock server.
        
        Args:
            host (str): Host to run the server on
            port (int): Port to run the server on
            debug (bool): Whether to run in debug mode
        """
        self.app.run(host=host, port=port, debug=debug)
    
    @classmethod
    def create_config(cls, output_path):
        """Create a default configuration file.
        
        Args:
            output_path (str): Path where the configuration file will be created
        """
        default_config = {
            'endpoints': [
                {
                    'path': '/api/v1/health',
                    'method': 'GET',
                    'response': {
                        'status': 'healthy',
                        'version': '1.0.0'
                    },
                    'status_code': 200
                },
                {
                    'path': '/api/v1/users',
                    'method': 'GET',
                    'response': {
                        'users': [
                            {'id': 1, 'name': 'John Doe'},
                            {'id': 2, 'name': 'Jane Smith'}
                        ]
                    },
                    'status_code': 200
                },
                {
                    'path': '/api/v1/users',
                    'method': 'POST',
                    'response': {
                        'message': 'User created successfully',
                        'id': 3
                    },
                    'status_code': 201
                }
            ]
        }
        
        with open(output_path, 'w') as f:
            yaml.dump(default_config, f, default_flow_style=False) 