"""Breakout state machine for the Jurik breakout indicator."""

from __future__ import annotations

import pandas as pd


class BreakoutStateMachine:
    """Sequentially tracks structures and breakout events."""

    def __init__(self, pivot_len: int):
        if pivot_len < 1:
            raise ValueError("pivot_len must be >= 1")
        self.pivot_len = pivot_len
        self.reset()

    def reset(self) -> None:
        self.H = None
        self.Hi = -1
        self.L = None
        self.Li = -1
        self.BreakUp = 0
        self.BreakDn = 0
        self.upper_active = False
        self.lower_active = False
        self.res_line_value = None
        self.sup_line_value = None
        self.res_line_start_idx = None
        self.res_line_end_idx = None
        self.sup_line_start_idx = None
        self.sup_line_end_idx = None
        self.upper_pivot1_value = None
        self.upper_pivot1_idx = None
        self.upper_pivot2_value = None
        self.upper_pivot2_idx = None
        self.lower_pivot1_value = None
        self.lower_pivot1_idx = None
        self.lower_pivot2_value = None
        self.lower_pivot2_idx = None
        self.prev_trend = None

    def _clear_upper(self) -> None:
        self.upper_active = False
        self.res_line_value = None
        self.res_line_start_idx = None
        self.res_line_end_idx = None
        self.upper_pivot1_value = None
        self.upper_pivot1_idx = None
        self.upper_pivot2_value = None
        self.upper_pivot2_idx = None

    def _clear_lower(self) -> None:
        self.lower_active = False
        self.sup_line_value = None
        self.sup_line_start_idx = None
        self.sup_line_end_idx = None
        self.lower_pivot1_value = None
        self.lower_pivot1_idx = None
        self.lower_pivot2_value = None
        self.lower_pivot2_idx = None

    @staticmethod
    def _valid_number(value) -> bool:
        return value is not None and not pd.isna(value)

    def update(self, idx: int, row: dict) -> dict:
        trend = bool(row["trend"])
        close = float(row["close"])
        atr = row.get("atr")
        ph = row.get("ph")
        pl = row.get("pl")
        ph_idx = row.get("ph_idx")
        pl_idx = row.get("pl_idx")

        signal = 0
        breakout_up = False
        breakout_down = False
        structure_event = False
        structure_event_side = None
        structure_event_pivot1_idx = None
        structure_event_pivot1_price = None
        structure_event_pivot2_idx = None
        structure_event_pivot2_price = None
        res_line = self.res_line_value
        sup_line = self.sup_line_value
        res_line_start_idx = self.res_line_start_idx
        res_line_end_idx = self.res_line_end_idx
        sup_line_start_idx = self.sup_line_start_idx
        sup_line_end_idx = self.sup_line_end_idx

        if self.prev_trend is not None and trend != self.prev_trend:
            self._clear_upper()
            self._clear_lower()

        if (
            trend
            and not self.upper_active
            and self._valid_number(ph)
            and self._valid_number(atr)
            and self.H is not None
            and self.Hi > self.BreakUp
            and abs(float(ph) - float(self.H)) < float(atr)
        ):
            self.upper_active = True
            self.res_line_value = float(ph)
            self.res_line_start_idx = int(ph_idx)
            self.res_line_end_idx = idx
            self.upper_pivot1_value = float(self.H)
            self.upper_pivot1_idx = int(self.Hi)
            self.upper_pivot2_value = float(ph)
            self.upper_pivot2_idx = int(ph_idx)
            structure_event = True
            structure_event_side = "upper"
            structure_event_pivot1_idx = self.upper_pivot1_idx
            structure_event_pivot1_price = self.upper_pivot1_value
            structure_event_pivot2_idx = self.upper_pivot2_idx
            structure_event_pivot2_price = self.upper_pivot2_value
            res_line = self.res_line_value
            res_line_start_idx = self.res_line_start_idx
            res_line_end_idx = self.res_line_end_idx

        if (
            (not trend)
            and not self.lower_active
            and self._valid_number(pl)
            and self._valid_number(atr)
            and self.L is not None
            and self.Li > self.BreakDn
            and abs(float(pl) - float(self.L)) < float(atr)
        ):
            self.lower_active = True
            self.sup_line_value = float(pl)
            self.sup_line_start_idx = int(pl_idx)
            self.sup_line_end_idx = idx
            self.lower_pivot1_value = float(self.L)
            self.lower_pivot1_idx = int(self.Li)
            self.lower_pivot2_value = float(pl)
            self.lower_pivot2_idx = int(pl_idx)
            structure_event = True
            structure_event_side = "lower"
            structure_event_pivot1_idx = self.lower_pivot1_idx
            structure_event_pivot1_price = self.lower_pivot1_value
            structure_event_pivot2_idx = self.lower_pivot2_idx
            structure_event_pivot2_price = self.lower_pivot2_value
            sup_line = self.sup_line_value
            sup_line_start_idx = self.sup_line_start_idx
            sup_line_end_idx = self.sup_line_end_idx

        if trend and self._valid_number(ph):
            self.H = float(ph)
            self.Hi = int(ph_idx)

        if (not trend) and self._valid_number(pl):
            self.L = float(pl)
            self.Li = int(pl_idx)

        if self.upper_active:
            self.res_line_end_idx = idx
            res_line = self.res_line_value
            res_line_start_idx = self.res_line_start_idx
            res_line_end_idx = self.res_line_end_idx
        if self.lower_active:
            self.sup_line_end_idx = idx
            sup_line = self.sup_line_value
            sup_line_start_idx = self.sup_line_start_idx
            sup_line_end_idx = self.sup_line_end_idx

        if self.upper_active and close > float(self.res_line_value):
            signal = 1
            breakout_up = True
            self.BreakUp = idx
            self._clear_upper()

        if self.lower_active and close < float(self.sup_line_value):
            signal = -1
            breakout_down = True
            self.BreakDn = idx
            self._clear_lower()

        self.prev_trend = trend
        structure_side = "upper" if self.upper_active else "lower" if self.lower_active else None

        return {
            "res_line": res_line,
            "sup_line": sup_line,
            "res_line_start_idx": res_line_start_idx,
            "res_line_end_idx": res_line_end_idx,
            "sup_line_start_idx": sup_line_start_idx,
            "sup_line_end_idx": sup_line_end_idx,
            "structure_active": self.upper_active or self.lower_active,
            "structure_side": structure_side,
            "structure_event": structure_event,
            "structure_event_side": structure_event_side,
            "structure_event_pivot1_idx": structure_event_pivot1_idx,
            "structure_event_pivot1_price": structure_event_pivot1_price,
            "structure_event_pivot2_idx": structure_event_pivot2_idx,
            "structure_event_pivot2_price": structure_event_pivot2_price,
            "signal": signal,
            "breakout_up": breakout_up,
            "breakout_down": breakout_down,
        }
