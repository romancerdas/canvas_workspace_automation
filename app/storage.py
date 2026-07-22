import json
import os
import tempfile
from pathlib import Path
from threading import RLock
from typing import Any


class JsonStore:
    """Small, thread-safe JSON persistence layer using atomic file replacement."""

    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._lock = RLock()

    def _path(self, name: str) -> Path:
        safe_name = Path(name).name
        if not safe_name.endswith(".json"):
            safe_name += ".json"
        return self.data_dir / safe_name

    def read(self, name: str, default: Any):
        path = self._path(name)
        with self._lock:
            if not path.exists():
                return default
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                return default

    def write(self, name: str, value: Any) -> None:
        path = self._path(name)
        with self._lock:
            fd, temp_name = tempfile.mkstemp(prefix=path.stem, suffix=".tmp", dir=path.parent)
            try:
                with os.fdopen(fd, "w", encoding="utf-8") as f:
                    json.dump(value, f, indent=2, sort_keys=True)
                    f.write("\n")
                os.replace(temp_name, path)
            finally:
                if os.path.exists(temp_name):
                    os.unlink(temp_name)

    def update(self, name: str, default: Any, mutator):
        with self._lock:
            value = self.read(name, default)
            new_value = mutator(value)
            self.write(name, new_value)
            return new_value
