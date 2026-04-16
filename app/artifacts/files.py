from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd

from app.core.config import Settings


def create_run_dir(
    *,
    settings: Settings,
    season_a: str,
    season_b: str,
    output_subdir: str | None = None,
) -> Path:
    timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    slug = output_subdir or f"{timestamp}_{season_a}_vs_{season_b}"
    run_dir = settings.output_root / "runs" / slug
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def write_dataframe_csv(df: pd.DataFrame, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def write_json_file(payload: dict[str, Any], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
    return path
