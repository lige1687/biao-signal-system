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
    # SMA60/120：compute_features 已按 sma_periods=[20,60,120] 算好，
    # 此前只是没导出。与 EMA60/120 并列，便于对照长周期的快慢口径差异。
    sma60 = [round(r, 4) if pd.notna(r) else None for r in frame.get("sma60", [])]
    sma120 = [round(r, 4) if pd.notna(r) else None for r in frame.get("sma120", [])]
    ref20 = [round(r, 4) if pd.notna(r) else None for r in frame.get("close_lag20", [])]
    states = [str(r) if pd.notna(r) else "unknown" for r in frame.get("signal_color", [])]

    volumes = [float(v) for v in frame["volume"]]
    vol_ratios = [
        float(r) if pd.notna(r) else 1.0
        for r in frame.get("volume_ratio20", [1.0] * len(frame))
    ]
    vol_states = [_classify_vol(r) for r in vol_ratios]

    a = result.assessment

    # ----- B1 -----
    b1_line: dict[str, Any] | None = None
    if a.b1_price is not None:
        b1_line = {
            "yAxis": round(a.b1_price, 4),
            "color": "#ea580c",
            "dash": "dash",
            "width": 1.4,
            # 以下字段供 Web 端点击横线把手后展示解释；Streamlit 模板不消费。
            "label_cn": "B1 第一阻力",
            "pivot_date": _date_to_str(a.b1_pivot_date),
            "distance_pct": (
                round(float(a.distance_to_b1_pct), 2)
                if a.distance_to_b1_pct is not None
                else None
            ),
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
                "label_cn": "C 点失效线",
                "structure_id": primary.structure_id,
                "structure_type": primary.structure_type,
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
                "label_cn": "顶部颈线",
                "structure_id": top.structure_id,
                "structure_type": top.structure_type,
            })

    # ----- 底部 / 顶部构造：标记用「确认日小图标」替代「色块区域」-----
    # 旧实现（markArea 琥珀色块）在多结构并存时严重重叠，改用 markPoint：
    # - 底部结构：确认日 K 线下方画绿色小钻石（失效结构灰色）
    # - 顶部结构：确认日 K 线上方画红色小钻石（失效结构灰色）
    # - 失效日：画灰色小 ×（一眼能看出"这里坏了"）
    # hover tooltip 仍展示完整结构信息（类型/确认日/C/失效日）。
    bottom_marks: list[dict[str, Any]] = []
    top_marks: list[dict[str, Any]] = []
    invalidated_marks: list[dict[str, Any]] = []

    def _struct_info(structure) -> dict[str, Any]:
        return {
            # structure_id 供 Web 端点击标记后关联到完整结构与其绑定事件；
            # Streamlit 端模板不消费该字段（纯新增，无影响）。
            "structure_id": getattr(structure, "structure_id", "") or "",
            "structure_type": getattr(structure, "structure_type", "") or "",
            "source_rule": getattr(structure, "source_rule_id", "") or "",
            "detected_date": _date_to_str(getattr(structure, "detected_date", None)),
            "confirmed_date": _date_to_str(getattr(structure, "confirmed_date", None)),
            "invalidated_date": _date_to_str(getattr(structure, "invalidated_date", None)),
        }

    for s in result.structures or []:
        info = _struct_info(s)
        if s.side == "bottom":
            if s.confirmed_date is not None and s.c_price is not None:
                bottom_marks.append({
                    "date": _date_to_str(s.confirmed_date),
                    "price": float(s.c_price),
                    "label": f"底部确认 {s.structure_type or ''}",
                    "live": s.invalidated_date is None,
                    "info": info,
                })
            if s.invalidated_date is not None and s.c_price is not None:
                invalidated_marks.append({
                    "date": _date_to_str(s.invalidated_date),
                    "price": float(s.c_price),
                    "label": "底部失效",
                    "info": info,
                })
        elif s.side == "top":
            if s.confirmed_date is not None and s.neckline is not None:
                top_marks.append({
                    "date": _date_to_str(s.confirmed_date),
                    "price": float(s.neckline),
                    "label": f"顶部确认 {s.structure_type or ''}",
                    "live": s.invalidated_date is None,
                    "info": info,
                })
            if s.invalidated_date is not None and s.neckline is not None:
                invalidated_marks.append({
                    "date": _date_to_str(s.invalidated_date),
                    "price": float(s.neckline),
                    "label": "顶部失效",
                    "info": info,
                })

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
        "sma60": sma60,
        "sma120": sma120,
        "ref20": ref20,
        "states": states,
        "volumes": volumes,
        "volStates": vol_states,
        "volColors": [_VOL_COLORS.get(s, _VOL_COLORS["正常"]) for s in vol_states],
        "b1Line": b1_line,
        "bottomLines": bottom_lines,
        "topLines": top_lines,
        "bottomMarks": bottom_marks,
        "topMarks": top_marks,
        "invalidatedMarks": invalidated_marks,
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
             "bottom_c", "top_neckline", "invalidated", "key_volatility")}
    # 失效结构默认不显示，避免图表杂乱
    show.setdefault("invalidated", False)

    echarts_js = _ECHARTS_JS.read_text(encoding="utf-8")
    data_json = json.dumps(data, ensure_ascii=False)

    total = len(data["dates"])
    start_pct = (
        round((1 - default_bars / total) * 100, 1) if total > default_bars else 0
    )

    # 标记点击 → echarts tooltip 弹讲解（人话版本）。
    # 突破结构失效 (C突破)、顶部确认、底部确认 — 都是关键信号，hover 给出定义和操作含义。
    def _to_mark_point(marks: list[dict[str, Any]], color: str, dead_color: str,
                       symbol: str, offset_y: int, side: str) -> list[dict[str, Any]]:
        out: list[dict[str, Any]] = []
        for m in marks:
            info = m.get("info", {})
            structure_type = info.get("structure_type", "")
            confirmed = info.get("confirmed_date", "-")
            invalidated = info.get("invalidated_date")
            source_rule = info.get("source_rule", "")

            # 人话版本：根据 side 给讲解
            if side == "bottom":
                head = "🟢 底部结构确认"
                explain = "摆动点识别出的「更高低点」或「双底」形态已成型"
                usage = ("此结构的 C 点是常用止损参考；"
                         "若价格跌破 C 即结构永久失效（不能再复活）")
            elif side == "top":
                head = "🔴 顶部结构确认"
                explain = "摆动点识别出的「更低高点」形态已成型"
                usage = "此结构的颈线被有效跌破后，才算顶部确立"
            else:  # invalidated
                head = "⚫ 结构失效"
                explain = "之前确认过的结构，因价格触及 C/颈线而永久失效"
                usage = "失效后不能再依赖此结构的止损/阻力"

            tooltip_lines = [
                head,
                f"<span style='color:#9a6510'>{m.get('label', '')}</span>",
                f"确认日: {confirmed}",
            ]
            if invalidated:
                tooltip_lines.append(f"失效日: {invalidated}")
            if structure_type:
                tooltip_lines.append(f"形态: {structure_type}")
            tooltip_lines.append(f"📖 {explain}")
            tooltip_lines.append(f"💡 {usage}")
            if source_rule:
                tooltip_lines.append(f"<small>规则: {source_rule}</small>")
            tooltip_html = "<br/>".join(tooltip_lines)

            detail_info = {
                "side": side,
                "date": m["date"],
                "price": m["price"],
                "live": m.get("live", True),
                "structure_type": structure_type,
                "confirmed_date": info.get("confirmed_date", ""),
                "invalidated_date": info.get("invalidated_date", ""),
            }

            out.append({
                "coord": [m["date"], m["price"]],
                "symbol": symbol,
                "symbolSize": 12,
                "symbolOffset": [0, offset_y],
                "itemStyle": {"color": color if m.get("live", True) else dead_color},
                "label": {"show": False},
                "tooltip": {"formatter": f"<b>{tooltip_html}</b>", "confine": True},
                "detailInfo": detail_info,
            })
        return out

    bottom_pts: list[dict[str, Any]] = []
    top_pts: list[dict[str, Any]] = []
    invalidated_pts: list[dict[str, Any]] = []
    if show["bottom_construction"]:
        bottom_pts = _to_mark_point(
            data.get("bottomMarks", []), "#0b9b64", "#9ca3af", "diamond", 20, "bottom",
        )
    if show["top_construction"]:
        top_pts = _to_mark_point(
            data.get("topMarks", []), "#dc2626", "#9ca3af", "diamond", -22, "top",
        )
    # 失效标记：默认隐藏，用户手动打开开关才显示
    invalidated_pts = []
    if show["invalidated"]:
        invalidated_pts = _to_mark_point(
            data.get("invalidatedMarks", []), "#9ca3af", "#9ca3af", "pin", -22, "invalidated",
        )
    all_mark_points = bottom_pts + top_pts + invalidated_pts

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
  .toolbar {{
    display: flex; justify-content: space-between; align-items: center;
    padding: 6px 12px; background: #fafbfc; border-bottom: 1px solid #edf1f6;
  }}
  .toolbar-title {{
    font-size: 13px; font-weight: 600; color: #172033;
  }}
  .download-btn {{
    padding: 4px 12px; font-size: 12px;
    background: #3867d6; color: #fff; border: none; border-radius: 5px;
    cursor: pointer;
  }}
  .download-btn:hover {{ background: #2955b8; }}
  .signal-detail {{
    position: absolute; top: 48px; right: 12px;
    background: #ffffff; border: 1px solid #dfe5ee;
    border-radius: 6px; padding: 12px 14px;
    box-shadow: 0 4px 12px rgba(15,23,42,.08);
    max-width: 320px; font-size: 12px; line-height: 1.6; color: #172033;
    z-index: 10; display: none;
  }}
  .signal-detail.show {{ display: block; }}
  .signal-detail .head {{
    display: flex; align-items: center; gap: 6px;
    font-weight: 700; margin-bottom: 8px; font-size: 13px;
  }}
  .signal-detail .close {{
    position: absolute; top: 6px; right: 8px;
    width: 18px; height: 18px; line-height: 16px; text-align: center;
    border: 1px solid #c9d4e3; border-radius: 50%;
    cursor: pointer; color: #64748b;
  }}
  .signal-detail .row {{ margin: 4px 0; }}
  .signal-detail .row .pill {{
    display: inline-block; padding: 1px 6px; border-radius: 3px;
    font-size: 11px; color: #fff; margin-right: 4px;
  }}
  .signal-detail .row.green .pill {{ background: #0b9b64; }}
  .signal-detail .row.gray .pill {{ background: #8c96a8; }}
  .signal-detail .row.black .pill {{ background: #1f2937; }}
  .signal-detail .note {{
    background: #f8fafc; border-left: 3px solid #3867d6;
    padding: 6px 8px; margin-top: 6px; border-radius: 3px;
    color: #475569; font-size: 11px;
  }}
</style>
</head>
<body style="position:relative">
<div id="signal-detail" class="signal-detail">
  <span class="close" id="signal-detail-close">×</span>
  <div class="head" id="sd-head"></div>
  <div id="sd-body"></div>
</div>
<div class="toolbar">
  <span class="toolbar-title">{data["displayName"]} · {data["symbol"]}</span>
  <button class="download-btn" id="dl-btn">📷 导出图片</button>
</div>
<div id="chart"></div>
<div class="legend-bar">
  <span class="legend-item"><span class="legend-line" style="border-color:#3867d6"></span>EMA20</span>
  <span class="legend-item"><span class="legend-line" style="border-color:#d89216;border-top-style:dashed"></span>SMA20</span>
  <span class="legend-item"><span class="legend-line" style="border-color:#8d4bd3;border-top-style:dotted"></span>20周期抵扣价</span>
  <span class="legend-item"><span class="legend-line" style="border-color:#0b9b64"></span>◆</span>底部确认</span>
  <span class="legend-item"><span class="legend-line" style="border-color:#dc2626"></span>◆</span>顶部确认</span>
  <span class="legend-item"><span class="legend-line" style="border-color:#9ca3af"></span>×</span>结构失效</span>
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

const constructPoints = {json.dumps(all_mark_points)};
const markLines = {json.dumps(line_blocks)};

const start = {start_pct};

const option = {{
  animation: false,
  backgroundColor: "#ffffff",
  textStyle: {{ color: "#68748a", fontFamily: "-apple-system,BlinkMacSystemFont,Segoe UI,PingFang SC,sans-serif" }},
  legend: {{ top: 2, data: ["K线", "EMA20", "SMA20", "20周期抵扣价", "成交量"], textStyle: {{ color: "#596579" }} }},
  tooltip: {{
    trigger: "axis", axisPointer: {{ type: "cross" }},
    backgroundColor: "rgba(255,255,255,.96)", borderColor: "#dfe5ee", textStyle: {{ color: "#172033" }},
    formatter: function(params) {{
      // 取 K 线那一项 + 当日颜色解读
      var k = null; var vol = null;
      for (var i = 0; i < params.length; i++) {{
        if (params[i].seriesName === "K线") k = params[i];
        if (params[i].seriesName === "成交量") vol = params[i];
      }}
      if (!k) return "";
      var date = k.axisValue;
      var idx = DATA.dates.indexOf(date);
      var state = (idx >= 0) ? DATA.states[idx] : "unknown";
      var stateText = {{green:"🟢 绿色（强势）", gray:"⚪ 灰色（关注）", black:"⚫ 黑色（弱势）", unknown:"❓ 未知"}}[state] || state;
      var stateNote = {{green:"收盘>EMA20 且 >20日前收盘", gray:"方向分歧，需关注", black:"收盘<EMA20 且 <20日前收盘", unknown:"数据不足"}}[state] || "";
      var html = "<b>" + date + "</b><br/>" +
        "状态：" + stateText + "<br/>" +
        "<small style='color:#888'>" + stateNote + "</small><br/>" +
        "开:" + k.data[0] + " 高:" + k.data[3] + " 低:" + k.data[2] + " 收:" + k.data[1];
      if (vol) {{
        html += "<br/>量:" + (vol.data || vol.value).toLocaleString();
      }}
      return html;
    }}
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
      markArea: {{ silent: true, data: stateAreas }},
      markPoint: {{
        symbol: "diamond", symbolSize: 12,
        data: constructPoints
      }},
      markLine: {{ silent: true, symbol: ["none", "none"],
        lineStyle: {{ color: "#caa23a", type: "dashed", width: 1 }},
        label: {{ show: false }},
        data: markLines
      }}
    }},
    {{ name: "EMA20", type: "line", data: DATA.ema20, showSymbol: false,
       lineStyle: {{ width: 1.8, color: "#2563eb" }} }},
    {{ name: "SMA20", type: "line", data: DATA.sma20, showSymbol: false,
       lineStyle: {{ width: 1.4, color: "#2563eb", type: "dashed" }} }},
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

// 点击信号标记 → 在图表右上角弹出"是什么+怎么用"浮层
const sd = document.getElementById('signal-detail');
const sdHead = document.getElementById('sd-head');
const sdBody = document.getElementById('sd-body');
document.getElementById('signal-detail-close').addEventListener('click', () => {{
  sd.classList.remove('show');
}});

const EXPLANATIONS = {{
  bottom: {{
    head: '🟢 底部结构确认',
    def: '摆动点识别出的「更高低点」或「双底」形态已成型',
    usage: '此结构的 C 点是常用止损参考；若价格跌破 C 即结构永久失效（不能再复活）',
    badge: 'green'
  }},
  top: {{
    head: '🔴 顶部结构确认',
    def: '摆动点识别出的「更低高点」形态已成型',
    usage: '此结构的颈线被有效跌破后，才算顶部确立',
    badge: 'red'
  }},
  invalidated: {{
    head: '⚫ 结构失效',
    def: '之前确认过的结构，因价格触及 C/颈线而永久失效',
    usage: '失效后不能再依赖此结构的止损/阻力',
    badge: 'gray'
  }}
}};

function showSignalDetail(marker) {{
  const data = marker.data || marker;
  const info = data.detailInfo || {{}};
  const side = info.side || 'bottom';
  const exp = EXPLANATIONS[side] || EXPLANATIONS.bottom;
  const cls = exp.badge === 'red' ? 'gray' : exp.badge;
  sdHead.innerHTML = exp.head;
  const dateStr = (data.coord && data.coord[0]) || info.date || '-';
  const priceStr = (data.coord && data.coord[1]) ? data.coord[1].toFixed(4) : '-';
  const stateStr = info.live ? '有效' : '已失效';
  sdBody.innerHTML =
    '<div class="row ' + cls + '">' +
      '<span class="pill">' + stateStr + '</span>' +
      (info.structure_type || exp.def) +
    '</div>' +
    '<div class="row">📍 价格 <b>' + priceStr + '</b> · 日期 <b>' + dateStr + '</b></div>' +
    (info.confirmed_date
      ? '<div class="row">确认日 <b>' + info.confirmed_date + '</b></div>'
      : '') +
    (info.invalidated_date
      ? '<div class="row">失效日 <b>' + info.invalidated_date + '</b></div>'
      : '') +
    '<div class="note">💡 <b>怎么用：</b>' + exp.usage + '</div>';
  sd.classList.add('show');
}}

// 监听 echarts 的 markPoint 点击
chart.on('click', function(params) {{
  // params.componentType === 'markPoint' 表示点的是 markPoint
  if (params.componentType === 'markPoint' && params.data && params.data.detailInfo) {{
    showSignalDetail(params);
  }}
}});
// 点击空白处关闭浮层
chart.getZr().on('click', function(params) {{
  if (!params.target) {{
    sd.classList.remove('show');
  }}
}});

document.getElementById('dl-btn').addEventListener('click', () => {{
  const url = chart.getDataURL({{
    type: 'png',
    pixelRatio: 2,
    backgroundColor: '#ffffff'
  }});
  const a = document.createElement('a');
  a.href = url;
  a.download = '{data["symbol"]}-kline-' + new Date().toISOString().slice(0, 10) + '.png';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}});
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


#: 供 Web API（lei_signal.api）使用的公开别名：与 Streamlit 端共用同一
#: 序列化口径，避免两套 K 线 JSON 结构漂移。
serialize_result = _serialize_result

__all__ = ["render_echarts_kline", "serialize_result"]