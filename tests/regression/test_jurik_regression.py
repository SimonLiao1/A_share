"""Regression checks using real daily-price CSV files."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.indicators.jurik_breakout import JurikBreakoutIndicator
from src.io.loader import load_price_data


class TestJurikRegression(unittest.TestCase):
    def test_china_railway_regression_summary(self) -> None:
        df = load_price_data(PROJECT_ROOT / "data" / "daily_price" / "中国中铁_20260410.csv")
        result = JurikBreakoutIndicator().compute(df)

        self.assertEqual(len(result), 306)
        self.assertEqual(int((result["signal"] == 1).sum()), 0)
        self.assertEqual(int((result["signal"] == -1).sum()), 1)
        self.assertEqual(int(result["pivot_confirm"].fillna(False).sum()), 40)
        self.assertEqual(result.index[result["signal"] == -1].tolist(), [301])
        self.assertEqual(float(result.loc[301, "breakout_level"]), 5.31)

    def test_ping_an_regression_summary(self) -> None:
        df = load_price_data(PROJECT_ROOT / "data" / "daily_price" / "中国平安_20260410.csv")
        result = JurikBreakoutIndicator().compute(df)

        self.assertEqual(int((result["signal"] == 1).sum()), 1)
        self.assertEqual(int((result["signal"] == -1).sum()), 0)
        self.assertEqual(int(result["pivot_confirm"].fillna(False).sum()), 40)


if __name__ == "__main__":
    unittest.main()
