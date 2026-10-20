#!/usr/bin/env python3
"""模拟盘账户状态机（2026-08-28 上线版·参数冻结口径）。

冻结配置（FINAL-VERDICT 后定版，禁改动，改动需彪哥拍板）：
- 分账制：ETF/指数腿 = B200 五档(h_80) 调新仓预算 × 50% 资金；
  个股腿（B'/C/D 信号）= 无闸 × 50% 资金；黄金(518850) 豁免宽度闸。
- 单笔风险 = 各腿权益 × 1% × 回撤降级(每 10% DD ×0.8) × 宽度cap(仅ETF腿)；
  并发上限 10（两腿各 5）。
- 买卖点：以 live 管线 daily_opportunity_scan 的 actionable 判定为
  候选（人工确认后 --fill 记录成交）；退出以 signal_alerts 的
  hard/warn 提示人工执行 --close。模拟盘不自动成交。

用法：
  python3 scripts/paper_account.py                # 生成当日简报+状态
  python3 scripts/paper_account.py --fill 510300.SS 4.12 4.05 ETF
  python3 scripts/paper_account.py --close 510300.SS 4.30
状态：~/.lei_signal_lab/paper/account.json；简报：paper/brief_*.md
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.request
from datetime import datetime
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "scripts"))
from run_final_form_v2 import H80  # noqa: E402

CACHE = Path.home() / ".lei_signal_lab"
PAPER = CACHE / "paper"
DB = CACHE / "lab.db"
GOLD = "518850.SS"
H80_T = tuple(H80)


def tier_cap(b200: float | None) -> float:
    if b200 is None:
        return 1.0
    for th, w in H80_T:
        if b200 <= th:
            return w
    return H80_T[-1][1]


def live_breadth() -> dict:
    """live 用途：优先 live 管线历史（每日更新），缺则研究史 33 年文件。"""
    live_hist = CACHE / "cache" / "a_share_ma_breadth_history.json"
    full = CACHE / "cache" / "a_share_ma_breadth_full_history.json"
    path = live_hist if live_hist.exists() else full
    try:
        obj = json.loads(path.read_text())
        assert isinstance(obj, list) and obj
    except Exception:  # noqa: BLE001
        obj = []
    last = obj[-1] if obj else {}
    return {"date": last.get("date"),
            "b20": last.get("ma20_pct") or last.get("b20"),
            "b50": last.get("ma50_pct") or last.get("b50"),
            "b200": last.get("ma200_pct") or last.get("b200")}


def scan_candidates() -> list[dict]:
    import sqlite3
    con = sqlite3.connect(DB)
    rows = con.execute(
        "SELECT symbol, display_name, verdict, verdict_cn, best_scenario_cn,"
        " reward_risk_ratio FROM daily_opportunity_scan"
        " WHERE verdict='actionable'"
        " AND scan_date=(SELECT MAX(scan_date) FROM daily_opportunity_scan)"
    ).fetchall()
    con.close()
    return [{"symbol": r[0], "name": r[1], "verdict_cn": r[3],
             "scenario": r[4], "rr": r[5]} for r in rows]


def qt_quote(symbol: str) -> float | None:
    """腾讯快照取最新价（sh/sz 前缀映射）。"""
    code = symbol.split(".")[0]
    pref = "sh" if symbol.endswith(".SS") else "sz"
    url = f"http://qt.gtimg.cn/q={pref}{code}"
    try:
        req = urllib.request.Request(
            url, headers={"User-Agent": "Mozilla/5.0"})
        txt = urllib.request.urlopen(req, timeout=5).read().decode("gbk")
        return float(txt.split("~")[3])
    except Exception:  # noqa: BLE001
        return None


def load_state() -> dict:
    f = PAPER / "account.json"
    if f.exists():
        return json.loads(f.read_text())
    return {"created": datetime.now().isoformat(),
            "legs": {"ETF": {"cash": 500_000.0, "peak": 500_000.0},
                     "STOCK": {"cash": 500_000.0, "peak": 500_000.0}},
            "positions": [], "history": []}


def save_state(st: dict) -> None:
    PAPER.mkdir(parents=True, exist_ok=True)
    (PAPER / "account.json").write_text(
        json.dumps(st, ensure_ascii=False, indent=1))


def leg_of(symbol: str) -> str:
    if symbol == GOLD:
        return "ETF"  # 豁免闸但在 ETF 腿记账
    return "ETF" if symbol.split(".")[0].startswith(
        ("51", "56", "58", "159")) else "STOCK"


def do_fill(st, symbol, price, stop, note="") -> None:
    leg = leg_of(symbol)
    lg = st["legs"][leg]
    br = live_breadth()
    cap = 1.0 if (symbol == GOLD or leg == "STOCK") else tier_cap(br["b200"])
    eq = lg["cash"] + sum(p["shares"] * p["last"] for p in st["positions"]
                          if p["leg"] == leg)
    dd = (lg["peak"] - eq) / lg["peak"] if lg["peak"] > 0 else 0
    factor = 0.8 ** int(dd / 0.10)
    budget = eq * 0.01 * factor * cap
    risk = max(price - stop, 1e-6)
    shares = int(budget / risk / 100) * 100
    if shares <= 0 or budget > lg["cash"]:
        print(f"[拒] {symbol} 预算 {budget:.0f} 或现金不足")
        return
    lg["cash"] -= shares * price
    st["positions"].append({
        "symbol": symbol, "leg": leg, "entry_date": datetime.now().date().isoformat(),
        "entry": price, "stop": stop, "shares": shares,
        "budget": round(budget, 2), "cap": cap, "factor": round(factor, 3),
        "last": price, "note": note})
    print(f"[成交] {symbol} {leg}腿 {shares}股 @ {price} 止损 {stop}"
          f"（预算 {budget:.0f} cap={cap} 降级×{factor:.2f}）")


def do_close(st, symbol, price) -> None:
    for i, p in enumerate(st["positions"]):
        if p["symbol"] == symbol:
            pnl = (price - p["entry"]) * p["shares"]
            st["legs"][p["leg"]]["cash"] += p["shares"] * price
            st["legs"][p["leg"]]["peak"] = max(
                st["legs"][p["leg"]]["peak"], st["legs"][p["leg"]]["cash"])
            st["positions"].pop(i)
            st["history"].append({**p, "exit": price,
                                  "pnl": round(pnl, 2),
                                  "exit_date": datetime.now().date().isoformat()})
            print(f"[平仓] {symbol} @ {price} 盈亏 {pnl:+,.0f}")
            return
    print(f"[缺] 无持仓 {symbol}")


def brief(st) -> str:
    br = live_breadth()
    cap = tier_cap(br["b200"])
    lines = [f"# 模拟盘简报 {datetime.now().date()}",
             f"\n## 市场层（宽度 {br['date']}）",
             f"- B20 {br['b20']:.1f}% / B50 {br['b50']:.1f}% / "
             f"B200 {br['b200']:.1f}% → ETF 腿新仓乘数 ×{cap}",
             "- 黄金 518850 豁免；个股腿无闸"]
    cands = scan_candidates()
    lines.append(f"\n## 今日候选（actionable {len(cands)} 个）")
    for c in cands:
        lines.append(f"- {c['symbol']} {c['name']}：{c['scenario']} "
                     f"(RR {c['rr'] or '—'}) 〔{leg_of(c['symbol'])}腿〕")
    lines.append("\n## 持仓")
    if not st["positions"]:
        lines.append("-（空仓）")
    for p in st["positions"]:
        px = qt_quote(p["symbol"]) or p["last"]
        p["last"] = px
        pnl = (px - p["entry"]) * p["shares"]
        lines.append(f"- {p['symbol']} {p['leg']}腿 {p['shares']}股 "
                     f"入 {p['entry']} → 现 {px} 止损 {p['stop']} "
                     f"盈亏 {pnl:+,.0f}")
    for k, lg in st["legs"].items():
        eq = lg["cash"] + sum(p["shares"] * p["last"]
                              for p in st["positions"] if p["leg"] == k)
        lines.append(f"\n{k}腿：权益 {eq:,.0f}（现金 {lg['cash']:,.0f}）")
    txt = "\n".join(lines)
    PAPER.mkdir(parents=True, exist_ok=True)
    (PAPER / f"brief_{datetime.now().date()}.md").write_text(txt,
                                                             encoding="utf-8")
    save_state(st)
    return txt


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fill", nargs=3, metavar=("SYMBOL", "PRICE", "STOP"))
    ap.add_argument("--close", nargs=2, metavar=("SYMBOL", "PRICE"))
    args = ap.parse_args()
    st = load_state()
    os.environ.setdefault("NO_PROXY", "*")
    if args.fill:
        do_fill(st, args.fill[0], float(args.fill[1]), float(args.fill[2]))
    if args.close:
        do_close(st, args.close[0], float(args.close[1]))
    print(brief(st))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
