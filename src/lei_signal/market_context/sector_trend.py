"""行业板块趋势工作台 · 预计算层（P1）。

设计要点（全部来自 docs/plan-sector-trend-page.md，照方案落地，不复核【实测】断言）：

- 板块层一切判定标 ``research_proxy``，绝不冒充 LEI 原始规则（红线 1）。
- 不出买卖点：本模块只产出「趋势确立/走弱/强度增强/衰减/阶段」类字段（红线 2）。
- MACD 必与 LEI 三色 + 均线斜率同屏出现，不独立成结论（红线 3）。
- 均线周期 / MACD 12·26·9 全部经 ``indicator_config()`` 读 ``configs/rules.v2.yaml``，
  不硬编码（红线 4）。
- 合成口径诚实标注：等权指数（本机合成非行情软件板块指数）；当前成分回溯含前视偏差；
  不含北交所（腾讯无历史自动剔除）；MA200 留痕中（红线 5）。
- 不可用字段不冒充：合成指数 ``atr14`` / ``volume_ratio20`` 等退化值不输出（红线 6）。
- 斜率跨板块比较用百分比口径 ``ema20_slope_pct``；``*_slope`` 绝对差只取符号（红线 7）。
- 原子写落盘，日志进 ``logs/``（红线 8）。

本模块只做纯计算 + 落盘；CLI 与 API 只是壳。网络取数集中在 ``fetch_sector_members``，
单元测试用 monkeypatch 隔离（照 test_market_breadth / test_fundamentals 风格）。
"""
from __future__ import annotations

import json
import logging
import os
import random
import threading
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from lei_signal.data.cache import DEFAULT_CACHE_DIR
from lei_signal.domain.rules_config import get_rule, indicator_config
from lei_signal.domain.types import LONG_TREND_CN, SignalColor
from lei_signal.features.indicators import compute_features
from lei_signal.market_context import retail_heat
from lei_signal.rules.lei_color import classify_colors
from lei_signal.rules.long_trend import compute_long_trend
from lei_signal.rules.macd_strength import read_macd_strength

logger = logging.getLogger(__name__)

# ── 缓存路径（与 a_share_breadth 同规则：LEI_CACHE_ROOT 覆盖）─────────────────
ROOT = Path(os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR)))


def _members_path() -> Path:
    return ROOT / "sector_members.json"


def _snapshot_path() -> Path:
    return ROOT / "sector_trend_snapshot.json"


def _history_path() -> Path:
    return ROOT / "sector_trend_history.json"


# ── 市场前缀（不能用 f13：北交所 920 段 f13=0 是错的【实测】）─────────────────
def _prefix(code: str) -> str:
    if code.startswith(("4", "8", "92")):
        return "bj"
    if code.startswith(("6", "9")):
        return "sh"
    return "sz"  # 0/3/2 开头


# 颜色 / 长趋势 中文映射（只用于展示，来自 domain.types）
_SIGNAL_COLOR_CN = {
    SignalColor.GREEN.value: "绿",
    SignalColor.GRAY.value: "灰",
    SignalColor.BLACK.value: "黑",
    SignalColor.UNKNOWN.value: "未知",
}

# 阶段 → 前端键（与 web/src/types.ts 的 SectorTrendRow.stage 对齐）
STAGE_KEYS = {
    "markup": "上升",
    "accumulation": "筑底",
    "distribution": "派发",
    "decline": "下降",
}

# L3 新板块 / 短序列：仅输出颜色，其余字段 null 的阈值
_MIN_BARS_FOR_TREND = 21          # 颜色最少 21 根
_MIN_BARS_FOR_MA = 121            # 长趋势 / 斜率稳定建议 ≥121 根
_MIN_HIT_FOR_INDEX = 5            # 命中成分股 <5 只不生成指数（方案【实测】28 个<3只）


# ════════════════════════════════════════════════════════════════════════════
# 1) 成分股映射（网络取数，P1.1 a）
# ════════════════════════════════════════════════════════════════════════════
def fetch_sector_boards() -> list[dict]:
    """板块列表（名称/涨跌/PE/主力净流入/涨跌家数），复用 fundamentals.sources。

    东财 push2 clist 在受限网络下可能不可达，由调用方决定降级。
    """
    from lei_signal.fundamentals import sources

    return sources.fetch_industry_boards()


def _fetch_board_members(code: str) -> list[str]:
    """东财 clist ``fs=b:{code}`` 翻页拉成分股，返回带前缀的 symbol 列表。

    ``pz=100`` 硬上限【实测】，需翻页；每请求 0.2s 抖动由调用方并发控制。
    """
    from lei_signal.fundamentals import sources

    members: list[str] = []
    total = None
    for page in range(1, 30):
        payload = sources._get_json(
            sources._CLIST_URLS,
            {
                "pn": page,
                "pz": 100,
                "po": 1,
                "np": 1,
                "fltt": 2,
                "invt": 2,
                "fid": "f3",
                "fs": f"b:{code}",
                "fields": "f12,f13,f14",
            },
        )
        data = payload.get("data") or {}
        if total is None:
            total = int(data.get("total") or 0)
        batch = data.get("diff") or []
        if not batch:
            break
        for row in batch:
            c = row.get("f12")
            if c:
                c = str(c).strip()
                members.append(f"{_prefix(c)}{c}")
        if total and len(members) >= total:
            break
    # 去重保序（同一成分可能跨页重复）
    seen: set[str] = set()
    out: list[str] = []
    for m in members:
        if m not in seen:
            seen.add(m)
            out.append(m)
    return out


def fetch_sector_members(
    *,
    concurrency: int = 6,
    jitter: float = 0.2,
    force: bool = False,
) -> dict[str, dict]:
    """拉全量板块成分股映射。

    返回 ``{code: {"name", "members": [prefixed_symbol, ...]}}``。
    当日已缓存且非 force 则跳过取数。命中判定：``date == today``（周末沿用周五）。
    """
    today = datetime.now().strftime("%Y-%m-%d")
    if not force:
        cached = load_members_cache()
        if cached and cached.get("date") == today:
            logger.info("成分股映射命中当日缓存，跳过取数")
            return cached["boards"]

    boards = fetch_sector_boards()
    codes = [b["code"] for b in boards if b.get("code")]
    names = {b["code"]: b.get("name") for b in boards}

    result: dict[str, dict] = {}
    lock = threading.Lock()

    def worker(code: str) -> None:
        time.sleep(random.uniform(0, jitter))
        try:
            members = _fetch_board_members(code)
        except Exception as exc:  # noqa: BLE001 - 单板块失败不阻断其余
            logger.warning("板块 %s 成分股拉取失败: %s", code, exc)
            members = []
        with lock:
            result[code] = {"name": names.get(code), "members": members}

    threads = []
    for i, code in enumerate(codes):
        t = threading.Thread(target=worker, args=(code,), daemon=True)
        threads.append(t)
        t.start()
        while len([x for x in threads if x.is_alive()]) >= concurrency:
            time.sleep(0.01)
    for t in threads:
        t.join()

    out = {
        "as_of": datetime.now().strftime("%Y-%m-%d %H:%M"),
        "date": today,
        "boards": result,
    }
    _save_atomic(out, _members_path())
    return result


# ════════════════════════════════════════════════════════════════════════════
# 1b) 板块资金流（网络取数；单据规模代理，非真实机构/散户身份）
#     实测教训：push2his 高并发（6 线程）触发临时封禁（RemoteDisconnected），
#     且系统代理白名单拒 push2his、push2delay 只返最近 1 日。因此采用
#     **本地累积 + 双通道增量**：
#     - 当日增量走 clist 批量排行（白名单 push2，5 页请求覆盖全板块五档）；
#     - 历史回填才用 push2his 直连（缓存不足 days 的板块，并发 2 + 1s 抖动）；
#     - 历史落 sector_flow_history.json，跨日稳定，直连被封也不影响每日累积。
# ════════════════════════════════════════════════════════════════════════════
def _flow_history_path() -> Path:
    return ROOT / "sector_flow_history.json"


def load_flow_history() -> dict[str, list[dict]]:
    p = _flow_history_path()
    if not p.exists():
        return {}
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except Exception:  # noqa: BLE001 - 缓存损坏按空处理，重拉即可
        return {}


def _merge_flow_points(
    cached: list[dict], new: list[dict], *, keep_days: int = 520
) -> list[dict]:
    """按日期合并（新值覆盖旧值），升序返回，最多保留 keep_days 天。

    keep_days=520（约 2 年）：散户热度/回测需要尽量长的本地累积史，
    东财 push2his 单次只给 120 天，跨日只能靠本地累积变长，故不短裁。
    """
    by_date = {p["date"]: p for p in cached if p.get("date")}
    for p in new or []:
        if p.get("date"):
            by_date[p["date"]] = p
    return [by_date[d] for d in sorted(by_date)][-keep_days:]


def _yi(v) -> float | None:
    return None if v in (None, "", "-") else round(float(v) / 1e8, 2)


def _fetch_flow_daily_snapshot() -> dict:
    """当日全板块五档资金流快照（clist 批量排行，走白名单 push2，约 5 页请求）。

    返回 ``{"date": str|None, "points": {code: point}}``，point 结构与 fflow 日史
    一致（main/small/medium/large/super_large_yi，单位亿）。日期不猜：取任一板块
    delay fflow 最新点的服务器日期，失败则 date=None 且快照弃用（不可用不冒充）。
    """
    from lei_signal.fundamentals import sources

    diff: list[dict] = []
    for page in range(1, 10):
        payload = sources._get_json(
            sources._CLIST_URLS,
            {
                "pn": page, "pz": 100, "po": 1, "np": 1, "fltt": 2, "invt": 2,
                "fid": "f62", "fs": "m:90+t:2+f:!50",
                "fields": "f12,f14,f62,f66,f72,f78,f84",
            },
        )
        data = payload.get("data") or {}
        batch = data.get("diff") or []
        diff.extend(batch)
        if not batch or len(diff) >= (data.get("total") or 0):
            break

    points: dict[str, dict] = {}
    for r in diff:
        code = str(r.get("f12") or "").strip()
        if not code:
            continue
        points[code] = {
            "main_yi": _yi(r.get("f62")),
            "small_yi": _yi(r.get("f84")),
            "medium_yi": _yi(r.get("f78")),
            "large_yi": _yi(r.get("f72")),
            "super_large_yi": _yi(r.get("f66")),
        }

    date: str | None = None
    if points:
        try:
            probe = sources.fetch_industry_flow(next(iter(points)), days=1)
            if probe:
                date = probe[-1].get("date")
        except Exception:  # noqa: BLE001 - 日期拿不到就弃用快照
            date = None
    return {"date": date, "points": points}


def fetch_sector_flows(
    codes: list[str],
    *,
    days: int = 120,
    concurrency: int = 2,
    jitter: float = 1.0,
) -> dict[str, list[dict]]:
    """增量维护板块资金流历史缓存，返回合并后的全量日史。

    1. 当日增量：clist 批量快照（稳定，5 页请求）；
    2. 历史回填：仅缓存不足 ``days`` 的板块（默认 120 = 东财 push2his
       单次可回填的最大深度），push2his 直连全量拉
       （先探一次直连可用性，被封则本轮跳过，等下个交易日再试）；
    3. 合并去重（新值覆盖旧值）后原子落盘 ``sector_flow_history.json``。
    """
    from lei_signal.fundamentals import sources

    cached_all = load_flow_history()

    snap = _fetch_flow_daily_snapshot()
    snap_date, snap_pts = snap["date"], snap["points"]

    def _have(code: str) -> int:
        n = len(cached_all.get(code) or [])
        if snap_date and code in snap_pts:
            last = (cached_all.get(code) or [{}])[-1].get("date")
            if last != snap_date:
                n += 1
        return n

    need_backfill = [c for c in codes if _have(c) < days]

    fetched: dict[str, list[dict]] = {}
    if need_backfill:
        direct_ok = True
        try:
            sources._get_json(
                sources._FLOW_URLS[:1],
                {"lmt": 1, "klt": 101, "secid": f"90.{need_backfill[0]}",
                 "fields1": "f1", "fields2": "f51"},
                trust_env=False,
            )
        except Exception:  # noqa: BLE001 - 直连不可用则本轮不回填
            direct_ok = False
            logger.warning(
                "push2his 直连不可用（可能临时封禁），%d 个板块历史回填延后",
                len(need_backfill),
            )
        if direct_ok:
            lock = threading.Lock()

            def worker(code: str) -> None:
                time.sleep(random.uniform(0, jitter))
                try:
                    pts = sources.fetch_industry_flow(code, days=days, prefer_direct=True)
                except Exception as exc:  # noqa: BLE001 - 单板块失败不阻断其余
                    logger.warning("板块 %s 资金流回填失败: %s", code, exc)
                    pts = []
                with lock:
                    fetched[code] = pts

            threads = []
            for code in need_backfill:
                t = threading.Thread(target=worker, args=(code,), daemon=True)
                threads.append(t)
                t.start()
                while len([x for x in threads if x.is_alive()]) >= concurrency:
                    time.sleep(0.01)
            for t in threads:
                t.join()

    merged_all = {
        code: _merge_flow_points(
            cached_all.get(code) or [],
            [
                *(fetched.get(code) or []),
                *(
                    [{"date": snap_date, **snap_pts[code]}]
                    if snap_date and code in snap_pts
                    else []
                ),
            ],
        )
        for code in set(codes) | set(cached_all)
    }
    _save_atomic(merged_all, _flow_history_path())
    return merged_all


# ════════════════════════════════════════════════════════════════════════════
# 2) 层级判定和去重（纯函数，P1.1 b）
# ════════════════════════════════════════════════════════════════════════════
def classify_hierarchy(
    boards: dict[str, set[str]],
    names: dict[str, str] | None = None,
) -> dict[str, dict]:
    """返回 ``{code: {"level", "parent", "canonical_of", "canonical"}}``。

    - 去重：以 ``frozenset(members)`` 分组；同集合内保留「无后缀 > Ⅱ > Ⅲ」为 canonical，
      其余记 alias。**绝不按名称去后缀合并**——反例：``其他电源设备Ⅲ`` ⊂
      ``其他电源设备Ⅱ`` 是真父子（不同集合），不合并。
    - 层级：无真超集 = L1；其余 parent = 包含它且成分股数最小的板块；level = 祖先深度+1（封顶 3）。
    - 交叉校验（父集==子集合并）在 ``validate_hierarchy`` 中执行。
    """
    names = names or {}
    groups: dict[frozenset, list[str]] = {}
    for code, members in boards.items():
        groups.setdefault(frozenset(members), []).append(code)

    canonical: dict[frozenset, str] = {}
    aliases: dict[str, list[str]] = {}
    for fset, codes in groups.items():
        if len(codes) == 1:
            canonical[fset] = codes[0]
            aliases[codes[0]] = []
        else:
            def _suffix_rank(c: str) -> int:
                nm = names.get(c, "")
                if nm.endswith("Ⅲ"):
                    return 3
                if nm.endswith("Ⅱ"):
                    return 2
                return 1

            canon = sorted(codes, key=_suffix_rank)[0]
            canonical[fset] = canon
            aliases[canon] = [c for c in codes if c != canon]

    parents: dict[str, str | None] = {}
    for code, members in boards.items():
        fset = frozenset(members)
        supersets = [
            other for other, om in boards.items()
            if other != code and frozenset(om) > fset
        ]
        parents[code] = (
            min(supersets, key=lambda o: len(boards[o])) if supersets else None
        )

    def _level(code: str, seen: set[str] | None = None) -> int:
        seen = seen or set()
        p = parents[code]
        if p is None or p in seen:
            return 1
        seen.add(code)
        return min(_level(p, seen) + 1, 3)

    out: dict[str, dict] = {}
    for code, members in boards.items():
        fset = frozenset(members)
        canon = canonical[fset]
        out[code] = {
            "level": _level(code),
            "parent": parents[code],
            "canonical_of": (aliases.get(canon, []) if code == canon else []),
            "canonical": code == canon,
        }
    return out


def validate_hierarchy(
    boards: dict[str, set[str]], hier: dict[str, dict]
) -> list[str]:
    """父板块成员集 == 子板块成员集之并 的交叉校验；返回 violation 文案列表。

    【实测】120/120 成立；失败只 warning 不中断。
    """
    warnings: list[str] = []
    children_of: dict[str, list[str]] = {}
    for code, info in hier.items():
        p = info.get("parent")
        if p:
            children_of.setdefault(p, []).append(code)
    for parent, children in children_of.items():
        union = set()
        for c in children:
            union |= boards.get(c, set())
        if union != boards.get(parent, set()):
            warnings.append(
                f"层级校验失败: {parent} 子集合并不等于父集 "
                f"(父{len(boards.get(parent,set()))} vs 子并{len(union)})"
            )
    return warnings


# ════════════════════════════════════════════════════════════════════════════
# 3) 等权指数合成（纯函数，P1.1 c）
# ════════════════════════════════════════════════════════════════════════════
def _align_window(wide: pd.DataFrame, min_valid: int = 4000, n_days: int = 320) -> pd.DataFrame:
    """按「每日有效 ≥ min_valid 只」裁 n_days 交易日（剔除早期残缺日）。

    【实测】union 365 天是假象，前 45 天每股数据残缺；对齐窗口须用每日有效 ≥4000 只。
    """
    valid_per_day = wide.notna().sum(axis=1)
    eligible = wide[valid_per_day >= min_valid]
    return eligible.iloc[-n_days:]


def build_equal_weight_index(member_prices: pd.DataFrame) -> pd.Series:
    """由个股收盘价宽表合成等权指数（本机合成，非行情软件板块指数）。

    算法（避坑全部来自【实测】）：
      1. valid = 上市前 NaN 不参与分母（``notna``）。
      2. 停牌沿用前收：``ffill`` 后停牌日收益 = 0。
      3. ret 用 valid 掩掉上市前，绝不 ``fillna(0)`` 后直接平均（否则假跳空）。
      4. daily_ret = ret.where(valid).mean(axis=1)（分母=当日有效成分股数，非固定分母）。
      5. idx = 1000 × cumprod(1 + daily_ret.dropna())。
    """
    wide = member_prices.astype(float)
    if wide.empty:
        return pd.Series(dtype=float)
    valid = wide.notna()
    wide_ff = wide.ffill()
    ret = wide_ff.pct_change()
    ret = ret.where(valid)
    daily_ret = ret.mean(axis=1, skipna=True)  # 分母=当日 valid 列数（NaN 自动排除）
    idx = 1000.0 * (1.0 + daily_ret.dropna()).cumprod()
    idx = idx.reindex(wide.index)
    return idx


# ════════════════════════════════════════════════════════════════════════════
# 4) RS 相对强度（纯函数，P1.1 d）
# ════════════════════════════════════════════════════════════════════════════
def _rs_norm(idx: pd.Series, bench: pd.Series) -> pd.Series:
    rs = idx / bench
    first = rs.first_valid_index()
    if first is None:
        return pd.Series(dtype=float, index=idx.index)
    base = rs.loc[first]
    if base == 0 or pd.isna(base):
        return pd.Series(dtype=float, index=idx.index)
    return rs / base * 100.0


def compute_rs_panel(
    boards_idx: dict[str, pd.Series],
    bench_all: pd.Series,
    levels: dict[str, int],
    ma: int = 20,
) -> dict[str, dict]:
    """主基准 = bench_all（等权 vs 等权，同口径）。

    返回 ``{code: {rs_norm, rs_above_ma20, rs_chg_20, rs_chg_60, rs_pctile, rs_pctile_delta_20}}``。
    rs_pctile 在同层级内算（L1 排 L1，L2 排 L2）；delta20 = 当前分位 − 20 日前分位
    （首次运行为 null，前端显示「留痕中」）。
    """
    rs_norm: dict[str, pd.Series] = {}
    for code, idx in boards_idx.items():
        rn = _rs_norm(idx, bench_all)
        if rn is not None and not rn.empty:
            rs_norm[code] = rn

    panel = pd.DataFrame(rs_norm)
    out: dict[str, dict] = {c: {} for c in rs_norm}
    for code, rn in rs_norm.items():
        ma20 = rn.rolling(ma).mean()
        above = (rn > ma20)
        chg20 = rn.pct_change(ma) * 100.0
        chg60 = rn.pct_change(60) * 100.0
        out[code] = {
            "rs_norm": rn,
            "rs_above_ma20": above,
            "rs_chg_20": chg20,
            "rs_chg_60": chg60,
        }

    # 同层级百分位排名
    for lvl in set(levels.values()):
        codes_lvl = [c for c in rs_norm if levels.get(c) == lvl]
        if not codes_lvl:
            continue
        sub = panel[codes_lvl]
        pct = sub.rank(axis=1, pct=True) * 100.0
        for c in codes_lvl:
            out[c]["rs_pctile"] = pct[c]
            out[c]["rs_pctile_delta_20"] = pct[c].diff(ma)

    # 兜底：未参与分位的板块给 null
    for c in out:
        out[c].setdefault("rs_pctile", pd.Series(dtype=float, index=panel.index))
        out[c].setdefault("rs_pctile_delta_20", pd.Series(dtype=float, index=panel.index))
    return out


# ════════════════════════════════════════════════════════════════════════════
# 5) 板块宽度（纯函数，P1.1 e）—— MA200 留痕中（红线 5）
# ════════════════════════════════════════════════════════════════════════════
def compute_breadth_series(member_prices: pd.DataFrame) -> dict[str, pd.Series]:
    """逐日 b20/b50（只用当日有效成分，分母同指数合成）。

    中期主看 b50。b200 在 320 日窗口内 MA200 只有 121 天【实测】，按红线 5 显式留痕中，
    由调用方置 null，绝不伪造。
    """
    wide = member_prices.astype(float)
    valid = wide.notna()
    wide_ff = wide.ffill()
    res: dict[str, pd.Series] = {}
    for w in (20, 50):
        ma = wide_ff.rolling(w).mean()
        above = (wide_ff > ma)
        # 分母=当日 valid 列数（仅统计有均线的有效成分）
        denom = (valid & ma.notna()).sum(axis=1)
        num = (above & valid & ma.notna()).sum(axis=1)
        res[f"b{w}"] = (num / denom.replace(0, np.nan) * 100.0)
    # nh60：收盘价 == 60 日滚动最高 的占比
    rollmax = wide_ff.rolling(60).max()
    nh = (wide_ff == rollmax) & valid
    res["nh60"] = (nh.sum(axis=1) / valid.sum(axis=1).replace(0, np.nan) * 100.0)
    return res


def compute_breadth_last(breadth: dict[str, pd.Series]) -> dict[str, float | None]:
    """取宽度序列最后一日值；b200 显式 null（留痕中）。"""
    out: dict[str, float | None] = {}
    for key in ("b20", "b50", "nh60"):
        s = breadth.get(key)
        if s is None or s.dropna().empty:
            out[key] = None
        else:
            v = s.iloc[-1]
            out[key] = None if pd.isna(v) else round(float(v), 2)
    out["b200"] = None  # 留痕中，绝不伪造（红线 5）
    return out


def breadth_divergence(
    idx: pd.Series, b50: pd.Series | None
) -> bool:
    """idx 创 60 日新高但 b50 < 其 60 日均值 → 宽度背离。"""
    if b50 is None or b50.dropna().empty:
        return False
    if len(idx) < 60 or len(b50) < 60:
        return False
    idx_high = idx.iloc[-1] >= idx.rolling(60).max().iloc[-1]
    b50_mean = b50.rolling(60).mean().iloc[-1]
    return bool(idx_high and (not pd.isna(b50_mean)) and b50.iloc[-1] < b50_mean)


# ════════════════════════════════════════════════════════════════════════════
# 6) 趋势读出（复用规则引擎 4 个轻入口，P1.1 f）
# ════════════════════════════════════════════════════════════════════════════
_SIGNS = {"sma60_slope", "sma120_slope", "ema20_slope"}


def _build_index_bars(close: pd.Series) -> pd.DataFrame:
    """补列：open=high=low=close + volume=0.0（compute_features 硬依赖 high/low/volume）。"""
    idx = close.index
    return pd.DataFrame(
        {
            "open": close.values,
            "high": close.values,
            "low": close.values,
            "close": close.values,
            "volume": 0.0,
        },
        index=idx,
    )


def read_trend_from_close(close: pd.Series, config: dict | None = None) -> dict:
    """用 4 个轻入口读出板块趋势状态（不跑 analyze_bars，避免退化事件）。"""
    if config is None:
        config = indicator_config()
    out: dict = {"provenance": "research_proxy"}
    if close is None or len(close) < _MIN_BARS_FOR_TREND:
        out.update(
            signal_color=None, signal_color_cn=None, ema20_slope_sign=None,
            sma60_slope_sign=None, sma120_slope_sign=None, ema20_slope_pct=None,
            long_trend_cn=None, macd_status=None, macd_label_cn=None,
            macd_detail_cn=None, macd_dimension=None, alignment_cn=None,
            color_rule_version=None, long_rule_version=None,
        )
        return out

    bars = _build_index_bars(close)
    frame = compute_features(bars, config)
    frame = classify_colors(frame)
    frame = compute_long_trend(frame)

    last = frame.iloc[-1]
    prev = frame.iloc[-2] if len(frame) > 1 else None
    macd = read_macd_strength(last, prev)

    out["signal_color"] = last.get("signal_color")
    out["signal_color_cn"] = _SIGNAL_COLOR_CN.get(
        last.get("signal_color"), last.get("signal_color")
    )
    out["color_rule_version"] = last.get("color_rule_version")
    out["long_rule_version"] = get_rule("long_trend").version

    def _sign(v):
        if v is None or pd.isna(v):
            return None
        return 1 if v > 0 else (-1 if v < 0 else 0)

    out["ema20_slope_sign"] = _sign(last.get("ema20_slope"))
    out["sma60_slope_sign"] = _sign(last.get("sma60_slope"))
    out["sma120_slope_sign"] = _sign(last.get("sma120_slope"))
    ema20 = last.get("ema20")
    ema20_slope = last.get("ema20_slope")
    out["ema20_slope_pct"] = (
        None if (ema20 is None or ema20_slope is None or pd.isna(ema20) or ema20 == 0)
        else round(float(ema20_slope) / float(ema20) * 100.0, 3)
    )

    lt = last.get("long_trend")
    out["long_trend_cn"] = LONG_TREND_CN.get(lt, lt)

    # 均线排列（研究代理补充维度，与 MACD 盲区补齐同义）
    sma20, sma60, sma120 = last.get("sma20"), last.get("sma60"), last.get("sma120")
    s60, s120 = out["sma60_slope_sign"], out["sma120_slope_sign"]
    if None not in (sma20, sma60, sma120, s60, s120):
        if sma20 > sma60 > sma120 and s60 > 0 and s120 > 0:
            out["alignment_cn"] = "多头排列"
        elif sma20 < sma60 < sma120 and s60 < 0 and s120 < 0:
            out["alignment_cn"] = "空头排列"
        else:
            out["alignment_cn"] = "均线纠结"
    else:
        out["alignment_cn"] = None

    if macd is not None:
        out["macd_status"] = macd.status
        out["macd_label_cn"] = macd.label_cn
        out["macd_detail_cn"] = macd.detail_cn
        out["macd_dimension"] = macd.dimension_value
    return out


# ════════════════════════════════════════════════════════════════════════════
# 7) 阶段判定 Stage（纯函数，标 research_proxy，P1.1 g）
# ════════════════════════════════════════════════════════════════════════════
def classify_stage(
    *,
    idx_close: pd.Series | None,
    sma60_series: pd.Series | None,
    sma60_slope_sign: int | None,
    ema20_slope_sign: int | None,
    rs_above_ma20: bool | None,
    breadth_divergence: bool,
    hit_count: int,
) -> tuple[str | None, list[str]]:
    """四阶段判定（顺序 ②→③→①→④）。阶段是合成结论，stage_basis 可追溯（红线级可审计）。"""
    if idx_close is None or sma60_series is None or hit_count < _MIN_HIT_FOR_INDEX:
        return None, ["样本不足（命中成分股 < 5 只）"]

    last_idx = float(idx_close.iloc[-1])
    last_sma60_v = sma60_series.iloc[-1]
    if pd.isna(last_sma60_v):
        return None, ["SMA60 尚不可用（样本不足）"]
    last_sma60 = float(last_sma60_v)
    basis: list[str] = []

    # ② 上升
    if last_idx > last_sma60 and (sma60_slope_sign or 0) > 0 and rs_above_ma20:
        basis = [
            f"价格({last_idx:.2f}) > SMA60({last_sma60:.2f})",
            "SMA60 斜率向上",
            "RS 强于等权基准（rs_above_ma20）",
        ]
        return "markup", basis

    # ③ 派发
    if last_idx > last_sma60 and (
        (sma60_slope_sign or 0) <= 0 or breadth_divergence
    ):
        basis = [f"价格({last_idx:.2f}) > SMA60({last_sma60:.2f})"]
        basis.append("SMA60 斜率走平/向下" if (sma60_slope_sign or 0) <= 0 else "宽度背离（价格新高但 b50 走弱）")
        return "distribution", basis

    # ① 筑底
    if rs_above_ma20 and (ema20_slope_sign or 0) >= 0:
        basis = [
            "RS 强于等权基准（rs_above_ma20）",
            "EMA20 斜率 ≥ 0（未转弱）" if (ema20_slope_sign or 0) >= 0 else "",
        ]
        basis = [b for b in basis if b]
        basis.append(f"价格 ≤ SMA60（{last_idx:.2f} vs {last_sma60:.2f}，未确立上升）")
        return "accumulation", basis

    # ④ 下降
    if last_idx < last_sma60 and (sma60_slope_sign or 0) < 0:
        basis = [
            f"价格({last_idx:.2f}) < SMA60({last_sma60:.2f})",
            "SMA60 斜率向下",
        ]
        return "decline", basis

    return None, ["未落入任一明确阶段（价格/均线/RS 组合中性）"]


# ════════════════════════════════════════════════════════════════════════════
# 7b) 道路层观察点（纯函数，research_proxy）
#     策略溯源：trading-spec-v1.md §2.2「均线运行方向是道路」——把 classify_stage
#     的阶段切换条件输出成「当前满足状态 + 差多少」，回答「下一观察点是什么」。
#     不新造条件、不新造参数，全部复用 classify_stage 的同一组输入（红线 4）。
# ════════════════════════════════════════════════════════════════════════════
def stage_checkpoints(
    *,
    stage: str | None,
    idx_close: pd.Series | None,
    sma60_series: pd.Series | None,
    sma60_slope_sign: int | None,
    ema20_slope_sign: int | None,
    rs_above_ma20: bool | None,
    breadth_divergence: bool,
    hit_count: int,
) -> dict:
    """返回 ``{dist_to_sma60_pct, conditions, next_watch, next_watch_kind}``。

    - conditions：道路确立（markup）三条件的满足清单，每条带中文与差距说明。
    - next_watch：一句话「下一观察点」，kind ∈ upgrade / risk / watch / None。
    - 样本不足 / SMA60 未成形 → conditions 空清单、next_watch=None（不可用不冒充）。
    """
    if (
        idx_close is None or sma60_series is None
        or hit_count < _MIN_HIT_FOR_INDEX
        or len(idx_close) == 0
        or sma60_series.dropna().empty
    ):
        return {
            "dist_to_sma60_pct": None,
            "conditions": [],
            "next_watch": None,
            "next_watch_kind": None,
        }

    last_idx = float(idx_close.iloc[-1])
    last_sma60 = float(sma60_series.iloc[-1])
    dist_pct = round((last_idx / last_sma60 - 1.0) * 100.0, 2)

    conditions = [
        {
            "key": "price_above_sma60",
            "label": "价格 > SMA60",
            "met": last_idx > last_sma60,
            "detail": f"{last_idx:.2f} vs SMA60 {last_sma60:.2f}（差 {dist_pct:+.2f}%）",
        },
        {
            "key": "sma60_slope_up",
            "label": "SMA60 斜率向上",
            "met": (sma60_slope_sign or 0) > 0,
            "detail": None if (sma60_slope_sign or 0) > 0 else "当前走平/向下",
        },
        {
            "key": "rs_above_ma20",
            "label": "RS 强于等权基准",
            "met": bool(rs_above_ma20),
            "detail": None if rs_above_ma20 else "相对强度在 MA20 下方",
        },
    ]
    unmet: list[str] = [str(c["label"]) for c in conditions if not c["met"]]

    next_watch: str | None = None
    kind: str | None = None
    if stage == "markup":
        if breadth_divergence:
            next_watch = "宽度背离已出现（价格新高但 b50 走弱）→ 警惕转入派发"
            kind = "risk"
        else:
            next_watch = f"跌破 SMA60（当前高出 {dist_pct:.2f}%）→ 道路转弱的第一信号"
            kind = "risk"
    elif stage == "accumulation":
        if unmet == ["价格 > SMA60"]:
            next_watch = (
                f"价格上穿 SMA60（还差 {abs(dist_pct):.2f}%）→ 升级为上升阶段"
                "（SMA60 斜率与 RS 已就绪）"
            )
        elif unmet:
            next_watch = f"待补齐：{'、'.join(unmet)} → 升级为上升阶段"
        else:  # 三条全满足但被判为筑底：不应发生（classify_stage 会判 markup），保守兜底
            next_watch = "三条件已满足，等待阶段重估"
        kind = "upgrade"
    elif stage == "distribution":
        if breadth_divergence:
            next_watch = (
                "SMA60 斜率转向上且宽度背离消除 → 修复为上升；跌破 SMA60 → 转入下降"
                f"（当前高出 {dist_pct:.2f}%）"
            )
        else:
            next_watch = (
                "SMA60 斜率转向上 → 修复为上升；跌破 SMA60 → 转入下降"
                f"（当前高出 {dist_pct:.2f}%）"
            )
        kind = "watch"
    elif stage == "decline":
        next_watch = "RS 重新强于等权基准且 EMA20 斜率转正 → 进入筑底观察"
        kind = "upgrade"
    elif stage is None and unmet:
        next_watch = f"未定阶段：待补齐 {'、'.join(unmet)} 后重估"
        kind = "watch"

    return {
        "dist_to_sma60_pct": dist_pct,
        "conditions": conditions,
        "next_watch": next_watch,
        "next_watch_kind": kind,
    }


# ════════════════════════════════════════════════════════════════════════════
# 7c) 资金流聚合 + 阶段交叉验证（纯函数，research_proxy）
#     定位：路牌/交叉验证层——只印证或矛盾，绝不参与阶段判定、不出买卖点。
#     口径：主力=超大单+大单、散户=中单+小单，为**单据规模代理**而非真实身份；
#     只用符号判定，不设金额阈值（不新造参数，红线 4）。
# ════════════════════════════════════════════════════════════════════════════
def aggregate_flows(points: list[dict] | None) -> dict:
    """由日级资金流点算 5/20/60 日累计主力与散户净流入（亿元）。

    窗口不足 N 个交易日 → 该窗口 None（不冒充）；散户 = 中单 + 小单，
    主力字段直接用东财 f52（= 超大 + 大单）。结构 struct 只看 20 日符号：
    main_in_retail_out（吸筹形态）/ main_out_retail_in（派发形态）/
    both_in（合力流入）/ both_out（合力流出）。
    """
    out: dict = {
        "flow_5d_main_yi": None, "flow_20d_main_yi": None, "flow_60d_main_yi": None,
        "flow_5d_retail_yi": None, "flow_20d_retail_yi": None, "flow_60d_retail_yi": None,
        "flow_20d_struct": None, "flow_note_cn": None,
    }
    if not points:
        return out

    def _sum(vals: list) -> float | None:
        clean = [v for v in vals if v is not None]
        if len(clean) < len(vals) or not clean:
            return None
        return round(sum(clean), 2)

    def _retail(p: dict) -> float | None:
        m, s = p.get("medium_yi"), p.get("small_yi")
        if m is None and s is None:
            return None
        return (m or 0) + (s or 0)

    for window in (5, 20, 60):
        if len(points) < window:
            continue
        tail = points[-window:]
        out[f"flow_{window}d_main_yi"] = _sum([p.get("main_yi") for p in tail])
        out[f"flow_{window}d_retail_yi"] = _sum([_retail(p) for p in tail])

    main20 = out["flow_20d_main_yi"]
    retail20 = out["flow_20d_retail_yi"]
    if main20 is not None and retail20 is not None:
        if main20 > 0 and retail20 < 0:
            out["flow_20d_struct"] = "main_in_retail_out"
            out["flow_note_cn"] = "吸筹形态（主力进·散户出）"
        elif main20 < 0 and retail20 > 0:
            out["flow_20d_struct"] = "main_out_retail_in"
            out["flow_note_cn"] = "派发形态（主力出·散户进）"
        elif main20 > 0 and retail20 > 0:
            out["flow_20d_struct"] = "both_in"
            out["flow_note_cn"] = "合力流入"
        else:
            out["flow_20d_struct"] = "both_out"
            out["flow_note_cn"] = "合力流出"
    return out


def flow_vs_stage(stage: str | None, flow_20d_main_yi: float | None) -> str | None:
    """主力 20 日净流入方向与阶段方向的交叉验证（只看符号）。

    返回 ``confirm``（资金印证）/ ``conflict``（资金矛盾）/ None。
    markup/accumulation 以主力流入为印证；distribution/decline 以流出为印证。
    """
    if stage is None or flow_20d_main_yi is None or flow_20d_main_yi == 0:
        return None
    inflow_confirms = stage in ("markup", "accumulation")
    if flow_20d_main_yi > 0:
        return "confirm" if inflow_confirms else "conflict"
    return "conflict" if inflow_confirms else "confirm"


_FLOW_VS_STAGE_CN = {"confirm": "资金印证", "conflict": "资金矛盾"}


# ════════════════════════════════════════════════════════════════════════════
# 8) 落盘产物（原子写，P1.1 h/i）
# ════════════════════════════════════════════════════════════════════════════
def _save_atomic(payload: dict | list, path: Path) -> None:
    """照抄 a_share_breadth._save_codes 的 tmp.replace(p) 原子写（红线 8）。

    ``list`` 用于逐日历史（sector_trend_history / sector_flow_history 均为数组）。
    """
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_name(path.name + ".tmp")
        tmp.write_text(json.dumps(payload, ensure_ascii=False, default=_json_default), encoding="utf-8")
        tmp.replace(path)
    except Exception as exc:  # noqa: BLE001
        logger.warning("原子写失败 %s: %s", path, exc)


def _json_default(o):
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return None if pd.isna(o) else float(o)
    if isinstance(o, (pd.Timestamp, datetime)):
        return str(o)
    if isinstance(o, float) and pd.isna(o):
        return None
    return str(o)


# ════════════════════════════════════════════════════════════════════════════
# 9) 编排：读 parquet → 纯函数计算 → 落盘（P1.1 全量）
# ════════════════════════════════════════════════════════════════════════════
def load_kline_wide() -> pd.DataFrame:
    """读 a_share_klines.parquet → symbol×date 收盘价宽表（index=date）。"""
    p = ROOT / "a_share_klines.parquet"
    if not p.exists():
        raise FileNotFoundError(f"K线缓存缺失: {p}（请先跑 precompute_a_share_ma.py）")
    df = pd.read_parquet(p)
    if "date" in df.columns and "symbol" in df.columns and "close" in df.columns:
        pass
    elif df.index.name == "symbol":
        df = df.reset_index()
    wide = df.pivot(index="date", columns="symbol", values="close")
    wide.index = pd.to_datetime(wide.index)
    return wide.sort_index()


def kline_symbols() -> set[str]:
    """返回 K线缓存中存在的 symbol 集合（仅读 symbol 列，零全量加载）。

    用于 /api/sectors/{code}/members 的 ``in_kline_cache`` 标记（离线安全）。
    parquet 缺失则返回空集。
    """
    p = ROOT / "a_share_klines.parquet"
    if not p.exists():
        return set()
    try:
        df = pd.read_parquet(p, columns=["symbol"])
        return set(df["symbol"].astype(str).tolist())
    except Exception as exc:  # noqa: BLE001
        logger.warning("读取 K线 symbol 列失败: %s", exc)
        return set()


def _load_bench_hs300() -> pd.Series | None:
    p = ROOT / "000300.SS.bars.parquet"
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p)
        col = "close" if "close" in df.columns else df.columns[0]
        s = df[col].astype(float)
        s.index = pd.to_datetime(df["date"] if "date" in df.columns else df.index)
        return s.sort_index()
    except Exception as exc:  # noqa: BLE001
        logger.warning("沪深300 基准读取失败: %s", exc)
        return None


def build_snapshot(
    members: dict[str, dict],
    wide: pd.DataFrame,
    daily_ref: dict[str, dict] | None = None,
    bench_hs300: pd.Series | None = None,
    flows: dict[str, list[dict]] | None = None,
    collect_series: bool = False,
) -> dict:
    """纯计算（不含网络）：由成员映射 + K线宽表产出当日全量快照。

    daily_ref: ``{code: {pct_change, pe_ttm, main_net_inflow_yi, up_count, down_count, total_mv_yi}}``
    来自 clist 当日快照（取数失败时可为 None，对应字段留 null）。
    flows: ``{code: [日级资金流点]}``（fetch_sector_flows 产出，失败/缺失时资金流字段留 null）。
    collect_series: True 时在快照挂 ``_series``（各板块 close/b50/rs_pctile 全量序列，
    供 backfill_history 用；调用方用完须 pop，不落盘）。
    """
    daily_ref = daily_ref or {}
    flows = flows or {}
    config = indicator_config()
    heat_cfg = retail_heat.heat_config()
    heat_raw: dict[str, float | None] = {}

    # 全A等权基准（与板块同口径：等权 vs 等权）
    wide_aligned = _align_window(wide)
    bench_all = build_equal_weight_index(wide_aligned)

    # 层级（去重）
    boards_set = {c: set(m["members"]) for c, m in members.items()}
    boards_names = {c: (m.get("name") or "") for c, m in members.items()}
    hier = classify_hierarchy(boards_set, boards_names)
    warnings = validate_hierarchy(boards_set, hier)

    # 只保留 canonical 板块（去重后 457，无重复行、无父子同榜）
    canonical_codes = [c for c, info in hier.items() if info["canonical"]]

    # 先建各板块指数
    boards_idx: dict[str, pd.Series] = {}
    boards_breadth: dict[str, dict] = {}
    boards_trend: dict[str, dict] = {}
    boards_stage_in: dict[str, tuple] = {}
    for code in canonical_codes:
        m = members[code]
        members_list = m["members"]
        hit = [s for s in members_list if s in wide_aligned.columns]
        hit_count = len(hit)
        if hit_count < _MIN_HIT_FOR_INDEX:
            boards_trend[code] = {"insufficient": True, "hit_count": hit_count}
            continue
        sub = wide_aligned[hit]
        idx = build_equal_weight_index(sub)
        if idx.dropna().empty:
            boards_trend[code] = {"insufficient": True, "hit_count": hit_count}
            continue
        boards_idx[code] = idx
        boards_breadth[code] = compute_breadth_series(sub)
        trend = read_trend_from_close(idx, config)
        boards_trend[code] = trend

    # RS 面板
    levels = {c: hier[c]["level"] for c in boards_idx}
    rs = compute_rs_panel(boards_idx, bench_all, levels)

    # 全量序列收集（backfill_history 用；不落快照）
    _series: dict[str, dict] = {}
    if collect_series:
        for code in boards_idx:
            _series[code] = {
                "close": boards_idx[code],
                "b50": (boards_breadth.get(code) or {}).get("b50"),
                "rs_pctile": (rs.get(code) or {}).get("rs_pctile"),
                "rs_pctile_delta_20": (rs.get(code) or {}).get("rs_pctile_delta_20"),
            }

    # 组装行
    rows: list[dict] = []
    for code in canonical_codes:
        info = hier[code]
        m = members[code]
        members_list = m["members"]
        hit = [s for s in members_list if s in wide_aligned.columns]
        hit_count = len(hit)
        ref = daily_ref.get(code, {})
        row: dict = {
            "code": code,
            "name": m.get("name"),
            "level": info["level"],
            "parent": info["parent"],
            "aliases": info["canonical_of"],
            "member_count": len(members_list),
            "hit_count": hit_count,
            "stage": None,
            "stage_basis": [],
            "dist_to_sma60_pct": None,
            "checkpoints": [],
            "next_watch": None,
            "next_watch_kind": None,
            "rs_pctile": None,
            "rs_pctile_delta_20": None,
            "rs_chg_20": None,
            "rs_chg_60": None,
            "rs_above_ma20": None,
            "b20": None,
            "b50": None,
            "b200": None,
            "nh60": None,
            "breadth_divergence": False,
            "signal_color": None,
            "signal_color_cn": None,
            "ema20_slope_pct": None,
            "long_trend_cn": None,
            "macd_status": None,
            "macd_label_cn": None,
            "macd_detail_cn": None,
            "macd_dimension": None,
            "alignment_cn": None,
            "close": None,
            "pct_change": ref.get("pct_change"),
            "pe_ttm": ref.get("pe_ttm"),
            "main_net_inflow_yi": ref.get("main_net_inflow_yi"),
            # 资金流（单据规模代理，research_proxy；抓取失败全 null）
            "flow_5d_main_yi": None,
            "flow_20d_main_yi": None,
            "flow_60d_main_yi": None,
            "flow_5d_retail_yi": None,
            "flow_20d_retail_yi": None,
            "flow_60d_retail_yi": None,
            "flow_20d_struct": None,
            "flow_note_cn": None,
            "flow_vs_stage": None,
            "flow_vs_stage_cn": None,
            # 散户热度（资金面路牌预警，research_proxy；口径与阈值见 rules.v2.yaml）
            "heat_value": None,
            "heat_pctile": None,
            "heat_hot": False,
            "heat_cold": False,
            "heat_warning": False,
            "heat_note_cn": None,
            "up_count": ref.get("up_count"),
            "down_count": ref.get("down_count"),
            "total_mv_yi": ref.get("total_mv_yi"),
            "provenance": "research_proxy",
        }

        if hit_count < _MIN_HIT_FOR_INDEX or code not in boards_idx:
            row["stage"] = None
            row["stage_basis"] = ["样本不足（命中成分股 < 5 只）"]
            row.update(**aggregate_flows(flows.get(code)))
            rows.append(row)
            continue

        idx = boards_idx[code]
        trend = boards_trend[code]
        breadth = compute_breadth_last(boards_breadth[code])
        b50_series = boards_breadth[code].get("b50")
        div = breadth_divergence(idx, b50_series)

        stage, basis = classify_stage(
            idx_close=idx,
            sma60_series=_sma60_from_close(idx, config),
            sma60_slope_sign=trend.get("sma60_slope_sign"),
            ema20_slope_sign=trend.get("ema20_slope_sign"),
            rs_above_ma20=(rs[code]["rs_above_ma20"].iloc[-1] if code in rs else None),
            breadth_divergence=div,
            hit_count=hit_count,
        )
        checkpoints = stage_checkpoints(
            stage=stage,
            idx_close=idx,
            sma60_series=_sma60_from_close(idx, config),
            sma60_slope_sign=trend.get("sma60_slope_sign"),
            ema20_slope_sign=trend.get("ema20_slope_sign"),
            rs_above_ma20=(rs[code]["rs_above_ma20"].iloc[-1] if code in rs else None),
            breadth_divergence=div,
            hit_count=hit_count,
        )
        row.update(
            stage=stage,
            stage_basis=basis,
            dist_to_sma60_pct=checkpoints["dist_to_sma60_pct"],
            checkpoints=checkpoints["conditions"],
            next_watch=checkpoints["next_watch"],
            next_watch_kind=checkpoints["next_watch_kind"],
            b20=breadth["b20"],
            b50=breadth["b50"],
            b200=breadth["b200"],
            nh60=breadth["nh60"],
            breadth_divergence=div,
            signal_color=trend.get("signal_color"),
            signal_color_cn=trend.get("signal_color_cn"),
            ema20_slope_pct=trend.get("ema20_slope_pct"),
            long_trend_cn=trend.get("long_trend_cn"),
            macd_status=trend.get("macd_status"),
            macd_label_cn=trend.get("macd_label_cn"),
            macd_detail_cn=trend.get("macd_detail_cn"),
            macd_dimension=trend.get("macd_dimension"),
            alignment_cn=trend.get("alignment_cn"),
            close=_round_last(idx),
        )
        r = rs.get(code, {})
        row["rs_above_ma20"] = _last(r.get("rs_above_ma20"))
        row["rs_chg_20"] = _round(_last(r.get("rs_chg_20")))
        row["rs_chg_60"] = _round(_last(r.get("rs_chg_60")))
        row["rs_pctile"] = _round(_last(r.get("rs_pctile")))
        row["rs_pctile_delta_20"] = _round(_last(r.get("rs_pctile_delta_20")))

        # 资金流聚合 + 阶段交叉验证（缺数保持 null，不冒充）
        agg = aggregate_flows(flows.get(code))
        row.update(**agg)
        vs = flow_vs_stage(stage, agg["flow_20d_main_yi"])
        row["flow_vs_stage"] = vs
        row["flow_vs_stage_cn"] = _FLOW_VS_STAGE_CN.get(vs) if vs else None

        # 散户热度口径值（横截面分位在全部行组装后统一算）
        hv = retail_heat.window_metric(
            flows.get(code), boards_idx.get(code), ref.get("total_mv_yi"),
            metric=heat_cfg["metric"], window=heat_cfg["window_days"],
        )
        row["heat_value"] = hv
        heat_raw[code] = hv
        rows.append(row)

    # 散户热度横截面分位 + 情境化警示
    # 排名池按 rules.v2.yaml pctile_pool（l1_l2）：L3 细分不进池但按池定位显示
    heat_vals = [v for v in heat_raw.values() if v is not None]
    heat_pool = retail_heat.heat_pool_values(rows, heat_cfg.get("pctile_pool", "l1_l2"))
    for row in rows:
        pct = retail_heat.cross_section_pctile(row.get("heat_value"), heat_pool)
        state = retail_heat.heat_state(pct, row.get("stage"), heat_cfg)
        row["heat_pctile"] = pct
        row["heat_hot"] = state["hot"]
        row["heat_cold"] = state["cold"]
        row["heat_warning"] = state["warning"]
        row["heat_note_cn"] = state["note_cn"]

    as_of = datetime.now().strftime("%Y-%m-%d %H:%M")
    trading_day = wide_aligned.index[-1].strftime("%Y-%m-%d") if not wide_aligned.empty else as_of
    snapshot = {
        "as_of": as_of,
        "date": trading_day,
        "trading_day": trading_day,
        "generated_at": as_of,
        "bench": {
            "all_equal_close": _round_last(bench_all),
            "hs300_close": _round_last(bench_hs300) if bench_hs300 is not None else None,
        },
        "heat": {
            "metric": heat_cfg["metric"],
            "metric_label_cn": retail_heat.METRIC_LABELS.get(heat_cfg["metric"]),
            "window_days": heat_cfg["window_days"],
            "pctile_pool": heat_cfg.get("pctile_pool", "l1_l2"),
            "hot_pctile": heat_cfg["hot_pctile"],
            "cold_pctile": heat_cfg.get("cold_pctile"),
            "warn_stages": list(heat_cfg["warn_stages"]),
            "rule_version": heat_cfg["version"],
            "n_valid": len(heat_vals),
            "n_pool": len(heat_pool),
            "note_cn": (
                "资金面路牌预警（research_proxy）：东财五档零和，散户净流入≡主力净流出，"
                "热度取小单−超大单分化；排名池为一、二级行业（L3 按池定位不上榜）；"
                "只标注、不构成买卖点。"
            ),
        },
        "boards": rows,
        "warnings": warnings,
        "errors": [],
        "research_proxy_note": (
            "板块趋势判定为研究代理（research_proxy）：等权指数为本机合成（非行情软件板块指数），"
            "以当前成分回溯含前视偏差（仅形态参考），不含北交所；MA200 留痕中。"
            "资金流「主力=超大单+大单、散户=中单+小单」为单据规模代理而非真实机构/散户身份，"
            "只作阶段交叉验证，不参与判定、不构成买卖建议。"
        ),
    }
    if collect_series:
        snapshot["_series"] = _series
    return snapshot


# ════════════════════════════════════════════════════════════════════════════
# 8b) 历史回填：由当前 320 日窗口一次性补齐 sector_trend_history.json
#     口径与快照声明一致：以当前成分回溯（含前视偏差，仅形态参考）。
#     已有的逐日实录优先（同日不覆盖）——实录是 point-in-time 真值。
# ════════════════════════════════════════════════════════════════════════════
def backfill_history(
    series_by_code: dict[str, dict], *, limit_days: int = 250
) -> dict:
    """用全量序列补历史缺失日期，返回 ``{"added": 新增天数, "total": 总天数}``。"""
    hist: list[dict] = []
    p = _history_path()
    if p.exists():
        try:
            loaded = json.loads(p.read_text(encoding="utf-8"))
            hist = loaded if isinstance(loaded, list) else []
        except Exception:  # noqa: BLE001 - 损坏按空处理
            hist = []
    existing_dates = {rec.get("date") for rec in hist}

    # 日期全集 = 各板块 close 序列索引的并集（升序）
    all_dates: set[pd.Timestamp] = set()
    for s in series_by_code.values():
        close = s.get("close")
        if close is not None:
            all_dates.update(close.index)
    new_dates = sorted(d for d in all_dates if d.strftime("%Y-%m-%d") not in existing_dates)
    new_dates = new_dates[-limit_days:]

    def _v(series, ts) -> float | None:
        if series is None:
            return None
        try:
            v = series.loc[ts]
        except KeyError:
            return None
        return None if pd.isna(v) else round(float(v), 2)

    for ts in new_dates:
        dstr = ts.strftime("%Y-%m-%d")
        boards_rec: dict[str, dict] = {}
        for code, s in series_by_code.items():
            boards_rec[code] = {
                "stage": None,  # 历史阶段需逐日重算，回填只补形态序列
                "rs_pctile": _v(s.get("rs_pctile"), ts),
                "rs_pctile_delta_20": _v(s.get("rs_pctile_delta_20"), ts),
                "b50": _v(s.get("b50"), ts),
                "close": _v(s.get("close"), ts),
            }
        hist.append({"date": dstr, "boards": boards_rec})
    hist.sort(key=lambda r: r.get("date", ""))
    _save_atomic(hist, p)
    return {"added": len(new_dates), "total": len(hist)}


def _sma60_from_close(close: pd.Series, config: dict) -> pd.Series:
    """板块指数自身的 SMA60（阶段判定用 idx vs sma60）。"""
    return close.rolling(60, min_periods=60).mean()


def _last(s):
    if s is None:
        return None
    if isinstance(s, pd.Series):
        if s.dropna().empty:
            return None
        return s.iloc[-1]
    return s


def _round(v, n=2):
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return None
    try:
        return round(float(v), n)
    except (TypeError, ValueError):
        return None


def _round_last(s, n=2):
    v = _last(s)
    return _round(v, n)


def run_sector_trend(
    *,
    limit: int | None = None,
    no_save: bool = False,
    force: bool = False,
    backfill: bool = False,
) -> dict:
    """端到端：成分股 → 读 parquet → 计算 → 原子写三份 json。

    返回快照 dict。取数失败抛异常（CLI 据此返回码 1）。
    ``backfill=True`` 额外把 320 日窗口的 close/b50/RS 分位序列一次性回填进
    ``sector_trend_history.json``（已有逐日实录优先，同日不覆盖）。
    """
    t0 = time.time()
    logger.info("▶ 拉取板块成分股映射…")
    members = fetch_sector_members(force=force)
    if limit:
        members = dict(list(members.items())[:limit])
    logger.info("  板块数 %d", len(members))

    logger.info("▶ 读取全A K线宽表…")
    wide = load_kline_wide()

    # 当日 clist 快照（涨跌/PE/主力净流入/涨跌家数）——取数失败降级为 null
    daily_ref: dict[str, dict] = {}
    try:
        boards = fetch_sector_boards()
        for b in boards:
            daily_ref[b["code"]] = {
                "pct_change": b.get("pct_change"),
                "pe_ttm": b.get("pe_ttm"),
                "main_net_inflow_yi": b.get("main_net_inflow_yi"),
                "up_count": b.get("up_count"),
                "down_count": b.get("down_count"),
                "total_mv_yi": b.get("total_mv_yi"),
            }
    except Exception as exc:  # noqa: BLE001
        logger.warning("板块当日快照拉取失败（字段留 null）: %s", exc)

    bench_hs300 = _load_bench_hs300()

    # 板块资金流日史（单据规模代理；整体失败降级 null，不阻断快照）
    flows: dict[str, list[dict]] = {}
    try:
        logger.info("▶ 拉取板块资金流日史…")
        flows = fetch_sector_flows(list(members.keys()))
        logger.info("  资金流命中 %d/%d 板块", sum(1 for v in flows.values() if v), len(flows))
    except Exception as exc:  # noqa: BLE001 - 整体失败不阻断主快照
        logger.warning("板块资金流整体拉取失败（字段留 null）: %s", exc)

    snapshot = build_snapshot(
        members, wide, daily_ref, bench_hs300, flows, collect_series=backfill
    )
    series = snapshot.pop("_series", None)  # 挂载序列永不落盘

    if not no_save:
        _save_atomic(snapshot, _snapshot_path())
        _append_history(snapshot)
        # 成分股映射也确保落盘（fetch 已落，这里幂等补一次以防 limit 调试未落）
        if not limit:
            _save_atomic(
                {"as_of": snapshot["as_of"], "date": snapshot["date"], "boards": members},
                _members_path(),
            )
        logger.info("✓ 已落盘 sector_trend_snapshot.json + sector_trend_history.json")
        if backfill and series is not None:
            stats = backfill_history(series)
            logger.info(
                "✓ 历史回填完成：新增 %d 天（含前视偏差，仅形态参考），历史共 %d 天",
                stats["added"], stats["total"],
            )

    logger.info("⏱ 耗时 %.1fs", time.time() - t0)
    return snapshot


def _append_history(snapshot: dict) -> None:
    """逐日追加历史（同日覆盖再 append）。对照 append_ma_breadth_history 语义，
    但 today 用 trading_day 修正。"""
    p = _history_path()
    today = snapshot.get("trading_day") or snapshot.get("date")
    rec_boards: dict[str, dict] = {}
    for row in snapshot.get("boards", []):
        rec_boards[row["code"]] = {
            "stage": row.get("stage"),
            "rs_pctile": row.get("rs_pctile"),
            "rs_pctile_delta_20": row.get("rs_pctile_delta_20"),
            "b50": row.get("b50"),
            "close": row.get("close"),
        }
    rec = {"date": today, "boards": rec_boards}
    hist: list[dict] = []
    try:
        if p.exists():
            hist = json.loads(p.read_text(encoding="utf-8"))
            if not isinstance(hist, list):
                hist = []
    except Exception:  # noqa: BLE001
        hist = []
    hist = [h for h in hist if h.get("date") != today]
    hist.append(rec)
    hist.sort(key=lambda h: h.get("date", ""))
    _save_atomic(hist, p)


# ── 读盘（API 层用）─────────────────────────────────────────────────────────
def load_snapshot() -> dict | None:
    p = _snapshot_path()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def load_history(limit_days: int = 250) -> list[dict]:
    p = _history_path()
    if not p.exists():
        return []
    try:
        hist = json.loads(p.read_text(encoding="utf-8"))
        if not isinstance(hist, list):
            return []
        return hist[-limit_days:]
    except Exception:  # noqa: BLE001
        return []


def load_members_cache() -> dict | None:
    p = _members_path()
    if not p.exists():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


__all__ = [
    "_prefix",
    "aggregate_flows",
    "build_equal_weight_index",
    "breadth_divergence",
    "classify_hierarchy",
    "classify_stage",
    "compute_breadth_last",
    "compute_breadth_series",
    "compute_rs_panel",
    "fetch_sector_boards",
    "fetch_sector_flows",
    "fetch_sector_members",
    "flow_vs_stage",
    "load_flow_history",
    "load_history",
    "load_kline_wide",
    "load_members_cache",
    "load_snapshot",
    "run_sector_trend",
    "stage_checkpoints",
    "validate_hierarchy",
]
