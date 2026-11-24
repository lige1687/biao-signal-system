"""防穿透样本外锁箱（HoldoutVault）、Purged Walk-Forward 滚动切分、市场体制切片与过拟合体检。

解决旧 `strategy_lab` 三大验证痛点：
1. `--unlock-holdout` 可无限重复解锁看同一份 2024+ 闭卷考并调参，失去真正样本外意义；
2. 单一静态二分（<=2023 熊市 vs >=2024 牛市）容易把体制差异误当成泛化能力；
3. 缺少考虑序列自相关与累计试错次数的统计显著性与过拟合折损警示（HAC / Block Bootstrap / DSR）。
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
from typing import Literal
import numpy as np
import pandas as pd
from scipy import stats

from .data_portal import HOLDOUT_START


@dataclass(frozen=True)
class WalkForwardFold:
    fold_id: int
    train_start: str
    train_end: str
    purge_end: str
    test_start: str
    test_end: str
    n_train_days: int
    n_test_days: int


def build_purged_walk_forward_folds(
    dates: pd.DatetimeIndex,
    *,
    train_min_days: int = 504,
    test_days: int = 252,
    purge_days: int = 20,
    expanding: bool = True,
    max_train_days: int = 1260,
) -> list[WalkForwardFold]:
    """构造严格时间序的 Purged Walk-Forward 滚动切分，训练与测试之间强制留出 purge_days 防止标签跨界泄漏。"""
    idx = pd.DatetimeIndex(sorted(pd.to_datetime(dates).unique()))
    n = len(idx)
    if n < train_min_days + purge_days + max(40, test_days // 3):
        return []

    folds: list[WalkForwardFold] = []
    train_end_pos = train_min_days - 1
    fold_id = 1
    while True:
        test_start_pos = train_end_pos + purge_days + 1
        if test_start_pos >= n:
            break
        test_end_pos = min(n - 1, test_start_pos + test_days - 1)
        if (test_end_pos - test_start_pos + 1) < max(30, test_days // 4):
            break
        train_start_pos = 0 if expanding else max(0, train_end_pos - max_train_days + 1)
        purge_end_pos = min(n - 1, train_end_pos + purge_days)
        folds.append(
            WalkForwardFold(
                fold_id=fold_id,
                train_start=str(idx[train_start_pos].date()),
                train_end=str(idx[train_end_pos].date()),
                purge_end=str(idx[purge_end_pos].date()),
                test_start=str(idx[test_start_pos].date()),
                test_end=str(idx[test_end_pos].date()),
                n_train_days=int(train_end_pos - train_start_pos + 1),
                n_test_days=int(test_end_pos - test_start_pos + 1),
            )
        )
        fold_id += 1
        train_end_pos = test_end_pos
    return folds


def classify_market_regimes(bench_close: pd.Series) -> pd.Series:
    """严格因果（仅使用截至当日行情）把交易日划分为四类大白话市场体制。

    - 单边上升牛：近半年趋势向上且站稳60日均线，未处于大幅回撤
    - 阴跌下行熊：近半年趋势向下且处于60日均线下方，距半年高点回撤超10%
    - 急涨急跌剧震：近20日年化波动率显著高于过去一年中枢（>= 1.35 倍）或单月振幅极端
    - 温和横盘震荡：其余状态
    """
    c = bench_close.astype(float).sort_index()
    ma60 = c.rolling(60, min_periods=40).mean()
    ret120 = c / c.shift(120) - 1.0
    hi120 = c.rolling(120, min_periods=40).max()
    dd120 = c / hi120 - 1.0
    daily_r = c.pct_change()
    vol20 = daily_r.rolling(20, min_periods=15).std()
    vol252_med = vol20.rolling(252, min_periods=60).median()

    labels = pd.Series("温和横盘震荡", index=c.index, dtype="object")
    high_vol = (vol20 > vol252_med * 1.35) & vol252_med.notna()
    bull = (c > ma60) & (ret120 >= 0.08) & (dd120 > -0.10)
    bear = (c < ma60) & ((ret120 <= -0.06) | (dd120 <= -0.12))

    labels.loc[bull] = "单边上升牛"
    labels.loc[bear] = "阴跌下行熊"
    # 极端高波剧震覆盖震荡与弱趋势，单列压测
    labels.loc[high_vol & (~bull | (dd120 <= -0.08))] = "急涨急跌剧震"
    return labels


def _slice_stats(strat_r: pd.Series, bench_r: pd.Series | None = None) -> dict[str, object]:
    n = len(strat_r)
    if n < 5:
        return {"days": int(n), "total_return": 0.0, "cagr": 0.0, "max_drawdown": 0.0, "excess_return": 0.0, "sharpe": 0.0}
    nav = (1.0 + strat_r).cumprod()
    tot = float(nav.iloc[-1] - 1.0)
    years = max(n / 252.0, 1.0 / 12.0)
    cagr = float(nav.iloc[-1] ** (1.0 / years) - 1.0) if nav.iloc[-1] > 0 else -1.0
    mdd = float((nav / nav.cummax() - 1.0).min())
    sd = float(strat_r.std(ddof=1))
    sharpe = float((strat_r.mean() / sd) * math.sqrt(252.0)) if sd > 1e-12 else 0.0
    excess = 0.0
    if bench_r is not None and len(bench_r) == n:
        b_nav = (1.0 + bench_r).cumprod()
        excess = float(nav.iloc[-1] / b_nav.iloc[-1] - 1.0) if b_nav.iloc[-1] > 0 else 0.0
    return {
        "days": int(n),
        "total_return": round(tot, 4),
        "cagr": round(cagr, 4),
        "max_drawdown": round(mdd, 4),
        "excess_return": round(excess, 4),
        "sharpe": round(sharpe, 2),
    }


def slice_performance_by_year_and_regime(
    daily_returns: pd.Series,
    bench_close: pd.Series,
) -> dict[str, list[dict[str, object]]]:
    """按自然年与纯因果市场体制双维度拆解策略表现，杜绝全期均值掩盖单年押宝或熊市失血。"""
    sr = daily_returns.astype(float).dropna().sort_index()
    bc = bench_close.astype(float).dropna().sort_index()
    br = bc.pct_change().reindex(sr.index).fillna(0.0)
    regimes = classify_market_regimes(bc).reindex(sr.index).ffill().fillna("温和横盘震荡")

    yearly: list[dict[str, object]] = []
    for yr, grp in sr.groupby(sr.index.year):
        st = _slice_stats(grp, br.reindex(grp.index))
        yearly.append({"year": int(yr), **st})

    by_regime: list[dict[str, object]] = []
    for reg in ("单边上升牛", "阴跌下行熊", "急涨急跌剧震", "温和横盘震荡"):
        mask = regimes == reg
        if int(mask.sum()) < 5:
            continue
        st = _slice_stats(sr.loc[mask], br.loc[mask])
        by_regime.append({"regime": reg, **st})

    return {"by_year": yearly, "by_regime": by_regime}


def newey_west_tstat(series: np.ndarray | pd.Series, *, nlags: int | None = None) -> dict[str, float]:
    """计算考虑自相关与异方差（Newey-West HAC / Bartlett核）的均值 t 统计量。"""
    x = np.asarray(series, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 10:
        return {"n": float(n), "mean": 0.0, "hac_se": 0.0, "t_stat": 0.0, "p_value": 1.0}
    mu = float(np.mean(x))
    e = x - mu
    lags = int(nlags) if nlags is not None else max(1, int(math.floor(4.0 * ((n / 100.0) ** (2.0 / 9.0)))))
    lags = min(lags, n - 2)
    gamma0 = float(np.dot(e, e) / n)
    var = gamma0
    for k in range(1, lags + 1):
        w = 1.0 - k / (lags + 1.0)
        cov = float(np.dot(e[k:], e[:-k]) / n)
        var += 2.0 * w * cov
    var = max(var, 1e-18)
    hac_se = math.sqrt(var / n)
    t_stat = mu / hac_se if hac_se > 0 else 0.0
    p_val = float(2.0 * (1.0 - stats.norm.cdf(abs(t_stat))))
    return {
        "n": float(n),
        "mean": round(mu, 6),
        "hac_se": round(hac_se, 6),
        "t_stat": round(t_stat, 3),
        "p_value": round(p_val, 4),
    }


def block_bootstrap_ci(
    daily_returns: np.ndarray | pd.Series,
    *,
    block_len: int = 20,
    n_boot: int = 400,
    seed: int = 42,
) -> dict[str, float]:
    """循环移动块自助法（Moving Block Bootstrap），保留相邻交易日相关性，估计年化收益与夏普 95% 区间。"""
    x = np.asarray(daily_returns, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < max(30, block_len + 5):
        return {
            "ann_return_ci_low": 0.0,
            "ann_return_ci_high": 0.0,
            "sharpe_ci_low": 0.0,
            "sharpe_ci_high": 0.0,
            "prob_positive": 0.5,
        }
    rng = np.random.default_rng(seed)
    n_blocks = int(math.ceil(n / block_len))
    ann_means = np.empty(n_boot, dtype=float)
    sharpes = np.empty(n_boot, dtype=float)
    offsets = np.arange(block_len)

    for b in range(n_boot):
        starts = rng.integers(0, n, size=n_blocks)
        idx = ((starts[:, None] + offsets) % n).ravel()[:n]
        sample = x[idx]
        m = float(sample.mean())
        s = float(sample.std(ddof=1))
        ann_means[b] = m * 252.0
        sharpes[b] = (m / s) * math.sqrt(252.0) if s > 1e-12 else 0.0

    return {
        "ann_return_ci_low": round(float(np.percentile(ann_means, 2.5)), 4),
        "ann_return_ci_high": round(float(np.percentile(ann_means, 97.5)), 4),
        "sharpe_ci_low": round(float(np.percentile(sharpes, 2.5)), 2),
        "sharpe_ci_high": round(float(np.percentile(sharpes, 97.5)), 2),
        "prob_positive": round(float(np.mean(ann_means > 0.0)), 3),
    }


def deflated_sharpe_probability(daily_returns: np.ndarray | pd.Series, n_trials: int = 1) -> float:
    """近似计算 Deflated Sharpe Ratio 概率（Bailey & López de Prado），显式惩罚反复试错次数与尖峰厚尾。"""
    x = np.asarray(daily_returns, dtype=float)
    x = x[np.isfinite(x)]
    n = len(x)
    if n < 30:
        return 0.5
    sd = float(np.std(x, ddof=1))
    if sd <= 1e-12:
        return 0.5
    sr = float(np.mean(x) / sd)  # 日频非年化 Sharpe
    skew = float(stats.skew(x, bias=False)) if n > 3 else 0.0
    kurt = float(stats.kurtosis(x, fisher=False, bias=False)) if n > 4 else 3.0  # 普通峰度(正态=3)

    trials = max(1, int(n_trials))
    if trials == 1:
        sr_star = 0.0
    else:
        euler_gamma = 0.5772156649
        z1 = float(stats.norm.ppf(1.0 - 1.0 / trials))
        z2 = float(stats.norm.ppf(1.0 - 1.0 / (trials * math.e)))
        # 假设独立候选池日频 Sharpe 标准差约 0.04（对应年化约 0.63）
        sr_star = 0.04 * ((1.0 - euler_gamma) * z1 + euler_gamma * z2)

    denom_sq = max(1e-8, 1.0 - skew * sr + ((kurt - 1.0) / 4.0) * (sr ** 2))
    z_val = ((sr - sr_star) * math.sqrt(max(1, n - 1))) / math.sqrt(denom_sq)
    return round(float(stats.norm.cdf(z_val)), 4)


def overfitting_risk_audit(
    daily_returns: pd.Series,
    *,
    bench_returns: pd.Series | None = None,
    n_trials: int = 1,
    block_len: int = 20,
    n_boot: int = 400,
    seed: int = 42,
) -> dict[str, object]:
    """综合 HAC 检验、块自助法置信区间与多次试错折损（DSR），给出大白话过拟合风险体检。"""
    sr = daily_returns.astype(float).dropna()
    target = (sr - bench_returns.reindex(sr.index).fillna(0.0)) if bench_returns is not None else sr
    hac = newey_west_tstat(target)
    boot = block_bootstrap_ci(target, block_len=block_len, n_boot=n_boot, seed=seed)
    dsr_prob = deflated_sharpe_probability(target, n_trials=n_trials)

    if dsr_prob >= 0.90 and boot["ann_return_ci_low"] > 0.0 and hac["t_stat"] >= 1.96:
        risk_light = "🟢 统计稳健（扣除试错折损后仍显著为正）"
    elif dsr_prob >= 0.70 and boot["prob_positive"] >= 0.80:
        risk_light = "🟡 中等把握（方向偏正但受样本长度或试错次数影响，需前向跟踪确认）"
    else:
        risk_light = "🔴 高过拟合/偶然性风险（扣除序列自相关与反复试错后，把握度不足）"

    return {
        "n_days": int(len(target)),
        "n_trials_penalized": int(max(1, n_trials)),
        "hac_t_stat": hac["t_stat"],
        "hac_p_value": hac["p_value"],
        "bootstrap_ann_excess_ci": [boot["ann_return_ci_low"], boot["ann_return_ci_high"]],
        "bootstrap_sharpe_ci": [boot["sharpe_ci_low"], boot["sharpe_ci_high"]],
        "bootstrap_prob_positive": boot["prob_positive"],
        "deflated_sharpe_prob": dsr_prob,
        "risk_light": risk_light,
    }


class HoldoutVault:
    """单次消耗闭卷考锁箱：防止同一策略家族反复解锁 2024+ holdout 调参导致样本外失效。"""

    def __init__(self, lab_home: Path) -> None:
        self.ledger_dir = Path(lab_home) / "strategy_lab_ledger"
        self.seals_path = self.ledger_dir / "holdout_seals.json"
        self.attempts_path = self.ledger_dir / "attempts.jsonl"

    def _load_seals(self) -> dict[str, dict]:
        if not self.seals_path.exists():
            return {}
        try:
            data = json.loads(self.seals_path.read_text(encoding="utf-8"))
            return data if isinstance(data, dict) else {}
        except Exception:
            return {}

    def _save_seals(self, data: dict[str, dict]) -> None:
        self.ledger_dir.mkdir(parents=True, exist_ok=True)
        self.seals_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def count_family_trials(self, family: str) -> dict[str, int]:
        """从历史 attempts.jsonl 统计该策略家族的探索期试错与闭卷考解锁次数。"""
        explore_cnt = 0
        holdout_cnt = 0
        if self.attempts_path.exists():
            for line in self.attempts_path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    rec = json.loads(line)
                except Exception:
                    continue
                act = str(rec.get("action") or "")
                if act == family or rec.get("family") == family:
                    if rec.get("split") == "holdout":
                        holdout_cnt += 1
                    elif rec.get("split") == "explore":
                        explore_cnt += 1
        return {"explore_trials": explore_cnt, "historical_holdout_opens": holdout_cnt}

    def check_or_consume(
        self,
        family: str,
        *,
        rule_fingerprint: str,
        holdout_window: str = f"{HOLDOUT_START}~",
        allow_repeek_as_explore: bool = False,
    ) -> dict[str, object]:
        """校验或首次消费某个策略家族的闭卷考锁箱。

        - 首次开封：状态 `virgin_holdout_consumed`，正式记为未见闭卷考并立即封存；
        - 再次开封且未声明降级：返回 `blocked=True`（防止暗箱反复看答案改规则）；
        - 再次开封且显式 `allow_repeek_as_explore=True`：放行但永久打标 `downgraded_to_explore_seen`，不再宣称样本外！
        """
        seals = self._load_seals()
        key = f"{family}::{holdout_window}"
        trial_stats = self.count_family_trials(family)
        now_iso = datetime.now(timezone.utc).isoformat()
        existing = seals.get(key)

        if existing is None:
            # 若历史 attempts.jsonl 里已有旧 holdout 记录，诚实继承其已查看事实
            already_seen_legacy = trial_stats["historical_holdout_opens"] > 0
            status: Literal["virgin_holdout_consumed", "downgraded_to_explore_seen"] = (
                "downgraded_to_explore_seen" if already_seen_legacy else "virgin_holdout_consumed"
            )
            seals[key] = {
                "family": family,
                "holdout_window": holdout_window,
                "first_opened_at": now_iso,
                "open_count": trial_stats["historical_holdout_opens"] + 1,
                "first_fingerprint": rule_fingerprint,
                "last_fingerprint": rule_fingerprint,
                "status": status,
            }
            self._save_seals(seals)
            return {
                "allowed": True,
                "blocked": False,
                "status": status,
                "open_count": seals[key]["open_count"],
                "explore_trials": trial_stats["explore_trials"],
                "warning_cn": (
                    "⚠️ 历史台账显示该策略家族曾解锁过本闭卷考区间，本次结果已诚实降级标记为【已看历史探索】。"
                    if already_seen_legacy
                    else "✅ 首次开封未见闭卷考，锁箱已自动标记消耗（后续再次查看将降级为探索参考）。"
                ),
            }

        if not allow_repeek_as_explore:
            return {
                "allowed": False,
                "blocked": True,
                "status": "holdout_already_consumed",
                "open_count": int(existing.get("open_count", 1)),
                "explore_trials": trial_stats["explore_trials"],
                "first_opened_at": existing.get("first_opened_at"),
                "warning_cn": (
                    f"🛑 闭卷考锁箱已于 {existing.get('first_opened_at')} 被【{family}】消耗（累计打开 {existing.get('open_count', 1)} 次）。"
                    "为防止反复偷看答案调参，默认拒绝再次解锁；若仅作复盘参考，请显式传入 --allow-repeek（结果将强制标为已看历史）。"
                ),
            }

        existing["open_count"] = int(existing.get("open_count", 1)) + 1
        existing["last_opened_at"] = now_iso
        existing["last_fingerprint"] = rule_fingerprint
        existing["status"] = "downgraded_to_explore_seen"
        seals[key] = existing
        self._save_seals(seals)
        return {
            "allowed": True,
            "blocked": False,
            "status": "downgraded_to_explore_seen",
            "open_count": existing["open_count"],
            "explore_trials": trial_stats["explore_trials"],
            "warning_cn": (
                f"⚠️ 已显式复看已消耗锁箱（第 {existing['open_count']} 次），本次结果严格降级为【已看历史探索】，严禁当作全新样本外验收！"
            ),
        }

    @staticmethod
    def fingerprint_rules(payload: dict | str) -> str:
        raw = payload if isinstance(payload, str) else json.dumps(payload, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:16]
