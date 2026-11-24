"""真全A市场宽度数据层（替换原 fixture 假样本）。

提供两个互补维度：

1. 涨跌家数（advance / decline）—— 最权威、最不易错的全市场宽度。
   数据源 = 腾讯实时快照 (qt.gtimg.cn) + 沪深交易所代码列表 (官网 akshare)。
   覆盖真全A：沪 + 深（北交所代码列表在部分网络策略下不可达，自动跳过）。

2. MA 上方占比（breadth_20 / 50 / 200）—— 券商金工"全A宽度"口径。
   数据源 = 腾讯日K线 (proxy.finance.qq.com/ifzqgtimg, 白名单放行)。
   该维度依赖个股历史K线，逐只拉取较慢，故由「本机收盘后定时预计算」落盘结果，
   global-strip 直接读结果缓存（磁盘文件，重启不丢），运行时不再实时拉K线。
   K线本身也有磁盘缓存(parquet)，每日仅增量补最新几天，且断网可复用。

所有数据均来自公开权威行情源，不再使用本地 fixture 假样本。
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

import pandas as pd
import requests

from lei_signal.data.cache import DEFAULT_CACHE_DIR
from lei_signal.market_context.breadth_qualification import (
    QFQ_CACHE_SCHEMA,
    QFQ_SOURCE_REF,
    merge_kline_series,
    qualify_breadth,
)

logger = logging.getLogger(__name__)

# ── 代理自适应 ────────────────────────────────────────────────────────────
# WorkBuddy 沙箱里 HTTP_PROXY 指向 127.0.0.1:57441，但 NO_PROXY 含 127.0.0.1，
# 会让 requests 把代理地址当目标直连而失败。检测到"代理指向本机"时清除豁免。
def _fix_proxy_env() -> None:
    hp = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    if not hp:
        return
    if "127.0.0.1" in hp or "localhost" in hp:
        for k in ("NO_PROXY", "no_proxy"):
            os.environ.pop(k, None)


_fix_proxy_env()


def _proxies() -> dict | None:
    hp = os.environ.get("HTTP_PROXY") or os.environ.get("http_proxy")
    if not hp:
        return None
    return {"http": hp, "https": hp}


@dataclass
class AShareBreadth:
    """真全A市场宽度快照。"""

    as_of: str
    # 涨跌家数维度（核心、最权威）
    up: int = 0
    down: int = 0
    flat: int = 0
    total: int = 0
    up_pct: float | None = None            # 上涨占比 %
    adv_dec_ratio: float | None = None     # 涨跌比 AD = up / down
    limit_up: int = 0
    limit_down: int = 0
    # MA 上方占比维度（券商金工口径；受限网络下为 None）
    ma20_pct: float | None = None
    ma50_pct: float | None = None
    ma200_pct: float | None = None
    data_status: str = "ok"                # ok | partial | unavailable
    source_detail: str = ""


# ── 代码列表 ──────────────────────────────────────────────────────────────

def _codes_cache_path() -> Path:
    """与 api/cache_root 同规则：LEI_CACHE_ROOT 覆盖，默认 data.cache 目录。"""
    root = Path(os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR)))
    return root / "a_share_codes.json"


def _load_cached_codes() -> dict | None:
    """当日代码列表缓存命中则直接用；交易所列表一天不变，没必要每次请求都拉官网。"""
    p = _codes_cache_path()
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        if data.get("date") == datetime.now().strftime("%Y-%m-%d"):
            codes = data.get("codes")
            sources = data.get("sources")
            if isinstance(codes, list) and codes:
                if not isinstance(sources, dict):
                    sources = {"sh": False, "sz": False, "bj": False}
                return {"codes": codes, "sources": sources}
    except Exception:  # noqa: BLE001 - 缓存读不了就当未命中
        pass
    return None


def _save_codes(codes: list[str], sources: dict[str, bool]) -> None:
    p = _codes_cache_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        tmp = p.with_name(p.name + ".tmp")
        tmp.write_text(
            json.dumps({
                "date": datetime.now().strftime("%Y-%m-%d"),
                "codes": codes,
                "sources": sources,
            }),
            encoding="utf-8",
        )
        tmp.replace(p)
    except Exception as e:  # noqa: BLE001
        logger.warning("代码列表缓存写入失败: %s", e)


def get_a_share_codes_with_status(
    include_bj: bool = True, *, allow_cached_partial: bool = False
) -> dict:
    """Return codes and source success separately; never cache a partial list as complete.

    返回带前缀的代码列表：sh/sz/bj + 6 位数字。
    任一交易所列表获取失败仅告警并跳过，不影响其余市场。
    当日成功拉取后落盘缓存，同一天内不再访问交易所官网。
    """
    cached = _load_cached_codes()
    required = ("sh", "sz", "bj") if include_bj else ("sh", "sz")
    if cached is not None and (
        allow_cached_partial
        or all(cached["sources"].get(market) is True for market in required)
    ):
        return cached

    import akshare as ak

    codes: list[str] = []
    sources = {"sh": False, "sz": False, "bj": False}
    try:
        sh = ak.stock_info_sh_name_code()["证券代码"].astype(str).tolist()
        sh = [str(c) for c in sh]
        # P0: 补科创板。akshare 的 stock_info_sh_name_code() 默认不含科创板；
        # 其 symbol="科创板" 参数可单独拉取该段（2026-08 实测返回 613 只）。
        # 两段 concat 后用 dict.fromkeys 保序去重（避免主板与科创板重复）。
        try:
            sh_kc = ak.stock_info_sh_name_code(symbol="科创板")["证券代码"].astype(str).tolist()
            sh_kc = [str(c) for c in sh_kc]
            sh = list(dict.fromkeys(sh + sh_kc))
            sources["sh"] = bool(sh) and bool(sh_kc)
        except Exception as e:  # noqa: BLE001
            logger.warning("上交所科创板代码列表获取失败(回落仅主板): %s", e)
        codes += [f"sh{c}" for c in sh]
    except Exception as e:  # noqa: BLE001
        logger.warning("上交所代码列表获取失败: %s", e)
    try:
        sz = ak.stock_info_sz_name_code()["A股代码"].astype(str).tolist()
        codes += [f"sz{c}" for c in sz]
        sources["sz"] = bool(sz)
    except Exception as e:  # noqa: BLE001
        logger.warning("深交所代码列表获取失败: %s", e)
    if include_bj:
        try:
            bj = ak.stock_info_bj_name_code()["证券代码"].astype(str).tolist()
            codes += [f"bj{c}" for c in bj]
            sources["bj"] = bool(bj)
        except Exception as e:  # noqa: BLE001
            logger.warning("北交所代码列表获取失败(可能受网络策略拦截): %s", e)
    codes = list(dict.fromkeys(codes))
    if codes and all(sources[market] for market in required):
        _save_codes(codes, sources)
    return {"codes": codes, "sources": sources}


def get_a_share_codes(include_bj: bool = True) -> list[str]:
    """Compatibility entrypoint; callers needing provenance use the status variant."""
    return get_a_share_codes_with_status(
        include_bj=include_bj, allow_cached_partial=True
    )["codes"]


# ── 涨跌家数（腾讯快照） ──────────────────────────────────────────────────

def _parse_chg_pct(text: str) -> list[float | None]:
    """解析腾讯快照文本，返回每只的涨跌幅%(float)或 None。

    腾讯快照每行形如 v_sz000001="51~平安银行~000001~11.18~...~涨跌幅%~..."，
    涨跌幅位于第 33 个 ~ 分隔字段（索引 32）。
    """
    out: list[float | None] = []
    for line in text.strip().split(";"):
        line = line.strip()
        if not line.startswith("v_"):
            continue
        payload = line.split("=", 1)[1].strip().strip('"')
        parts = payload.split("~")
        if len(parts) < 33:
            out.append(None)
            continue
        try:
            out.append(float(parts[32]))
        except ValueError:
            out.append(None)
    return out


def fetch_advance_decline(
    codes: list[str], batch: int = 500, pause: float = 0.1,
) -> dict:
    """腾讯快照批量拉取 → 涨跌家数统计。

    Returns dict: up / down / flat / bad / total / limit_up / limit_down。
    limit_up/down 以涨跌幅 ≥9.9% / ≤-9.9% 近似（主板±10%、双创±20% 均覆盖，
    为市场温度参考，非精确的「封板」判定）。
    """
    proxies = _proxies()
    up = down = flat = bad = limit_up = limit_down = 0
    for i in range(0, len(codes), batch):
        chunk = codes[i:i + batch]
        try:
            r = requests.get(
                "https://qt.gtimg.cn/q=" + ",".join(chunk),
                proxies=proxies, timeout=30,
            )
            text = r.content.decode("gbk", "ignore")
            for chg in _parse_chg_pct(text):
                if chg is None:
                    bad += 1
                elif chg >= 9.9:
                    up += 1
                    limit_up += 1
                elif chg <= -9.9:
                    down += 1
                    limit_down += 1
                elif chg > 0:
                    up += 1
                elif chg < 0:
                    down += 1
                else:
                    flat += 1
        except Exception as e:  # noqa: BLE001
            logger.warning("批量快照失败 %s..: %s", chunk[:2], e)
            bad += len(chunk)
        if i + batch < len(codes):
            time.sleep(pause)
    return {"up": up, "down": down, "flat": flat, "bad": bad,
            "total": up + down + flat, "limit_up": limit_up,
            "limit_down": limit_down}


# ── MA 上方占比（腾讯日K线 proxy.finance.qq.com 白名单放行；彪哥本机环境） ──

def _fetch_kline(sym: str) -> list[tuple[str, float]] | None:
    """腾讯日K线 → [(date, close), ...]（最近 ~800 交易日，约3.2年）。"""
    import requests

    _H = {"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"}
    url = f"https://proxy.finance.qq.com/ifzqgtimg/appstock/app/fqkline/get?param={sym},day,,,800,qfq"
    for _ in range(3):
        try:
            r = requests.get(url, timeout=12, headers=_H)
            node = ((r.json() or {}).get("data") or {}).get(sym) or {}
            # This breadth series is defined on forward-adjusted closes only.
            # A valid response without qfqday is a source gap, not a retryable network error.
            arr = node.get("qfqday")
            if not isinstance(arr, list):
                return None
            out: list[tuple[str, float]] = []
            for row in arr:
                try:
                    # 腾讯格式: [日期,开,收,高,低,...] → (date, close)
                    out.append((str(row[0]), float(row[2])))
                except (ValueError, TypeError, IndexError):
                    continue
            if len(out) >= 5:
                return out
            return None
        except Exception:  # noqa: BLE001
            pass
        time.sleep(0.3)
    return None


# 保留较长的原始价格历史；短接口响应不能将其裁回约 800 根。
_KLINE_KEEP = 2600


def _kline_cache_path() -> Path:
    root = Path(os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR)))
    return root / "a_share_klines.parquet"


def _qfq_kline_cache_path() -> Path:
    """Separate proved-qfq prices from the historical cache with unknown adjustment."""
    return _kline_cache_path().with_name("a_share_klines_qfq.parquet")


def load_qfq_kline_cache(path: Path) -> tuple[dict[str, list[tuple[str, float]]], bool]:
    """Return (prices, provenance_valid); an unknown old file is never trusted."""
    if not path.exists():
        return {}, True
    try:
        df = pd.read_parquet(path)
        required = {"symbol", "date", "close", "adjustment", "source_ref", "schema_version"}
        if (not required.issubset(df.columns)
                or not df["adjustment"].eq("qfqday").all()
                or not df["source_ref"].eq(QFQ_SOURCE_REF).all()
                or not df["schema_version"].eq(QFQ_CACHE_SCHEMA).all()
                or df.duplicated(["symbol", "date"]).any()):
            return {}, False
        out: dict[str, list[tuple[str, float]]] = {}
        for symbol, group in df.groupby("symbol"):
            rows = sorted(zip(group["date"].astype(str), group["close"].astype(float), strict=True))
            out[symbol] = rows[-_KLINE_KEEP:]
        return out, True
    except Exception:  # noqa: BLE001 - unreadable provenance never qualifies
        return {}, False


def save_qfq_kline_cache(data: dict[str, list[tuple[str, float]]], path: Path) -> bool:
    """Write a distinct, self-describing qfq cache; never replace an unknown old file."""
    if path.exists() and not load_qfq_kline_cache(path)[1]:
        return False
    rows = [
        (symbol, day, close, "qfqday", QFQ_SOURCE_REF, QFQ_CACHE_SCHEMA)
        for symbol, series in data.items()
        for day, close in series[-_KLINE_KEEP:]
    ]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        pd.DataFrame(rows, columns=[
            "symbol", "date", "close", "adjustment", "source_ref", "schema_version"
        ]).to_parquet(temporary, index=False)
        temporary.replace(path)
        return True
    except Exception as exc:  # noqa: BLE001
        logger.warning("前复权K线缓存写入失败: %s", exc)
        return False


def load_kline_cache(path: Path | None = None) -> dict[str, list[tuple[str, float]]]:
    """加载逐只日K收盘价缓存（磁盘 parquet，重启不丢、断网可复用）。"""
    p = path or _kline_cache_path()
    try:
        df = pd.read_parquet(p)
        out: dict[str, list[tuple[str, float]]] = {}
        for sym, g in df.groupby("symbol"):
            rows = sorted(
                zip(
                    g["date"].astype(str),
                    g["close"].astype(float),
                    strict=True,
                ),
                key=lambda x: x[0],
            )
            out[sym] = rows[-_KLINE_KEEP:]
        return out
    except Exception:  # noqa: BLE001 - 无缓存/读不了就当空
        return {}


def save_kline_cache(
    data: dict[str, list[tuple[str, float]]], path: Path | None = None
) -> bool:
    """落盘逐只日K收盘价缓存（增量更新后整表回写）。"""
    rows = []
    for sym, series in data.items():
        for date, close in series[-_KLINE_KEEP:]:
            rows.append((sym, date, close))
    try:
        df = pd.DataFrame(rows, columns=["symbol", "date", "close"])
        p = path or _kline_cache_path()
        p.parent.mkdir(parents=True, exist_ok=True)
        temporary = p.with_name(p.name + ".tmp")
        df.to_parquet(temporary, index=False)
        temporary.replace(p)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("K线缓存写入失败: %s", e)
        return False


def fetch_ma_breadth(
    codes: list[str], lookback_days: int = 520, use_cache: bool = True,
    *, target_day: str | None = None, code_sources: dict[str, bool] | None = None,
    max_fetch: int | None = None, cache_path: Path | None = None,
    persist_cache: bool = True,
) -> dict | None:
    """腾讯日K线 → MA20/50/200 上方占比（站上均线股票占比）。

    逐只取收盘价，计算收盘价站上均线的股票占比。腾讯接口在受限网络(走白名单代理)
    与直连下均可用。因依赖历史K线且逐只拉取慢(全A 5000+ 只)：
      - 通过「磁盘 K线缓存」做增量：仅拉取缓存缺失/过期的个股，正常每日只需补最新几天；
      - 由本机定时任务(收盘后)预计算落盘结果，global-strip 直接读结果缓存，运行时不拉K线。
    返回 dict 含 ma20/50/200_pct、有效样本数 eligible、该快照代表的交易日 trading_day。
    """
    if max_fetch is not None and max_fetch < 0:
        raise ValueError("max_fetch must be non-negative")
    qualified_path = cache_path or _qfq_kline_cache_path()
    cache, provenance_valid = load_qfq_kline_cache(qualified_path) if use_cache else ({}, True)
    target_day = target_day or datetime.now().strftime("%Y-%m-%d")

    need: list[str] = []
    if code_sources and all(code_sources.get(market) is True for market in ("sh", "sz", "bj")):
        for c in codes:
            series = cache.get(c)
            if series and series[-1][0] >= target_day:
                continue
            need.append(c)

    revision_conflicts = 0
    changed = False
    persist_failed = not provenance_valid
    deferred_fetches = max(0, len(need) - max_fetch) if max_fetch is not None else 0
    attempted_fetches = 0
    if need:
        for c in need[:max_fetch]:
            attempted_fetches += 1
            kl = _fetch_kline(c)  # c 已带 sh/sz/bj 前缀，腾讯需带前缀
            if kl:
                merged, conflict = merge_kline_series(cache.get(c, ()), kl)
                if conflict:
                    revision_conflicts += 1
                    logger.warning("K线 %s 存在 %s；保留原缓存，不盲拼复权序列", c, conflict)
                elif merged != cache.get(c):
                    cache[c] = merged[-_KLINE_KEEP:]
                    changed = True
        if use_cache and persist_cache and changed and provenance_valid:
            persist_failed = not save_qfq_kline_cache(cache, qualified_path)

    if not codes:
        return None
    quality = qualify_breadth(
        target_day=target_day,
        codes=codes,
        code_sources=code_sources or {},
        series_by_symbol=cache,
        revision_conflicts=revision_conflicts,
    )
    quality["attempted_fetches"] = attempted_fetches
    quality["deferred_fetches"] = deferred_fetches
    proof_complete = (
        use_cache and provenance_valid and qualified_path.is_file()
        and (not changed or (persist_cache and not persist_failed))
    )
    cache_hash = None
    if proof_complete:
        try:
            cache_hash = hashlib.sha256(qualified_path.read_bytes()).hexdigest()
        except OSError:
            proof_complete = False
    quality.update(
        price_adjustment="qfqday" if proof_complete else "unknown",
        price_provenance="qfq_cache_v1" if proof_complete else "unverified",
        price_source_ref=QFQ_SOURCE_REF if proof_complete else None,
        price_cache_sha256=cache_hash if proof_complete else None,
    )
    if deferred_fetches:
        quality["status"] = "needs_check"
        quality["reasons"].append("fetch_budget_deferred")
    if persist_failed:
        quality["status"] = "needs_check"
        quality["reasons"].append(
            "qfq_cache_provenance_unverified" if not provenance_valid
            else "kline_cache_persist_failed"
        )
    if not proof_complete:
        quality["status"] = "needs_check"
        if "qfq_cache_proof_missing" not in quality["reasons"]:
            quality["reasons"].append("qfq_cache_proof_missing")
    return {
        "ma20_pct": quality["ma20_pct"],
        "ma50_pct": quality["ma50_pct"],
        "ma200_pct": quality["ma200_pct"],
        "eligible": quality["eligible20"],
        "trading_day": target_day,
        "qualification": quality,
    }


# ── 聚合入口 ──────────────────────────────────────────────────────────────

# 结果 TTL 缓存：涨跌家数分钟级变化无意义，5 分钟内同参数直接回缓存。
# include_ma=True 的计算要几分钟，与 False 各自独立锁，互不阻塞。
_BREADTH_TTL_SECONDS = 300
_breadth_cache: dict[bool, tuple[datetime, AShareBreadth]] = {}
_breadth_locks: dict[bool, threading.Lock] = {
    False: threading.Lock(), True: threading.Lock(),
}


def get_a_share_breadth(include_ma: bool = False) -> AShareBreadth:
    """聚合真全A市场宽度（带 5 分钟 TTL 缓存 + 单飞防击穿）。

    include_ma=False（默认）：仅算涨跌家数，首次约 2s（代码列表当日已缓存时），
    之后 5 分钟内秒回。include_ma=True：额外算 MA 上方占比（需正常网络环境；
    失败自动降级）。
    """
    cached = _breadth_cache.get(include_ma)
    if cached and (datetime.now() - cached[0]).total_seconds() < _BREADTH_TTL_SECONDS:
        return cached[1]

    with _breadth_locks[include_ma]:
        # double-check：排队等锁期间可能已被并发请求算好
        cached = _breadth_cache.get(include_ma)
        if cached and (datetime.now() - cached[0]).total_seconds() < _BREADTH_TTL_SECONDS:
            return cached[1]
        b = _compute_a_share_breadth(include_ma)
        _breadth_cache[include_ma] = (datetime.now(), b)
        return b


def _compute_a_share_breadth(include_ma: bool = False) -> AShareBreadth:
    code_result = get_a_share_codes_with_status(include_bj=True, allow_cached_partial=True)
    codes = code_result["codes"]
    ad = fetch_advance_decline(codes)
    total = ad["total"]
    up_pct = ad["up"] / total * 100 if total else None
    adv_dec = ad["up"] / ad["down"] if ad["down"] else None

    ma20 = ma50 = ma200 = None
    status = "ok"
    detail = f"涨跌家数:腾讯快照+沪深交易所代码列表(共{total}只, 解析失败{ad['bad']})"

    if include_ma:
        try:
            ma = fetch_ma_breadth(codes, code_sources=code_result["sources"])
            if ma and ma["qualification"]["status"] == "verified":
                ma20, ma50, ma200 = ma["ma20_pct"], ma["ma50_pct"], ma["ma200_pct"]
                detail += "; MA占比:腾讯日K线"
            else:
                status = "partial"
                detail += "; MA占比:成员来源或同日K线未核齐"
        except Exception as e:  # noqa: BLE001
            status = "partial"
            detail += f"; MA占比降级:{e}"

    return AShareBreadth(
        as_of=datetime.now().strftime("%Y-%m-%d %H:%M"),
        up=ad["up"], down=ad["down"], flat=ad["flat"], total=total,
        up_pct=up_pct, adv_dec_ratio=adv_dec,
        limit_up=ad["limit_up"], limit_down=ad["limit_down"],
        ma20_pct=ma20, ma50_pct=ma50, ma200_pct=ma200,
        data_status=status, source_detail=detail,
    )


# ── MA 上方占比缓存层（本机收盘后预计算落盘，global-strip / 趋势图读取） ─────
# 收盘后定时预计算：拉腾讯日K线(走白名单代理/直连)算 B20/B50/B200，连同收盘涨跌家数
# 一起落盘到 LEI_CACHE_ROOT 下的 JSON（磁盘文件，重启不丢）。global-strip 直接读
# 这份「冻结快照」展示(次日整天 + 周末均不重算)；缓存缺失时优雅降级(退回实时涨跌家数)。

def _ma_cache_path() -> Path:
    root = Path(os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR)))
    return root / "a_share_ma_breadth.json"


def _ma_history_path() -> Path:
    root = Path(os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR)))
    return root / "a_share_ma_breadth_history.json"


def _ma_qualification_path() -> Path:
    return _ma_cache_path().with_name("a_share_ma_breadth_qualification.json")


def save_ma_breadth_qualification(quality: dict) -> bool:
    """Persist the latest qualification attempt separately from historical readings."""
    path = _ma_qualification_path()
    previous = get_cached_ma_breadth_qualification() or {}
    invalidated = list(dict.fromkeys(
        date for date in (
            *(previous.get("invalidates_legacy_dates") or []),
            *(quality.get("invalidates_legacy_dates") or []),
        ) if isinstance(date, str)
    ))
    payload = {"checked_at": datetime.now().isoformat(), **quality,
               "invalidates_legacy_dates": invalidated}
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_name(path.name + ".tmp")
        temporary.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        temporary.replace(path)
        return True
    except OSError as exc:
        logger.warning("宽度资格证据写入失败: %s", exc)
        return False


def get_cached_ma_breadth_qualification() -> dict | None:
    try:
        payload = json.loads(_ma_qualification_path().read_text(encoding="utf-8"))
        return payload if isinstance(payload, dict) else None
    except (OSError, ValueError):
        return None


def save_ma_breadth_cache(
    ma20: float | None, ma50: float | None, ma200: float | None,
    eligible: int = 0,
    up: int = 0, down: int = 0, flat: int = 0, total: int = 0,
    up_pct: float | None = None, adv_dec_ratio: float | None = None,
    limit_up: int = 0, limit_down: int = 0,
    trading_day: str = "",
    source: str = "腾讯日K线(本机收盘后预计算)",
    qualification: dict | None = None,
) -> bool:
    """落盘「冻结的每日市场宽度快照」（由本机收盘后预计算脚本调用）。

    包含：B20/B50/B200 上方占比 + 收盘时点的涨跌家数 + 该快照代表的交易日(trading_day)。
    global-strip 次日整天/周末直接读这份快照，不再实时重算。
    """
    p = _ma_cache_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        temporary = p.with_name(p.name + ".tmp")
        temporary.write_text(json.dumps({
            "as_of": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "date": trading_day or datetime.now().strftime("%Y-%m-%d"),
            "ma20_pct": ma20, "ma50_pct": ma50, "ma200_pct": ma200,
            "eligible": eligible,  # legacy MA20 denominator, not quote total
            "ma_eligible20": (qualification or {}).get("eligible20"),
            "ma_eligible50": (qualification or {}).get("eligible50"),
            "ma_eligible200": (qualification or {}).get("eligible200"),
            "breadth_universe_total": (qualification or {}).get("universe_total"),
            "breadth_status": (qualification or {}).get("status"),
            "up": up, "down": down, "flat": flat, "total": total,
            "quote_parsed": total,
            "quote_expected": (qualification or {}).get("universe_total"),
            "up_pct": up_pct, "adv_dec_ratio": adv_dec_ratio,
            "limit_up": limit_up, "limit_down": limit_down,
            "source": source,
        }, ensure_ascii=False), encoding="utf-8")
        temporary.replace(p)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("MA 宽度缓存写入失败: %s", e)
        return False


def get_cached_ma_breadth() -> dict | None:
    """读取本机预计算落盘的最新 MA 上方占比；无则 None。"""
    p = _ma_cache_path()
    try:
        d = json.loads(p.read_text(encoding="utf-8"))
        if d.get("ma20_pct") is None and d.get("ma50_pct") is None and d.get("ma200_pct") is None:
            return None
        quality = get_cached_ma_breadth_qualification() or {}
        if d.get("date") in (quality.get("invalidates_legacy_dates") or []):
            corrected = (
                quality.get("target_day") == d.get("date")
                and quality.get("status") == "verified"
                and quality.get("applied_to_snapshot") is True
                and all(d.get(f"ma{window}_pct") == quality.get(f"ma{window}_pct")
                        and d.get(f"ma_eligible{window}") == quality.get(f"eligible{window}")
                        and d.get(f"ma_eligible{window}") is not None
                        for window in (20, 50, 200))
            )
            if not corrected:
                return None
        return d
    except Exception:  # noqa: BLE001
        return None


def get_ma_breadth_derived(ttl_seconds: int = 300) -> dict:
    """从历史序列派生：5 日变化 + 点时百分位（1260 日窗口，与 SP500 口径同族）。

    结果做 TTL 缓存（默认 5 分钟）：strip 每次刷新都会调，但历史文件只在
    收盘后预计算时变一次，没必要每请求都重算 2600 点。
    无历史/无当前快照时各字段为 None（前端按缺失展示，不冒充）。
    """
    now = time.time()
    cached = _DERIVED_CACHE.get("v")
    if cached and now - cached[0] < ttl_seconds:
        return cached[1]

    out: dict = {
        "breadth_20_delta_5": None, "breadth_50_delta_5": None,
        "percentile_20": None, "percentile_50": None,
    }
    try:
        hist = get_ma_breadth_history(lookback_days=1400)
        snap = get_cached_ma_breadth()
        if hist and snap:
            import pandas as pd

            as_of = snap.get("trading_day") or hist[-1]["date"]
            for key, cur, hist_key in (
                ("breadth_20", snap.get("ma20_pct"), "ma20_pct"),
                ("breadth_50", snap.get("ma50_pct"), "ma50_pct"),
            ):
                if cur is None:
                    continue
                s_hist = pd.Series(
                    {h["date"]: h.get(hist_key) for h in hist if h.get(hist_key) is not None},
                    dtype=float,
                ).sort_index()
                s_hist.index = pd.to_datetime(s_hist.index)
                # 用历史末值对齐当前（快照代表交易日可能比历史末行晚半天）
                vis = s_hist[s_hist.index <= pd.Timestamp(as_of)]
                if len(vis) >= 6:
                    out[f"{key}_delta_5"] = round(float(cur - vis.iloc[-5]), 2)
                if len(vis) >= 250:
                    from lei_signal.market_context.breadth import rolling_percentile_at

                    pct = rolling_percentile_at(
                        vis, as_of=pd.Timestamp(as_of).date(), lookback=1260, min_periods=250,
                    )
                    if pct is not None:
                        out[f"percentile_{key.split('_')[1]}"] = round(float(pct), 1)
    except Exception as e:  # noqa: BLE001 — 派生值失败不炸 strip
        logger.warning("宽度派生值计算失败: %s", e)

    _DERIVED_CACHE["v"] = (now, out)
    return out


_DERIVED_CACHE: dict = {}


def append_ma_breadth_history(
    ma20: float | None, ma50: float | None, ma200: float | None,
    max_points: int = 20000, trading_day: str | None = None,
) -> bool:
    """把当日 MA 上方占比追加进历史序列（供趋势图）。同日多次运行则覆盖。

    trading_day 传数据代表的交易日（来自 K 线最后一根日期）；缺省回落 now()。
    不传时在周末运行会把周五的值写成周末日期，产生假数据点。
    """
    p = _ma_history_path()
    today = trading_day or datetime.now().strftime("%Y-%m-%d")
    rec = {"date": today, "ma20_pct": ma20, "ma50_pct": ma50, "ma200_pct": ma200}
    hist: list[dict] = []
    try:
        if p.exists():
            hist = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(hist, list):
            hist = []
    except Exception:  # noqa: BLE001
        hist = []
    if any(h.get("date") == today for h in hist):
        return True  # 旧历史保留原件；资格证据另存 sidecar
    hist.append(rec)
    hist.sort(key=lambda h: h.get("date", ""))
    hist = hist[-max_points:]
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        temporary = p.with_name(p.name + ".tmp")
        temporary.write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
        temporary.replace(p)
        return True
    except Exception as e:  # noqa: BLE001
        logger.warning("MA 宽度历史写入失败: %s", e)
        return False


_MA_HIST_MERGED_CACHE: dict[str, tuple[tuple, list[dict]]] = {}


def _stat_sig(path: Path) -> tuple[int, int] | None:
    try:
        st = path.stat()
        return (st.st_mtime_ns, st.st_size)
    except OSError:
        return None


def get_ma_breadth_history(lookback_days: int = 180) -> list[dict]:
    """返回历史 MA 上方占比序列（最多 lookback_days 个交易日）。

    读侧合并同目录下可选的 33 年全史基座 `a_share_ma_breadth_full_history.json`
    与滚动更新的 `a_share_ma_breadth_history.json`（重叠日期以 live 文件为准）。
    """
    p = _ma_history_path()
    full_p = p.with_name("a_share_ma_breadth_full_history.json")
    sig = (str(full_p), _stat_sig(full_p), str(p), _stat_sig(p))
    cached = _MA_HIST_MERGED_CACHE.get("merged")
    if cached and cached[0] == sig:
        merged = cached[1]
        return merged[-lookback_days:] if lookback_days > 0 else []

    by_date: dict[str, dict] = {}
    for candidate in (full_p, p):
        if not candidate.exists():
            continue
        try:
            rows = json.loads(candidate.read_text(encoding="utf-8"))
            if isinstance(rows, list):
                for row in rows:
                    d = row.get("date") if isinstance(row, dict) else None
                    if isinstance(d, str) and d:
                        by_date[d] = row
        except Exception:  # noqa: BLE001
            continue

    if not by_date:
        return []
    merged = [by_date[d] for d in sorted(by_date)]
    _MA_HIST_MERGED_CACHE["merged"] = (sig, merged)
    return merged[-lookback_days:] if lookback_days > 0 else []


def backfill_ma_breadth_history(max_points: int = 1260, min_eligible: int = 100) -> list[dict]:
    """从磁盘 K线缓存重建全历史 MA 上方占比序列（一次性补齐，供趋势图/叠加图）。

    腾讯日K线缓存 (a_share_klines.parquet) 已含每只最近 ~320 交易日收盘价，
    足够算 MA200。逐日滚动计算"站上均线的个股占比"，向量化完成。
    仅保留有效样本（站上 MA20 的合格股票数）≥ min_eligible 的交易日，避免
    早期样本过少造成的噪声。

    返回并落盘历史列表（覆盖式写入 a_share_ma_breadth_history.json）。
    """
    cache = load_kline_cache()
    if not cache:
        logger.warning("K线缓存为空，无法回溯宽度历史。请先跑一次预计算拉取K线。")
        return []

    import pandas as pd

    rows: list[tuple[str, str, float]] = []
    for sym, series in cache.items():
        for date, close in series:
            rows.append((str(date), sym, float(close)))
    df = pd.DataFrame(rows, columns=["date", "symbol", "close"])
    df["date"] = pd.to_datetime(df["date"])
    df = df.sort_values("date")
    piv = df.pivot(index="date", columns="symbol", values="close").sort_index()

    ma = {w: piv.rolling(w).mean() for w in (20, 50, 200)}
    above = {w: (piv > ma[w]) for w in (20, 50, 200)}
    elig = {w: (piv.notna() & ma[w].notna()) for w in (20, 50, 200)}

    pct = {}
    for w, key in ((20, "ma20_pct"), (50, "ma50_pct"), (200, "ma200_pct")):
        denom = elig[w].sum(axis=1)
        pct[key] = (above[w].sum(axis=1) / denom * 100).where(denom >= min_eligible)

    hist: list[dict] = []
    for d in piv.index:
        if pd.isna(pct["ma20_pct"].get(d)):
            continue
        hist.append({
            "date": d.strftime("%Y-%m-%d"),
            "ma20_pct": round(float(pct["ma20_pct"].loc[d]), 4)
            if not pd.isna(pct["ma20_pct"].loc[d]) else None,
            "ma50_pct": round(float(pct["ma50_pct"].loc[d]), 4)
            if d in pct["ma50_pct"].index and not pd.isna(pct["ma50_pct"].loc[d]) else None,
            "ma200_pct": round(float(pct["ma200_pct"].loc[d]), 4)
            if d in pct["ma200_pct"].index and not pd.isna(pct["ma200_pct"].loc[d]) else None,
        })

    # 合并：保留已落盘但回溯未覆盖的较新点（如当日实时算的），按日期去重。
    try:
        existing = json.loads(_ma_history_path().read_text(encoding="utf-8"))
        if isinstance(existing, list):
            seen = {h.get("date") for h in hist}
            for h in existing:
                if h.get("date") not in seen:
                    hist.append(h)
    except Exception:  # noqa: BLE001
        pass
    hist.sort(key=lambda h: h.get("date", ""))
    hist = hist[-max_points:]

    try:
        _ma_history_path().write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
    except Exception as e:  # noqa: BLE001
        logger.warning("回溯宽度历史写入失败: %s", e)
    logger.info("回溯完成：共 %d 个交易日的宽度历史（%s → %s）", len(hist),
                hist[0]["date"] if hist else "-", hist[-1]["date"] if hist else "-")
    return hist
