# -*- coding: utf-8 -*-
"""定投埋伏×GLM 自主退出实验（2026-09-07，用户口径「结合glm自主性去测」）。

规则版结论（ambush_dca_exit_study.py）：止盈退出的价值取决于后续走势类型
（半导体不退出赢/恒科止盈赢/白酒医药怎么都亏）——规则无法预知，测 GLM
综合判断是否优于固定规则。

设计：
- 埋伏同规则版（下跌型周投）；持仓>0 时每 2 个月末给 GLM 一次决策材料：
  当前形态/近90日涨幅/累计成本收益/已投周数/A股宽度三值；
- GLM 决策：hold（继续持有，埋伏与否由形态规则管）/ sell_half（卖一半
  锁利）/ clear（清仓）；
- 对照：不退出 / 规则趋势止盈 / GLM版；temperature=0，全部响应存档。

用法：python scripts/ambush_dca_glm_exit.py [--limit 标的数]
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

POOL = Path.home() / ".lei_signal_lab" / "backtest_pool"
TARGETS = {
    "512690.SS": "白酒ETF", "513180.SS": "恒生科技", "512010.SS": "医药ETF",
    "512480.SS": "半导体ETF", "510300.SS": "沪深300ETF",
}
START, END = "2021-01-04", "2026-08-24"
FEE = 0.001

PROMPT = """你是趋势交易系统的定投埋伏退出决策员。某标的一直在下跌区间做周度定投埋伏（下跌型周投、其它停投持有），现在你来决定持仓怎么办。

【背景知识（历史回测）】
- 止盈退出的价值取决于后续走势：一路走牛的标的（如半导体2023-2026）不退出最赚，中途止盈踏空；反弹后回落的（如恒生科技2025）趋势止盈锁利最赚；永不反转的（白酒/医药2021-2026）怎么退都亏。
- 定投的现金流结构自带风控（跌时只有部分资金在场内），防御性清仓已被证伪。
- 你的任务不是预测，是判断「当前证据下锁利还是持有更划算」。

【当前材料】
{material}

【任务】只依据材料判断：hold（继续持有）/ sell_half（卖一半锁利）/ clear（清仓）。
输出 JSON：{{"action": "hold"|"sell_half"|"clear", "reason": "一句话不超30字"}}"""


def load_env() -> None:
    env = Path(__file__).resolve().parents[1] / ".env"
    if env.exists():
        for line in env.read_text().splitlines():
            if "=" in line and not line.strip().startswith("#"):
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip())


def call_glm(material: str) -> dict:
    key = os.environ["GLM_API_KEY"]
    model = os.environ.get("GLM_MODEL", "glm-5.3")
    base = os.environ.get("GLM_BASE_URL", "https://open.bigmodel.cn/api/coding/paas/v4")
    body = json.dumps({
        "model": model, "temperature": 0,
        "messages": [{"role": "user", "content": PROMPT.format(material=material)}],
    }).encode()
    req = urllib.request.Request(
        f"{base}/chat/completions", data=body,
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=60) as resp:
        out = json.load(resp)
    text = (out.get("choices") or [{}])[0].get("message", {}).get("content", "")
    m = re.search(r"\{[^{}]*\}", text, re.S)
    if not m:
        return {"action": "hold", "reason": ""}
    try:
        d = json.loads(m.group(0))
        if d.get("action") not in ("hold", "sell_half", "clear"):
            d["action"] = "hold"
        return d
    except json.JSONDecodeError:
        return {"action": "hold", "reason": ""}


def regime_series(close: pd.Series) -> pd.Series:
    ema20 = close.ewm(span=20, adjust=False).mean()
    ema60 = close.ewm(span=60, adjust=False).mean()
    env = ((ema20 > ema60) & (ema20.diff() > 0)).rolling(250, min_periods=120).mean()
    ret = close.pct_change(250)
    below = close < ema20 * 0.985
    brk = (below & ~below.shift(1, fill_value=False)).rolling(250, min_periods=120).sum()
    out = pd.Series("range", index=close.index)
    out[ret < -0.15] = "downtrend"
    out[(env >= 0.55) & (brk <= 20)] = "steady_uptrend"
    out[(ret > 0.50) & ~((env >= 0.55) & (brk <= 20))] = "fast_uptrend"
    return out


REG_CN = {"downtrend": "下跌型", "steady_uptrend": "稳涨型", "fast_uptrend": "急涨型", "range": "震荡型"}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0)
    args = ap.parse_args()
    load_env()
    bh = json.load(open(Path.home() / ".lei_signal_lab/cache/a_share_ma_breadth_history.json"))
    bmap = {str(r["date"]): r for r in bh if r.get("date")}
    bdates = sorted(bmap)

    cache_path = Path("/tmp/ambush_glm_decisions.jsonl")
    done: set[tuple] = set()
    if cache_path.exists():
        for line in cache_path.read_text().splitlines():
            try:
                d = json.loads(line)
                done.add((d["symbol"], d["date"]))
            except (json.JSONDecodeError, KeyError):
                continue

    results = {}
    syms = list(TARGETS.items())[: args.limit] if args.limit else list(TARGETS.items())
    for sym, name in syms:
        df = pd.read_parquet(POOL / f"{sym}.bars.parquet")
        df.index = pd.to_datetime(df.index)
        w = df.loc[START:END]
        close = w["close"]
        reg = regime_series(close).reindex(w.index)
        shares = 0.0
        invested = 0.0
        cash = 0.0
        last_week = None
        last_decision_month = None
        equity: list[float] = []
        decisions = 0
        for date, price in close.items():
            r = reg.loc[date]
            wk = (date.isocalendar()[1], date.isocalendar()[0])
            if last_week is None or wk != last_week:
                last_week = wk
                if r == "downtrend":
                    shares += (1 - FEE) / price
                    invested += 1.0
            # 双月决策：每月最后一个交易日（次日已跨月才算月末）
            if shares > 1e-9:
                pos = close.index.get_loc(date)
                if pos + 1 < len(close.index):
                    nxt = close.index[pos + 1]
                    is_last_day = nxt.month != date.month or nxt.year != date.year
                else:
                    is_last_day = False
                if is_last_day and (date.month % 2 == 0):
                    key = (sym, str(date.date()))
                    if key not in done:
                        bd = [x for x in bdates if x <= str(date.date())]
                        bw = bmap[bd[-1]] if bd else None
                        value = shares * price
                        material = json.dumps({
                            "标的": f"{name}({sym})",
                            "日期": str(date.date()),
                            "当前形态": REG_CN.get(r, r),
                            "近90日涨幅%": round(float(price / close.loc[:date].iloc[-90] - 1) * 100, 1) if len(close.loc[:date]) > 90 else None,
                            "持仓累计收益率%": round((value / invested - 1) * 100, 1) if invested else None,
                            "已投周数": int(invested),
                            "A股宽度": {"ma20": round(bw["ma20_pct"], 0), "ma200": round(bw["ma200_pct"], 0)} if bw else None,
                        }, ensure_ascii=False)
                        j = call_glm(material)
                        with open(cache_path, "a") as fh:
                            fh.write(json.dumps({"symbol": sym, "date": str(date.date()), **j}, ensure_ascii=False) + "\n")
                        done.add(key)
                        decisions += 1
                        time.sleep(0.3)
                    # 执行已缓存的当日决策
                    for line in cache_path.read_text().splitlines():
                        try:
                            d = json.loads(line)
                        except json.JSONDecodeError:
                            continue
                        if d.get("symbol") == sym and d.get("date") == str(date.date()):
                            act = d.get("action")
                            if act == "sell_half":
                                cash += shares / 2 * price * (1 - FEE)
                                shares /= 2
                            elif act == "clear":
                                cash += shares * price * (1 - FEE)
                                shares = 0.0
                            break
            equity.append(cash + shares * price)
        eq = pd.Series(equity, index=close.index)
        final = float(eq.iloc[-1])
        years = (close.index[-1] - close.index[0]).days / 365
        peak = eq.cummax()
        mdd = float((eq / peak - 1).min())
        results[sym] = {
            "name": name, "invested": round(invested, 0), "final": round(final, 0),
            "multiple": round(final / invested, 2) if invested else None,
            "cagr": round(((final / invested) ** (1 / years) - 1) * 100, 1) if invested and final > 0 else None,
            "mdd": round(mdd * 100, 1), "decisions": decisions,
        }
        print(f"{name:8s} GLM版: 投入{invested:.0f} 终值{final:.0f} "
              f"倍数{results[sym]['multiple']} 年化{results[sym]['cagr']}% 回撤{results[sym]['mdd']}% 决策{decisions}次")
    print(json.dumps(results, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
