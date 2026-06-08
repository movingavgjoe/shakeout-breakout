"""Simple CSV-based cache keyed by name.

Each cached dataset is one CSV in CACHE_DIR. A sidecar timestamp (file mtime)
is used to decide staleness. Cached CSVs are git-ignored.
"""
from __future__ import annotations

import time
from pathlib import Path
from typing import Optional

import pandas as pd

from . import config


def _safe(name: str) -> str:
    """Make a name filesystem-safe."""
    return "".join(c if c.isalnum() or c in "-_." else "_" for c in name)


def cache_path(name: str) -> Path:
    return config.CACHE_DIR / f"{_safe(name)}.csv"


def is_fresh(name: str, max_age_days: float) -> bool:
    path = cache_path(name)
    if not path.exists():
        return False
    age_days = (time.time() - path.stat().st_mtime) / 86400.0
    return age_days <= max_age_days


def load(name: str, max_age_days: float) -> Optional[pd.DataFrame]:
    """Return cached DataFrame if present and fresh, else None."""
    if not is_fresh(name, max_age_days):
        return None
    try:
        return pd.read_csv(cache_path(name))
    except Exception:
        return None


def save(name: str, df: pd.DataFrame) -> Path:
    path = cache_path(name)
    df.to_csv(path, index=False)
    return path
