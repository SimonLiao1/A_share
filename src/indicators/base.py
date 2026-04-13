"""Base indicator abstractions."""

from __future__ import annotations

import pandas as pd


class BaseIndicator:
    """Base class for indicators."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}
        self.validate_config()

    def validate_config(self) -> None:
        """Validate configuration."""

    def compute(self, df: pd.DataFrame) -> pd.DataFrame:
        raise NotImplementedError
