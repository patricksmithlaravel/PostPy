"""
Configuration loader for PostPy.
"""
import os
from typing import Dict, Any, Optional
import yaml
from pathlib import Path


class ConfigLoader:
    """Loads and validates configuration from YAML files."""

    def __init__(self, config_path: Optional[str] = None):
        """Initialize the config loader.

        Args:
            config_path: Path to the configuration file. If None, uses the default config.
        """
        self.config_path = config_path or self._get_default_config_path()
        self.config: Dict[str, Any] = {}

    def _get_default_config_path(self) -> str:
        """Get the path to the default configuration file.

        Returns:
            str: Path to the default configuration file.
        """
        return os.path.join(os.path.dirname(__file__), "..", "config", "default_config.yaml")

    def load_config(self, config_path: Optional[str] = None) -> Dict[str, Any]:
        """Load configuration from a YAML file.

        Args:
            config_path: Path to the configuration file. If None, uses the current config path.

        Returns:
            Dict[str, Any]: The loaded configuration.

        Raises:
            FileNotFoundError: If the configuration file does not exist.
            yaml.YAMLError: If the configuration file is invalid YAML.
        """
        path = config_path or self.config_path
        if not os.path.exists(path):
            raise FileNotFoundError(f"Configuration file not found: {path}")

        with open(path, "r") as f:
            config = yaml.safe_load(f)

        if self.validate_config(config):
            return config
        raise ValueError("Invalid configuration format")

    def load(self) -> Dict[str, Any]:
        """Load the configuration from the specified file.

        Returns:
            Dict[str, Any]: The loaded configuration.

        Raises:
            FileNotFoundError: If the configuration file does not exist.
            yaml.YAMLError: If the configuration file is invalid YAML.
        """
        self.config = self.load_config()
        return self.config

    def validate_config(self, config: Dict[str, Any]) -> bool:
        """Validate configuration against schema.

        Args:
            config: Configuration to validate

        Returns:
            bool: True if valid, False otherwise
        """
        # Basic validation of required fields
        required_fields = ['endpoints']
        return all(field in config for field in required_fields)

    def save(self, config: Dict[str, Any], path: Optional[str] = None) -> None:
        """Save the configuration to a file.

        Args:
            config: The configuration to save.
            path: Path to save the configuration to. If None, uses the current config path.

        Raises:
            IOError: If the configuration file cannot be written.
        """
        save_path = path or self.config_path
        os.makedirs(os.path.dirname(save_path), exist_ok=True)

        with open(save_path, "w") as f:
            yaml.dump(config, f, default_flow_style=False) 