import hashlib
import os
from pathlib import Path
from typing import Iterable, List, Optional, Union

from pydantic import ValidationError

from .models import RequestHistory

MAX_ENTRIES = 1000


def postpy_home() -> Path:
    """Directory for PostPy's own data; override with ``POSTPY_HOME``."""
    return Path(os.environ.get("POSTPY_HOME") or Path.home() / ".postpy")


class HistoryStore:
    """Request history for one collection, stored as JSON lines.

    Only the method, endpoint template, status, timing and timestamp are kept.
    Headers, bodies and substituted variables are never written.
    """

    def __init__(self, collection_path: Union[str, Path], home: Optional[Path] = None):
        resolved = Path(collection_path).resolve()
        digest = hashlib.sha256(str(resolved).encode("utf-8")).hexdigest()[:12]
        self.path = (
            (home or postpy_home()) / "history" / f"{resolved.stem}-{digest}.jsonl"
        )

    def append(self, entries: Iterable[RequestHistory]) -> None:
        """Add entries, keeping only the most recent ``MAX_ENTRIES``."""
        new_lines = [entry.model_dump_json() for entry in entries]
        if not new_lines:
            return
        lines = self._read_lines() + new_lines
        self.path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        # Owner-only: an endpoint template can contain a hard-coded credential.
        fd = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        os.chmod(self.path, 0o600)  # also tighten files created by older versions
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write("\n".join(lines[-MAX_ENTRIES:]) + "\n")

    def read(self, limit: Optional[int] = None) -> List[RequestHistory]:
        """Return entries oldest first; ``limit`` keeps only the newest ones."""
        entries = []
        for line in self._read_lines():
            try:
                entries.append(RequestHistory.model_validate_json(line))
            except ValidationError:
                continue
        if limit is not None:
            entries = entries[-limit:] if limit > 0 else []
        return entries

    def _read_lines(self) -> List[str]:
        if not self.path.is_file():
            return []
        text = self.path.read_text(encoding="utf-8")
        return [line for line in text.splitlines() if line.strip()]
