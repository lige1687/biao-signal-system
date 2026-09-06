"""大盘情绪环境（市场情绪仪表盘数据层，research_proxy）。

定位：叙事标注层——只标注环境、不硬过滤、不出买卖点（AGENTS.md 红线）。
两个市场四个成分 + 美国调查情绪（外部实证阈值，rules.v2.yaml
us_survey_sentiment 段登记，未硬编码）。

成分（全部本地数据或既有管道，单项失败独立降级不阻塞）：
- CN 情绪（热/中/冷，三票多数）：两融余额 20 日变化 + 全A散户小单净流入
  20 日合计 + 全A等权指数 20 日动能；
- US 情绪（宽/窄 + 恐慌档）：SP500 宽度（lab.db 1986 起）60 日分位、
  VIX（fetch_vix_history，惯例分档）、XLY/XLP 风险偏好（etf_strength）。
"""
from __future__ import annotations

import json
import os
import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from lei_signal.domain.rules_config import get_rule

_CACHE = Path(os.environ.get("LEI_CACHE_ROOT", Path.home() / ".lei_signal_lab/cache"))


# ─────────────────────── CN 情绪（三票） ───────────────────────
def _margin_chg20() -> pd.Series | None:
    try:
        from lei_signal.fundamentals import sources

        hist = sources.fetch_margin_history(lookback_days=900)
        s = pd.Series({pd.to_datetime(d): v.get("rzye_yi") for d, v in hist.items()
                       if v.get("rzye_yi") is not None}).sort_index()
        return s.pct_change(20)
    except Exception:  # noqa: BLE001 - 单成分失败降级
        return None


def _cn_small_flow20() -> pd.Series | None:
    """全A散户小单净流入 20 日合计（腾讯试点文件 + 东财缓存合并取并集）。"""
    series: dict = {}
    for fname in ("tx_sector_flow_pilot.json", "sector_flow_history.json"):
        p = _CACHE / fname
        if not p.exists():
            continue
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        boards = data.get("boards") if "boards" in data else data
        for code, pts in (boards or {}).items():
            for pt in pts:
                v = pt.get("small_yi") if "small_yi" in pt else pt.get("small_yi")
                if v is not None:
                    series.setdefault(pd.to_datetime(pt["date"]), {}).setdefault(code, v)
    if not series:
        return None
    agg = pd.Series({k: sum(v.values()) for k, v in series.items()}).sort_index()
    return agg.rolling(20, min_periods=20).sum()


def _all_a_equal_index() -> pd.Series | None:
    try:
        rows = json.loads((_CACHE / "sector_trend_history.json").read_text(encoding="utf-8"))
        close = pd.DataFrame(
            {r["date"]: {c: v.get("close") for c, v in r["boards"].items()} for r in rows}
        ).T.sort_index()
        close.index = pd.to_datetime(close.index)
        ret = close.pct_change(fill_method=None).mean(axis=1)
        idx = (1 + ret.fillna(0)).cumprod()
        return idx.pct_change(20)
    except Exception:  # noqa: BLE001
        return None


def cn_mood() -> dict:
    """全A情绪：三成分 + 多数票合成。任一成分缺失标注 degraded。"""
    comp: dict[str, dict] = {}
    for key, fn, label in (
        ("margin20", _margin_chg20, "融资余额20日变化"),
        ("retail_small20", _cn_small_flow20, "全A散户小单净流入20日合计"),
        ("equal_mom20", _all_a_equal_index, "全A等权指数20日动能"),
    ):
        s = fn()
        if s is None or s.dropna().empty:
            comp[key] = {"label_cn": label, "ok": False}
            continue
        last = float(s.dropna().iloc[-1])
        comp[key] = {
            "label_cn": label, "ok": True, "value": round(last * 100, 2),
            "unit": "%", "vote": int(np.sign(last)),
            "as_of": str(s.dropna().index[-1].date()),
        }
    votes = [c["vote"] for c in comp.values() if c.get("ok")]
    score = int(np.sign(sum(votes))) if len(votes) >= 2 else None
    state = {1: "热", -1: "冷", 0: "中"}.get(score) if score is not None else None
    return {
        "components": comp,
        "state": state,
        "state_cn": {"热": "情绪偏热（散户加杠杆/净流入/动能多数向上）",
                     "冷": "情绪偏冷（多数向下，冰点或恐慌期）",
                     "中": "情绪中性（成分分歧）"}.get(state, "成分不足，暂不判定"),
        "note_cn": "三票多数合成（两融变化+散户小单净流入+等权动能）；research_proxy，只标注不判定。",
    }


# ─────────────────────── US 情绪 ───────────────────────
def us_breadth() -> dict:
    """SP500 宽度（站上 MA50 成分占比）60 日分位。"""
    db = Path.home() / ".lei_signal_lab" / "lab.db"
    try:
        con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
        rows = con.execute(
            "SELECT as_of, breadth_50 FROM market_breadth_snapshots "
            "WHERE market_id='SP500' AND breadth_50 IS NOT NULL ORDER BY as_of"
        ).fetchall()
        con.close()
    except sqlite3.Error:
        return {"ok": False}
    if len(rows) < 120:
        return {"ok": False}
    s = pd.Series({pd.to_datetime(d): v for d, v in rows}).sort_index()
    pct = s.rolling(60, min_periods=60).rank(pct=True)
    last_date = s.index[-1]
    out = {
        "ok": True, "as_of": str(last_date.date()),
        "breadth_50": round(float(s.iloc[-1]), 1),
        "pctile_60d": round(float(pct.iloc[-1]) * 100, 1) if pd.notna(pct.iloc[-1]) else None,
        "state": None,
    }
    p = out["pctile_60d"]
    out["state"] = "宽" if p is not None and p > 50 else ("窄" if p is not None else None)
    return out


def vix_level() -> dict:
    """VIX 现值 + 惯例分档（阈值读 rules.v2.yaml us_survey_sentiment）。"""
    try:
        from lei_signal.fundamentals import sources

        hist = sources.fetch_vix_history(lookback_days=60)
        s = pd.Series({pd.to_datetime(d): v for d, v in hist.items()}).sort_index()
        now = float(s.iloc[-1])
    except Exception:  # noqa: BLE001
        return {"ok": False}
    try:
        rule = get_rule("us_survey_sentiment")
        calm, normal, elev, fear = (rule.param("vix_calm", 15), rule.param("vix_normal", 20),
                                    rule.param("vix_elevated", 25), rule.param("vix_fear", 30))
    except Exception:  # noqa: BLE001
        calm, normal, elev, fear = 15, 20, 25, 30
    if now < calm:
        state_cn = "低位自满（波动率被压低，常对应乐观末期）"
    elif now < normal:
        state_cn = "正常偏低"
    elif now < elev:
        state_cn = "正常"
    elif now < fear:
        state_cn = "偏恐慌（关注风险偏好收缩）"
    else:
        state_cn = "恐慌区（历史上常对应阶段性底部区，反向视角）"
    return {"ok": True, "value": round(now, 1), "as_of": str(s.index[-1].date()),
            "state_cn": state_cn, "thresholds": [calm, normal, elev, fear],
            "source": "外部惯例分档（rules.v2.yaml us_survey_sentiment）"}


def us_risk_appetite() -> dict:
    """XLY/XLP（可选消费/必选消费）趋势 = 美股风险偏好方向。"""
    try:
        from lei_signal.fundamentals import sources

        data = sources.fetch_etf_strength()
        if not data:
            return {"ok": False}
        ratio = data.get("xly_xlp") or data.get("discretionary_staples")
        if not ratio:
            # 尝试从序列判断方向
            series = (data.get("series") or {}).get("XLY_XLP") or (data.get("risk_line"))
            if series and len(series) >= 21:
                s = pd.Series({pd.to_datetime(p["date"]): p["value"] for p in series}).sort_index()
                chg = float(s.iloc[-1] / s.iloc[-21] - 1) if s.iloc[-21] else None
                return {"ok": True, "chg_20d_pct": round(chg * 100, 2) if chg is not None else None,
                        "state_cn": "风险偏好上升" if (chg or 0) > 0 else "避险升温",
                        "as_of": str(s.index[-1].date())}
        return {"ok": False}
    except Exception:  # noqa: BLE001
        return {"ok": False}


# ─────────────────────── 美国调查情绪（AAII/NAAIM） ───────────────────────
def us_survey_latest() -> dict:
    """AAII/NAAIM 最新一期读数 + 外部实证阈值分档（数据需手动导入）。"""
    root = os.environ.get("LEI_SENTIMENT_ROOT", "")
    out: dict = {"available": False, "root": root or None,
                 "hint_cn": "未设置 LEI_SENTIMENT_ROOT；放入 naaim.csv/aaii.csv 或在基本面页手动录入"}
    try:
        rule = get_rule("us_survey_sentiment")
        th = {
            "spread_greed": rule.param("bull_bear_spread_greed", 20),
            "spread_fear": rule.param("bull_bear_spread_fear", -20),
            "bullish_greed": rule.param("bullish_greed", 50),
            "bearish_fear": rule.param("bearish_fear", 50),
        }
    except Exception:  # noqa: BLE001
        th = {"spread_greed": 20, "spread_fear": -20, "bullish_greed": 50, "bearish_fear": 50}
    out["thresholds"] = th
    out["threshold_source_cn"] = "AAII 官方定义与历史极值（aaii.com，价差均值约+6.5pp；2009-03 看空70.3%见底案例）——外部实证阈值，非本系统回测"
    if not root:
        return out
    from lei_signal.market_context import sentiment as senti

    aaii_rows = []
    p = Path(root) / "aaii.csv"
    if p.exists():
        try:
            obs = senti.load_aaii_observations(p)
            o = obs[-1]
            spread = float(o.bullish - o.bearish)  # type: ignore[attr-defined]
            aaii_rows = [{"bullish": o.bullish, "neutral": o.neutral, "bearish": o.bearish}]  # type: ignore[attr-defined]
            state = ("贪婪/过度乐观" if spread > th["spread_greed"] or o.bullish > th["bullish_greed"]  # type: ignore[attr-defined]
                     else "恐惧/极度悲观" if spread < th["spread_fear"] or o.bearish > th["bearish_fear"]  # type: ignore[attr-defined]
                     else "中性")
            out["aaii"] = {"available": True, "as_of": str(o.survey_week),  # type: ignore[attr-defined]
                           "bullish": o.bullish, "bearish": o.bearish,  # type: ignore[attr-defined]
                           "spread": round(spread, 1), "state_cn": state}
            out["available"] = True
        except Exception:  # noqa: BLE001
            pass
    p = Path(root) / "naaim.csv"
    if p.exists():
        try:
            obs = senti.load_naaim_observations(p)
            o = obs[-1]
            expo = float(o.exposure_index)  # type: ignore[attr-defined]
            state = "机构极端乐观" if expo > 100 else ("机构极端悲观" if expo < 40 else "中性")
            out["naaim"] = {"available": True, "as_of": str(o.survey_week),  # type: ignore[attr-defined]
                            "exposure_index": expo, "state_cn": state,
                            "threshold_source_cn": "NAAIM 惯例（>100 极端乐观 / <40 极端悲观）"}
            out["available"] = True
        except Exception:  # noqa: BLE001
            pass
    return out


# ─────────────────────── 板块散户热度（复用快照） ───────────────────────
def sector_heat_boards() -> dict:
    """快照热度（仅一、二级行业上榜口径），供情绪页板块区。"""
    try:
        snap = json.loads((_CACHE / "sector_trend_snapshot.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"available": False}
    meta = snap.get("heat") or {}
    rows = [b for b in snap.get("boards", [])
            if b.get("heat_pctile") is not None and (b.get("level") or 3) <= 2]
    rows.sort(key=lambda b: -(b.get("heat_pctile") or 0))
    return {
        "available": bool(rows), "as_of": snap.get("as_of"), "meta": meta, "boards": rows,
    }


# ─────────────────────── 市场结构分化（结构市识别） ───────────────────────
def market_structure() -> dict:
    """板块热度结构：极化指数 + 热/冷板块群（结构市识别）。

    极化 = 同时存在 b50>70（强）与 b50<30（弱）的板块占比之和；高极化 +
    整体中性 = 结构市（部分板块狂欢、部分冰点），此时板块必须按自身画像
    单独对待，不能用整体环境一概而论（用户 2026-09-06 提出）。
    历史序列：sector_trend_history 的 b50（246 交易日）。
    """
    try:
        rows = json.loads((_CACHE / "sector_trend_history.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"available": False}
    l1l2 = None
    try:
        snap = json.loads((_CACHE / "sector_trend_snapshot.json").read_text(encoding="utf-8"))
        l1l2 = {b["code"] for b in snap.get("boards", []) if (b.get("level") or 3) <= 2}
    except (OSError, json.JSONDecodeError):
        l1l2 = None

    series = []
    for r in rows:
        vals = [v.get("b50") for c, v in (r.get("boards") or {}).items()
                if v.get("b50") is not None and (l1l2 is None or c in l1l2)]
        if len(vals) < 50:
            continue
        strong = sum(1 for x in vals if x > 70) / len(vals) * 100
        weak = sum(1 for x in vals if x < 30) / len(vals) * 100
        series.append({"date": r["date"], "strong_pct": round(strong, 1),
                       "weak_pct": round(weak, 1),
                       "polar": round(strong + weak, 1),
                       "median_b50": round(sorted(vals)[len(vals) // 2], 1)})
    if not series:
        return {"available": False}
    last = series[-1]
    # 当前热/冷板块群（强/弱名单，来自快照）
    groups = {"strong": [], "weak": []}
    try:
        for b in snap.get("boards", []):
            if (b.get("level") or 3) > 2 or b.get("b50") is None:
                continue
            item = {"name": b["name"], "b50": b["b50"], "code": b["code"]}
            if b["b50"] > 70:
                groups["strong"].append(item)
            elif b["b50"] < 30:
                groups["weak"].append(item)
        groups["strong"].sort(key=lambda x: -x["b50"])
        groups["weak"].sort(key=lambda x: x["b50"])
    except Exception:  # noqa: BLE001
        pass
    pol = last["polar"]
    state = ("结构市（强弱的板块同时大量存在，板块须单独画像，勿用整体环境一概而论）"
             if pol >= 50 else ("单边市（板块同涨同跌，整体环境权重更高）" if pol <= 25
                                else "中度分化"))
    return {
        "available": True, "as_of": last["date"], "state_cn": state,
        "polar": pol, "strong_pct": last["strong_pct"], "weak_pct": last["weak_pct"],
        "median_b50": last["median_b50"],
        "series": series[-120:],
        "strong_boards": groups["strong"][:10], "weak_boards": groups["weak"][:10],
        "note_cn": "极化指数 = b50>70 板块占比 + b50<30 占比（一、二级行业池）。"
                   "高极化 + 中位中性 = 结构市：热板块按警报读、冷板块按机会读，分别对待。",
    }


def board_profile(code: str) -> dict:
    """单板块情绪画像：自身热度（z）/ 相对热度（横截面分位）/ 趋势档位 / 信号 + 语义读法。"""
    try:
        snap = json.loads((_CACHE / "sector_trend_snapshot.json").read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {"available": False}
    row = next((b for b in snap.get("boards", []) if b.get("code") == code), None)
    if not row:
        return {"available": False}
    z = row.get("sig_retail_z")
    pct = row.get("heat_pctile")
    b50, b200 = row.get("b50"), None
    try:
        import pandas as pd
        df = pd.read_parquet(_CACHE / "a_share_klines.parquet")
        wide = df.pivot(index="date", columns="symbol", values="close").sort_index()
        members = json.loads((_CACHE / "sector_members.json").read_text(encoding="utf-8"))["boards"]
        b200 = self_b200(wide, members, code)
    except Exception:  # noqa: BLE001
        pass
    tier = None
    if b50 is not None and b200 is not None:
        if b50 > 70 and b200 > 70:
            tier = "全面强势"
        elif b50 > 50 and b200 < 30:
            tier = "反弹初"
        elif b50 < 50 and b200 > 70:
            tier = "回调中"
        elif b50 < 30:
            tier = "深度弱势"
    reading = []
    if z is not None and z >= 1.5 and tier == "全面强势":
        reading.append("散户涌入+全面强势=警报形态（回测-9.3%档）")
    if z is not None and z >= 1.5 and tier in ("深度弱势", None) and (row.get("sig_icepoint_pick")):
        reading.append("冰点机会形态（回测+6.5~7.8%档）")
    if pct is not None and pct >= 85:
        reading.append("相对全市场热度前15%（拥挤区，注意区分结构市背景）")
    if pct is not None and pct <= 15:
        reading.append("相对全市场热度后15%（冰点区）")
    return {
        "available": True, "code": code, "name": row.get("name"),
        "self_z": z, "cross_pctile": pct, "b50": b50, "b200": b200,
        "tier_cn": tier, "stage": row.get("stage"),
        "sig_icepoint_pick": row.get("sig_icepoint_pick"),
        "sig_heat_alarm": row.get("sig_heat_alarm"),
        "reading_cn": reading or ["无特殊形态（中性区）"],
    }


def self_b200(wide, members: dict, code: str) -> float | None:
    ma200 = wide.rolling(200, min_periods=200).mean()
    above = (wide > ma200).where(wide.notna())
    mem = [s for s in members.get(code, {}).get("members", []) if s in wide.columns]
    if len(mem) < 5:
        return None
    sub = above[mem].dropna(how="all")
    if len(sub) < 55 or sub.empty:
        return None
    last = sub.iloc[-1]
    n = last.notna().sum()
    return round(float(last.sum() / n * 100), 1) if n >= 5 else None


# ─────────────────────── 行动区（状态灯/预备进度/操作卡/持仓风险） ───────────────────────
_HOLDING_BOARDS = {
    "BK1215", "BK1036", "BK1207", "BK1201",          # cn_info 通信/半导体/计算机/电子
    "BK0478", "BK0732", "BK1015",                    # cn_metal 有色/贵金属/能源金属
    "BK1200", "BK1033", "BK0427",                    # cn_green_other 电力设备/电池/公用事业
    "BK0465", "BK1044", "BK1216",                    # 医药（创新药近似）
    "BK1277",                                        # 白酒
}


def _snap() -> dict:
    return json.loads((_CACHE / "sector_trend_snapshot.json").read_text(encoding="utf-8"))


def build_action() -> dict:
    """行动区数据（全部读冻结快照，无网络）。

    light: blue=冰点机会窗口开启 / red=有强热警报 / gray=无信号
    cn_ready: 三票预备进度（几票冷/共几票，含每票名称）
    opportunity_cards / alarm_cards: 操作卡原始件（胜率文案含证据账本数字）
    holding_risk: 持仓赛道板块的 危险/注意/安全 分级
    """
    try:
        snap = _snap()
    except (OSError, json.JSONDecodeError):
        return {"available": False, "light": "gray"}
    boards = snap.get("boards", [])
    meta = snap.get("sentiment_signals") or {}

    picks = [b for b in boards if b.get("sig_icepoint_pick")]
    alarms = [b for b in boards if b.get("sig_heat_alarm")]

    def card(b: dict, kind: str) -> dict:
        z = b.get("sig_retail_z")
        if kind == "pick":
            plan = ("操作参考（回测口径）：一周内任意时点入场 → 持有 15 日 → "
                    "中途不设紧止盈（回测：紧止盈把 95% 胜率洗成 60%）→ "
                    "36 日前必须离场（收益峰在第 14-16 日，36 日后转负）")
            win = ("多年验证通过（2022-2026 四次恐慌全盈利）：单事件收益 +0.6%~+12.9%、"
                   "胜率 57%~94%——恐慌越深越强（2026-07 与 2022 上海疫情段最强）；"
                   "板块同向性 92%（154 例）")
        else:
            plan = ("操作参考（回测口径）：警惕/回避——历史同形态 10 日 -9.3%、"
                    "29 例无一板块幸免；风险随时间累积，无短线博反弹价值")
            win = ("历史同条件：-9.3%（p=0.0009，单年样本；边界：仅 50&200 同高档，"
                   "反弹初档散户热为正向勿误读）")
        return {
            "code": b["code"], "name": b["name"], "level": b.get("level"),
            "z": z, "r60_pct": None, "b50": b.get("b50"),
            "stage": b.get("stage"), "plan_cn": plan, "win_rate_cn": win,
            "holding": b["code"] in _HOLDING_BOARDS,
        }

    # 持仓风险
    cn_cold = meta.get("cn_cold")
    holding = []
    for b in boards:
        if b["code"] not in _HOLDING_BOARDS:
            continue
        z, b50 = b.get("sig_retail_z"), b.get("b50")
        if b.get("sig_heat_alarm"):
            state, detail = "danger", "强热警报触发（散户涌入×全面强势）"
        elif b.get("sig_icepoint_pick"):
            state, detail = "watch", "冰点机会候选（观察）"
        elif z is not None and z >= 1.0 and b50 is not None and b50 > 70:
            state, detail = "watch", f"警报预备（散户z={z}、b50={b50:.0f}偏高，缺 b200 条件）"
        else:
            state, detail = "safe", "无情绪风险形态"
        holding.append({"code": b["code"], "name": b["name"], "state": state,
                        "detail_cn": detail, "z": z, "b50": b50})
    order = {"danger": 0, "watch": 1, "safe": 2}
    holding.sort(key=lambda x: order.get(x["state"], 9))

    light = "blue" if picks else ("red" if alarms else "gray")
    return {
        "available": True, "light": light,
        "cn_cold": cn_cold,
        "cn_ready": None,  # 三票明细在 cn_mood（网络）——轻端点不带，前端 dashboard 合并
        "opportunity_cards": [card(b, "pick") for b in picks],
        "alarm_cards": [card(b, "alarm") for b in alarms],
        "holding_risk": holding,
        "note_cn": "行动区为研究代理展示（research_proxy）：操作参考来自单年回测与"
                   "2026-07 单次恐慌期验证，多年终审进行中，非买卖点。",
    }
