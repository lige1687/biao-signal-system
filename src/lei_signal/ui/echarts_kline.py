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

# 底部构造区域色（琥珀）；顶部构造区域色（暗红）。
_BOTTOM_AREA_COLOR = "rgba(216,146,22,0.18)"
_BOTTOM_AREA_BORDER = "#d89216"
_TOP_AREA_COLOR = "rgba(220,38,38,0.15)"
_TOP_AREA_BORDER = "#dc2626"


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


def _date_to_str(d: object) -> str | None:
    """把 date/datetime 序列化为 YYYY-MM-DD。None/NaT 返回 None。"""
    if d is None:
        return None
    try:
        if pd.isna(d):
            return None
    except (TypeError, ValueError):
        pass
    if hasattr(d, "strftime"):
        return d.strftime("%Y-%m-%d")  # type: ignore[union-attr]
    return str(d)


def _serialize_result(
    result: AnalysisResult,
    *,
    color_mode: str,
    max_bars: int = 1000,
) -> dict[str, Any]:
    """把 AnalysisResult 序列化为 ECharts 可消费的 JSON 结构。

    各类图内标记分别打包，前端按 ``display`` 开关选择性渲染：
    - ``b1_line``: 第一阻力参考线
    - ``bottom_lines``: 主底部 C 线（live）
    - ``top_lines``: 活跃顶部颈线
    - ``bottom_areas``: 底部构造 markArea（候选→确认→失效区间）
    - ``top_areas``: 顶部构造 markArea
    - ``key_volatility``: 关键性波动竖线（颜色转换日）
    """
    frame = result.frame.tail(max_bars).copy()
    dates = [idx.strftime("%Y-%m-%d") for idx in frame.index]

    ohlc = [
        [round(r["open"], 4), round(r["close"], 4), round(r["low"], 4), round(r["high"], 4)]
        for _, r in frame.iterrows()
    ]

    ema20 = [round(r, 4) if pd.notna(r) else None for r in frame.get("ema20", [])]
    sma20 = [round(r, 4) if pd.notna(r) else None for r in frame.get("sma20", [])]
    ema60 = [round(r, 4) if pd.notna(r) else None for r in frame.get("ema60", [])]
    ema120 = [round(r, 4) if pd.notna(r) else None for r in frame.get("ema120", [])]
    ref20 = [round(r, 4) if pd.notna(r) else None for r in frame.get("close_lag20", [])]
    states = [str(r) if pd.notna(r) else "unknown" for r in frame.get("signal_color", [])]

    volumes = [float(v) for v in frame["volume"]]
    vol_ratios = [
        float(r) if pd.notna(r) else 1.0
        for r in frame.get("volume_ratio20", [1.0] * len(frame))
    ]
    vol_states = [_classify_vol(r) for r in vol_ratios]

    a = result.assessment
    last_date = dates[-1] if dates else None

    # ----- B1 -----
    b1_line: dict[str, Any] | None = None
    if a.b1_price is not None:
        b1_line = {
            "yAxis": round(a.b1_price, 4),
            "color": "#ea580c",
            "dash": "dash",
            "width": 1.4,
        }

    # ----- 主底部 C 线（live 底部中最近确认的一个）-----
    bottom_lines: list[dict[str, Any]] = []
    live_bottoms = [
        s for s in (result.structures or [])
        if s.side == "bottom"
        and s.c_price is not None
        and s.invalidated_date is None
    ]
    if live_bottoms:
        primary = max(
            live_bottoms,
            key=lambda s: s.confirmed_date or s.detected_date,
        )
        if primary.c_price is not None:
            bottom_lines.append({
                "yAxis": round(float(primary.c_price), 4),
                "color": "#059669",
                "dash": "dot",
                "width": 1.4,
            })

    # ----- 活跃顶部颈线 -----
    top_lines: list[dict[str, Any]] = []
    active_tops = [
        s for s in (result.structures or [])
        if s.side == "top"
        and s.neckline is not None
        and s.invalidated_date is None
        and s.confirmed_date is not None
    ]
    for top in active_tops[:3]:
        if top.neckline is not None:
            top_lines.append({
                "yAxis": round(float(top.neckline), 4),
                "color": "#dc2626",
                "dash": "dot",
                "width": 1.4,
            })

    # ----- 底部 / 顶部构造 markArea -----
    # 区间：detected_date → max(confirmed_date, invalidated_date) 或 last_date
    bottom_areas: list[dict[str, Any]] = []
    top_areas: list[dict[str, Any]] = []

    def _make_area(structure) -> dict[str, Any] | None:
        start = _date_to_str(structure.detected_date)
        if start is None:
            start = _date_to_str(structure.confirmed_date)
        end = _date_to_str(structure.invalidated_date)
        if end is None:
            end = _date_to_str(structure.confirmed_date)
        if end is None:
            end = last_date
        if start is None or end is None:
            return None
        return {"start": start, "end": end}

    for s in result.structures or []:
        area = _make_area(s)
        if area is None:
            continue
        if s.side == "bottom":
            bottom_areas.append(area)
        elif s.side == "top" and s.neckline is not None:
            top_areas.append(area)

    # ----- 关键性波动（颜色从非绿→绿 或 非黑→黑 的转换日）-----
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
        "b1Line": b1_line,
        "bottomLines": bottom_lines,
        "topLines": top_lines,
        "bottomAreas": bottom_areas,
        "topAreas": top_areas,
        "keyVolatility": key_volatility,
        "colorMode": color_mode,
        "stateColors": _STATE_COLORS,
        "priceUp": _PRICE_UP,
        "priceDown": _PRICE_DOWN,
        "symbol": result.symbol,
        "displayName": result.display_name,
        "lastClose": round(float(frame["close"].iloc[-1]), 4) if len(frame) else None,
    }


def _build_html(
    data: dict[str, Any],
    *,
    default_bars: int = 60,
    height: int = 680,
    display: dict[str, bool] | None = None,
) -> str:
    """生成包含 ECharts 的完整 HTML 字符串。

    ``default_bars``: 初始展示最近多少根 K线；dataZoom ``start`` 按此计算。
    ``display``: 标记显隐开关，键包括
        ``b1`` / ``bottom_construction`` / ``top_construction`` /
        ``bottom_c`` / ``top_neckline`` / ``key_volatility``，
        缺省视为 True。
    """
    if display is None:
        display = {}
    show = {k: display.get(k, True) for k in
            ("b1", "bottom_construction", "top_construction",
             "bottom_c", "top_neckline", "key_volatility")}

    echarts_js = _ECHARTS_JS.read_text(encoding="utf-8")
    data_json = json.dumps(data, ensure_ascii=False)

    total = len(data["dates"])
    if total > default_bars:
        start_pct = round((1 - default_bars / total) * 100, 1)
    else:
        start_pct = 0

    # 组装 markArea（构造区域）+ markLine（水平线 + 关键波动竖线）
    area_blocks: list[dict[str, Any]] = []
    if show["bottom_construction"]:
        for a in data["bottomAreas"]:
            area_blocks.append([{
                "xAxis": a["start"],
                "itemStyle": {"color": _BOTTOM_AREA_COLOR, "borderColor": _BOTTOM_AREA_BORDER, "borderWidth": 1},
                "label": {"show": True, "position": "insideTop", "formatter": "底", "color": "#9a6510", "fontSize": 10, "fontWeight": "bold"},
            }, {"xAxis": a["end"]}])
    if show["top_construction"]:
        for a in data["topAreas"]:
            area_blocks.append([{
                "xAxis": a["start"],
                "itemStyle": {"color": _TOP_AREA_COLOR, "borderColor": _TOP_AREA_BORDER, "borderWidth": 1},
                "label": {"show": True, "position": "insideTop", "formatter": "顶", "color": "#b12b35", "fontSize": 10, "fontWeight": "bold"},
            }, {"xAxis": a["end"]}])

    line_blocks: list[dict[str, Any]] = []
    if show["b1"] and data.get("b1Line"):
        bl = data["b1Line"]
        line_blocks.append({
            "yAxis": bl["yAxis"],
            "label": {"show": False},
            "lineStyle": {"color": bl["color"], "type": bl["dash"], "width": bl["width"], "opacity": 0.7},
        })
    if show["bottom_c"]:
        for ln in data["bottomLines"]:
            line_blocks.append({
                "yAxis": ln["yAxis"],
                "label": {"show": False},
                "lineStyle": {"color": ln["color"], "type": ln["dash"], "width": ln["width"], "opacity": 0.7},
            })
    if show["top_neckline"]:
        for ln in data["topLines"]:
            line_blocks.append({
                "yAxis": ln["yAxis"],
                "label": {"show": False},
                "lineStyle": {"color": ln["color"], "type": ln["dash"], "width": ln["width"], "opacity": 0.7},
            })
    if show["key_volatility"]:
        for k in data["keyVolatility"]:
            line_blocks.append({
                "xAxis": k["date"],
                "label": {"show": False},
                "lineStyle": {"color": data["stateColors"].get(k["state"], "#888"), "type": "dashed", "width": 1, "opacity": 0.3},
            })

    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  * {{ margin: 0; padding: 0; box-sizing: border-box; }}
  body {{ background: #fff; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", sans-serif; }}
  #chart {{ width: 100%; height: {height}px; }}
  .legend-bar {{
    display: flex; flex-wrap: wrap; gap: 12px;
    padding: 8px 12px; font-size: 12px; color: #596579;
    border-top: 1px solid #edf1f6;
  }}
  .legend-item {{ display: inline-flex; align-items: center; gap: 5px; }}
  .legend-swatch {{
    width: 16px; height: 10px; border-radius: 2px; display: inline-block;
  }}
  .legend-line {{
    width: 18px; height: 0; border-top-width: 1.5px; border-top-style: solid;
    display: inline-block;
  }}
</style>
</head>
<body>
<div id="chart"></div>
<div class="legend-bar">
  <span class="legend-item"><span class="legend-line" style="border-color:#3867d6"></span>EMA20</span>
  <span class="legend-item"><span class="legend-line" style="border-color:#d89216;border-top-style:dashed"></span>SMA20</span>
  <span class="legend-item"><span class="legend-line" style="border-color:#8d4bd3;border-top-style:dotted"></span>20周期抵扣价</span>
  <span class="legend-item"><span class="legend-swatch" style="background:rgba(216,146,22,0.18);border:1px solid #d89216"></span>底部构造</span>
  <span class="legend-item"><span class="legend-swatch" style="background:rgba(220,38,38,0.15);border:1px solid #dc2626"></span>顶部构造</span>
  <span class="legend-item"><span class="legend-line" style="border-color:#ea580c;border-top-style:dashed"></span>B1 第一阻力</span>
  <span class="legend-item"><span class="legend-line" style="border-color:#059669;border-top-style:dotted"></span>主底部 C</span>
  <span class="legend-item"><span class="legend-line" style="border-color:#dc2626;border-top-style:dotted"></span>顶部颈线</span>
  <span class="legend-item"><span class="legend-swatch" style="background:#e8590c"></span>放量</span>
</div>
<script>
{echarts_js}
</script>
<script>
const DATA = {data_json};
const DISPLAY = {json.dumps(show)};

const stateColors = DATA.stateColors;
const stateAreas = DATA.dates.map((d, i) => [
  {{ xAxis: d, itemStyle: {{ color: stateColors[DATA.states[i]] || stateColors.unknown, opacity: 0.04 }} }},
  {{ xAxis: d }}
]);

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

const constructAreas = {json.dumps(area_blocks)};
const markLines = {json.dumps(line_blocks)};

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
    {{ left: 66, right: 70, top: 40, height: "60%" }},
    {{ left: 66, right: 70, top: "72%", height: "18%" }}
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
      markArea: {{ silent: true, data: stateAreas.concat(constructAreas) }},
      markLine: {{ silent: true, symbol: ["none", "none"],
        lineStyle: {{ color: "#caa23a", type: "dashed", width: 1 }},
        label: {{ show: false }},
        data: markLines
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
      data: DATA.volumes.map((v, i) => {{
        const isSpike = DATA.volStates[i] === "放量";
        return {{
          value: v,
          itemStyle: {{
            color: DATA.volColors[i],
            borderColor: isSpike ? DATA.volColors[i] :
              (DATA.ohlc[i][1] >= DATA.ohlc[i][0]
                ? "rgba(227,61,71,.4)" : "rgba(11,155,100,.4)"),
            borderWidth: isSpike ? 2 : 1
          }},
          label: {{
            show: isSpike,
            position: "top",
            formatter: "放量",
            color: "#e8590c",
            fontSize: 9,
            fontWeight: "bold"
          }}
        }};
      }})
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
    display: dict[str, bool] | None = None,
    component_key: str = "echarts_kline",
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
    display : dict[str, bool] | None
        标记显隐开关：
        - ``b1`` / ``bottom_c`` / ``top_neckline`` / ``bottom_construction`` /
          ``top_construction`` / ``key_volatility``
        缺省视为 True。
    component_key : str
        Streamlit 组件 key；切换 display 时需改成新值才能强制重渲染。
    """
    import streamlit.components.v1 as components

    data = _serialize_result(result, color_mode=color_mode, max_bars=max_bars)
    html = _build_html(
        data,
        default_bars=default_bars,
        height=height,
        display=display,
    )
    components.html(html, height=height + 60, scrolling=False)


__all__ = ["render_echarts_kline"]