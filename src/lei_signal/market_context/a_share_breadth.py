"""真全A市场宽度数据层（替换原 fixture 假样本）。

提供两个互补维度：

1. 涨跌家数（advance / decline）—— 最权威、最不易错的全市场宽度。
   数据源 = 腾讯实时快照 (qt.gtimg.cn) + 沪深交易所代码列表 (官网 akshare)。
   覆盖真全A：沪 + 深（北交所代码列表在部分网络策略下不可达，自动跳过）。

2. MA 上方占比（breadth_20 / 50 / 200）—— 券商金工"全A宽度"口径。
   数据源 = akshare 东财历史K线 (stock_zh_a_hist)。
   该维度依赖个股历史K线接口，在受限网络环境（如某些开发沙箱）无法访问，
   此时通过 `include_ma=False`（默认）完全跳过，绝不伪造或超时卡死。
   在正常网络环境传 `include_ma=True` 即可计算。

所有数据均来自公开权威行情源，不再使用本地 fixture 假样本。
"""
from __future__ import annotations

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd
import requests

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

def get_a_share_codes(include_bj: bool = True) -> list[str]:
    """沪深交易所代码列表（akshare 官网，通用放行）+ 北交所（联网环境）。

    返回带前缀的代码列表：sh/sz/bj + 6 位数字。
    任一交易所列表获取失败仅告警并跳过，不影响其余市场。
    """
    import akshare as ak

    codes: list[str] = []
    try:
        sh = ak.stock_info_sh_name_code()["证券代码"].astype(str).tolist()
        codes += [f"sh{c}" for c in sh]
    except Exception as e:  # noqa: BLE001
        logger.warning("上交所代码列表获取失败: %s", e)
    try:
        sz = ak.stock_info_sz_name_code()["A股代码"].astype(str).tolist()
        codes += [f"sz{c}" for c in sz]
    except Exception as e:  # noqa: BLE001
        logger.warning("深交所代码列表获取失败: %s", e)
    if include_bj:
        try:
            bj = ak.stock_info_bj_name_code()["证券代码"].astype(str).tolist()
            codes += [f"bj{c}" for c in bj]
        except Exception as e:  # noqa: BLE001
            logger.warning("北交所代码列表获取失败(可能受网络策略拦截): %s", e)
    return codes


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
    codes: list[str], batch: int = 200, pause: float = 0.4,
) -> dict:
    """腾讯快照批量拉取 → 涨跌家数统计。

    Returns dict: up / down / flat / bad / total。
    """
    proxies = _proxies()
    up = down = flat = bad = 0
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
                elif chg > 0:
                    up += 1
                elif chg < 0:
                    down += 1
                else:
                    flat += 1
        except Exception as e:  # noqa: BLE001
            logger.warning("批量快照失败 %s..: %s", chunk[:2], e)
            bad += len(chunk)
        time.sleep(pause)
    return {"up": up, "down": down, "flat": flat, "bad": bad,
            "total": up + down + flat}


# ── MA 上方占比（akshare 东财历史K线，彪哥环境） ──────────────────────────

def fetch_ma_breadth(codes: list[str], lookback_days: int = 520) -> dict | None:
    """akshare 东财历史K线 → MA20/50/200 上方占比（站上均线股票占比）。

    在正常网络环境调用。受限网络下会抛出异常，由调用方捕获降级。
    逐只拉取较慢（全A 5000+ 只），建议异步/定时预计算，而非实时请求。
    """
    import akshare as ak

    proxies = _proxies()
    above = {"ma20": 0, "ma50": 0, "ma200": 0}
    eligible = {"ma20": 0, "ma50": 0, "ma200": 0}

    end = datetime.now().strftime("%Y%m%d")
    start = (datetime.now() - pd.Timedelta(days=lookback_days)).strftime("%Y%m%d")

    for c in codes:
        sym = c[2:]  # 去掉 sh/sz/bj 前缀
        try:
            df = ak.stock_zh_a_hist(
                symbol=sym, period="daily",
                start_date=start, end_date=end, adjust="",
            )
            if df is None or len(df) < 200:
                continue
            close = pd.to_numeric(df["收盘"], errors="coerce").dropna()
            if len(close) < 200:
                continue
            for w, key in ((20, "ma20"), (50, "ma50"), (200, "ma200")):
                ma = close.rolling(w).mean().iloc[-1]
                eligible[key] += 1
                if close.iloc[-1] > ma:
                    above[key] += 1
        except Exception as e:  # noqa: BLE001
            logger.warning("历史K线失败 %s: %s", c, e)
            continue

    if eligible["ma20"] == 0:
        return None
    return {
        "ma20_pct": above["ma20"] / eligible["ma20"] * 100,
        "ma50_pct": (above["ma50"] / eligible["ma50"] * 100
                     if eligible["ma50"] else None),
        "ma200_pct": (above["ma200"] / eligible["ma200"] * 100
                      if eligible["ma200"] else None),
    }


# ── 聚合入口 ──────────────────────────────────────────────────────────────

def get_a_share_breadth(include_ma: bool = False) -> AShareBreadth:
    """聚合真全A市场宽度。

    include_ma=False（默认）：仅算涨跌家数，秒级、受限网络可验。
    include_ma=True：额外算 MA 上方占比（需正常网络环境；失败自动降级）。
    """
    codes = get_a_share_codes(include_bj=True)
    ad = fetch_advance_decline(codes)
    total = ad["total"]
    up_pct = ad["up"] / total * 100 if total else None
    adv_dec = ad["up"] / ad["down"] if ad["down"] else None

    ma20 = ma50 = ma200 = None
    status = "ok"
    detail = f"涨跌家数:腾讯快照+沪深交易所代码列表(共{total}只, 解析失败{ad['bad']})"

    if include_ma:
        try:
            ma = fetch_ma_breadth(codes)
            if ma:
                ma20, ma50, ma200 = ma["ma20_pct"], ma["ma50_pct"], ma["ma200_pct"]
                detail += "; MA占比:akshare东财历史K线"
            else:
                status = "partial"
                detail += "; MA占比:历史K线源不可用(需正常网络环境)"
        except Exception as e:  # noqa: BLE001
            status = "partial"
            detail += f"; MA占比降级:{e}"

    return AShareBreadth(
        as_of=datetime.now().strftime("%Y-%m-%d %H:%M"),
        up=ad["up"], down=ad["down"], flat=ad["flat"], total=total,
        up_pct=up_pct, adv_dec_ratio=adv_dec,
        ma20_pct=ma20, ma50_pct=ma50, ma200_pct=ma200,
        data_status=status, source_detail=detail,
    )
