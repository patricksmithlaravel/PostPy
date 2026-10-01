from typing import Tuple, Union

from pydantic import ValidationError


def _format_location(location: Tuple[Union[int, str], ...]) -> str:
    text = ""
    for part in location:
        text += f"[{part}]" if isinstance(part, int) else f".{part}"
    return text.lstrip(".") or "(root)"


def format_validation_error(exc: ValidationError, title: str) -> str:
    """Render a pydantic error as one ``location: message`` line per problem."""
    lines = [title]
    for error in exc.errors():
        message = error["msg"].removeprefix("Value error, ")
        lines.append(f"  {_format_location(error['loc'])}: {message}")
    return "\n".join(lines)
