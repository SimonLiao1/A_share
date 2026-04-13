"""CSV loading and validation helpers."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

REQUIRED_COLUMNS = ["date", "open", "high", "low", "close", "volume"]


def validate_ohlcv_schema(df: pd.DataFrame, require_sorted: bool = True) -> None:
    """Validate the input DataFrame schema."""
    missing = [column for column in REQUIRED_COLUMNS if column not in df.columns]
    if missing:
        raise ValueError(f"missing required columns: {missing}")
    if df.empty:
        raise ValueError("input data is empty")
    if df["close"].isna().any():
        raise ValueError("close column contains null values")
    if require_sorted and not df["date"].is_monotonic_increasing:
        raise ValueError("date column must be sorted ascending")
    if df["date"].duplicated().any():
        raise ValueError("date column contains duplicates")


def load_price_data(path: str | Path) -> pd.DataFrame:
    """Load and normalize OHLCV price data."""
    df = pd.read_csv(path)
    validate_ohlcv_schema(df, require_sorted=False)
    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="raise")
    for column in ["open", "high", "low", "close", "volume"]:
        df[column] = pd.to_numeric(df[column], errors="raise")
    df = df.sort_values("date").reset_index(drop=True)
    validate_ohlcv_schema(df, require_sorted=True)
    return df
