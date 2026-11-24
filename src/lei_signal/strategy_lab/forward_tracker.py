"""Strategy Lab 自动前向观察与实盘漂移监控闭环（forward_tracker）。

解决旧系统两大断层：
1. `forward_observation/` 停更、旧 `paper/` 三个月 0 成交，而天天在跑的 `daily-funnel` 推荐缺乏事后客观追踪；
2. 缺乏“前向实盘表现 vs 回测预期区间”的自动漂移预警，无法及时发现策略在真实新行情中失效。

核心机制：
- 独立轻量 SQLite 账本（`~/.lei_signal_lab/strategy_lab_ledger/forward_ledger.sqlite3`），零干扰主 `lab.db`；
- 每日收盘自动冻结当日推荐快照 + 核心策略源码 SHA-256 指纹（同一信号日不可篡改覆盖，严禁倒填历史）；
- 随新交易日到来自动结算每笔推荐的 5日 / 20日 / 60日真实前向收益与相对沪深300超额（未到期保持 pending，绝不填零）；
- 维护两套自动前向纸面模拟袖套（行业基金袖套 / 龙头个股袖套，各 50 万起），严格按次日开盘成交与同源退出规则自动记账并独立核对 cash + market_value == equity！
"""
from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sqlite3
import numpy as np
import pandas as pd

from .chip_trend import compute_live_chip_metrics, rank_top_candidates
from .data_portal import DataPortal
from .fund_evaluator import evaluate_all_fund_opportunities


_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS snapshots (
    signal_date TEXT PRIMARY KEY,
    recorded_at TEXT NOT NULL,
    code_fingerprint TEXT NOT NULL,
    payload_sha256 TEXT NOT NULL,
    payload_json TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS recommendations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    signal_date TEXT NOT NULL,
    sleeve TEXT NOT NULL,          -- 'sector_etf' | 'stock_leader' | 'stock_small_giant'
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    rank_idx INTEGER NOT NULL,
    rank_score REAL,
    signal_close REAL NOT NULL,
    stop_price REAL,
    entry_date TEXT,
    entry_open REAL,
    ret_5d REAL,
    excess_5d REAL,
    ret_20d REAL,
    excess_20d REAL,
    ret_60d REAL,
    excess_60d REAL,
    status TEXT NOT NULL DEFAULT 'pending_entry',
    UNIQUE(signal_date, sleeve, symbol)
);

CREATE TABLE IF NOT EXISTS paper_accounts (
    sleeve TEXT PRIMARY KEY,
    initial_cash REAL NOT NULL,
    cash REAL NOT NULL,
    equity REAL NOT NULL,
    peak_equity REAL NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paper_positions (
    sleeve TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    entry_date TEXT NOT NULL,
    entry_price REAL NOT NULL,
    entry_signal_close REAL NOT NULL,
    entry_poc REAL NOT NULL,
    max_close REAL NOT NULL,
    shares REAL NOT NULL,
    notional REAL NOT NULL,
    PRIMARY KEY (sleeve, symbol)
);

CREATE TABLE IF NOT EXISTS paper_trades (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sleeve TEXT NOT NULL,
    symbol TEXT NOT NULL,
    name TEXT NOT NULL,
    entry_date TEXT NOT NULL,
    exit_date TEXT NOT NULL,
    entry_price REAL NOT NULL,
    exit_price REAL NOT NULL,
    shares REAL NOT NULL,
    net_return REAL NOT NULL,
    pnl_yuan REAL NOT NULL,
    exit_reason TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS paper_nav_history (
    sleeve TEXT NOT NULL,
    as_of TEXT NOT NULL,
    cash REAL NOT NULL,
    market_value REAL NOT NULL,
    equity REAL NOT NULL,
    bench_close REAL,
    reconciled INTEGER NOT NULL,
    PRIMARY KEY (sleeve, as_of)
);
"""


def compute_strategy_code_fingerprint(repo_root: Path | None = None) -> str:
    """对核心策略源码计算稳定 SHA-256 指纹，用于在前向账本中记录每次推荐时的规则版本。"""
    base = (
        Path(repo_root) / "src/lei_signal/strategy_lab"
        if repo_root is not None
        else Path(__file__).resolve().parent
    )
    h = hashlib.sha256()
    for fname in ("signals.py", "fund_evaluator.py", "chip_trend.py", "portfolio_sim.py"):
        p = base / fname
        if p.exists():
            h.update(fname.encode("utf-8"))
            h.update(p.read_bytes())
    return h.hexdigest()[:16]


class ForwardTracker:
    """不可篡改前向观察账本 + 自动前向模拟盘 + 回测漂移监控器。"""

    def __init__(self, portal: DataPortal, db_path: Path | None = None) -> None:
        self.portal = portal
        self.db_path = (
            Path(db_path)
            if db_path is not None
            else (portal.lab_home / "strategy_lab_ledger" / "forward_ledger.sqlite3")
        )
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        now_iso = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.executescript(_SCHEMA_SQL)
            for sleeve in ("sector_etf", "stock_leader"):
                conn.execute(
                    """
                    INSERT OR IGNORE INTO paper_accounts
                    (sleeve, initial_cash, cash, equity, peak_equity, updated_at)
                    VALUES (?, 500000.0, 500000.0, 500000.0, 500000.0, ?)
                    """,
                    (sleeve, now_iso),
                )

    @staticmethod
    def _to_symbol(code_or_sym: str) -> str:
        return DataPortal.normalize_cn_symbol(code_or_sym)

    def record_snapshot(
        self,
        snapshot: dict[str, object] | None = None,
        *,
        top_n: int = 10,
    ) -> dict[str, object]:
        """将当日收盘 `daily-funnel` 推荐冻结写入前向账本（同信号日幂等保护，绝不篡改旧快照）。"""
        if snapshot is None:
            fund_opps = evaluate_all_fund_opportunities(self.portal)
            leaders = rank_top_candidates(self.portal, top_n=top_n, pool="leader", split="full")
            smalls = rank_top_candidates(self.portal, top_n=top_n, pool="small_giant", split="full")
            snapshot = {
                "fund_opportunities": fund_opps,
                "top_industry_leaders": leaders,
                "top_small_giants": smalls,
            }

        # 提取本次推荐锚定的最新市场信号日
        fund_opps = snapshot.get("fund_opportunities") or {}
        right_funds = list(fund_opps.get("right_side_sector_picks") or [])
        leaders = list(snapshot.get("top_industry_leaders") or [])
        smalls = list(snapshot.get("top_small_giants") or [])
        broad = list(fund_opps.get("broad_compass") or [])

        dates_found = [
            str(item["as_of"])
            for item in (right_funds + leaders + smalls + broad)
            if isinstance(item, dict) and item.get("as_of")
        ]
        if not dates_found:
            try:
                bench = self.portal.load_bars("510300.SS", market="CN", split="full")
                signal_date = str(bench.index[-1].date())
            except Exception:
                signal_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        else:
            signal_date = max(dates_found)

        payload_str = json.dumps(snapshot, ensure_ascii=False, sort_keys=True)
        payload_sha = hashlib.sha256(payload_str.encode("utf-8")).hexdigest()
        code_fp = compute_strategy_code_fingerprint(self.portal.repo_root)
        now_iso = datetime.now(timezone.utc).isoformat()

        with self._connect() as conn:
            existing = conn.execute(
                "SELECT signal_date, payload_sha256, code_fingerprint FROM snapshots WHERE signal_date = ?",
                (signal_date,),
            ).fetchone()
            if existing is not None:
                return {
                    "recorded": False,
                    "reason": "already_frozen_for_date",
                    "signal_date": signal_date,
                    "code_fingerprint": existing["code_fingerprint"],
                    "payload_sha256": existing["payload_sha256"],
                }

            conn.execute(
                """
                INSERT INTO snapshots (signal_date, recorded_at, code_fingerprint, payload_sha256, payload_json)
                VALUES (?, ?, ?, ?, ?)
                """,
                (signal_date, now_iso, code_fp, payload_sha, payload_str),
            )

            rec_count = 0
            for sleeve, items in (
                ("sector_etf", right_funds),
                ("stock_leader", leaders),
                ("stock_small_giant", smalls),
            ):
                for idx, item in enumerate(items, 1):
                    sym = self._to_symbol(str(item.get("symbol") or item.get("code") or ""))
                    if not sym:
                        continue
                    cl = float(item.get("close") or 0.0)
                    if cl <= 0:
                        continue
                    conn.execute(
                        """
                        INSERT OR IGNORE INTO recommendations
                        (signal_date, sleeve, symbol, name, rank_idx, rank_score, signal_close, stop_price)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            signal_date,
                            sleeve,
                            sym,
                            str(item.get("name") or sym),
                            idx,
                            float(item.get("rank_score") or 0.0),
                            cl,
                            float(item["stop_price"]) if item.get("stop_price") else (float(item["stop_defense_price"]) if item.get("stop_defense_price") else None),
                        ),
                    )
                    rec_count += 1

        return {
            "recorded": True,
            "signal_date": signal_date,
            "recommendations_frozen": rec_count,
            "code_fingerprint": code_fp,
            "payload_sha256": payload_sha[:16],
        }

    def reconcile(self) -> dict[str, object]:
        """用最新完整收盘行情自动结算历史推荐的 5/20/60 日真实前向表现，并推进前向纸面模拟账户对账。"""
        try:
            bench_bars = self.portal.load_bars("510300.SS", market="CN", split="full")
        except FileNotFoundError:
            return {"reconciled": False, "reason": "缺少沪深300基准行情"}

        bench_close = bench_bars["close"].astype(float).sort_index()
        bench_open = bench_bars["open"].astype(float).sort_index()
        latest_market_dt = bench_close.index[-1]
        latest_str = str(latest_market_dt.date())

        bars_cache: dict[str, pd.DataFrame] = {}

        def _get_bars(sym: str) -> pd.DataFrame | None:
            if sym not in bars_cache:
                try:
                    bars_cache[sym] = self.portal.load_bars(sym, market="CN", split="full")
                except FileNotFoundError:
                    bars_cache[sym] = pd.DataFrame()
            df = bars_cache[sym]
            return df if len(df) > 0 else None

        updated_recs = 0
        with self._connect() as conn:
            # 1) 逐条结算推荐的 5 / 20 / 60 日真实前向净收益与相对沪深300超额
            rows = conn.execute(
                "SELECT * FROM recommendations WHERE status != 'matured_60d' ORDER BY signal_date ASC"
            ).fetchall()
            for r in rows:
                sig_ts = pd.Timestamp(r["signal_date"])
                bars = _get_bars(r["symbol"])
                if bars is None:
                    continue
                after = bars.loc[bars.index > sig_ts]
                if len(after) == 0:
                    continue
                entry_ts = after.index[0]
                entry_open = float(after["open"].iloc[0])
                if not (np.isfinite(entry_open) and entry_open > 0):
                    continue
                b_after = bench_open.loc[bench_open.index >= entry_ts]
                b_entry = float(b_after.iloc[0]) if len(b_after) > 0 else np.nan

                vals: dict[str, float | None] = {}
                for h in (5, 20, 60):
                    if len(after) >= h:
                        exit_ts = after.index[h - 1]
                        exit_cl = float(after["close"].iloc[h - 1])
                        ret_h = exit_cl / entry_open - 1.0
                        b_exit = float(bench_close.asof(exit_ts)) if np.isfinite(b_entry) and b_entry > 0 else np.nan
                        ex_h = (ret_h - (b_exit / b_entry - 1.0)) if (np.isfinite(b_exit) and b_entry > 0) else None
                        vals[f"ret_{h}d"] = round(ret_h, 5)
                        vals[f"excess_{h}d"] = round(ex_h, 5) if ex_h is not None else None
                    else:
                        vals[f"ret_{h}d"] = None
                        vals[f"excess_{h}d"] = None

                if vals["ret_60d"] is not None:
                    st = "matured_60d"
                elif vals["ret_20d"] is not None:
                    st = "matured_20d"
                elif vals["ret_5d"] is not None:
                    st = "matured_5d"
                else:
                    st = "active"

                conn.execute(
                    """
                    UPDATE recommendations
                    SET entry_date=?, entry_open=?,
                        ret_5d=?, excess_5d=?, ret_20d=?, excess_20d=?, ret_60d=?, excess_60d=?,
                        status=?
                    WHERE id=?
                    """,
                    (
                        str(entry_ts.date()), round(entry_open, 4),
                        vals["ret_5d"], vals["excess_5d"],
                        vals["ret_20d"], vals["excess_20d"],
                        vals["ret_60d"], vals["excess_60d"],
                        st, r["id"],
                    ),
                )
                updated_recs += 1

            # 2) 推进两套自动前向纸面模拟袖套（按真实次日开盘价成交 + 同源止盈止损 + 资金恒等式对账）
            reconcile_checks: dict[str, bool] = {}
            for sleeve, max_pos, cost_buy, cost_sell in (
                ("sector_etf", 4, 0.0008, 0.0008),
                ("stock_leader", 5, 0.0008, 0.0018),
            ):
                acc = conn.execute("SELECT * FROM paper_accounts WHERE sleeve=?", (sleeve,)).fetchone()
                cash = float(acc["cash"])
                peak = float(acc["peak_equity"])

                # 2a) 检查现有持仓是否触发出场（严格用上一个信号日收盘判定、最新交易日开盘卖出）
                open_pos = conn.execute("SELECT * FROM paper_positions WHERE sleeve=?", (sleeve,)).fetchall()
                for pos in open_pos:
                    sym = str(pos["symbol"])
                    bars = _get_bars(sym)
                    if bars is None or len(bars) < 60:
                        continue
                    if str(bars.index[-1].date()) <= str(pos["entry_date"]):
                        continue
                    m = compute_live_chip_metrics(bars)
                    prev_bar = m.iloc[-2]  # 昨日收盘判断今日开盘是否走人
                    today_op = float(bars["open"].iloc[-1])
                    today_cl = float(bars["close"].iloc[-1])
                    prev_cl = float(prev_bar["close"])
                    max_cl = max(float(pos["max_close"]), prev_cl, today_cl)

                    should_exit = False
                    reason = ""
                    ma20, ema20, ma60, atr20, poc = (
                        float(prev_bar["ma20"]), float(prev_bar["ema20"]),
                        float(prev_bar["ma60"]), float(prev_bar["atr20"]),
                        float(prev_bar["poc_price"]),
                    )
                    if sleeve == "stock_leader":
                        entry_poc = float(pos["entry_poc"])
                        entry_sig = float(pos["entry_signal_close"])
                        if np.isfinite(poc) and entry_poc > 0 and poc > entry_poc * 1.15 and prev_cl < poc and prev_cl < ema20:
                            should_exit, reason = True, "高位筹码派发破峰锁利"
                        elif (max_cl / max(entry_sig, 1e-6) - 1.0) >= 0.15 and (not np.isfinite(poc) or poc <= entry_poc * 1.15):
                            if np.isfinite(ma60) and prev_cl < max(ma60, entry_sig * 1.02):
                                should_exit, reason = True, "第二步宽保护线止盈"
                        elif np.isfinite(ma20) and np.isfinite(ema20) and np.isfinite(atr20):
                            if prev_cl < min(ma20, ema20) - 0.55 * atr20:
                                should_exit, reason = True, "第一步20日成本线止损"
                    else:
                        if np.isfinite(ma20) and np.isfinite(ema20) and np.isfinite(atr20):
                            if prev_cl < min(ma20, ema20) - 0.55 * atr20:
                                should_exit, reason = True, "跌破20日成本缓冲离场"

                    if should_exit and np.isfinite(today_op) and today_op > 0:
                        gross = float(pos["shares"]) * today_op
                        net = gross * (1.0 - cost_sell)
                        cash += net
                        exit_px = today_op * (1.0 - cost_sell)
                        net_ret = exit_px / float(pos["entry_price"]) - 1.0
                        pnl = net - float(pos["notional"])
                        conn.execute(
                            """
                            INSERT INTO paper_trades
                            (sleeve, symbol, name, entry_date, exit_date, entry_price, exit_price, shares, net_return, pnl_yuan, exit_reason)
                            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                            """,
                            (
                                sleeve, sym, pos["name"], pos["entry_date"], str(bars.index[-1].date()),
                                float(pos["entry_price"]), round(exit_px, 4), float(pos["shares"]),
                                round(net_ret, 5), round(pnl, 2), reason,
                            ),
                        )
                        conn.execute("DELETE FROM paper_positions WHERE sleeve=? AND symbol=?", (sleeve, sym))
                    else:
                        conn.execute(
                            "UPDATE paper_positions SET max_close=? WHERE sleeve=? AND symbol=?",
                            (round(max_cl, 4), sleeve, sym),
                        )

                # 2b) 若有空位，读取已产生次日开盘价的最新一批推荐自动建仓
                cur_pos = conn.execute("SELECT symbol FROM paper_positions WHERE sleeve=?", (sleeve,)).fetchall()
                held_syms = {str(x["symbol"]) for x in cur_pos}
                slots = max(0, max_pos - len(held_syms))
                if slots > 0 and cash > 20_000.0:
                    cands = conn.execute(
                        """
                        SELECT * FROM recommendations
                        WHERE sleeve=? AND entry_date IS NOT NULL AND entry_open > 0
                        ORDER BY signal_date DESC, rank_idx ASC
                        LIMIT 12
                        """,
                        (sleeve,),
                    ).fetchall()
                    if cands:
                        latest_cand_sig = cands[0]["signal_date"]
                        for c in cands:
                            if slots <= 0 or c["signal_date"] != latest_cand_sig:
                                break
                            sym = str(c["symbol"])
                            if sym in held_syms:
                                continue
                            entry_op = float(c["entry_open"])
                            alloc = min(cash, float(acc["equity"]) / max_pos)
                            if alloc < 10_000.0:
                                break
                            invest = alloc / (1.0 + cost_buy)
                            shares = invest / entry_op
                            cash -= alloc
                            bars = _get_bars(sym)
                            poc_val = float(c["signal_close"])
                            if bars is not None and len(bars) >= 60:
                                m_poc = compute_live_chip_metrics(bars.loc[: pd.Timestamp(c["signal_date"])])["poc_price"].dropna()
                                if len(m_poc) > 0:
                                    poc_val = float(m_poc.iloc[-1])
                            conn.execute(
                                """
                                INSERT OR IGNORE INTO paper_positions
                                (sleeve, symbol, name, entry_date, entry_price, entry_signal_close, entry_poc, max_close, shares, notional)
                                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """,
                                (
                                    sleeve, sym, c["name"], c["entry_date"], round(entry_op * (1.0 + cost_buy), 4),
                                    float(c["signal_close"]), round(poc_val, 4), float(c["signal_close"]),
                                    shares, round(alloc, 2),
                                ),
                            )
                            held_syms.add(sym)
                            slots -= 1

                # 2c) 收盘估值与独立账户恒等式核对（cash + market_value == equity）
                mv = 0.0
                for pos in conn.execute("SELECT * FROM paper_positions WHERE sleeve=?", (sleeve,)).fetchall():
                    bars = _get_bars(str(pos["symbol"]))
                    px = float(bars["close"].iloc[-1]) if (bars is not None and len(bars) > 0) else float(pos["entry_price"])
                    mv += float(pos["shares"]) * px
                eq = cash + mv
                peak = max(peak, eq)
                reconciled_ok = abs((cash + mv) - eq) < 1e-4 and cash >= -1e-4 and mv >= -1e-4
                reconcile_checks[sleeve] = reconciled_ok

                now_iso = datetime.now(timezone.utc).isoformat()
                conn.execute(
                    "UPDATE paper_accounts SET cash=?, equity=?, peak_equity=?, updated_at=? WHERE sleeve=?",
                    (round(cash, 2), round(eq, 2), round(peak, 2), now_iso, sleeve),
                )
                conn.execute(
                    """
                    INSERT OR REPLACE INTO paper_nav_history
                    (sleeve, as_of, cash, market_value, equity, bench_close, reconciled)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (sleeve, latest_str, round(cash, 2), round(mv, 2), round(eq, 2), round(float(bench_close.iloc[-1]), 4), int(reconciled_ok)),
                )

        return {
            "reconciled": all(reconcile_checks.values()) if reconcile_checks else True,
            "as_of": latest_str,
            "recommendations_updated": updated_recs,
            "sleeve_checks": reconcile_checks,
        }

    def drift_report(
        self,
        *,
        expected_win_rate: float = 0.42,
        expected_20d_excess_low: float = -0.02,
    ) -> dict[str, object]:
        """生成前向观察复盘与 Live-vs-Backtest 漂移监控报告。"""
        with self._connect() as conn:
            n_snaps = int(conn.execute("SELECT COUNT(*) FROM snapshots").fetchone()[0])
            recs = conn.execute("SELECT * FROM recommendations").fetchall()
            accounts = [dict(r) for r in conn.execute("SELECT * FROM paper_accounts").fetchall()]
            positions = [dict(r) for r in conn.execute("SELECT * FROM paper_positions").fetchall()]
            trades = [dict(r) for r in conn.execute("SELECT * FROM paper_trades").fetchall()]

        sleeve_stats: dict[str, dict[str, object]] = {}
        for sleeve in ("sector_etf", "stock_leader", "stock_small_giant"):
            s_recs = [r for r in recs if r["sleeve"] == sleeve]
            r5 = [float(r["ret_5d"]) for r in s_recs if r["ret_5d"] is not None]
            e5 = [float(r["excess_5d"]) for r in s_recs if r["excess_5d"] is not None]
            r20 = [float(r["ret_20d"]) for r in s_recs if r["ret_20d"] is not None]
            e20 = [float(r["excess_20d"]) for r in s_recs if r["excess_20d"] is not None]
            r60 = [float(r["ret_60d"]) for r in s_recs if r["ret_60d"] is not None]
            e60 = [float(r["excess_60d"]) for r in s_recs if r["excess_60d"] is not None]

            if len(e20) < 8:
                drift_light = "🟡 前向样本积累中（20日已到期样本 < 8 笔，暂不判漂移）"
            else:
                mean_e20 = float(np.mean(e20))
                wr_20 = float(np.mean([x > 0 for x in r20]))
                if mean_e20 < expected_20d_excess_low and wr_20 < expected_win_rate - 0.10:
                    drift_light = "🔴 负漂移预警（前向20日超额与胜率均跌破回测预期下界，请复查体制或因子失效）"
                elif mean_e20 >= 0.0:
                    drift_light = "🟢 前向验证正常（20日相对沪深300平均超额为正）"
                else:
                    drift_light = "🟡 轻度偏弱（仍在正常波动带内，继续观察）"

            sleeve_stats[sleeve] = {
                "total_recommendations": len(s_recs),
                "matured_5d": len(r5),
                "mean_ret_5d": round(float(np.mean(r5)), 4) if r5 else None,
                "mean_excess_5d": round(float(np.mean(e5)), 4) if e5 else None,
                "matured_20d": len(r20),
                "mean_ret_20d": round(float(np.mean(r20)), 4) if r20 else None,
                "mean_excess_20d": round(float(np.mean(e20)), 4) if e20 else None,
                "win_rate_20d": round(float(np.mean([x > 0 for x in r20])), 4) if r20 else None,
                "matured_60d": len(r60),
                "mean_ret_60d": round(float(np.mean(r60)), 4) if r60 else None,
                "mean_excess_60d": round(float(np.mean(e60)), 4) if e60 else None,
                "drift_status": drift_light,
            }

        return {
            "snapshots_frozen": n_snaps,
            "total_recommendations": len(recs),
            "sleeve_forward_stats": sleeve_stats,
            "paper_accounts": accounts,
            "open_positions_count": len(positions),
            "closed_trades_count": len(trades),
            "db_path": str(self.db_path),
        }
