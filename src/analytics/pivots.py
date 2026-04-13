"""Pivot detection helpers."""

from __future__ import annotations

import pandas as pd


def _is_unique_center_high(window: pd.Series, center_pos: int) -> bool:
    center_value = float(window.iloc[center_pos])
    return center_value == float(window.max()) and int((window == center_value).sum()) == 1


def _is_unique_center_low(window: pd.Series, center_pos: int) -> bool:
    center_value = float(window.iloc[center_pos])
    return center_value == float(window.min()) and int((window == center_value).sum()) == 1


def detect_pivots(df: pd.DataFrame, pivot_len: int) -> pd.DataFrame:
    """Detect Pine-style pivots using delayed confirmation semantics."""
    if pivot_len < 1:
        raise ValueError("pivot_len must be >= 1")

    high = df["high"].astype(float)
    low = df["low"].astype(float)
    result = pd.DataFrame(index=df.index)
    result["ph"] = pd.Series([pd.NA] * len(df), index=df.index, dtype="object")
    result["pl"] = pd.Series([pd.NA] * len(df), index=df.index, dtype="object")
    result["ph_idx"] = pd.Series([pd.NA] * len(df), index=df.index, dtype="object")
    result["pl_idx"] = pd.Series([pd.NA] * len(df), index=df.index, dtype="object")

    for i in range(2 * pivot_len, len(df)):
        pivot_idx = i - pivot_len
        start = i - 2 * pivot_len
        stop = i + 1

        high_window = high.iloc[start:stop]
        low_window = low.iloc[start:stop]

        if _is_unique_center_high(high_window, pivot_len):
            result.at[df.index[i], "ph"] = float(high.iloc[pivot_idx])
            result.at[df.index[i], "ph_idx"] = int(pivot_idx)

        if _is_unique_center_low(low_window, pivot_len):
            result.at[df.index[i], "pl"] = float(low.iloc[pivot_idx])
            result.at[df.index[i], "pl_idx"] = int(pivot_idx)

    result["pivot_confirm"] = result["ph"].notna() | result["pl"].notna()
    result["pivot_type"] = pd.Series([None] * len(df), index=df.index, dtype="object")
    result.loc[result["ph"].notna(), "pivot_type"] = "high"
    result.loc[result["pl"].notna(), "pivot_type"] = "low"
    return result
