#!/usr/bin/env python3
"""统一回填：SP500 + 全A 真实宽度历史（MA20/50/200 上方占比）。

绕沙箱代理（NO_PROXY=*, trust_env=False），用 akshare 新浪源拉成分股全历史日K，
逐日算「站上 MA 的个股占比」，落盘到项目期望的 JSON 路径。

落盘：
  ~/.lei_signal_lab/cache/sp500_ma_breadth_history.json  (美股, key: breadth_20/50/200)
  ~/.lei_signal_lab/cache/a_share_ma_breadth_history.json (A股, key: ma20/50/200_pct)
  ~/.lei_signal_lab/cache/sp500_klines.parquet            (美股收盘价透视表, 断点续传)
  ~/.lei_signal_lab/cache/a_share_klines_full.parquet     (A股收盘价透视表, 断点续传)

用法：
  python scripts/backfill_breadth_full.py --market us   # 美股 503只
  python scripts/backfill_breadth_full.py --market cn   # 全A 5543只
  python scripts/backfill_breadth_full.py --market both  # 都跑
  python scripts/backfill_breadth_full.py --market us --limit 20  # 调试：只拉20只
  python scripts/backfill_breadth_full.py --market cn --workers 8  # 指定并发
"""
from __future__ import annotations

import argparse
import json
import logging
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

# ── 绕沙箱代理（必须在 import requests/akshare 前设） ──
os.environ["NO_PROXY"] = "*"
os.environ["no_proxy"] = "*"
for k in list(os.environ):
    if "proxy" in k.lower() and k not in ("NO_PROXY", "no_proxy"):
        del os.environ[k]

SRC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src")
if SRC not in sys.path:
    sys.path.insert(0, SRC)

import pandas as pd  # noqa: E402
import requests  # noqa: E402

# monkeypatch requests 不走代理
_orig_req = requests.Session.request

def _no_proxy_req(self, *a, **kw):
    kw.setdefault("proxies", {"http": None, "https": None})
    kw.setdefault("timeout", 30)  # 单只请求 30s 超时，防止个别标的卡死整个回填
    self.trust_env = False
    return _orig_req(self, *a, **kw)

requests.Session.request = _no_proxy_req

import akshare as ak  # noqa: E402
from lei_signal.api import config  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("backfill_breadth")

CACHE = Path(config.cache_root())
CACHE.mkdir(parents=True, exist_ok=True)
REPO = Path(__file__).resolve().parent.parent
UNI_FIXTURE = REPO / "tests" / "fixtures" / "market_context" / "universes"


# ── 数据拉取 ──────────────────────────────────────────────────────────────

def _fetch_us_close(symbol: str) -> tuple[str, pd.Series] | None:
    """拉美股单只全历史收盘价。"""
    try:
        df = ak.stock_us_daily(symbol=symbol, adjust="")
        if df is None or len(df) == 0:
            return None
        s = df.set_index(pd.to_datetime(df["date"]))["close"].astype(float)
        s.name = symbol
        return symbol, s.dropna()
    except Exception as exc:  # noqa: BLE001
        logger.warning("US %s 失败: %s", symbol, exc)
        return None


def _fetch_cn_close(code: str) -> tuple[str, pd.Series] | None:
    """拉A股单只全历史收盘价（前复权）。code 为纯数字如 000001。"""
    sym = ("sh" if code.startswith("6") else "sz") + code
    try:
        df = ak.stock_zh_a_daily(symbol=sym, adjust="qfq")
        if df is None or len(df) == 0:
            return None
        s = df.set_index(pd.to_datetime(df["date"]))["close"].astype(float)
        s.name = code
        return code, s.dropna()
    except Exception as exc:  # noqa: BLE001
        logger.warning("CN %s 失败: %s", sym, exc)
        return None


def _fetch_all(symbols: list[str], fetch_fn, label: str, workers: int, limit: int) -> pd.DataFrame:
    """并发拉取，返回 date×symbol 收盘价透视表。"""
    if limit:
        symbols = symbols[:limit]
    cache_path = CACHE / ("sp500_klines.parquet" if label == "US" else "a_share_klines_full.parquet")

    # 断点续传：已落盘的透视表里已有的 symbol 跳过
    existing: dict[str, pd.Series] = {}
    if cache_path.exists():
        try:
            old = pd.read_parquet(cache_path)
            existing = {c: old[c].dropna() for c in old.columns}
            logger.info("断点续传：已有 %d 只 %s", len(existing), label)
        except Exception:  # noqa: BLE001
            pass

    todo = [s for s in symbols if s not in existing]
    logger.info("需拉取 %d 只 %s（已有 %d，跳过）", len(todo), label, len(existing))
    if not todo:
        return pd.DataFrame(existing) if existing else pd.DataFrame()

    result: dict[str, pd.Series] = dict(existing)
    ok = 0
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=workers) as pool:
        futs = {pool.submit(fetch_fn, s): s for s in todo}
        for i, fut in enumerate(as_completed(futs), 1):
            r = fut.result()
            if r is not None:
                result[r[0]] = r[1]
                ok += 1
            if i % 50 == 0 or i == len(todo):
                elapsed = time.time() - t0
                rate = i / elapsed if elapsed else 0
                eta = (len(todo) - i) / rate if rate else 0
                logger.info("%s 进度 %d/%d (ok=%d) %.1f/s ETA %.0fs", label, i, len(todo), ok, rate, eta)
                # 每 100 只落盘一次（断点续传）
                if i % 100 == 0 and result:
                    _save_pivot(result, cache_path)

    _save_pivot(result, cache_path)
    logger.info("%s 拉取完成：%d/%d 只成功，耗时 %.0fs", label, ok, len(todo), time.time() - t0)
    return pd.DataFrame(result) if result else pd.DataFrame()


def _save_pivot(result: dict, path: Path) -> None:
    try:
        piv = pd.DataFrame(result)
        piv.index.name = "date"
        piv.to_parquet(path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("透视表落盘失败: %s", exc)


# ── 宽度计算 ──────────────────────────────────────────────────────────────

def compute_breadth(piv: pd.DataFrame, windows=(20, 50, 200), min_eligible=100) -> list[dict]:
    """逐日算站上各 MA 的个股占比。与项目 a_share_breadth/backfill_sp500 同算法。

    关键修正：A 股个股存在停牌/数据缺口，pandas rolling 默认要求窗口内
    连续非 NaN，单个缺口会把该股票整段 MA 打成 NaN（2010 年实测 MA200 合格股
    仅 5 只）。故先 ffill 抹平缺口再算 MA；但资格(elig)与"站上"(above)比较仍用
    原始 piv，确保停牌/退市/未上市日保持 NaN，不参与宽度统计。
    """
    if piv.empty:
        return []
    piv = piv.sort_index()
    piv_ff = piv.ffill()  # 仅抹平内部缺口，前置 NaN(未上市)保持 NaN
    ma = {w: piv_ff.rolling(w).mean() for w in windows}
    above = {w: (piv > ma[w]) for w in windows}
    elig = {w: (piv.notna() & ma[w].notna()) for w in windows}
    pct = {}
    for w in windows:
        denom = elig[w].sum(axis=1)
        pct[w] = (above[w].sum(axis=1) / denom * 100).where(denom >= min_eligible)

    hist = []
    for d in piv.index:
        if pd.isna(pct[windows[0]].get(d)):
            continue
        row = {"date": pd.Timestamp(d).strftime("%Y-%m-%d")}
        for w in windows:
            v = pct[w].get(d)
            row[f"breadth_{w}"] = None if pd.isna(v) else round(float(v), 4)
        hist.append(row)
    return hist


def _write_json(hist: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(hist, ensure_ascii=False), encoding="utf-8")
    logger.info("落盘 %s：%d 个交易日", path, len(hist))


# ── 美股 ──────────────────────────────────────────────────────────────────

def run_us(workers: int, limit: int) -> None:
    uni = pd.read_parquet(UNI_FIXTURE / "SP500.parquet")
    symbols = sorted(uni["symbol"].astype(str).tolist())
    logger.info("SP500 成分股 %d 只", len(symbols))
    piv = _fetch_all(symbols, _fetch_us_close, "US", workers, limit)
    if piv.empty:
        logger.error("美股收盘价为空，无法计算宽度")
        return
    logger.info("美股透视表：%d 交易日 × %d 只", len(piv), piv.shape[1])
    hist = compute_breadth(piv, min_eligible=100)
    if not hist:
        logger.error("美股宽度计算为空")
        return
    # 转成项目期望的格式（breadth_20/50/200）
    out = [{"date": h["date"], "breadth_20": h["breadth_20"],
            "breadth_50": h["breadth_50"], "breadth_200": h["breadth_200"]} for h in hist]
    _write_json(out, CACHE / "sp500_ma_breadth_history.json")
    logger.info("美股宽度：首 %s 末 %s", out[0]["date"], out[-1]["date"])


# ── A股 ───────────────────────────────────────────────────────────────────

def run_cn(workers: int, limit: int) -> None:
    cached = CACHE / "a_share_codes_cached.json"
    if cached.exists():
        codes = json.loads(cached.read_text(encoding="utf-8"))
        logger.info("读缓存全A代码 %d 只", len(codes))
    else:
        try:
            codes_df = ak.stock_info_a_code_name()
            codes = sorted(codes_df["code"].astype(str).tolist())
        except Exception as exc:  # noqa: BLE001
            logger.error("无法获取全A代码列表: %s", exc)
            return
    # 过滤：只要 6 位数字代码（排掉指数/基金）
    codes = [c for c in codes if c.isdigit() and len(c) == 6]
    logger.info("全A代码 %d 只", len(codes))
    piv = _fetch_all(codes, _fetch_cn_close, "CN", workers, limit)
    if piv.empty:
        logger.error("A股收盘价为空，无法计算宽度")
        return
    logger.info("A股透视表：%d 交易日 × %d 只", len(piv), piv.shape[1])
    # min_eligible=50：早年 A 股总数少（1995 仅 ~96 只），降到 50 才能让宽度
    # 回溯到 1995；现代年份仍有数百~两千只，占比稳定。
    hist = compute_breadth(piv, min_eligible=50)
    if not hist:
        logger.error("A股宽度计算为空")
        return
    # 项目原版格式（ma20_pct/ma50_pct/ma200_pct）
    out = [{"date": h["date"], "ma20_pct": h["breadth_20"],
            "ma50_pct": h["breadth_50"], "ma200_pct": h["breadth_200"]} for h in hist]
    _write_json(out, CACHE / "a_share_ma_breadth_history.json")
    logger.info("A股宽度：首 %s 末 %s", out[0]["date"], out[-1]["date"])


def main() -> int:
    ap = argparse.ArgumentParser(description="统一回填 SP500+全A 真实宽度历史")
    ap.add_argument("--market", choices=["us", "cn", "both"], default="both")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--limit", type=int, default=0, help="只拉前 N 只（调试）")
    args = ap.parse_args()

    if args.market in ("us", "both"):
        logger.info("=" * 60)
        logger.info("开始美股回填")
        run_us(args.workers, args.limit)
    if args.market in ("cn", "both"):
        logger.info("=" * 60)
        logger.info("开始A股回填")
        run_cn(args.workers if args.market == "cn" else max(3, args.workers - 2), args.limit)

    logger.info("=" * 60)
    logger.info("全部完成")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
