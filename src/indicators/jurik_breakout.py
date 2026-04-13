"""Jurik breakout indicator implementation."""

from __future__ import annotations

import pandas as pd

from src.analytics.atr import compute_atr
from src.analytics.jma import compute_jma, derive_trend
from src.analytics.pivots import detect_pivots
from src.indicators.base import BaseIndicator
from src.io.loader import validate_ohlcv_schema
from src.state_machine.breakout import BreakoutStateMachine


class JurikBreakoutIndicator(BaseIndicator):
    """Python implementation of the TradingView Jurik breakout indicator."""

    DEFAULT_CONFIG = {
        "len": 9,
        "phase": 0.15,
        "pivot_len": 4,
        "atr_window": 200,
    }

    def __init__(self, config: dict | None = None):
        merged = dict(self.DEFAULT_CONFIG)
        if config:
            merged.update(config)
        super().__init__(config=merged)

    def validate_config(self) -> None:
        if self.config["len"] <= 0:
            raise ValueError("len must be > 0")
        if self.config["phase"] <= 0:
            raise ValueError("phase must be > 0")
        if self.config["pivot_len"] < 1:
            raise ValueError("pivot_len must be >= 1")
        if self.config["atr_window"] < 1:
            raise ValueError("atr_window must be >= 1")

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        result = df.copy()
        if "date" not in result.columns:
            raise ValueError("missing required columns: ['date']")
        result["date"] = pd.to_datetime(result["date"], errors="raise")
        result = result.sort_values("date").reset_index(drop=True)
        validate_ohlcv_schema(result, require_sorted=True)

        result["jma"] = compute_jma(result["close"], self.config["len"], self.config["phase"])
        result["trend"] = derive_trend(result["jma"])
        result["atr"] = compute_atr(result, self.config["atr_window"])

        pivot_df = detect_pivots(result, self.config["pivot_len"])
        result = pd.concat([result, pivot_df], axis=1)

        state_machine = BreakoutStateMachine(pivot_len=self.config["pivot_len"])
        state_rows = []
        for idx, row in result.iterrows():
            state_rows.append(
                state_machine.update(
                    idx=idx,
                    row={
                        "close": row["close"],
                        "trend": row["trend"],
                        "atr": row["atr"],
                        "ph": row["ph"],
                        "pl": row["pl"],
                        "ph_idx": row["ph_idx"],
                        "pl_idx": row["pl_idx"],
                    },
                )
            )

        state_df = pd.DataFrame(state_rows, index=result.index)
        result = pd.concat([result, state_df], axis=1)
        result["signal"] = result["signal"].fillna(0).astype(int)
        result["breakout_level"] = pd.NA
        result.loc[result["signal"] == 1, "breakout_level"] = result.loc[result["signal"] == 1, "res_line"]
        result.loc[result["signal"] == -1, "breakout_level"] = result.loc[result["signal"] == -1, "sup_line"]
        result["jma_glow"] = result["jma"]
        return result
