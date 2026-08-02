"""ECharts K线渲染器——把 LEI 分析结果嵌入 Streamlit。

为什么用 ECharts
----------------
Plotly 的拖拽/缩放体验远不如 ECharts 的 dataZoom。本模块把 LEI 分析管线
产出的完整信号数据（颜色、均线、抵扣价、结构、量能、关键性波动）序列化
为 JSON，交给 ECharts 渲染，交互体验与用户旧看板一致。

数据来源
--------
所有数据来自 :class:`~lei_signal.compose.pipeline.AnalysisResult`——
不重新计算任何指标，只做展示层序列化。
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd

from lei_signal.compose.pipeline import AnalysisResult

_ECHARTS_JS = Path(__file__).parent / "assets" / "echarts.min.js"

# 与旧看板一致的配色。
_STATE_COLORS = {
    "green": "#0b9b64",
    "gray": "#8c96a8",
    "black": "#1f2937",
    "unknown": "#c9a227",
}
_STATE_LABELS = {
    "green": "绿色",
    "gray": "灰色",
    "black": "黑色",
    "unknown": "未知",
}
_PRICE_UP = "#e33d47"
_PRICE_DOWN = "#0b9b64"
_VOL_COLORS = {
    "放量": "#e8590c",
    "温和": "#f4a261",
    "正常": "#8aa0bd",
    "缩量": "#9cc4b2",
}


def _classify_vol(ratio: float) -> str:
    if pd.isna(ratio):
        return "正常"
    if ratio >= 2.0:
        return "放量"
    if ratio >= 1.2:
        return "温和"
    if ratio < 0.8:
        return "缩量"
    return "正常"


def _serialize_result(
    result: AnalysisResult,
    *,
    color_mode: str,
    max_bars: int = 1000,
) -> dict[str, Any]:
    """把 AnalysisResult 序列化为 ECharts 可消费的 JSON 结构。

    ``max_bars`` 控制传给前端的最多 K 线根数（默认 1000，足够拖拽回看）。
    dataZoom 的 ``start`` 在 :func:`_build_html` 中按 ``default_bars`` 计算，
    默认只展示最后 60 根，用户拖拽滑块可回看全部。
    """
    # 传全部数据（截断到 max_bars 上限），让用户拖拽时能看到历史。
    frame = result.frame.tail(max_bars).copy()
    dates = [idx.strftime("%Y-%m-%d") for idx in frame.index]

    # OHLC
    ohlc = [
        [round(r["open"], 4), round(r["close"], 4), round(r["low"], 4), round(r["high"], 4)]
        for _, r in frame.iterrows()
    ]

    # 均线
    ema20 = [round(r, 4) if pd.notna(r) else None for r in frame.get("ema20", [])]
    sma20 = [round(r, 4) if pd.notna(r) else None for r in frame.get("sma20", [])]
    ema60 = [round(r, 4) if pd.notna(r) else None for r in frame.get("ema60", [])]
    ema120 = [round(r, 4) if pd.notna(r) else None for r in frame.get("ema120", [])]

    # 20 周期抵扣价
    ref20 = [round(r, 4) if pd.notna(r) else None for r in frame.get("close_lag20", [])]

    # LEI 颜色状态
    states = [str(r) if pd.notna(r) else "unknown" for r in frame.get("signal_color", [])]

    # 量能
    volumes = [float(v) for v in frame["volume"]]
    vol_ratios = [
        float(r) if pd.notna(r) else 1.0
        for r in frame.get("volume_ratio20", [1.0] * len(frame))
    ]
    vol_states = [_classify_vol(r) for r in vol_ratios]

    # 结构标记：底部 C + 顶部颈线
    a = result.assessment
    structure_lines: list[dict[str, Any]] = []

    # B1
    if a.b1_price is not None:
        structure_lines.append({
            "yAxis": round(a.b1_price, 4),
            "label": "B1",
            "color": "#ea580c",
            "dash": "dash",
        })

    # 主底部 C + 活跃顶部颈线
    live_bottoms = [
        s for s in (result.structures or [])
        if s.side == "bottom" and s.c_price is not None and s.invalidated_date is None
    ]
    if live_bottoms:
        primary = max(live_bottoms, key=lambda s: s.confirmed_date or s.detected_date)
        if primary.c_price is not None:
            structure_lines.append({
                "yAxis": round(float(primary.c_price), 4),
                "label": "C",
                "color": "#059669",
                "dash": "dot",
            })

    active_tops = [
        s for s in (result.structures or [])
        if s.side == "top" and s.neckline is not None
        and s.invalidated_date is None and s.confirmed_date is not None
    ]
    for top in active_tops[:3]:
        if top.neckline is not None:
            structure_lines.append({
                "yAxis": round(float(top.neckline), 4),
                "label": "颈线",
                "color": "#dc2626",
                "dash": "dot",
            })

    # 关键性波动（颜色从非绿→绿 或 非黑→黑 的转换日）
    key_volatility: list[dict[str, Any]] = []
    if "signal_color" in frame.columns and "color_changed" in frame.columns:
        changed = frame[frame["color_changed"] == True]  # noqa: E712
        for idx, row in changed.iterrows():
            state = str(row.get("signal_color", "unknown"))
            if state in ("green", "black"):
                key_volatility.append({
                    "date": idx.strftime("%Y-%m-%d"),
                    "state": state,
                    "label": _STATE_LABELS.get(state, state),
                })

    return {
        "dates": dates,
        "ohlc": ohlc,
        "ema20": ema20,
        "sma20": sma20,
        "ema60": ema60,
        "ema120": ema120,
        "ref20": ref20,
        "states": states,
        "volumes": volumes,
        "volStates": vol_states,
        "volColors": [_VOL_COLORS.get(s, _VOL_COLORS["正常"]) for s in vol_states],
        "structureLines": structure_lines,
        "keyVolatility": key_volatility,
        "colorMode": color_mode,
        "stateColors": _STATE_COLORS,
        "priceUp": _PRICE_UP,
        "priceDown": _PRICE_DOWN,
        "symbol": result.symbol,
        "displayName": result.display_name,
        "lastClose": round(float(frame["close"].iloc[-1]), 4) if len(frame) else None,
    }


def _build_html(data: dict[str, Any], *, default_bars: int = 60, height: int = 680) -> str:
    """生成包含 ECharts 的完整 HTML 字符串。

    ``default_bars`` 控制初始展示最近多少根 K线；dataZoom 的 ``start``
    按此计算百分比，用户拖拽滑块可回看全部 ``max_bars`` 根。
    """
    echarts_js = _ECHARTS_JS.read_text(encoding="utf-8")
    data_json = json.dumps(data, ensure_ascii=False)

    # 计算初始 dataZoom start：只展示最后 default_bars 根。
    total = len(data["dates"])
    if total > default_bars:
        start_pct = round((1 - default_bars / total) * 100, 1)
    else:
        start_pct = 0

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #fff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; }}
  #chart {{ width: 100%; height: {height}px; }}
  .legend-note {{ font-size: 12px; color: #596579; padding: 4px 12px; }}
</style>
</head>
<body>
<div id="chart"></div>
<script>
{echarts_js}
</script>
<script>
const DATA = {data_json};

const stateColors = DATA.stateColors;
const stateAreas = DATA.dates.map((d, i) => {{
  const c = stateColors[DATA.states[i]] || stateColors.unknown;
  return [{{ xAxis: d, itemStyle: {{ color: c, opacity: 0.04 }} }}, {{ xAxis: d }}];
}});

const candleStyle = DATA.colorMode === 'lei_color'
  ? DATA.dates.map((d, i) => {{
      const c = stateColors[DATA.states[i]] || stateColors.unknown;
      return {{ itemStyle: {{ color: c, color0: c, borderColor: c, borderColor0: c }} }};
    }})
  : null;

const priceDefaults = {{
  color: DATA.priceUp, color0: DATA.priceDown,
  borderColor: DATA.priceUp, borderColor0: DATA.priceDown
}};
const stateDefaults = {{
  color: stateColors.gray, color0: stateColors.gray,
  borderColor: stateColors.gray, borderColor0: stateColors.gray
}};

const structureMarkLines = DATA.structureLines.map(l => ({{
  yAxis: l.yAxis,
  label: {{
    show: true, position: "insideStartTop",
    formatter: l.label + " " + l.yAxis,
    color: l.color, fontSize: 10
  }},
  lineStyle: {{ color: l.color, type: l.dash, width: 1.2, opacity: 0.7 }}
}}));

const kvLines = DATA.keyVolatility.map(k => ({{
  xAxis: k.date,
  label: {{
    show: true, position: "insideEndTop",
    formatter: k.label, color: stateColors[k.state] || "#888",
    fontSize: 9, fontWeight: "bold"
  }},
  lineStyle: {{ color: stateColors[k.state] || "#888", type: "dashed", width: 1, opacity: 0.5 }}
}}));

const start = {start_pct};

const option = {{
  animation: false,
  backgroundColor: "#ffffff",
  textStyle: {{ color: "#68748a", fontFamily: "-apple-system,BlinkMacSystemFont,Segoe UI,PingFang SC,sans-serif" }},
  legend: {{ top: 2, data: ["K线", "EMA20", "SMA20", "20周期抵扣价", "成交量"], textStyle: {{ color: "#596579" }} }},
  tooltip: {{
    trigger: "axis", axisPointer: {{ type: "cross" }},
    backgroundColor: "rgba(255,255,255,.96)", borderColor: "#dfe5ee", textStyle: {{ color: "#172033" }}
  }},
  axisPointer: {{ link: [{{ xAxisIndex: "all" }}] }},
  grid: [
    {{ left: 66, right: 70, top: 40, height: "62%" }},
    {{ left: 66, right: 70, top: "74%", height: "16%" }}
  ],
  xAxis: [
    {{ type: "category", data: DATA.dates, boundaryGap: false,
       axisLine: {{ lineStyle: {{ color: "#d9e0ea" }} }},
       axisLabel: {{ show: false }}, splitLine: {{ show: false }},
       min: "dataMin", max: "dataMax" }},
    {{ type: "category", gridIndex: 1, data: DATA.dates, boundaryGap: false,
       axisLine: {{ lineStyle: {{ color: "#d9e0ea" }} }},
       axisLabel: {{ color: "#7c8799", hideOverlap: true }},
       splitLine: {{ show: false }}, min: "dataMin", max: "dataMax" }}
  ],
  yAxis: [
    {{ scale: true, position: "right", splitArea: {{ show: false }},
       splitLine: {{ lineStyle: {{ color: "#edf1f6" }} }},
       axisLabel: {{ color: "#7c8799" }} }},
    {{ scale: true, gridIndex: 1, position: "right", splitNumber: 2,
       splitLine: {{ show: false }},
       axisLabel: {{ color: "#7c8799" }} }}
  ],
  dataZoom: [
    {{ type: "inside", xAxisIndex: [0, 1], start: start, end: 100 }},
    {{ type: "slider", xAxisIndex: [0, 1], bottom: 4, height: 20,
       start: start, end: 100, borderColor: "#e1e6ee",
       fillerColor: "rgba(56,103,214,.12)" }}
  ],
  series: [
    {{
      name: "K线", type: "candlestick", data: candleStyle
        ? DATA.ohlc.map((item, i) => ({{ value: item, itemStyle: candleStyle[i].itemStyle }}))
        : DATA.ohlc,
      itemStyle: DATA.colorMode === 'lei_color' ? stateDefaults : priceDefaults,
      markArea: {{ silent: true, data: stateAreas }},
      markLine: {{ silent: true, symbol: ["none", "none"],
        lineStyle: {{ color: "#caa23a", type: "dashed", width: 1 }},
        label: {{ show: false }},
        data: structureMarkLines.concat(kvLines)
      }}
    }},
    {{ name: "EMA20", type: "line", data: DATA.ema20, showSymbol: false,
       lineStyle: {{ width: 1.8, color: "#3867d6" }} }},
    {{ name: "SMA20", type: "line", data: DATA.sma20, showSymbol: false,
       lineStyle: {{ width: 1.4, color: "#d89216", type: "dashed" }} }},
    {{
      name: "20周期抵扣价", type: "line", data: DATA.ref20, showSymbol: false,
      lineStyle: {{ width: 1.2, color: "#8d4bd3", type: "dotted", opacity: 0.6 }},
      connectNulls: false
    }},
    {{
      name: "成交量", type: "bar", xAxisIndex: 1, yAxisIndex: 1,
      data: DATA.volumes.map((v, i) => ({{
        value: v,
        itemStyle: {{
          color: DATA.volColors[i],
          borderColor: DATA.ohlc[i][1] >= DATA.ohlc[i][0]
            ? "rgba(227,61,71,.4)" : "rgba(11,155,100,.4)",
          borderWidth: 1
        }}
      }}))
    }}
  ]
}};

const chart = echarts.init(document.getElementById('chart'));
chart.setOption(option);
window.addEventListener('resize', () => chart.resize());
</script>
</body>
</html>"""


def render_echarts_kline(
    result: AnalysisResult,
    *,
    color_mode: str = "red_green",
    default_bars: int = 60,
    max_bars: int = 1000,
    height: int = 680,
) -> None:
    """在 Streamlit 中渲染 ECharts K线图。

    参数
    ----------
    result : AnalysisResult
        LEI 分析管线完整结果。
    color_mode : str
        ``"red_green"`` 红涨绿跌（A股惯例）或 ``"lei_color"`` 绿灰黑三色。
    default_bars : int
        初始展示最近多少根 K线（默认 60）。用户可通过 dataZoom 拖拽回看。
    max_bars : int
        传给前端的最多 K 线根数（默认 1000），限制 DOM 体积。
    height : int
        图表高度（像素）。
    """
    import streamlit.components.v1 as components

    data = _serialize_result(result, color_mode=color_mode, max_bars=max_bars)
    html = _build_html(data, default_bars=default_bars, height=height)
    components.html(html, height=height + 10, scrolling=False)


__all__ = ["render_echarts_kline"]
