"""T2 续：已封存模块 A 候选的机会母体审计（只数事件与标签，不计算任何收益）。

对象：GitHub 已跟踪的冻结候选
  docs/experiments/raw/research-broad-etf-technical-2026-09-08/execution/inputs/source-candidates/precision-candidates.json.gz
中全部 A 类（A20/60/120 × E 早期版 / J 确认版），共 504 条，四个产品 sh510300、sz159915、sh513100、sh518880。
步骤：
  1. 用第十二批已核行情（bars-helper-native）＋已存行动（现金分红、拆分前复权，技术价格研究代理），
     调用生产 first_ma_pullback 3.0.0 重算事件；按 event_id 与冻结候选逐条对上（复现检查）。
     指标对整体缩放不变，所以前复权与冻结批次的分段基准在比较“是否离开触碰带”上等价；止损/收盘比另行核对。
  2. 对复现的候选，按 T2 推荐读法分类：是否落在推荐读法的同一次回撤里；不在的，触碰前是否有过
     “整天最低价 > SMA_g + ATR20”（真正离开再回来）；落在里面的，首次标记与止损是否不同。
  3. 统计 48 账户实际成交（roundtrips）里各类各占多少。
不读、不算任何持仓收益；结果写 population-audit.json。
"""
from __future__ import annotations

import gzip
import json
import math
import sys
from collections import Counter, defaultdict
from pathlib import Path

import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[3]
T2 = HERE.parent / "remote-astra-T2-2026-09-30"
sys.path[:0] = [str(T2), str(REPO / "src")]

import lei_signal.rules.first_ma_pullback as fmp  # noqa: E402
from lei_signal.rules.first_ma_pullback import detect_first_ma_pullback_events  # noqa: E402
from lei_signal.rules.strict_structure import SIDE_BOTTOM, detect_strict_structures  # noqa: E402
from lifecycle_ref import PRODUCTION, RECOMMENDED, run_reference  # noqa: E402
from real_coverage import features, rows_of  # noqa: E402

TECH = REPO / "docs/experiments/raw/research-broad-etf-technical-2026-09-08/execution"
BARS = REPO / ("docs/experiments/raw/research-twelfth-2026-09-08/independent-review/accepted/"
               "product-qualification/bars-helper-native")
CANDS = TECH / "inputs/source-candidates/precision-candidates.json.gz"
SYMBOLS = ("sh510300", "sz159915", "sh513100", "sh518880")
GROUP_LABEL = {"sh510300": "国内宽基", "sz159915": "国内宽基", "sh513100": "海外（纳指）", "sh518880": "黄金"}


def load(symbol: str) -> tuple[pd.DataFrame, list[dict]]:
    bars = pd.read_csv(BARS / f"{symbol}-nominal.csv", parse_dates=["date"]).set_index("date")
    actions = json.loads((TECH / "inputs/actions.json").read_text(encoding="utf-8"))
    applied = []
    for act in sorted((a for a in actions if a["symbol"] == symbol), key=lambda a: a["effective_date"]):
        ex = pd.Timestamp(act["effective_date"])
        before = bars.index[bars.index < ex]
        if len(before) == 0 or ex > bars.index[-1]:
            continue
        if act["type"] == "cash_dividend":
            prev = float(bars.loc[before[-1], "close"])
            factor = (prev - float(act["cash"])) / prev
        elif act["type"] == "split":
            factor = 1.0 / float(act["ratio"])
        else:
            continue
        for col in ("open", "high", "low", "close"):
            bars.loc[bars.index < ex, col] *= factor
        applied.append({"event_id": act["event_id"], "factor": factor})
    return bars, applied


def asof_structures(frame):
    """逐日只用当日及此前行情识别严格构造：取第 i 日前缀里“确认日=第 i 日”的构造；
    失效日由其后最低价跌破构造前低点决定（向前看失效只用于 as_of 之后的判断）。"""
    lows = frame["low"].to_numpy()
    dates = [ts.date() for ts in frame.index]
    out = []
    for i in range(len(frame)):
        for st in detect_strict_structures(frame.iloc[: i + 1]):
            if st.confirmed_date != dates[i]:
                continue
            st.invalidated_date, st.invalidated_reason = None, None
            for j in range(i + 1, len(frame)):
                if st.side == SIDE_BOTTOM and lows[j] < st.reference_price:
                    st.invalidated_date, st.invalidated_reason = dates[j], "new_low_breaks_bottom"
                    break
                if st.side != SIDE_BOTTOM and frame["high"].iat[j] > st.reference_price:
                    st.invalidated_date, st.invalidated_reason = dates[j], "higher_high_breaks_top"
                    break
            out.append(st)
    return out


def prod_events(frame, symbol, structures=None):
    if structures is not None:
        original = fmp.detect_strict_structures
        fmp.detect_strict_structures = lambda f: list(structures)
        try:
            return prod_events(frame, symbol)
        finally:
            fmp.detect_strict_structures = original
    out = {}
    for e in detect_first_ma_pullback_events(frame, symbol):
        x = e.evidence
        out[e.event_id] = dict(date=e.available_date.isoformat(), group=x["ma_period"],
                               kind=x["sub_rule"].replace("first_ma_pullback_", ""),
                               variant=x.get("entry_variant"), first=x["is_first_touch"],
                               touch=x.get("touch_date"), stop=x.get("stop_price"), close=x.get("close"),
                               reason=x.get("failure_reason"))
    return out


def ref_windows(rows, structs, variant):
    """推荐读法下每组的回撤存续区间 [touch, end] 及其结果。"""
    win = defaultdict(list)
    for e in run_reference(rows, structures=structs, entry_variant=variant, **RECOMMENDED):
        if e["type"] == "signal" and e.get("variant") == variant:
            win[e["group"]].append((e["touch"], e["date"], "signal", e["first"], e["C"]))
        elif e["type"] == "cancel":
            win[e["group"]].append((e["touch"], e["date"], "cancel", e["first"], None))
    return win


def main() -> int:
    asof = "--asof-structures" in sys.argv
    cands = [c for c in json.load(gzip.open(CANDS)) if c["config_id"].startswith("A")]
    traded = Counter()
    for acct in sorted((TECH / "account-results").glob("*-A*-fee10bp")):
        for rt in json.loads((acct / "roundtrips.json").read_text(encoding="utf-8")):
            traded[rt["candidate_id"]] += 1
    result = {"_note": "只数事件与标签；不读收益。技术价格＝名义价前复权（研究代理）；构造识别为生产全历史计算。",
              "frozen_A_candidates": len(cands), "traded_roundtrips_fee10bp": sum(traded.values()),
              "per_symbol": {}}
    totals = Counter()
    traded_totals = Counter()
    for symbol in SYMBOLS:
        bars, applied = load(symbol)
        frame, structs = features(bars)
        asof_list = None
        if asof:
            asof_list = asof_structures(frame)
            structs = [dict(id=x.structure_id, confirmed_date=x.confirmed_date.isoformat(),
                            invalidated_date=x.invalidated_date.isoformat() if x.invalidated_date else None)
                       for x in asof_list if x.side == SIDE_BOTTOM]
        rows = rows_of(frame)
        prod = prod_events(frame, symbol, asof_list)
        clear = {g: (frame["low"] > frame[f"sma{g}"] + frame["atr20"]) for g in (20, 60, 120)}
        days = [r["date"] for r in rows]
        pos = {d: i for i, d in enumerate(days)}
        opens = [e["date"] for e in run_reference(rows, structures=structs, **PRODUCTION) if e["type"] == "episode_open"]
        ends = defaultdict(list)
        for e in prod.values():
            if e["kind"] in ("failed", "confirmed"):
                ends[e["group"]].append(e["date"])
        windows = {"early": ref_windows(rows, structs, "early"), "confirmed": ref_windows(rows, structs, "confirmed")}
        sym = [c for c in cands if c["symbol"] == symbol]
        cls = Counter()
        traded_cls = Counter()
        repro = Counter()
        examples = []
        for c in sym:
            ev = c["metadata"]["source_event"]
            mine = prod.get(ev["event_id"])
            x = ev["evidence"]
            if mine is None:
                repro["not_reproduced"] += 1
                continue
            ratio_frozen = float(x["stop_price"]) / float(x["close"])
            ratio_mine = float(mine["stop"]) / float(mine["close"])
            same = (mine["date"] == ev["available_date"] and mine["touch"] == x["touch_date"]
                    and mine["first"] == x["is_first_touch"] and mine["variant"] == x["entry_variant"]
                    and abs(ratio_frozen - ratio_mine) < 1e-9)
            repro["reproduced" if same else "id_match_fields_differ"] += 1
            if not same:
                continue
            g, variant = mine["group"], mine["variant"]
            w = next((w for w in windows[variant][g] if w[0] <= mine["date"] <= w[1]), None)
            if w is None:
                start = max([d for d in ends[g] if d < mine["touch"]] + [d for d in opens if d <= mine["touch"]]
                            + [days[0]])
                departed = bool(clear[g].iloc[pos[start] + 1: pos[mine["touch"]]].any())
                k = "outside_recommended_departed" if departed else "no_departure_before_touch"
            elif w[2] == "cancel":
                k = "recommended_same_pullback_but_cancelled"
            else:
                diff = []
                if w[3] != mine["first"]:
                    diff.append("first_flag")
                if w[4] is not None and float(mine["stop"]) / float(mine["close"]) > (w[4] / float(mine["close"])) + 1e-12:
                    diff.append("stop_raised")
                if w[1] != mine["date"]:
                    diff.append("entry_date")
                k = "same_pullback_" + ("+".join(diff) if diff else "identical")
            cls[k] += 1
            if traded[c["candidate_id"]]:
                traded_cls[k] += traded[c["candidate_id"]]
            if len(examples) < 6 and k.startswith("no_departure"):
                examples.append({"candidate_id": c["candidate_id"], "signal_date": mine["date"], "touch": mine["touch"],
                                 "group": g, "variant": variant})
        totals.update(cls)
        traded_totals.update(traded_cls)
        result["per_symbol"][symbol] = {"label": GROUP_LABEL[symbol], "actions_applied": len(applied),
                                        "frozen": len(sym), "reproduction": dict(repro),
                                        "classes": dict(cls), "traded_roundtrips_by_class": dict(traded_cls),
                                        "examples_no_departure": examples}
    result["totals"] = dict(totals)
    result["traded_totals"] = dict(traded_totals)
    result["structure_mode"] = "as_of_daily_prefix" if asof else "production_full_history"
    (HERE / ("population-audit-asof.json" if asof else "population-audit.json")).write_text(json.dumps(result, ensure_ascii=False, indent=1) + "\n",
                                                encoding="utf-8")
    for s, v in result["per_symbol"].items():
        print(s, v["frozen"], v["reproduction"], v["classes"], "traded:", v["traded_roundtrips_by_class"])
    print("TOTAL", result["totals"], "TRADED", result["traded_totals"], "of", result["traded_roundtrips_fee10bp"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
