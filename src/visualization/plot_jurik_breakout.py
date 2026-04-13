"""Plotly chart output for the Jurik breakout indicator."""

from __future__ import annotations

from pathlib import Path

import pandas as pd

UP_COLOR = "#53d769"
DOWN_COLOR = "#5aa9ff"
UP_CANDLE = "#26a69a"
DOWN_CANDLE = "#ef5350"
GRID_COLOR = "rgba(148, 163, 184, 0.12)"
BG_COLOR = "#0b1220"
PAPER_COLOR = "#0f172a"
TEXT_COLOR = "#dbe4f0"


def _iter_trend_segments(df: pd.DataFrame) -> list[tuple[int, int, bool]]:
    segments: list[tuple[int, int, bool]] = []
    if df.empty:
        return segments

    start = 0
    current = bool(df.iloc[0]["trend"])
    for idx in range(1, len(df)):
        trend = bool(df.iloc[idx]["trend"])
        if trend != current:
            segments.append((start, idx - 1, current))
            start = idx - 1
            current = trend
    segments.append((start, len(df) - 1, current))
    return segments


def _iter_level_segments(
    df: pd.DataFrame,
    level_col: str,
    start_col: str,
    end_col: str,
) -> list[tuple[int, int, float]]:
    segments: list[tuple[int, int, float]] = []
    active = False
    start_idx = 0
    end_idx = 0
    level = 0.0

    for _, row in df.iterrows():
        if pd.notna(row[level_col]):
            active = True
            start_idx = int(row[start_col]) if pd.notna(row[start_col]) else int(row.name)
            end_idx = int(row[end_col]) if pd.notna(row[end_col]) else int(row.name)
            level = float(row[level_col])
            continue

        if active:
            segments.append((start_idx, end_idx, level))
            active = False

    if active:
        segments.append((start_idx, end_idx, level))

    return segments


def _price_padding(df: pd.DataFrame) -> float:
    return float((df["high"].max() - df["low"].min()) * 0.03 or 1.0)


def _build_missing_calendar_dates(df: pd.DataFrame) -> list[pd.Timestamp]:
    if df.empty:
        return []

    observed = pd.DatetimeIndex(pd.to_datetime(df["date"], errors="raise")).normalize().unique().sort_values()
    full_span = pd.date_range(observed.min(), observed.max(), freq="D")
    return list(full_span.difference(observed))


def _plot_structure_events(fig, df: pd.DataFrame, padding: float) -> None:
    try:
        import plotly.graph_objects as go
    except ImportError as exc:
        raise RuntimeError("plotly is required for chart output") from exc

    required = {
        "structure_event",
        "structure_event_side",
        "structure_event_pivot1_idx",
        "structure_event_pivot1_price",
        "structure_event_pivot2_idx",
        "structure_event_pivot2_price",
    }
    if not required.issubset(df.columns):
        return

    events = df[df["structure_event"].fillna(False)].copy()
    if events.empty:
        return

    for _, row in events.iterrows():
        is_upper = row["structure_event_side"] == "upper"
        color = UP_COLOR if is_upper else DOWN_COLOR
        pivot1_idx = int(row["structure_event_pivot1_idx"])
        pivot2_idx = int(row["structure_event_pivot2_idx"])
        pivot1_price = float(row["structure_event_pivot1_price"])
        pivot2_price = float(row["structure_event_pivot2_price"])
        text_y_shift = padding * (0.5 if is_upper else -0.5)

        fig.add_trace(
            go.Scatter(
                x=[df.iloc[pivot1_idx]["date"], df.iloc[pivot2_idx]["date"]],
                y=[pivot1_price, pivot2_price],
                mode="lines",
                showlegend=False,
                hoverinfo="skip",
                line={"width": 1.25, "dash": "dot", "color": color},
            )
        )
        fig.add_trace(
            go.Scatter(
                x=[df.iloc[pivot1_idx]["date"], df.iloc[pivot2_idx]["date"]],
                y=[pivot1_price + text_y_shift, pivot2_price + text_y_shift],
                mode="text",
                text=["\u2713", "\u2713"],
                textfont={"size": 15, "color": color},
                showlegend=False,
                hoverinfo="skip",
            )
        )


def plot_jurik_breakout(df: pd.DataFrame, output_file: str, show: bool = False) -> None:
    """Render a TradingView-inspired HTML chart if Plotly is available."""
    try:
        import plotly.graph_objects as go
    except ImportError as exc:
        raise RuntimeError("plotly is required for chart output") from exc

    df = df.copy()
    df["date"] = pd.to_datetime(df["date"], errors="raise")
    padding = _price_padding(df)
    missing_dates = _build_missing_calendar_dates(df)

    fig = go.Figure()
    fig.add_trace(
        go.Candlestick(
            x=df["date"],
            open=df["open"],
            high=df["high"],
            low=df["low"],
            close=df["close"],
            name="Price",
            increasing={"line": {"color": UP_CANDLE, "width": 1}, "fillcolor": UP_CANDLE},
            decreasing={"line": {"color": DOWN_CANDLE, "width": 1}, "fillcolor": DOWN_CANDLE},
        )
    )

    for start, end, trend in _iter_trend_segments(df):
        color = UP_COLOR if trend else DOWN_COLOR
        x = df["date"].iloc[start : end + 1]
        y = df["jma"].iloc[start : end + 1]
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                hoverinfo="skip",
                showlegend=False,
                line={"width": 12, "color": color},
                opacity=0.18,
            )
        )
        fig.add_trace(
            go.Scatter(
                x=x,
                y=y,
                mode="lines",
                name="JMA" if start == 0 else None,
                showlegend=start == 0,
                line={"width": 3.2, "color": color},
            )
        )

    for start, end, level in _iter_level_segments(df, "res_line", "res_line_start_idx", "res_line_end_idx"):
        fig.add_trace(
            go.Scatter(
                x=[df.iloc[start]["date"], df.iloc[end]["date"]],
                y=[level, level],
                mode="lines",
                name="Resistance",
                showlegend=False,
                line={"width": 1.25, "dash": "dot", "color": "rgba(83, 215, 105, 0.95)"},
            )
        )

    for start, end, level in _iter_level_segments(df, "sup_line", "sup_line_start_idx", "sup_line_end_idx"):
        fig.add_trace(
            go.Scatter(
                x=[df.iloc[start]["date"], df.iloc[end]["date"]],
                y=[level, level],
                mode="lines",
                name="Support",
                showlegend=False,
                line={"width": 1.25, "dash": "dot", "color": "rgba(90, 169, 255, 0.95)"},
            )
        )

    _plot_structure_events(fig, df, padding)

    if "signal" in df.columns and (df["signal"] == 1).any():
        up = df[df["signal"] == 1].copy()
        y = up["breakout_level"].fillna(up["high"]) + padding * 0.55
        fig.add_trace(
            go.Scatter(
                x=up["date"],
                y=y,
                mode="markers+text",
                text=["Break Up"] * len(up),
                textposition="top center",
                name="Break Up",
                marker={
                    "symbol": "arrow-up",
                    "size": 14,
                    "color": UP_COLOR,
                    "line": {"color": "#f8fafc", "width": 1},
                },
                textfont={"size": 11, "color": UP_COLOR},
            )
        )

    if "signal" in df.columns and (df["signal"] == -1).any():
        down = df[df["signal"] == -1].copy()
        y = down["breakout_level"].fillna(down["low"]) - padding * 0.55
        fig.add_trace(
            go.Scatter(
                x=down["date"],
                y=y,
                mode="markers+text",
                text=["Break Dn"] * len(down),
                textposition="bottom center",
                name="Break Down",
                marker={
                    "symbol": "arrow-down",
                    "size": 14,
                    "color": DOWN_COLOR,
                    "line": {"color": "#f8fafc", "width": 1},
                },
                textfont={"size": 11, "color": DOWN_COLOR},
            )
        )

    fig.update_layout(
        title={"text": "Jurik Breakout", "x": 0.02, "font": {"size": 20, "color": TEXT_COLOR}},
        xaxis_title=None,
        yaxis_title=None,
        xaxis_rangeslider_visible=False,
        paper_bgcolor=PAPER_COLOR,
        plot_bgcolor=BG_COLOR,
        font={"color": TEXT_COLOR, "family": "Arial, sans-serif"},
        hovermode="x unified",
        dragmode="pan",
        legend={
            "orientation": "h",
            "yanchor": "bottom",
            "y": 1.01,
            "xanchor": "left",
            "x": 0.01,
            "bgcolor": "rgba(15, 23, 42, 0.65)",
        },
        margin={"l": 56, "r": 24, "t": 52, "b": 40},
    )
    fig.update_xaxes(
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        showspikes=True,
        spikemode="across",
        spikecolor="rgba(219, 228, 240, 0.25)",
        rangeslider_visible=False,
        rangebreaks=[{"values": missing_dates}] if missing_dates else [],
    )
    fig.update_yaxes(
        showgrid=True,
        gridcolor=GRID_COLOR,
        zeroline=False,
        side="right",
    )

    output_path = Path(output_file)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fig.write_html(
        str(output_path),
        config={
            "scrollZoom": True,
            "displaylogo": False,
            "modeBarButtonsToRemove": ["lasso2d", "select2d"],
        },
    )
    if show:
        fig.show()
