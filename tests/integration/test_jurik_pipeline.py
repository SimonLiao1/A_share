"""Integration tests for the Jurik pipeline."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.indicators.jurik_breakout import JurikBreakoutIndicator
from src.io.loader import load_price_data
from src.io.writer import get_error_log_path
from src.visualization.plot_jurik_breakout import plot_jurik_breakout


class TestJurikPipeline(unittest.TestCase):
    def test_real_csv_computes_required_columns(self) -> None:
        csv_path = PROJECT_ROOT / "data" / "daily_price" / "中国中铁_20260410.csv"
        df = load_price_data(csv_path)
        result = JurikBreakoutIndicator().compute(df)

        for column in ["jma", "trend", "atr", "ph", "pl", "res_line", "sup_line", "signal"]:
            self.assertIn(column, result.columns)

        self.assertEqual(len(result), len(df))

    def test_error_log_path_points_to_root_log_directory(self) -> None:
        log_path = get_error_log_path("jurik_breakout")
        self.assertEqual(log_path.parent.name, "log")
        self.assertTrue(log_path.name.endswith("_error.log"))

    def test_chart_output_is_generated(self) -> None:
        csv_path = PROJECT_ROOT / "data" / "daily_price" / "中国中铁_20260410.csv"
        df = load_price_data(csv_path)
        result = JurikBreakoutIndicator().compute(df)

        with tempfile.TemporaryDirectory() as tmpdir:
            chart_path = Path(tmpdir) / "jurik_breakout.html"
            plot_jurik_breakout(result, str(chart_path))
            self.assertTrue(chart_path.exists())
            self.assertIn("<html", chart_path.read_text(encoding="utf-8").lower())


if __name__ == "__main__":
    unittest.main()
