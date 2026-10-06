"""Repository paths. No Flask."""

from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = REPO_ROOT / "data"
REPORTS_DIR = DATA_DIR / "reports"
CACHE_DIR = DATA_DIR / "cache"
DATABASES_DIR = DATA_DIR / "databases"
DB_PATH = DATABASES_DIR / "cfb.db"


def ensure_data_dirs() -> None:
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    DATABASES_DIR.mkdir(parents=True, exist_ok=True)


def load_report(name: str) -> dict | None:
    path = REPORTS_DIR / name
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def write_report(name: str, payload: dict) -> Path:
    ensure_data_dirs()
    path = REPORTS_DIR / name
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    return path
