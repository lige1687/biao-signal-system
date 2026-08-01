"""Plotly 图表：K线、均线、结构标记、成交量与筹码分布代理。"""
from __future__ import annotations

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from lei_signal.domain.types import StructureInstance
from lei_signal.features.volume_profile import VolumeProfileProxy

COLOR_HEX = {
    "green": "#16a34a",
    "gray": "#9ca3af",
    "black": "#111827",
    "unknown": "#e5e7eb",
}

MA_COLORS = {
    "sma20": "#f59e0b",
    "ema20": "#2563eb",
    "ema60": "#7c3aed",
    "ema120": "#db2777",
}


def build_price_figure(
    frame: pd.DataFrame,
    *,
    structures: list[StructureInstance] | None = None,
    b1_price: float | None = None,
    profile: VolumeProfileProxy | None = None,
) -> go.Figure:
    """主图：K线 + 四条均线 + 颜色带 + 结构标记 + 成交量。"""
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.74, 0.26],
        vertical_spacing=0.04,
        subplot_titles=("复权K线 · MA20/EMA20/EMA60/EMA120", "成交量"),
    )

    figure.add_trace(
        go.Candlestick(
            x=frame.index,
            open=frame["open"],
            high=frame["high"],
            low=frame["low"],
            close=frame["close"],
            name="复权K线",
            increasing_line_color="#ef4444",
            decreasing_line_color="#16a34a",
        ),
        row=1,
        col=1,
    )

    labels = {"sma20": "MA20", "ema20": "EMA20", "ema60": "EMA60", "ema120": "EMA120"}
    for column, label in labels.items():
        if column in frame.columns:
            figure.add_trace(
                go.Scatter(
                    x=frame.index,
                    y=frame[column],
                    name=label,
                    line={"width": 1.4, "color": MA_COLORS[column]},
                ),
                row=1,
                col=1,
            )

    # 颜色状态带
    if "signal_color" in frame.columns:
        figure.add_trace(
            go.Scatter(
                x=frame.index,
                y=frame["low"] * 0.985,
                mode="markers",
                name="颜色状态",
                marker={
                    "size": 5,
                    "color": frame["signal_color"].map(COLOR_HEX).fillna("#e5e7eb"),
                    "symbol": "square",
                },
                customdata=frame[["signal_color", "signal_reason"]].to_numpy(),
                hovertemplate="%{x|%Y-%m-%d}<br>状态=%{customdata[0]}<br>%{customdata[1]}<extra></extra>",
            ),
            row=1,
            col=1,
        )

    # 结构标记
    for structure in structures or []:
        if structure.side == "bottom" and structure.c_price is not None:
            live = structure.invalidated_date is None
            figure.add_hline(
                y=structure.c_price,
                line={
                    "color": "#059669" if live else "#9ca3af",
                    "width": 1.2,
                    "dash": "dot" if live else "dashdot",
                },
                annotation_text=(
                    f"底部C {structure.c_price:.3f}"
                    f"{'' if live else '（已失效）'}"
                ),
                annotation_position="bottom left",
                row=1,
                col=1,
            )
        if structure.side == "top" and structure.neckline is not None:
            active = structure.invalidated_date is None and structure.confirmed_date is not None
            if active:
                figure.add_hline(
                    y=structure.neckline,
                    line={"color": "#dc2626", "width": 1.2, "dash": "dot"},
                    annotation_text=f"顶部颈线 {structure.neckline:.3f}",
                    annotation_position="top left",
                    row=1,
                    col=1,
                )

    if b1_price is not None:
        figure.add_hline(
            y=b1_price,
            line={"color": "#ea580c", "width": 1.4, "dash": "dash"},
            annotation_text=f"B1第一阻力 {b1_price:.3f}",
            annotation_position="top right",
            row=1,
            col=1,
        )

    if profile is not None:
        for value, label, color in (
            (profile.poc, "POC（代理）", "#0891b2"),
            (profile.vah, "VAH（代理）", "#64748b"),
            (profile.val, "VAL（代理）", "#64748b"),
        ):
            figure.add_hline(
                y=value,
                line={"color": color, "width": 1.0, "dash": "longdash"},
                annotation_text=label,
                annotation_position="right",
                row=1,
                col=1,
            )

    volume_colors = (
        frame["signal_color"].map(COLOR_HEX).fillna("#cbd5e1")
        if "signal_color" in frame.columns
        else "#94a3b8"
    )
    figure.add_trace(
        go.Bar(x=frame.index, y=frame["volume"], name="成交量", marker_color=volume_colors),
        row=2,
        col=1,
    )
    if "volume_mean20" in frame.columns:
        figure.add_trace(
            go.Scatter(
                x=frame.index,
                y=frame["volume_mean20"],
                name="20日均量",
                line={"width": 1.2, "color": "#f97316"},
            ),
            row=2,
            col=1,
        )

    figure.update_layout(
        height=760,
        xaxis_rangeslider_visible=False,
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.06},
        margin={"l": 40, "r": 40, "t": 60, "b": 30},
    )
    return figure


def build_volume_profile_figure(profile: VolumeProfileProxy) -> go.Figure:
    """筹码分布代理横向柱状图。标题必须写「代理」。"""
    centers = [
        (profile.bin_edges[index] + profile.bin_edges[index + 1]) / 2
        for index in range(len(profile.bin_volumes))
    ]
    figure = go.Figure()
    figure.add_trace(
        go.Bar(
            x=list(profile.bin_volumes),
            y=centers,
            orientation="h",
            name="代理成交量分布",
            marker_color="#93c5fd",
        )
    )
    for value, label, color in (
        (profile.poc, "POC", "#0891b2"),
        (profile.vah, "VAH", "#475569"),
        (profile.val, "VAL", "#475569"),
        (profile.current_price, "当前价", "#dc2626"),
    ):
        figure.add_hline(
            y=value,
            line={"color": color, "width": 1.2, "dash": "dot"},
            annotation_text=label,
        )
    figure.update_layout(
        height=460,
        title=(
            f"筹码分布代理（最近{profile.window}根，{profile.bins}个价格箱，"
            f"价值区{profile.value_area:.0%}）—— 非真实持仓成本"
        ),
        xaxis_title="代理成交量",
        yaxis_title="价格",
        margin={"l": 40, "r": 30, "t": 60, "b": 30},
    )
    return figure


def build_stage_history_figure(history_frame: pd.DataFrame) -> go.Figure:
    """阶段演进图。"""
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=history_frame.index,
            y=history_frame["stage_rank"],
            mode="lines+markers",
            name="机会阶段",
            line={"width": 1.6, "color": "#2563eb"},
            customdata=history_frame[["stage_cn"]].to_numpy(),
            hovertemplate="%{x|%Y-%m-%d}<br>阶段=%{customdata[0]}<extra></extra>",
        )
    )
    figure.update_layout(
        height=320,
        yaxis={
            "tickmode": "array",
            "tickvals": [0, 1, 2, 3, 4, 5],
            "ticktext": ["无线索", "底部观察", "结构确认", "早期转强", "共同确认", "趋势增强"],
        },
        margin={"l": 40, "r": 30, "t": 30, "b": 30},
        hovermode="x unified",
    )
    return figure


__all__ = [
    "COLOR_HEX",
    "MA_COLORS",
    "build_price_figure",
    "build_stage_history_figure",
    "build_volume_profile_figure",
]
