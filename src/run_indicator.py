#!/usr/bin/env python3
"""CLI entry point for indicator execution."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.indicators.engine import IndicatorEngine
from src.indicators.jurik_breakout import JurikBreakoutIndicator
from src.io.loader import load_price_data
from src.io.writer import generate_output_filename, get_error_log_path, write_output_csv
from src.visualization.plot_jurik_breakout import plot_jurik_breakout


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run an indicator on one price CSV file.")
    parser.add_argument("--indicator", default="jurik_breakout", help="Indicator name")
    parser.add_argument("--input", required=True, help="Input CSV path")
    parser.add_argument("--output", help="Output CSV path")
    parser.add_argument("--chart", help="Optional chart HTML output path")
    parser.add_argument("--log-dir", default="log", help="Root-level log directory")
    parser.add_argument("--len", type=int, default=9, dest="length", help="JMA length")
    parser.add_argument("--phase", type=float, default=0.15, help="JMA phase")
    parser.add_argument("--pivot-len", type=int, default=4, help="Pivot length")
    parser.add_argument("--atr-window", type=int, default=200, help="ATR window")
    parser.add_argument("--show-chart", action="store_true", help="Display the chart after rendering")
    return parser.parse_args()


def setup_logger(indicator_name: str, log_dir: str) -> logging.Logger:
    logger = logging.getLogger(indicator_name)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    error_handler = logging.FileHandler(get_error_log_path(indicator_name, log_dir), encoding="utf-8")
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))

    logger.addHandler(console_handler)
    logger.addHandler(error_handler)
    return logger


def build_engine() -> IndicatorEngine:
    engine = IndicatorEngine()
    engine.register("jurik_breakout", JurikBreakoutIndicator)
    return engine


def main() -> int:
    args = parse_args()
    logger = setup_logger(args.indicator, args.log_dir)

    try:
        input_path = Path(args.input)
        output_path = Path(args.output) if args.output else PROJECT_ROOT / "output" / "result_csv" / generate_output_filename(
            input_path.stem,
            args.indicator,
        )
        config = {
            "len": args.length,
            "phase": args.phase,
            "pivot_len": args.pivot_len,
            "atr_window": args.atr_window,
        }

        logger.info("loading price data from %s", input_path)
        df = load_price_data(input_path)

        logger.info("running indicator %s", args.indicator)
        result = build_engine().run(args.indicator, df, config)
        write_output_csv(result, output_path)
        logger.info("wrote result csv to %s", output_path)

        if args.chart:
            plot_jurik_breakout(result, args.chart, show=args.show_chart)
            logger.info("wrote chart to %s", args.chart)

        return 0
    except Exception as exc:
        logger.exception("indicator run failed: %s", exc)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
