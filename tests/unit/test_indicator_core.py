"""Unit tests for core indicator logic."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.analytics.atr import compute_atr
from src.analytics.jma import compute_jma
from src.analytics.pivots import detect_pivots
from src.state_machine.breakout import BreakoutStateMachine
from src.visualization.plot_jurik_breakout import _build_missing_calendar_dates


class TestIndicatorCore(unittest.TestCase):
    def test_compute_jma_initializes_from_first_close(self) -> None:
        close = pd.Series([10.0, 11.0, 12.0])
        jma = compute_jma(close, length=3, phase=1.0)
        self.assertEqual(jma.iloc[0], 10.0)

    def test_detect_pivots_respects_confirmation_delay(self) -> None:
        df = pd.DataFrame(
            {
                "high": [1.0, 3.0, 2.0, 1.0, 1.0],
                "low": [0.5, 1.5, 1.0, 0.9, 0.8],
            }
        )
        pivots = detect_pivots(df, pivot_len=1)
        self.assertTrue(pd.isna(pivots.loc[1, "ph"]))
        self.assertEqual(float(pivots.loc[2, "ph"]), 3.0)
        self.assertEqual(int(pivots.loc[2, "ph_idx"]), 1)

    def test_detect_pivots_rejects_tied_extremes(self) -> None:
        df = pd.DataFrame(
            {
                "high": [1.0, 3.0, 3.0, 1.0, 1.0],
                "low": [0.5, 0.2, 0.2, 0.9, 1.0],
            }
        )

        pivots = detect_pivots(df, pivot_len=1)

        self.assertTrue(pivots["ph"].isna().all())
        self.assertTrue(pivots["pl"].isna().all())

    def test_compute_atr_matches_pandas_ta_rma_behavior(self) -> None:
        df = pd.DataFrame(
            {
                "high": [10.0, 11.0, 12.0, 13.0],
                "low": [9.0, 9.5, 10.5, 11.5],
                "close": [9.5, 10.0, 11.0, 12.0],
            }
        )

        atr = compute_atr(df, window=3)

        self.assertTrue(pd.isna(atr.iloc[0]))
        self.assertTrue(pd.isna(atr.iloc[1]))
        self.assertAlmostEqual(float(atr.iloc[2]), 1.5, places=6)
        self.assertAlmostEqual(float(atr.iloc[3]), 5.0 / 3.0, places=6)

    def test_build_missing_calendar_dates_hides_non_trading_gaps(self) -> None:
        df = pd.DataFrame(
            {
                "date": ["2026-01-02", "2026-01-05", "2026-01-07"],
            }
        )

        missing = _build_missing_calendar_dates(df)

        self.assertEqual(
            [value.strftime("%Y-%m-%d") for value in missing],
            ["2026-01-03", "2026-01-04", "2026-01-06"],
        )

    def test_state_machine_emits_breakout_signal(self) -> None:
        state_machine = BreakoutStateMachine(pivot_len=1)

        first_pivot_row = state_machine.update(
            0,
            {"close": 9.9, "trend": True, "atr": 1.0, "ph": None, "pl": None, "ph_idx": None, "pl_idx": None},
        )
        second_pivot_row = state_machine.update(
            1,
            {"close": 10.0, "trend": True, "atr": 1.0, "ph": 10.0, "pl": None, "ph_idx": 1, "pl_idx": None},
        )
        structure_row = state_machine.update(
            2,
            {"close": 10.1, "trend": True, "atr": 1.0, "ph": 10.2, "pl": None, "ph_idx": 2, "pl_idx": None},
        )
        row = state_machine.update(
            3,
            {"close": 10.3, "trend": True, "atr": 1.0, "ph": None, "pl": None, "ph_idx": None, "pl_idx": None},
        )

        self.assertFalse(first_pivot_row["structure_event"])
        self.assertFalse(second_pivot_row["structure_event"])
        self.assertTrue(structure_row["structure_event"])
        self.assertEqual(structure_row["structure_event_side"], "upper")
        self.assertEqual(row["signal"], 1)
        self.assertTrue(row["breakout_up"])
        self.assertEqual(row["res_line"], 10.2)


if __name__ == "__main__":
    unittest.main()
