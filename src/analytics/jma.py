"""Jurik moving-average helpers."""

from __future__ import annotations

import pandas as pd


def compute_jma(close: pd.Series, length: int, phase: float) -> pd.Series:
    """Compute the simplified recursive JMA used by the Pine reference."""
    if length <= 0:
        raise ValueError("length must be > 0")
    if phase <= 0:
        raise ValueError("phase must be > 0")
    if close.empty:
        raise ValueError("close series must not be empty")

    beta = 0.45 * (length - 1) / (0.45 * (length - 1) + 2)
    alpha = beta**phase

    values = []
    prev = float(close.iloc[0])
    for current in close.astype(float):
        prev = (1 - alpha) * float(current) + alpha * prev
        values.append(prev)

    return pd.Series(values, index=close.index, name="jma")


def derive_trend(jma: pd.Series, lag: int = 3) -> pd.Series:
    """Derive trend from JMA vs its lagged value."""
    if lag <= 0:
        raise ValueError("lag must be > 0")

    trend = pd.Series(False, index=jma.index, name="trend")
    if len(jma) <= lag:
        return trend

    trend.iloc[lag:] = (jma.iloc[lag:] >= jma.shift(lag).iloc[lag:]).astype(bool)
    return trend
