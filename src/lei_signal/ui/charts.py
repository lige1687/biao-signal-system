"""Plotly 图表：K线、均线、结构标记、成交量与筹码分布代理。

K线颜色模式
-----------
``build_price_figure`` 支持两种 K线颜色模式，通过 ``color_mode`` 参数切换：

- ``red_green``（默认，A股惯例）：收盘高于开盘为红色（``#ef4444``），
  收盘低于开盘为绿色（``#16a34a``）。下方仍保留日级 LEI 颜色小方块。
- ``lei_color``（LEI 三色模式）：**每根K线整体**按当日 ``signal_color``
  上色——绿/灰/黑三种状态直接体现在 K 线本体的填充和边框上，
  不再依赖「涨红跌绿」二元信号。需要 ``frame`` 含 ``signal_color`` 列。

切换图表模式属于**展示**修改，不会改变任何底层 LEI 计算或生命周期判断。
"""
from __future__ import annotations

from typing import Literal

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from lei_signal.domain.types import StructureInstance
from lei_signal.features.volume_profile import VolumeProfileProxy

ColorMode = Literal["red_green", "lei_color"]

COLOR_HEX = {
    "green": "#16a34a",
    "gray": "#9ca3af",
    "black": "#111827",
    "unknown": "#e5e7eb",
}

#: LEI 三色在 K 线上的中文化映射（仅展示用，不参与任何计算）。
COLOR_CN = {"green": "绿色", "gray": "灰色", "black": "黑色", "unknown": "未知"}

MA_COLORS = {
    "sma20": "#f59e0b",
    "ema20": "#2563eb",
    "ema60": "#7c3aed",
    "ema120": "#db2777",
}

# A 股惯例：涨红跌绿（与美股相反）。
_RED_GREEN_UP = "#ef4444"
_RED_GREEN_DOWN = "#16a34a"


def _split_by_signal_color(frame: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """按 ``signal_color`` 列分桶，跳过未知/缺失。"""
    if "signal_color" not in frame.columns:
        return {}
    buckets: dict[str, pd.DataFrame] = {}
    for color in ("green", "gray", "black"):
        mask = frame["signal_color"] == color
        if mask.any():
            buckets[color] = frame.loc[mask]
    return buckets


def _add_candle_traces(
    figure: go.Figure,
    frame: pd.DataFrame,
    color_mode: ColorMode,
) -> None:
    """添加 K 线本体。lei_color 模式按日级 signal_color 分桶。"""
    if color_mode == "lei_color" and "signal_color" in frame.columns:
        buckets = _split_by_signal_color(frame)
        if not buckets:
            # 没有可分桶的颜色，回退到默认涨跌色（绝不静默画错色）。
            figure.add_trace(_candle_trace(frame), row=1, col=1)
            return
        for color, sub in buckets.items():
            hex_color = COLOR_HEX[color]
            figure.add_trace(
                go.Candlestick(
                    x=sub.index,
                    open=sub["open"],
                    high=sub["high"],
                    low=sub["low"],
                    close=sub["close"],
                    name=f"K线（{COLOR_CN[color]}）",
                    increasing_line_color=hex_color,
                    decreasing_line_color=hex_color,
                    increasing_fillcolor=hex_color,
                    decreasing_fillcolor=hex_color,
                    showlegend=False,
                    hovertext=[
                        f"{idx.strftime('%Y-%m-%d')} · {COLOR_CN[color]}"
                        for idx in sub.index
                    ],
                    hoverinfo="x+text",
                ),
                row=1,
                col=1,
            )
        return

    # 默认 red_green 模式：A股惯例，涨红跌绿。
    figure.add_trace(
        go.Candlestick(
            x=frame.index,
            open=frame["open"],
            high=frame["high"],
            low=frame["low"],
            close=frame["close"],
            name="复权K线",
            increasing_line_color=_RED_GREEN_UP,
            decreasing_line_color=_RED_GREEN_DOWN,
        ),
        row=1,
        col=1,
    )


def _candle_trace(frame: pd.DataFrame) -> go.Candlestick:
    """LEI 颜色模式下回退路径使用的 K 线 trace（按 A 股涨跌色）。"""
    return go.Candlestick(
        x=frame.index,
        open=frame["open"],
        high=frame["high"],
        low=frame["low"],
        close=frame["close"],
        name="复权K线",
        increasing_line_color=_RED_GREEN_UP,
        decreasing_line_color=_RED_GREEN_DOWN,
    )


def collect_levels(
    frame: pd.DataFrame,
    *,
    structures: list[StructureInstance] | None = None,
    b1_price: float | None = None,
    profile: VolumeProfileProxy | None = None,
) -> list[dict[str, object]]:
    """汇总图上水平线对应的「价格档位」，供 UI 在图表外列表展示。

    返回每条记录含 ``type / subtype / price / color / live / note``，
    与 ``build_price_figure`` 中绘制的线一一对应——一个在图上画线的类型
    必须有一条记录，保证 UI 能完整复述图上的水平线含义。
    """
    levels: list[dict[str, object]] = []
    current_price = float(frame["close"].iloc[-1]) if len(frame) else None

    for structure in structures or []:
        if structure.side == "bottom" and structure.c_price is not None:
            live = structure.invalidated_date is None
            note = ""
            if structure.confirmed_date is not None:
                note = f"确认日 {structure.confirmed_date}"
            elif structure.detected_date is not None:
                note = f"候选日 {structure.detected_date}"
            levels.append({
                "type": "底部 C",
                "subtype": "live" if live else "invalidated",
                "price": float(structure.c_price),
                "color": "#059669" if live else "#9ca3af",
                "dash": "dot" if live else "dashdot",
                "live": live,
                "note": note,
                "structure_type": structure.structure_type,
                "source_rule": structure.source_rule_id or "",
                "current_price": current_price,
            })
        if (
            structure.side == "top"
            and structure.neckline is not None
            and structure.invalidated_date is None
            and structure.confirmed_date is not None
        ):
            levels.append({
                "type": "顶部颈线",
                "subtype": "active",
                "price": float(structure.neckline),
                "color": "#dc2626",
                "dash": "dot",
                "live": True,
                "note": f"确认日 {structure.confirmed_date}",
                "structure_type": structure.structure_type,
                "source_rule": structure.source_rule_id or "",
                "current_price": current_price,
            })

    if b1_price is not None:
        levels.append({
            "type": "B1 第一阻力",
            "subtype": "reference",
            "price": float(b1_price),
            "color": "#ea580c",
            "dash": "dash",
            "live": True,
            "note": "参考前高，非强制止盈",
            "structure_type": "",
            "source_rule": "",
            "current_price": current_price,
        })

    if profile is not None:
        for value, subtype, color, label in (
            (profile.poc, "POC", "#0891b2", "POC（代理）"),
            (profile.vah, "VAH", "#64748b", "VAH（代理）"),
            (profile.val, "VAL", "#64748b", "VAL（代理）"),
        ):
            levels.append({
                "type": "筹码分布",
                "subtype": subtype,
                "price": float(value),
                "color": color,
                "dash": "longdash",
                "live": True,
                "note": label,
                "structure_type": "",
                "source_rule": "",
                "current_price": current_price,
            })

    return levels


def build_price_figure(
    frame: pd.DataFrame,
    *,
    structures: list[StructureInstance] | None = None,
    b1_price: float | None = None,
    profile: VolumeProfileProxy | None = None,
    color_mode: ColorMode = "red_green",
) -> go.Figure:
    """主图：K线 + 四条均线 + 颜色带 + 结构标记 + 成交量。

    设计原则：图表本体只画线，不写字——所有水平档位的含义由调用方通过
    :func:`collect_levels` 在图表外列表展示，避免文字叠加遮蔽 K 线。

    参数 ``color_mode``
    ------------------
    - ``"red_green"``（默认）：K 线按 A 股惯例红涨绿跌，下方保留日级 LEI 小方块。
    - ``"lei_color"``：K 线本体按当日 ``signal_color``（绿/灰/黑）染色；
      小方块带在该模式下被省略以免冗余，但成交量柱仍按日级颜色上色。
    """
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.78, 0.22],
        vertical_spacing=0.03,
        subplot_titles=(
            (
                "复权K线 · 绿灰黑三色"
                if color_mode == "lei_color"
                else "复权K线 · MA20/EMA20/EMA60/EMA120"
            ),
            "成交量",
        ),
    )

    _add_candle_traces(figure, frame, color_mode)

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

    # 颜色状态带：red_green 模式下显示（LEI 模式下 K 线本体已上色，省略）。
    if color_mode == "red_green" and "signal_color" in frame.columns:
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

    # 结构标记：仅画线 + 写入图例 hover，不在图内堆字。
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
                row=1,
                col=1,
            )
        if structure.side == "top" and structure.neckline is not None:
            active = structure.invalidated_date is None and structure.confirmed_date is not None
            if active:
                figure.add_hline(
                    y=structure.neckline,
                    line={"color": "#dc2626", "width": 1.2, "dash": "dot"},
                    row=1,
                    col=1,
                )

    if b1_price is not None:
        figure.add_hline(
            y=b1_price,
            line={"color": "#ea580c", "width": 1.4, "dash": "dash"},
            row=1,
            col=1,
        )

    if profile is not None:
        for value, color in (
            (profile.poc, "#0891b2"),
            (profile.vah, "#64748b"),
            (profile.val, "#64748b"),
        ):
            figure.add_hline(
                y=value,
                line={"color": color, "width": 1.0, "dash": "longdash"},
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

    # 体积下方的迷你 range slider 取代左侧手动画线 slider，
    # 用户直接拖动缩放主图；不展示时直接关掉即可。
    figure.update_layout(
        height=620,
        xaxis_rangeslider_visible=False,
        xaxis2_rangeslider_visible=True,
        xaxis2_rangeslider_thickness=0.06,
        hovermode="x unified",
        legend={"orientation": "h", "y": 1.06},
        margin={"l": 40, "r": 40, "t": 50, "b": 20},
        dragmode="zoom",
    )
    # 跳过周末和非交易日，让 K 线连续排列，不再出现「5 根一组中间断开」。
    # bounds ["sat","mon"] 表示从周六到周一之间的区间不画——即跳过周六周日。
    # 如果将来需要跳过 A 股节假日，在 list 里加 dict(values=["2024-10-01",...]) 即可。
    figure.update_xaxes(
        rangebreaks=[{"bounds": ["sat", "mon"]}],
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
    """阶段演进图。

    蓝线 = 机会阶段（opportunity_stage）。若 ``history_frame`` 含 ``risk_rank`` /
    ``risk_cn`` 列，叠加红线 = 风险状态（次 y 轴），两条线独立、互不覆盖。
    """
    figure = go.Figure()
    figure.add_trace(
        go.Scatter(
            x=history_frame.index,
            y=history_frame["stage_rank"],
            mode="lines+markers",
            name="机会阶段",
            line={"width": 1.6, "color": "#2563eb"},
            customdata=history_frame[["stage_cn"]].to_numpy(),
            hovertemplate="%{x|%Y-%m-%d}<br>机会阶段=%{customdata[0]}<extra></extra>",
        )
    )
    layout: dict = {
        "height": 320,
        "yaxis": {
            "tickmode": "array",
            "tickvals": [0, 1, 2, 3, 4, 5],
            "ticktext": ["无线索", "底部观察", "结构确认", "早期转强", "共同确认", "趋势增强"],
        },
        "margin": {"l": 40, "r": 50, "t": 30, "b": 30},
        "hovermode": "x unified",
    }
    if "risk_rank" in history_frame.columns:
        figure.add_trace(
            go.Scatter(
                x=history_frame.index,
                y=history_frame["risk_rank"],
                mode="lines+markers",
                name="风险状态",
                yaxis="y2",
                line={"width": 1.6, "color": "#dc2626"},
                customdata=history_frame[["risk_cn"]].to_numpy(),
                hovertemplate="%{x|%Y-%m-%d}<br>风险状态=%{customdata[0]}<extra></extra>",
            )
        )
        layout["yaxis2"] = {
            "tickmode": "array",
            "tickvals": [0, 1, 2, 3, 4, 5],
            "ticktext": ["正常", "转灰", "顶部", "黑色", "Top+Black", "C失效"],
            "overlaying": "y",
            "side": "right",
            "showgrid": False,
        }
    figure.update_layout(**layout)
    return figure


__all__ = [
    "COLOR_HEX",
    "MA_COLORS",
    "build_price_figure",
    "build_stage_history_figure",
    "build_volume_profile_figure",
    "collect_levels",
]
