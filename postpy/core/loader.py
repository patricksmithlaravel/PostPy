import json
import os
from pathlib import Path
from typing import Any, Union

import yaml
from dotenv import dotenv_values

from .models import Collection, Environment


class _NoAliasLoader(yaml.SafeLoader):
    """``yaml.SafeLoader`` that rejects aliases (``*name``).

    Nested aliases let a file of a few hundred bytes expand into gigabytes,
    and collections have no use for them.
    """

    def compose_node(self, parent: Any, index: Any) -> Any:
        if self.check_event(yaml.AliasEvent):
            raise yaml.composer.ComposerError(
                None,
                None,
                "aliases (*name) are not allowed in collections",
                self.peek_event().start_mark,
            )
        return super().compose_node(parent, index)


class CollectionLoader:
    @staticmethod
    def load_collection(file_path: Union[str, "os.PathLike[str]"]) -> Collection:
        """Load a collection from a JSON or YAML file.

        Raises:
            FileNotFoundError: If the file does not exist.
            ValueError: If the file cannot be parsed.
            pydantic.ValidationError: If the contents are not a valid collection.
        """
        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(f"Collection file not found: {file_path}")

        text = path.read_text(encoding="utf-8")
        data: Any
        if path.suffix.lower() in [".yaml", ".yml"]:
            try:
                data = yaml.load(text, Loader=_NoAliasLoader)
            except yaml.YAMLError as exc:
                raise ValueError(f"{file_path} is not valid YAML: {exc}") from None
        else:
            try:
                data = json.loads(text)
            except json.JSONDecodeError as exc:
                raise ValueError(f"{file_path} is not valid JSON: {exc}") from None

        if not isinstance(data, dict):
            raise ValueError(f"{file_path} must contain a collection object")
        return Collection(**data)

    @staticmethod
    def load_environment(file_path: Union[str, "os.PathLike[str]"]) -> Environment:
        """Load variables from a .env file.

        Supports comments, blank lines, quoted values and ``export`` prefixes.
        Keys without a value are ignored.
        """
        path = Path(file_path)

        if not path.is_file():
            raise FileNotFoundError(f"Environment file not found: {file_path}")

        values = dotenv_values(path, interpolate=False)
        variables = {key: value for key, value in values.items() if value is not None}
        return Environment(variables=variables)
