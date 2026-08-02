"""Plotly 图表：K线、均线、20周期抵扣价、量能、结构标记。

设计原则
--------
参考用户旧看板的简洁风格：

- K线本体不再被文字档位糊住；所有水平档位含义由 :func:`collect_levels`
  在图表外的表格展示。
- Y 轴放在右侧（与同花顺/旧看板一致），左侧留给结构线/抵扣价等注释空间。
- 颜色更克制：EMA20 蓝、SMA20 琥珀虚线、20 周期抵扣价紫虚线。
- 量能按 **放量/温和/正常/缩量** 四级配色，对应 :func:`_classify_volume`。
- 图内结构线**只画关键的几条**（B1 + 活跃顶部颈线 + 主结构 C）；
  其余结构只在档位表里出现，避免「灰色线条覆盖整个图表」。

K线颜色模式
-----------
``build_price_figure`` 支持两种 K线颜色模式，通过 ``color_mode`` 参数切换：

- ``red_green``（默认，A股惯例）：收盘高于开盘为红色（``#e33d47``），
  收盘低于开盘为绿色（``#0b9b64``）。下方保留日级 LEI 颜色小方块。
- ``lei_color``（LEI 三色模式）：**每根K线整体**按当日 ``signal_color``
  上色——绿/灰/黑三种状态直接体现在 K 线本体的填充和边框上。

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

# LEI 三色 hex（与 collect_levels 共用）。
COLOR_HEX = {
    "green": "#0b9b64",
    "gray": "#8c96a8",
    "black": "#1f2937",
    "unknown": "#c9a227",
}

#: LEI 三色在 K 线上的中文化映射（仅展示用，不参与任何计算）。
COLOR_CN = {"green": "绿色", "gray": "灰色", "black": "黑色", "unknown": "未知"}

# 与用户旧看板一致的均线配色。
MA_COLORS = {
    "sma20": "#d89216",   # 琥珀虚线
    "ema20": "#3867d6",   # 蓝实线
    "ema60": "#9a65b0",   # 紫灰
    "ema120": "#c25450",  # 暗红
}

# 20 周期抵扣价用紫色虚线（与旧看板一致）。
_REF20_COLOR = "#8d4bd3"

# A 股惯例：涨红跌绿（与美股相反）。
_RED_GREEN_UP = "#e33d47"
_RED_GREEN_DOWN = "#0b9b64"

# 量能四级配色（与旧看板一致）。
_VOL_COLORS = {
    "放量": "#e8590c",
    "温和": "#f4a261",
    "正常": "#8aa0bd",
    "缩量": "#9cc4b2",
}


def _classify_volume(ratio: float) -> str:
    """根据量比（与 20 日均量之比）返回放量/温和/正常/缩量。"""
    if pd.isna(ratio):
        return "正常"
    if ratio >= 2.0:
        return "放量"
    if ratio >= 1.2:
        return "温和"
    if ratio < 0.8:
        return "缩量"
    return "正常"


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


def _candle_trace(frame: pd.DataFrame) -> go.Candlestick:
    """LEI 颜色模式下回退路径使用的 K 线 trace（按 A 股涨跌色）。"""
    return go.Candlestick(
        x=frame.index,
        open=frame["open"],
        high=frame["high"],
        low=frame["low"],
        close=frame["close"],
        name="K线",
        increasing_line_color=_RED_GREEN_UP,
        decreasing_line_color=_RED_GREEN_DOWN,
        showlegend=True,
    )


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
    figure.add_trace(_candle_trace(frame), row=1, col=1)


def _select_chart_structures(
    structures: list[StructureInstance] | None,
    b1_price: float | None,
) -> tuple[list[StructureInstance], list[StructureInstance], float | None]:
    """把结构分为「图上画」与「只在表里」两组。

    - **图上画**：B1 阻力、活跃顶部颈线、主结构 C（最近确认的 live 底部）。
    - **只在表里**：其他次要底部/已失效结构，避免图上灰色线密麻。

    主结构判定：取 ``live_bottoms`` 中 ``confirmed_date`` 最大的一个。
    """
    structures = structures or []
    chart_lines: list[StructureInstance] = []
    table_only: list[StructureInstance] = []

    live_bottoms = [
        s for s in structures
        if s.side == "bottom"
        and s.c_price is not None
        and s.invalidated_date is None
        and s.confirmed_date is not None
    ]
    primary_bottom: StructureInstance | None = None
    if live_bottoms:
        primary_bottom = max(
            live_bottoms,
            key=lambda s: s.confirmed_date or s.detected_date,
        )

    active_tops = [
        s for s in structures
        if s.side == "top"
        and s.neckline is not None
        and s.invalidated_date is None
        and s.confirmed_date is not None
    ]
    # 最多 3 条活跃顶部，避免顶部结构多时图上糊住。
    active_tops_sorted = sorted(
        active_tops,
        key=lambda s: s.confirmed_date or s.detected_date,
        reverse=True,
    )[:3]

    chart_lines = active_tops_sorted + ([primary_bottom] if primary_bottom else [])
    seen = {id(s) for s in chart_lines}
    table_only = [s for s in structures if id(s) not in seen]
    return chart_lines, table_only, b1_price


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


def _add_segment_line(
    figure: go.Figure,
    *,
    x0: object,
    x1: object,
    y: float,
    color: str,
    width: float = 1.2,
    dash: str = "dot",
) -> None:
    """画一条只在 [x0, x1] 区间内可见的水平段（避免 add_hline 跨整图）。"""
    if x0 == x1:
        return
    figure.add_shape(
        type="line",
        xref="x", yref="y",
        x0=x0, x1=x1, y0=y, y1=y,
        line={"color": color, "width": width, "dash": dash},
        row=1, col=1,
    )


def build_price_figure(
    frame: pd.DataFrame,
    *,
    structures: list[StructureInstance] | None = None,
    b1_price: float | None = None,
    profile: VolumeProfileProxy | None = None,
    color_mode: ColorMode = "red_green",
) -> go.Figure:
    """主图：K线 + 四条均线 + 20周期抵扣价 + 关键结构线 + 量能（4 级配色）。

    设计原则：图表本体只画线，所有水平档位含义由 :func:`collect_levels`
    在图表外的表格展示。
    """
    figure = make_subplots(
        rows=2,
        cols=1,
        shared_xaxes=True,
        row_heights=[0.78, 0.22],
        vertical_spacing=0.05,
        subplot_titles=(
            (
                "复权K线 · 绿灰黑三色"
                if color_mode == "lei_color"
                else "复权K线 · EMA20/SMA20/抵扣价"
            ),
            "成交量（放量/温和/正常/缩量）",
        ),
    )

    _add_candle_traces(figure, frame, color_mode)

    # 四条均线：EMA20 主、SMA20 虚线辅助、EMA60/EMA120 长周期背景。
    labels = {"sma20": "SMA20", "ema20": "EMA20", "ema60": "EMA60", "ema120": "EMA120"}
    for column, label in labels.items():
        if column in frame.columns:
            figure.add_trace(
                go.Scatter(
                    x=frame.index,
                    y=frame[column],
                    name=label,
                    line={
                        "width": 1.8 if column == "ema20" else 1.3,
                        "color": MA_COLORS[column],
                        "dash": "dash" if column == "sma20" else "solid",
                    },
                    showlegend=column in {"sma20", "ema20"},
                    hoverinfo="skip",
                ),
                row=1, col=1,
            )

    # 20 周期抵扣价（=20 周期前的收盘价；用 close_lag20 列）。
    if "close_lag20" in frame.columns:
        figure.add_trace(
            go.Scatter(
                x=frame.index,
                y=frame["close_lag20"],
                name="20周期抵扣价",
                line={"width": 1.2, "color": _REF20_COLOR, "dash": "dot"},
                opacity=0.7,
                showlegend=True,
                hoverinfo="skip",
            ),
            row=1, col=1,
        )

    # 颜色状态带：red_green 模式下显示（LEI 模式下 K 线本体已上色，省略）。
    if color_mode == "red_green" and "signal_color" in frame.columns:
        figure.add_trace(
            go.Scatter(
                x=frame.index,
                y=frame["low"] * 0.985,
                mode="markers",
                name="LEI颜色",
                marker={
                    "size": 4,
                    "color": frame["signal_color"].map(COLOR_HEX).fillna("#e5e7eb"),
                    "symbol": "square",
                },
                showlegend=False,
                customdata=frame[["signal_color", "signal_reason"]].to_numpy(),
                hovertemplate="%{x|%Y-%m-%d}<br>状态=%{customdata[0]}<br>%{customdata[1]}<extra></extra>",
            ),
            row=1, col=1,
        )

    # 结构标记：仅画关键的「主底部 C + 活跃顶部颈线 + B1」，
    # 其余结构全部进右侧表格，避免图上灰色线条覆盖整个图表。
    chart_lines, _, b1_to_show = _select_chart_structures(structures, b1_price)
    last_date = frame.index[-1] if len(frame) else None
    for structure in chart_lines:
        if structure.side == "bottom" and structure.c_price is not None:
            x0 = structure.detected_date or frame.index[0]
            x1 = structure.invalidated_date or last_date
            live = structure.invalidated_date is None
            _add_segment_line(
                figure,
                x0=x0, x1=x1,
                y=float(structure.c_price),
                color="#059669" if live else "#9ca3af",
                width=1.2,
                dash="dot" if live else "dashdot",
            )
        if (
            structure.side == "top"
            and structure.neckline is not None
            and structure.invalidated_date is None
            and structure.confirmed_date is not None
        ):
            x0 = structure.detected_date or structure.confirmed_date
            x1 = structure.invalidated_date or last_date
            _add_segment_line(
                figure,
                x0=x0, x1=x1,
                y=float(structure.neckline),
                color="#dc2626",
                width=1.2,
                dash="dot",
            )

    if b1_to_show is not None:
        figure.add_shape(
            type="line",
            xref="x", yref="y",
            x0=frame.index[0], x1=last_date,
            y0=b1_to_show, y1=b1_to_show,
            line={"color": "#ea580c", "width": 1.4, "dash": "dash"},
            row=1, col=1,
        )

    # 量能：按 ratio 分级配色（放量/温和/正常/缩量）。
    if "volume_ratio20" in frame.columns:
        vol_states = frame["volume_ratio20"].map(_classify_volume)
        vol_colors = vol_states.map(lambda s: _VOL_COLORS.get(s, _VOL_COLORS["正常"]))
    else:
        vol_colors = "#8aa0bd"
    figure.add_trace(
        go.Bar(
            x=frame.index,
            y=frame["volume"],
            name="成交量",
            marker_color=vol_colors,
            hovertemplate="%{x|%Y-%m-%d}<br>量=%{y:.0f}<extra></extra>",
        ),
        row=2, col=1,
    )
    if "volume_mean20" in frame.columns:
        figure.add_trace(
            go.Scatter(
                x=frame.index,
                y=frame["volume_mean20"],
                name="20日均量",
                line={"width": 1.0, "color": "#475569"},
                showlegend=False,
                hoverinfo="skip",
            ),
            row=2, col=1,
        )

    figure.update_layout(
        height=620,
        # 显式锁定 legend：避免自动堆叠产生拥挤（多trace时）。
        legend={
            "orientation": "h",
            "y": 1.08,
            "x": 0,
            "xanchor": "left",
            "yanchor": "bottom",
            "traceorder": "normal",
        },
        margin={"l": 50, "r": 70, "t": 50, "b": 20},
        dragmode="zoom",
        hovermode="x unified",
        # Y 轴放右侧（与旧看板/同花顺一致），左侧留白给结构线/注释。
        yaxis={
            "position": 1.0,
            "side": "right",
            "showgrid": True,
            "gridcolor": "#edf1f6",
            "zeroline": False,
        },
        yaxis2={
            "position": 1.0,
            "side": "right",
            "showgrid": False,
            "zeroline": False,
        },
        # 成交量子图的迷你 range slider 供用户拖动缩放主图。
        xaxis2_rangeslider_visible=True,
        xaxis2_rangeslider_thickness=0.06,
        plot_bgcolor="#ffffff",
        paper_bgcolor="#ffffff",
        font={
            "family": "-apple-system,BlinkMacSystemFont,Segoe UI,PingFang SC,sans-serif",
            "color": "#172033",
        },
    )
    figure.update_xaxes(
        rangebreaks=[{"bounds": ["sat", "mon"]}],
        showgrid=False,
        zeroline=False,
        showline=True,
        linecolor="#d9e0ea",
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
    "COLOR_CN",
    "MA_COLORS",
    "build_price_figure",
    "build_stage_history_figure",
    "build_volume_profile_figure",
    "collect_levels",
]