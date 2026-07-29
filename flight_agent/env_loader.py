from __future__ import annotations

import os
from pathlib import Path


def load_env(root: Path | None = None) -> None:
    """Load KEY=VALUE pairs from `.env` in `root` into os.environ (no overwrite)."""
    root = root or Path(__file__).resolve().parent
    env_path = root / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value
