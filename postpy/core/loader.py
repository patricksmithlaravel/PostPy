import json
import yaml
from pathlib import Path
from typing import Dict, Optional

from .models import Collection, Environment

class CollectionLoader:
    @staticmethod
    def load_collection(file_path: str) -> Collection:
        """Load a collection from a JSON or YAML file."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Collection file not found: {file_path}")
        
        with open(path, 'r') as f:
            if path.suffix.lower() in ['.yaml', '.yml']:
                data = yaml.safe_load(f)
            else:
                data = json.load(f)
        
        return Collection(**data)

    @staticmethod
    def load_environment(file_path: str) -> Environment:
        """Load environment variables from a .env file."""
        path = Path(file_path)
        
        if not path.exists():
            raise FileNotFoundError(f"Environment file not found: {file_path}")
        
        variables = {}
        with open(path, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    variables[key.strip()] = value.strip()
        
        return Environment(variables=variables) 