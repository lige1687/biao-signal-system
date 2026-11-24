"""全市场‘真龙头 + 细分小巨人’基本面与收盘前复权行情同步器（live_refresh）。

严格遵循用户选股铁律：‘不熟悉的、业绩不好、现金流一般的公司少看’。
独立维护在 ~/.lei_signal_lab/strategy_lab_bars/，绝不触碰其他目录：
1. 自动拉取全市场最新三季报/年报真实财务指标（净资产回报率、净利润同比增速、营收增速、每股经营现金流、细分行业）；
2. 自动拉取全市场实时总市值与官方中文简称，切分为两个干净专属池：
   - 【行业真龙头池】：总市值 >= 300 亿元（或细分行业市值前2名）+ 业绩盈利稳健 + 经营现金流为正；
   - 【细分小巨人池】：总市值 80~300 亿元 + 净资产回报率高(>=9%) + 净利润正增长(>=5%) + 经营现金流为正；
3. 并发同步上述精选股票池与全部场内基金的完整收盘前复权日线（盘中未收盘时段自动剔除当日半截K线，确保筹码计算严谨）。
"""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, time as dtime
import json
from pathlib import Path
import urllib.parse
import urllib.request
import numpy as np
import pandas as pd

from lei_signal.data.providers import TencentPriceProvider
from .data_portal import DataPortal
from .fund_evaluator import CORE_BROAD_FUNDS, DISTINCT_SECTOR_FUNDS, select_sector_representative_stocks


def _code_to_symbol(code6: str) -> str | None:
    code6 = str(code6).strip()
    if len(code6) != 6 or not code6.isdigit():
        return None
    if code6.startswith(("600", "601", "603", "605", "688")):
        return f"{code6}.SS"
    if code6.startswith(("000", "001", "002", "003", "300", "301")):
        return f"{code6}.SZ"
    return None


def fetch_quotes_and_mktcap_batch(symbols: list[str]) -> dict[str, dict[str, object]]:
    """通过腾讯摘要接口批量获取中文简称、总市值(亿元)与市盈率（每次70只，全市场约3秒）。"""
    out: dict[str, dict[str, object]] = {}
    tc_pairs: list[tuple[str, str]] = []
    for sym in symbols:
        if sym.endswith(".SS"):
            tc_pairs.append((sym, "sh" + sym[:6]))
        elif sym.endswith(".SZ"):
            tc_pairs.append((sym, "sz" + sym[:6]))

    def _fetch_chunk(chunk: list[tuple[str, str]]) -> dict[str, dict[str, object]]:
        local: dict[str, dict[str, object]] = {}
        q_str = ",".join(tc for _, tc in chunk)
        url = f"https://qt.gtimg.cn/q={q_str}"
        try:
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://gu.qq.com/"}
            )
            with urllib.request.urlopen(req, timeout=8.0) as resp:
                raw = resp.read().decode("gbk", errors="ignore")
            tc_to_sym = {tc: sym for sym, tc in chunk}
            for line in raw.splitlines():
                if '="' not in line:
                    continue
                left, right = line.split('="', 1)
                tc_code = left.strip().replace("v_", "")
                parts = right.split("~")
                if tc_code not in tc_to_sym or len(parts) < 46:
                    continue
                sym = tc_to_sym[tc_code]
                name = parts[1].strip()
                try:
                    mktcap_yi = float(parts[45]) if parts[45] else np.nan
                except ValueError:
                    mktcap_yi = np.nan
                try:
                    pe = float(parts[39]) if parts[39] else np.nan
                except ValueError:
                    pe = np.nan
                local[sym] = {"name": name, "mktcap_yi": mktcap_yi, "pe": pe}
        except Exception:
            pass
        return local

    chunks = [tc_pairs[i : i + 70] for i in range(0, len(tc_pairs), 70)]
    with ThreadPoolExecutor(max_workers=8) as ex:
        for res in ex.map(_fetch_chunk, chunks):
            out.update(res)
    return out


def fetch_latest_full_market_fundamentals(out_dir: Path) -> pd.DataFrame:
    """拉取全市场最新季报核心基本面（净资产回报率、净利增速、营收增速、每股经营现金流、所属行业）并合并总市值。"""
    # 自动探测最新已大规模披露的季报期（优先 2026-09-30，回退 2026-06-30）
    rows_all: list[dict] = []
    chosen_report_date = ""
    for rpt_dt in ("2026-09-30", "2026-06-30"):
        temp: list[dict] = []
        for page in range(1, 15):
            params = urllib.parse.urlencode(
                {
                    "reportName": "RPT_LICO_FN_CPD",
                    "columns": (
                        "SECURITY_CODE,SECURITY_NAME_ABBR,REPORTDATE,NOTICE_DATE,"
                        "BASIC_EPS,WEIGHTAVG_ROE,YSTZ,SJLTZ,MGJYXJJE,XSMLL,PUBLISHNAME"
                    ),
                    "filter": f"(REPORTDATE='{rpt_dt}')",
                    "pageNumber": page,
                    "pageSize": 500,
                }
            )
            url = f"https://datacenter-web.eastmoney.com/api/data/v1/get?{params}"
            req = urllib.request.Request(
                url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://data.eastmoney.com/"}
            )
            with urllib.request.urlopen(req, timeout=10.0) as resp:
                payload = json.loads(resp.read().decode("utf-8"))
            page_rows = (payload.get("result") or {}).get("data") or []
            if not page_rows:
                break
            temp.extend(page_rows)
        if len(temp) >= 3000:
            rows_all = temp
            chosen_report_date = rpt_dt
            break

    if not rows_all:
        raise RuntimeError("未能获取到全市场最新财报列表")

    df = pd.DataFrame(rows_all)
    df["symbol"] = df["SECURITY_CODE"].map(_code_to_symbol)
    df = df.dropna(subset=["symbol"]).drop_duplicates("symbol", keep="first").copy()
    df["name"] = df["SECURITY_NAME_ABBR"].astype(str).str.strip()
    df = df[~df["name"].str.upper().str.contains("ST|退", na=True)].copy()

    df["industry"] = df["PUBLISHNAME"].fillna("其他").astype(str).str.replace("Ⅱ", "", regex=False).str.strip()
    df["roe"] = pd.to_numeric(df["WEIGHTAVG_ROE"], errors="coerce")
    df["profit_yoy"] = pd.to_numeric(df["SJLTZ"], errors="coerce")
    df["rev_yoy"] = pd.to_numeric(df["YSTZ"], errors="coerce")
    df["ocf_ps"] = pd.to_numeric(df["MGJYXJJE"], errors="coerce")
    df["eps"] = pd.to_numeric(df["BASIC_EPS"], errors="coerce")
    df["gross_margin"] = pd.to_numeric(df["XSMLL"], errors="coerce")
    df["report_date"] = chosen_report_date
    df["notice_date"] = pd.to_datetime(df["NOTICE_DATE"], errors="coerce").dt.strftime("%Y-%m-%d")

    # 批量补齐实时总市值（亿元）与腾讯最新简称
    q_map = fetch_quotes_and_mktcap_batch(df["symbol"].tolist())
    df["mktcap_yi"] = df["symbol"].map(lambda s: q_map.get(s, {}).get("mktcap_yi", np.nan))
    df["pe"] = df["symbol"].map(lambda s: q_map.get(s, {}).get("pe", np.nan))
    live_names = df["symbol"].map(lambda s: q_map.get(s, {}).get("name", ""))
    df["name"] = np.where(live_names.astype(bool), live_names, df["name"])
    df = df[~df["name"].astype(str).str.upper().str.contains("ST|退", na=True)].copy()

    # 计算同细分行业内的总市值排名与净资产回报率分位
    df["ind_mktcap_rank"] = df.groupby("industry")["mktcap_yi"].rank(ascending=False, method="min")
    df["ind_roe_pct"] = df.groupby("industry")["roe"].rank(pct=True)

    # 划分两档专属好生意池（业绩好 + 现金流真金白银为正）
    is_fin_utility = df["industry"].str.contains("银行|保险|电力|航运港口|铁路公路", na=False)
    cash_flow_solid = (df["ocf_ps"] > 0.05) | (is_fin_utility & (df["roe"] >= 6.0))
    earnings_healthy = (df["eps"] > 0) & (
        ((df["roe"] >= 6.5) & (df["profit_yoy"] >= -5.0))
        | ((df["roe"] >= 5.0) & (df["profit_yoy"] >= 10.0))
        | (is_fin_utility & (df["roe"] >= 5.5) & (df["profit_yoy"] >= -2.0))
    )

    # 1. 【行业真龙头池】：总市值 >= 300亿（或细分行业市值前2且>=180亿）+ 业绩健康 + 现金流硬
    is_leader = (
        ((df["mktcap_yi"] >= 300.0) | ((df["ind_mktcap_rank"] <= 2) & (df["mktcap_yi"] >= 180.0)))
        & earnings_healthy
        & cash_flow_solid
    )

    # 2. 【细分小巨人池】：80亿 <= 总市值 < 300亿 + 高回报(ROE>=9%且行业前30%) + 净利润正增长(>=5%) + 每股现金流硬(>0.15)
    is_small_giant = (
        (~is_leader)
        & (df["mktcap_yi"] >= 80.0)
        & (df["mktcap_yi"] < 300.0)
        & (df["roe"] >= 9.0)
        & (df["ind_roe_pct"] >= 0.70)
        & (df["profit_yoy"] >= 5.0)
        & (df["ocf_ps"] > 0.15)
    )

    df["tier"] = np.where(is_leader, "leader", np.where(is_small_giant, "small_giant", "other"))
    keep_cols = [
        "symbol", "name", "industry", "mktcap_yi", "pe", "roe", "profit_yoy",
        "rev_yoy", "ocf_ps", "gross_margin", "ind_mktcap_rank", "ind_roe_pct",
        "report_date", "notice_date", "tier",
    ]
    out_df = df[keep_cols].reset_index(drop=True)
    out_dir.mkdir(parents=True, exist_ok=True)
    out_df.to_parquet(out_dir / "fundamentals_latest.parquet")
    return out_df


def _last_complete_session_cutoff() -> pd.Timestamp:
    """盘中交易未结束（15:05前）时，剔除当日未走完的半根日K线，确保只用完整收盘K线计算活筹码。"""
    now = datetime.now()
    if now.weekday() < 5 and now.time() < dtime(15, 5):
        return pd.Timestamp(now.date()) - pd.Timedelta(days=1)
    return pd.Timestamp(now.date())


def refresh_live_pool(
    portal: DataPortal,
    *,
    max_workers: int = 12,
    force: bool = False,
) -> dict[str, int]:
    """全自动拉取全市场好生意分层名单（真龙头 + 细分小巨人）与场内基金最新完整收盘日线。"""
    out_dir = portal.live_bars_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. 更新或读取当天已缓存的全市场三季报好生意分层表
    fund_path = out_dir / "fundamentals_latest.parquet"
    if force or not fund_path.exists() or (
        datetime.fromtimestamp(fund_path.stat().st_mtime).date() < datetime.now().date()
    ):
        fund_df = fetch_latest_full_market_fundamentals(out_dir)
    else:
        fund_df = pd.read_parquet(fund_path)

    leaders = sorted(fund_df.loc[fund_df["tier"] == "leader", "symbol"].astype(str).tolist())
    small_giants = sorted(fund_df.loc[fund_df["tier"] == "small_giant", "symbol"].astype(str).tolist())
    sector_reps = select_sector_representative_stocks(fund_df, per_sector_top=12)
    etfs = sorted(
        set(portal.list_cn_etfs())
        | {s for s, _, _ in CORE_BROAD_FUNDS}
        | {s for s, _, _ in DISTINCT_SECTOR_FUNDS}
    )

    names_path = out_dir / "names.json"
    names_map: dict[str, str] = {}
    if names_path.exists():
        try:
            names_map = json.loads(names_path.read_text(encoding="utf-8"))
        except Exception:
            names_map = {}

    for _, row in fund_df.iterrows():
        if row["name"]:
            names_map[str(row["symbol"])] = str(row["name"]).replace(" ", "")
    etf_quotes = fetch_quotes_and_mktcap_batch([s for s in etfs if s not in names_map])
    for s, info in etf_quotes.items():
        if info.get("name"):
            names_map[s] = str(info["name"]).replace(" ", "")
    names_path.write_text(json.dumps(names_map, ensure_ascii=False, indent=2), encoding="utf-8")

    # 2. 并发增量同步完整收盘前复权日K线
    all_symbols = sorted(set(etfs) | set(leaders) | set(small_giants) | set(sector_reps))
    cutoff_dt = _last_complete_session_cutoff()
    # 找上证指数或沪深300最近完整收盘日作新鲜度基准
    provider = TencentPriceProvider(timeout=8.0, max_bars=650, attempts=2, backoff=0.8)
    try:
        ref_bars = provider.fetch("510300.SS", min_rows=30).bars
        ref_bars.index = pd.to_datetime(ref_bars.index).tz_localize(None).normalize()
        ref_bars = ref_bars[ref_bars.index <= cutoff_dt]
        target_latest_dt = ref_bars.index[-1]
    except Exception:
        target_latest_dt = cutoff_dt

    to_fetch: list[str] = []
    skipped = 0
    for sym in all_symbols:
        p = out_dir / f"{sym}.bars.parquet"
        if not force and p.exists():
            try:
                existing = pd.read_parquet(p)
                existing_clean = existing[existing.index <= cutoff_dt]
                if len(existing_clean) >= 60 and existing_clean.index.max() >= target_latest_dt:
                    if len(existing_clean) != len(existing):
                        existing_clean.to_parquet(p)
                    skipped += 1
                    continue
            except Exception:
                pass
        to_fetch.append(sym)

    def _one(sym: str) -> tuple[str, pd.DataFrame | None]:
        try:
            res = provider.fetch(sym, min_rows=30)
            df = res.bars[["open", "high", "low", "close", "volume"]].astype(float).copy()
            df.index = pd.to_datetime(df.index).tz_localize(None).normalize()
            df = df[df.index <= cutoff_dt].sort_index()
            df = df[~df.index.duplicated(keep="last")]
            return sym, df
        except Exception:
            return sym, None

    ok = 0
    failed = 0
    if to_fetch:
        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futs = [ex.submit(_one, s) for s in to_fetch]
            for fut in as_completed(futs):
                sym, df = fut.result()
                if df is not None and len(df) >= 30:
                    df.to_parquet(out_dir / f"{sym}.bars.parquet")
                    ok += 1
                else:
                    failed += 1

    return {
        "total_universe": len(all_symbols),
        "etf_count": len(etfs),
        "leader_pool_count": len(leaders),
        "small_giant_pool_count": len(small_giants),
        "updated": ok,
        "already_fresh": skipped,
        "failed": failed,
        "latest_complete_date": str(target_latest_dt.date()),
    }
