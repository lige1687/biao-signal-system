"""Frozen local research ledger and read-only presentation."""

from __future__ import annotations

import gzip
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from .ledger import advance, initialize, sessions, summary

ROOT = Path(__file__).resolve().parents[3]
RAW = ROOT / "docs/experiments/raw/factor-strategy-portfolios-2026-10-20"
ACTIVE = ROOT / "data/strategy-portfolios"
CONFIG = ROOT / "configs/strategy-portfolios.v1.json"


def utcnow():
    return datetime.now(ZoneInfo("UTC")).isoformat()


def digest(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def load_json(path):
    path = Path(path)
    data = gzip.decompress(path.read_bytes()) if path.suffix == ".gz" else path.read_bytes()
    return json.loads(data)


def binding():
    paths = [
        CONFIG,
        *(
            Path(__file__).parent / f
            for f in [
                "engine.py",
                "sources.py",
                "ledger.py",
                "collector.py",
                "service.py",
                "runner.py",
                "server.py",
            ]
        ),
    ]
    return {str(p.relative_to(ROOT)): digest(p) for p in paths}


def connect(active=ACTIVE):
    active = Path(active)
    active.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(active / "ledger.sqlite", timeout=20)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(
        "CREATE TABLE IF NOT EXISTS frozen "
        "(id INTEGER PRIMARY KEY CHECK(id=1), payload TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS events (id INTEGER PRIMARY KEY, at TEXT NOT NULL, "
        "source_hash TEXT UNIQUE NOT NULL, source_path TEXT NOT NULL, payload TEXT NOT NULL)"
    )
    conn.execute(
        "CREATE TABLE IF NOT EXISTS runs "
        "(date TEXT PRIMARY KEY, at TEXT NOT NULL, status TEXT NOT NULL, detail TEXT)"
    )
    conn.commit()
    return conn


def freeze(active=ACTIVE, at=None):
    with connect(active) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute("SELECT payload FROM frozen WHERE id=1").fetchone()
        if row:
            return json.loads(row[0])
        state = initialize(load_json(CONFIG), at or utcnow())
        frozen = {"bindings": binding(), "state": state}
        conn.execute("INSERT INTO frozen VALUES (1,?)", (json.dumps(frozen, ensure_ascii=False),))
        return frozen


def read_state(active=ACTIVE):
    with connect(active) as conn:
        frozen = conn.execute("SELECT payload FROM frozen WHERE id=1").fetchone()
        if not frozen:
            return None
        result = json.loads(frozen[0])
        latest = conn.execute("SELECT payload FROM events ORDER BY id DESC LIMIT 1").fetchone()
        return json.loads(latest[0]) if latest else result["state"]


def ingest(locator_path, active=ACTIVE, at=None):
    locator = load_json(locator_path)
    source = Path(locator["snapshot"])
    if digest(source) != locator["snapshot_sha256"]:
        raise ValueError("采集原件指纹不一致")
    snapshot = load_json(source)
    now = at or utcnow()
    if datetime.fromisoformat(snapshot["received_at"]) > datetime.fromisoformat(now):
        raise ValueError("未来接收时间")
    freeze(active, now)
    with connect(active) as conn:
        conn.execute("BEGIN IMMEDIATE")
        frozen = json.loads(conn.execute("SELECT payload FROM frozen WHERE id=1").fetchone()[0])
        if frozen["bindings"] != binding():
            raise ValueError("冻结代码或规则变化；需新版本，不覆盖旧账")
        duplicate = conn.execute(
            "SELECT 1 FROM events WHERE source_hash=?", (locator["snapshot_sha256"],)
        ).fetchone()
        if duplicate:
            return json.loads(
                conn.execute("SELECT payload FROM events ORDER BY id DESC LIMIT 1").fetchone()[0]
            )
        previous = conn.execute("SELECT payload FROM events ORDER BY id DESC LIMIT 1").fetchone()
        state = json.loads(previous[0]) if previous else frozen["state"]
        for market in ("CN", "US"):
            state = advance(state, market, snapshot["markets"].get(market, {}), now)
        conn.execute(
            "INSERT INTO events(at,source_hash,source_path,payload) VALUES (?,?,?,?)",
            (
                now,
                locator["snapshot_sha256"],
                str(source),
                json.dumps(state, ensure_ascii=False, allow_nan=False),
            ),
        )
    return state


def next_collection(at=None):
    now = datetime.fromisoformat(at or utcnow()).astimezone(ZoneInfo("America/New_York"))
    if now.year != 2026:
        return None
    for day in sorted(set(sessions("US", now.year)) | set(sessions("CN", now.year))):
        candidate = datetime.fromisoformat(day + "T17:00:00").replace(tzinfo=now.tzinfo)
        if candidate > now:
            return candidate.isoformat()
    return None


NAMES = {
    "mv": "中期上涨＋低波动",
    "rv": "近期偏冷＋低波动",
    "m": "只用中期上涨",
    "v": "只用低波动",
    "r": "只用近期偏冷",
    "equal": "合格股票平均分配",
    "mv_no_exit": "上涨组合：取消每日均线退出",
    "rv_no_exit": "偏冷组合：取消每日均线退出",
    "mv_high_fee": "上涨组合：较高费用",
    "rv_high_fee": "偏冷组合：较高费用",
}

RULES = [
    "每月最后一个交易日收盘选前20只，每只目标5%；首次启动按最新完整收盘建初始名单。",
    "新买要求价格在120日均线上方；每天跌破则申请下个交易日退出，最早下月重新入选。",
    "单只超过10%申请减至5%；卖不成保留持仓和未知价格占比，不把它变成现金。",
    "收盘时冻结数量，下一交易日开盘报价模拟；费用扣入现金，不借钱；未成交买单当天失效。",
    "分数是两项因子在同一市场的相对排名各占一半。调整价格研究单位可含小数，不能当真实股票股数。",
]


def _empty_history():
    return {"summary": {}, "series": [], "years": []}


def combined_forward(accounts):
    a, b = accounts.get("mv", {}), accounts.get("rv", {})
    left = {r["date"]: r for r in a.get("series", [])}
    right = {r["date"]: r for r in b.get("series", [])}
    series, previous, peak = [], 100000, 100000
    for day in sorted(left.keys() & right.keys()):
        x, y = left[day], right[day]
        equity = (x["equity"] + y["equity"]) / 2
        peak = max(peak, equity)
        series.append(
            {
                "date": day,
                "equity": equity,
                "nav": equity / 100000,
                "drawdown": equity / peak - 1,
                "return": equity / previous - 1,
                "cash": (x["cash"] + y["cash"]) / 2,
                "exposure": (x["exposure"] * x["equity"] + y["exposure"] * y["equity"])
                / (2 * equity),
                "unknown_weight": (
                    x["unknown_weight"] * x["equity"] + y["unknown_weight"] * y["equity"]
                )
                / (2 * equity),
            }
        )
        previous = equity
    return {
        "series": series,
        "summary": summary(series, 100000, (a.get("cost", 0) + b.get("cost", 0)) / 2),
    }


def dashboard(active=ACTIVE):
    state = read_state(active)
    data = {
        "version": "stock-factor-portfolios/1.0",
        "generated_at": utcnow(),
        "started_at": state["started_at"] if state else None,
        "markets": [],
        "run": {
            "status": "等待首次采集",
            "last_run_at": None,
            "next_run_at": next_collection(),
            "error": None,
        },
        "pending": [
            {
                "name": "经营盈利＋中期上涨",
                "reason": (
                    "美股公开组合收益不能代替逐股财报；"
                    "两市场逐股披露时点、字段和行业可比性仍需补齐。"
                ),
            }
        ],
        "sources": [
            {
                "title": "本次规则、历史结果和限制",
                "url": (
                    "/library?report=docs%2Fexperiments%2Ffactor-strategy-portfolios-2026-10-20.md"
                ),
            },
            {
                "title": "上交所2026休市安排",
                "url": "https://www.sse.com.cn/disclosure/announcement/general/c/c_20251222_10802507.shtml",
            },
            {"title": "纽约交易所交易日历", "url": "https://www.nyse.com/trade/hours-calendars"},
        ],
        "limitations": [
            "本页为独立研究方案，尚未证明有效，不替代原LEI技术体系。",
            "两个模型都包含低波动，不能仅因名字不同就视为不同收益来源。",
            "报价模拟未证明开盘一定能成交，未包含真实交易单位、个税与涨跌停排队；费用是统一假设。",
            "前向只保留实际启动后记录，不用过去行情补成绩；短期夏普及年化收益留空。",
            "组合以同样10万本金分别交给两策略各一半，不在两策略间每天调钱；A股人民币、美股美元分别比较。",
        ],
    }
    history = {}
    try:
        locator = load_json(RAW / "history-result.json")
        path = locator.get("dashboard") or locator.get("dashboard_path")
        if not path:
            raise ValueError("历史结果缺展示文件路径")
        if digest(path) != locator["dashboard_sha256"]:
            raise ValueError("历史展示资料指纹不一致")
        history = load_json(path)
    except (OSError, ValueError, KeyError) as exc:
        data["run"]["error"] = f"历史资料尚未就绪：{exc}"
    if state:
        data["run"]["status"] = "已冻结，按日等待新收盘"
        with connect(active) as conn:
            latest = conn.execute("SELECT at FROM events ORDER BY id DESC LIMIT 1").fetchone()
            data["run"]["last_run_at"] = latest[0] if latest else None
            recent_run = conn.execute(
                "SELECT date,status,detail FROM runs ORDER BY date DESC LIMIT 1"
            ).fetchone()
            if recent_run and recent_run[1] == "failed":
                try:
                    data["run"]["error"] = json.loads(recent_run[2])["message"]
                except (ValueError, KeyError, TypeError):
                    data["run"]["error"] = recent_run[2]
        frozen = freeze(active)
        if frozen["bindings"] != binding():
            data["run"]["error"] = "代码或规则已变化，暂停新增记账，历史保留。"
        try:
            heartbeat = load_json(Path(active) / "worker-status.json")
            age = (
                datetime.fromisoformat(utcnow()) - datetime.fromisoformat(heartbeat["heartbeat_at"])
            ).total_seconds()
            data["run"]["status"] = "运行中，按日等待新收盘" if age < 180 else "采集进程心跳过期"
            if heartbeat.get("error"):
                data["run"]["error"] = heartbeat["error"]
        except (OSError, ValueError, KeyError):
            data["run"]["status"] = "已冻结，采集进程尚未启动"
    for market in ("CN", "US"):
        ms = state["markets"].get(market, {}) if state else {}
        h = (
            history.get("markets", {}).get(market, {})
            if isinstance(history.get("markets", {}), dict)
            else next((m for m in history["markets"] if m["id"] == market), {})
        )
        item = {
            "id": market,
            "name": "A股" if market == "CN" else "美股",
            "currency": "CNY" if market == "CN" else "USD",
            "universe_count": len(ms.get("universe", [])) or (300 if market == "CN" else 504),
            "qualified_count": ms.get("qualified_count", 0),
            "source_date": ms.get("source_date"),
            "accounts": [],
            "limitations": [
                "A股历史范围是2014年末固定的300只，不代表整个A股市场。"
                if market == "CN"
                else (
                    "美股历史用2026年IVV持仓504只回看，有当前成分偏差；"
                    "不能当整个美股市场的无偏证据。"
                ),
                "原件缺失、退市和资料修订单独保留；尚未合格的股票不会被悄悄替换。",
            ],
            "comparison": h.get(
                "comparison",
                {
                    "return_correlation": None,
                    "holding_overlap": None,
                    "combined_history": _empty_history(),
                    "note": "等待固定历史比较。",
                },
            ),
        }
        historical_accounts = h.get("schemes", h.get("accounts", {}))
        if isinstance(historical_accounts, list):
            historical_accounts = {a["scheme"]: a for a in historical_accounts}
        raw_comparison = h.get("comparison", {})
        combo = historical_accounts.get("mv_rv_50_50", _empty_history())
        item["comparison"] = {
            "return_correlation": raw_comparison.get("daily_return_correlation"),
            "holding_overlap": raw_comparison.get("last_month_target_jaccard"),
            "combined_history": combo,
            "combined_forward": combined_forward(ms.get("accounts", {})),
            "note": (
                "日收益相关程度越接近1，越容易一起涨跌；当前两方案仍高度相关。"
                f"历史同时下跌 {raw_comparison.get('both_down_days', '—')} 日。"
                "持股重合采用最后一次月度目标名单交集占并集的比例，仅代表当次名单。"
            ),
        }
        for scheme, name in NAMES.items():
            a = ms.get("accounts", {}).get(scheme, {})
            historic = historical_accounts.get(scheme, {})
            hist = historic.get("history", historic) or _empty_history()
            if "summary" not in hist:
                hist = _empty_history()
            hist["summary"]["sharpe"] = hist["summary"].get(
                "sharpe", hist["summary"].get("sharpe_daily_zero_rate")
            )
            hist["years"] = [
                {"year": int(y), "return": v["return"]}
                for y, v in hist["summary"].get("years", {}).items()
            ]
            item["accounts"].append(
                {
                    "id": market + ":" + scheme,
                    "scheme": scheme,
                    "name": name,
                    "role": "main" if scheme in ("mv", "rv") else "control",
                    "status": ms.get("status", "等待资料"),
                    "started_at": data["started_at"],
                    "rules": RULES,
                    "history": hist,
                    "forward": {
                        "summary": summary(a.get("series", []), 100000, a.get("cost", 0)),
                        "series": a.get("series", []),
                        "holdings": list(a.get("holdings", {}).values()),
                        "targets": a.get("targets", []),
                        "orders": a.get("orders", []),
                        "decisions": a.get("decisions", []),
                        "reason": ms.get("reason", "等待当前股票资料，尚无前向成绩。"),
                    },
                }
            )
        data["markets"].append(item)
    return data
