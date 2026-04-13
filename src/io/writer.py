"""Output and runtime path helpers."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pandas as pd


def get_project_root() -> Path:
    """Return the repository root."""
    return Path(__file__).resolve().parents[2]


def ensure_directory(path: str | Path) -> Path:
    """Create the target directory when needed."""
    directory = Path(path)
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def generate_output_filename(symbol: str, indicator: str) -> str:
    """Generate a result CSV name."""
    return f"{symbol}_{indicator}_result.csv"


def get_error_log_path(indicator_name: str, log_dir: str = "log") -> Path:
    """Return the error log path under the root-level log directory."""
    directory = ensure_directory(get_project_root() / log_dir)
    today = datetime.now().strftime("%Y%m%d")
    return directory / f"{indicator_name}_{today}_error.log"


def write_output_csv(df: pd.DataFrame, output_path: str | Path) -> Path:
    """Write a result DataFrame to CSV."""
    output_path = Path(output_path)
    ensure_directory(output_path.parent)
    df.to_csv(output_path, index=False, encoding="utf-8")
    return output_path
