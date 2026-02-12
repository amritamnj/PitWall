"""
Caching utilities for the F1 Strategy Explorer backend.

Caches degradation data as JSON files on disk to avoid repeated FastF1 fetches.
FastF1 itself caches raw session data, but our processed degradation summaries
are stored separately for fast retrieval.
"""

import json
import hashlib
import time
from pathlib import Path
from typing import Any

# Cache root lives alongside the backend package
CACHE_DIR = Path(__file__).resolve().parent.parent / "cache"


def _ensure_dir(subdir: str) -> Path:
    """Create cache subdirectory if it doesn't exist and return its Path."""
    path = CACHE_DIR / subdir
    path.mkdir(parents=True, exist_ok=True)
    return path


def _cache_key(prefix: str, **kwargs: Any) -> str:
    """
    Build a deterministic filename from arbitrary keyword args.
    Example: prefix="degradation", circuit="albert_park", years="2023-2025"
    -> degradation_<md5>.json
    """
    raw = json.dumps(kwargs, sort_keys=True)
    digest = hashlib.md5(raw.encode()).hexdigest()[:12]
    return f"{prefix}_{digest}.json"


def read_cache(subdir: str, ttl_seconds: int | None = None, **kwargs: Any) -> dict | None:
    """Return cached dict or None if cache miss.

    If *ttl_seconds* is given, treat entries older than that as expired
    (return None so the caller re-fetches).  Existing callers that omit
    ttl_seconds are unaffected — entries never expire for them.
    """
    directory = _ensure_dir(subdir)
    filename = _cache_key(subdir, **kwargs)
    filepath = directory / filename
    if filepath.exists():
        if ttl_seconds is not None:
            if time.time() - filepath.stat().st_mtime > ttl_seconds:
                return None
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    return None


def write_cache(subdir: str, data: dict, **kwargs: Any) -> Path:
    """Write data to cache and return the file path."""
    directory = _ensure_dir(subdir)
    filename = _cache_key(subdir, **kwargs)
    filepath = directory / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    return filepath
