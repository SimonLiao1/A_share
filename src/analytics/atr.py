"""ATR helpers."""

from __future__ import annotations

import pandas as pd
import pandas_ta as ta


def compute_atr(df: pd.DataFrame, window: int = 200) -> pd.Series:
    """Compute ATR using pandas-ta with Pine-style RMA smoothing."""
    if window <= 0:
        raise ValueError("window must be > 0")

    atr = ta.atr(
        high=df["high"].astype(float),
        low=df["low"].astype(float),
        close=df["close"].astype(float),
        length=window,
        mamode="rma",
        talib=False,
    )
    return atr.rename("atr")
