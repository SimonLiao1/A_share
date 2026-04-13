"""Indicator registry and execution helpers."""

from __future__ import annotations

import pandas as pd

from src.indicators.base import BaseIndicator


class IndicatorEngine:
    """Registers and runs indicators by name."""

    def __init__(self):
        self._registry: dict[str, type[BaseIndicator]] = {}

    def register(self, name: str, indicator_cls: type[BaseIndicator]) -> None:
        if name in self._registry:
            raise ValueError(f"indicator already registered: {name}")
        self._registry[name] = indicator_cls

    def run(self, name: str, df: pd.DataFrame, config: dict | None = None) -> pd.DataFrame:
        if name not in self._registry:
            raise KeyError(f"unknown indicator: {name}")
        indicator = self._registry[name](config=config)
        return indicator.compute(df)
