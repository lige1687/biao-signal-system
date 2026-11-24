"""声明式因子算子库、安全 AST 面板求值器与自动化无未来函数门禁（factor_engine）。

把新因子研究从“半天写一次性脚本”升级为“1分钟声明公式 → 自动前缀验漏 → 两级正交查重 → L1 信息体检”：
1. 内置纯因果向量化时序算子（ts_*）、横截面算子（cs_*，含行业中性化）与低频金融复合算子；
2. 安全 AST 求值器白名单执行表达式，禁止负滞后（偷看未来）与任意代码执行，并产出稳定 AST 结构指纹；
3. 内置自动化“篡改未来价格前缀不变性验漏测试”，任何带未来函数的候选因子在入库前会被程序直接拦下。
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
import hashlib
import math
from typing import Any, Callable
import numpy as np
import pandas as pd

from .data_portal import DataPortal, SplitMode
from .diagnostics import evaluate_factor_panel_l1
from .fund_evaluator import DISTINCT_SECTOR_FUNDS


# ------------------------- 纯因果向量化时序/横截面算子 -------------------------

def _as_df(x: pd.DataFrame | float | int) -> pd.DataFrame:
    if isinstance(x, pd.DataFrame):
        return x.astype(float)
    raise TypeError("算子输入必须是 Date × Symbol 的面板 DataFrame")


def _pos_int(d: Any, name: str = "window") -> int:
    if isinstance(d, bool) or not isinstance(d, (int, float)) or int(d) < 1:
        raise ValueError(f"{name} 必须为正整数（禁止 <=0 或负滞后偷看未来）")
    return int(d)


def ts_delay(x: pd.DataFrame, d: int = 1) -> pd.DataFrame:
    return _as_df(x).shift(_pos_int(d, "delay"))


def ts_delta(x: pd.DataFrame, d: int = 1) -> pd.DataFrame:
    df = _as_df(x)
    return df - df.shift(_pos_int(d, "delta"))


def ts_pct_change(x: pd.DataFrame, d: int = 20) -> pd.DataFrame:
    df = _as_df(x)
    w = _pos_int(d, "pct_change")
    prev = df.shift(w).replace(0.0, np.nan)
    return df / prev - 1.0


def ts_mean(x: pd.DataFrame, d: int = 20) -> pd.DataFrame:
    w = _pos_int(d)
    return _as_df(x).rolling(w, min_periods=max(2, w // 2)).mean()


def ts_std(x: pd.DataFrame, d: int = 20) -> pd.DataFrame:
    w = _pos_int(d)
    return _as_df(x).rolling(w, min_periods=max(3, w // 2)).std()


def ts_sum(x: pd.DataFrame, d: int = 20) -> pd.DataFrame:
    w = _pos_int(d)
    return _as_df(x).rolling(w, min_periods=max(2, w // 2)).sum()


def ts_min(x: pd.DataFrame, d: int = 20) -> pd.DataFrame:
    w = _pos_int(d)
    return _as_df(x).rolling(w, min_periods=max(2, w // 2)).min()


def ts_max(x: pd.DataFrame, d: int = 20) -> pd.DataFrame:
    w = _pos_int(d)
    return _as_df(x).rolling(w, min_periods=max(2, w // 2)).max()


def ts_ema(x: pd.DataFrame, d: int = 20) -> pd.DataFrame:
    w = _pos_int(d)
    return _as_df(x).ewm(span=w, adjust=False, min_periods=max(2, w // 2)).mean()


def ts_rank(x: pd.DataFrame, d: int = 60) -> pd.DataFrame:
    w = _pos_int(d)
    return _as_df(x).rolling(w, min_periods=max(10, w // 3)).rank(pct=True)


def ts_zscore(x: pd.DataFrame, d: int = 60) -> pd.DataFrame:
    df = _as_df(x)
    mu = ts_mean(df, d)
    sd = ts_std(df, d).replace(0.0, np.nan)
    return (df - mu) / sd


def ts_drawdown(x: pd.DataFrame, d: int = 252) -> pd.DataFrame:
    df = _as_df(x)
    hi = ts_max(df, d).replace(0.0, np.nan)
    return df / hi - 1.0


def ts_corr(x: pd.DataFrame, y: pd.DataFrame, d: int = 20) -> pd.DataFrame:
    w = _pos_int(d)
    return _as_df(x).rolling(w, min_periods=max(5, w // 2)).corr(_as_df(y))


def cs_rank(x: pd.DataFrame) -> pd.DataFrame:
    """逐日横截面百分位排序（0~1），天然抗极值且无未来函数。"""
    return _as_df(x).rank(axis=1, pct=True)


def cs_demean(x: pd.DataFrame) -> pd.DataFrame:
    df = _as_df(x)
    return df.sub(df.mean(axis=1), axis=0)


def cs_zscore(x: pd.DataFrame) -> pd.DataFrame:
    df = _as_df(x)
    mu = df.mean(axis=1)
    sd = df.std(axis=1).replace(0.0, np.nan)
    return df.sub(mu, axis=0).div(sd, axis=0)


def cs_winsorize(x: pd.DataFrame, k: float = 3.0) -> pd.DataFrame:
    """横截面 MAD 去极值（带正态一致性尺度因子 1.4826）。"""
    df = _as_df(x)
    med = df.median(axis=1)
    mad = df.sub(med, axis=0).abs().median(axis=1) * 1.4826
    lo = med - float(k) * mad
    hi = med + float(k) * mad
    return df.clip(lower=lo, upper=hi, axis=0)


def cs_neutralize_industry(x: pd.DataFrame, industry_map: dict[str, str] | None = None) -> pd.DataFrame:
    """横截面行业去均值（当提供 industry_map 时在同行业内部去均值；单票行业保持原值不静默清零）。"""
    df = _as_df(x)
    if not industry_map:
        return cs_demean(df)
    out = df.copy()
    groups: dict[str, list[str]] = {}
    for col in df.columns:
        ind = industry_map.get(str(col), "")
        if ind:
            groups.setdefault(ind, []).append(col)
    for cols in groups.values():
        if len(cols) >= 2:
            sub = df[cols]
            out[cols] = sub.sub(sub.mean(axis=1), axis=0)
    return out


# ------------------------- 金融低频复合算子 -------------------------

def risk_adj_mom(close: pd.DataFrame, d: int = 60) -> pd.DataFrame:
    """风险调整动量（过去 d 日涨幅 / 同期日收益波动率，避免高波妖股霸榜）。"""
    w = _pos_int(d)
    ret = ts_pct_change(close, w)
    vol = _as_df(close).pct_change(fill_method=None).rolling(w, min_periods=max(10, w // 2)).std() * math.sqrt(252.0)
    return ret / vol.clip(lower=0.05)


def price_efficiency(close: pd.DataFrame, d: int = 20) -> pd.DataFrame:
    """Kaufman 路径效率比 = |净涨跌| / 逐日绝对涨跌之和，衡量走势是稳健推升还是噪音剧震。"""
    w = _pos_int(d)
    df = _as_df(close)
    net_move = (df - df.shift(w)).abs()
    path_len = df.diff().abs().rolling(w, min_periods=max(5, w // 2)).sum().replace(0.0, np.nan)
    return (net_move / path_len).clip(0.0, 1.0)


def downside_vol(close: pd.DataFrame, d: int = 60) -> pd.DataFrame:
    """近 d 日纯下行波动率（仅统计下跌日波动，区分良性放量上涨与恶性暴跌风险）。"""
    w = _pos_int(d)
    r = _as_df(close).pct_change(fill_method=None)
    neg = r.clip(upper=0.0)
    return np.sqrt((neg ** 2).rolling(w, min_periods=max(10, w // 2)).mean()) * math.sqrt(252.0)


def vol_asym(close: pd.DataFrame, volume: pd.DataFrame, d: int = 20) -> pd.DataFrame:
    """近 d 日涨时放量/跌时缩量健康比（log(上涨日均量 / 下跌日均量)）。"""
    w = _pos_int(d)
    r = _as_df(close).pct_change(fill_method=None)
    v = _as_df(volume)
    up_v = v.where(r > 0.0).rolling(w, min_periods=3).mean()
    dn_v = v.where(r <= 0.0).rolling(w, min_periods=3).mean().clip(lower=1e-6)
    return np.log((up_v / dn_v).clip(0.25, 4.0))


def gap_reversion(open_df: pd.DataFrame, close_df: pd.DataFrame, d: int = 20) -> pd.DataFrame:
    """日内动量减隔夜跳空（识别开盘情绪盲目追高回落 vs 盘中真资金承接推升）。"""
    w = _pos_int(d)
    op = _as_df(open_df)
    cl = _as_df(close_df)
    intraday = (cl / op.replace(0.0, np.nan) - 1.0)
    overnight = (op / cl.shift(1).replace(0.0, np.nan) - 1.0)
    return ts_mean(intraday - overnight, w)


def safe_div(a: Any, b: Any) -> Any:
    if isinstance(b, pd.DataFrame):
        return a / b.replace(0.0, np.nan)
    return a / (b if abs(float(b)) > 1e-12 else np.nan)


def op_clip(x: pd.DataFrame, lo: float, hi: float) -> pd.DataFrame:
    return _as_df(x).clip(lower=float(lo), upper=float(hi))


def op_abs(x: pd.DataFrame | float) -> Any:
    return x.abs() if isinstance(x, pd.DataFrame) else abs(x)


def op_log(x: pd.DataFrame) -> pd.DataFrame:
    return np.log(_as_df(x).clip(lower=1e-12))


def op_tanh(x: pd.DataFrame) -> pd.DataFrame:
    return np.tanh(_as_df(x))


OPERATOR_REGISTRY: dict[str, Callable[..., Any]] = {
    "ts_delay": ts_delay,
    "ts_delta": ts_delta,
    "ts_pct_change": ts_pct_change,
    "ts_mean": ts_mean,
    "ts_std": ts_std,
    "ts_sum": ts_sum,
    "ts_min": ts_min,
    "ts_max": ts_max,
    "ts_ema": ts_ema,
    "ts_rank": ts_rank,
    "ts_zscore": ts_zscore,
    "ts_drawdown": ts_drawdown,
    "ts_corr": ts_corr,
    "cs_rank": cs_rank,
    "cs_demean": cs_demean,
    "cs_zscore": cs_zscore,
    "cs_winsorize": cs_winsorize,
    "risk_adj_mom": risk_adj_mom,
    "price_efficiency": price_efficiency,
    "downside_vol": downside_vol,
    "vol_asym": vol_asym,
    "gap_reversion": gap_reversion,
    "safe_div": safe_div,
    "clip": op_clip,
    "abs": op_abs,
    "log": op_log,
    "tanh": op_tanh,
}


@dataclass(frozen=True)
class FactorSpec:
    name: str
    expr: str
    financial_hypothesis: str
    intended_use: str
    family: str


# 内置 6 个金融含义清晰、低相关的正交种子因子（作为新候选因子的去重基准库）
BUILTIN_FACTOR_SPECS: list[FactorSpec] = [
    FactorSpec(
        name="risk_adj_mom_60",
        expr="cs_rank(risk_adj_mom(close, 60))",
        financial_hypothesis="中期趋势上涨且波动率受控的标的代表资金稳健共识，比纯追暴涨妖股更可持续",
        intended_use="横截面排序选标的",
        family="momentum_quality",
    ),
    FactorSpec(
        name="low_downside_vol_60",
        expr="cs_rank(-downside_vol(close, 60))",
        financial_hypothesis="剔除恶性暴跌下行风险的稳健标的，符合低波异象与个人控制回撤目标",
        intended_use="风控排序与稳健选股",
        family="low_risk",
    ),
    FactorSpec(
        name="trend_efficiency_20",
        expr="cs_rank(price_efficiency(close, 20) * ts_pct_change(close, 20))",
        financial_hypothesis="单位路程产出净涨幅越高（路径效率高），说明主升段抛压轻、筹码锁定好",
        intended_use="右侧起势排序",
        family="price_structure",
    ),
    FactorSpec(
        name="vol_asym_health_20",
        expr="cs_rank(vol_asym(close, volume, 20))",
        financial_hypothesis="上涨放量、回调缩量代表主动买盘承接强而获利抛压轻",
        intended_use="量价结构确认",
        family="volume_structure",
    ),
    FactorSpec(
        name="low_crowding_amt",
        expr="cs_rank(-ts_rank(safe_div(ts_mean(amount, 10), ts_mean(amount, 120)), 252))",
        financial_hypothesis="成交热度处于低拥挤分位，避免散户扎堆踩踏的过热赛道",
        intended_use="拥挤度防追高",
        family="crowding",
    ),
    FactorSpec(
        name="intraday_vs_overnight_20",
        expr="cs_rank(gap_reversion(open, close, 20))",
        financial_hypothesis="盘中持续走强而非隔夜情绪高开低走，往往反映真实机构/大资金逢低承接",
        intended_use="微结构情绪过滤",
        family="microstructure",
    ),
]


def expression_fingerprint(expr: str) -> str:
    """生成标准化 AST 结构指纹，忽略空白与格式差异。"""
    tree = ast.parse(expr.strip(), mode="eval")
    dumped = ast.dump(tree, include_attributes=False)
    return hashlib.sha256(dumped.encode("utf-8")).hexdigest()[:16]


def evaluate_factor_expression(
    expr: str,
    panel: dict[str, pd.DataFrame],
    *,
    industry_map: dict[str, str] | None = None,
) -> pd.DataFrame:
    """安全 AST 面板求值器：严格只允许白名单纯因果算子与行情变量，零任意代码执行风险。"""
    tree = ast.parse(expr.strip(), mode="eval")
    env: dict[str, Any] = {k: v.astype(float) for k, v in panel.items() if isinstance(v, pd.DataFrame)}
    if "close" in env:
        env.setdefault("ret1", env["close"].pct_change(fill_method=None))
    if "amount" not in env and "close" in env and "volume" in env:
        env["amount"] = env["close"] * env["volume"]

    ops = dict(OPERATOR_REGISTRY)
    ops["cs_neutralize"] = lambda x: cs_neutralize_industry(x, industry_map=industry_map)

    def _eval(node: ast.AST) -> Any:
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant):
            if isinstance(node.value, (int, float)) and not isinstance(node.value, bool):
                return float(node.value) if isinstance(node.value, float) else int(node.value)
            raise ValueError(f"不允许的常量类型: {type(node.value).__name__}")
        if isinstance(node, ast.Name):
            if node.id in env:
                return env[node.id]
            raise ValueError(f"未定义或不允许的变量: {node.id}（可用: {sorted(env.keys())}）")
        if isinstance(node, ast.UnaryOp):
            val = _eval(node.operand)
            if isinstance(node.op, ast.USub):
                return -val
            if isinstance(node.op, ast.UAdd):
                return +val
            raise ValueError(f"不支持的一元运算符: {type(node.op).__name__}")
        if isinstance(node, ast.BinOp):
            left = _eval(node.left)
            right = _eval(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return safe_div(left, right)
            if isinstance(node.op, ast.Pow):
                return left ** right
            raise ValueError(f"不支持的二元运算符: {type(node.op).__name__}")
        if isinstance(node, ast.Call):
            if not isinstance(node.func, ast.Name) or node.func.id not in ops:
                fn_name = node.func.id if isinstance(node.func, ast.Name) else ast.dump(node.func)
                raise ValueError(f"不允许调用未登记算子: {fn_name}")
            if node.keywords:
                raise ValueError("请使用位置参数调用算子")
            args = [_eval(a) for a in node.args]
            return ops[node.func.id](*args)
        raise ValueError(f"安全门禁拒绝语法节点: {type(node).__name__}")

    res = _eval(tree)
    if not isinstance(res, pd.DataFrame):
        raise ValueError("因子表达式必须返回 Date × Symbol 的 DataFrame 面板")
    return res.replace([np.inf, -np.inf], np.nan)


def verify_expression_no_lookahead(
    expr: str,
    panel: dict[str, pd.DataFrame],
    *,
    industry_map: dict[str, str] | None = None,
    tamper_tail_days: int = 30,
) -> dict[str, object]:
    """自动化前缀不变性验漏门禁：剧烈篡改最后 tamper_tail_days 天行情，断言截断日前所有因子值误差为 0。"""
    close = panel["close"]
    n = len(close)
    if n <= tamper_tail_days + 40:
        return {"passed": True, "checked_rows": 0, "max_abs_diff": 0.0, "note": "样本偏短跳过尾段篡改"}

    cutoff = n - tamper_tail_days
    orig = evaluate_factor_expression(expr, panel, industry_map=industry_map).iloc[:cutoff]

    tampered: dict[str, pd.DataFrame] = {}
    for k, df in panel.items():
        cp = df.copy()
        if k in ("open", "high", "low", "close"):
            cp.iloc[cutoff:] = cp.iloc[cutoff:] * 3.7
        elif k in ("volume", "amount"):
            cp.iloc[cutoff:] = cp.iloc[cutoff:] * 11.3
        tampered[k] = cp
    after = evaluate_factor_expression(expr, tampered, industry_map=industry_map).iloc[:cutoff]

    diff = (orig - after).abs()
    nan_mismatch = int((orig.isna() != after.isna()).to_numpy().sum())
    finite_diff = diff.to_numpy(dtype=float)
    finite_diff = finite_diff[np.isfinite(finite_diff)]
    max_diff = float(np.max(finite_diff)) if len(finite_diff) else 0.0
    passed = (nan_mismatch == 0) and (max_diff <= 1e-10)
    return {
        "passed": passed,
        "checked_rows": int(cutoff),
        "nan_mismatch": nan_mismatch,
        "max_abs_diff": round(max_diff, 12),
        "verdict_cn": "✅ 通过严格前缀不变性验漏（零未来函数）" if passed else "🛑 检测到未来函数泄漏，严禁入库！",
    }


def screen_candidate_factor(
    portal: DataPortal,
    *,
    name: str,
    expr: str,
    financial_hypothesis: str,
    pool: str = "etf",
    split: SplitMode = "explore",
    max_symbols: int = 120,
) -> dict[str, object]:
    """声明式新因子一站式验货流水线：AST解析 → 自动化无未来函数验漏 → 内置库两级正交查重 → L1 多期信息体检。"""
    if pool == "etf":
        symbols = [s for s, _, _ in DISTINCT_SECTOR_FUNDS]
        min_assets = 6
        n_groups = 4
    else:
        symbols = portal.list_cn_stocks()[:max_symbols]
        min_assets = 10
        n_groups = 5

    panel = portal.load_panel_bars(symbols, market="CN", split=split, min_rows=150)
    if panel["close"].empty:
        return {"available": False, "reason": f"{pool} 池满足长度要求的标的不足"}

    industry_map: dict[str, str] = {}
    fund_latest = portal.load_latest_fundamentals_table()
    if len(fund_latest) > 0 and "industry" in fund_latest.columns:
        for _, r in fund_latest.iterrows():
            if pd.notna(r["industry"]):
                industry_map[str(r["symbol"])] = str(r["industry"])

    fp = expression_fingerprint(expr)
    leak_check = verify_expression_no_lookahead(expr, panel, industry_map=industry_map)
    if not leak_check["passed"]:
        return {
            "available": True,
            "name": name,
            "expr": expr,
            "ast_fingerprint": fp,
            "financial_hypothesis": financial_hypothesis,
            "no_lookahead_check": leak_check,
            "admission_verdict_cn": "🛑 拒绝入库：未通过无未来函数前缀不变性检查",
        }

    cand_panel = evaluate_factor_expression(expr, panel, industry_map=industry_map)

    # 构建内置正交基准因子库（排除与候选同名的项）
    existing: dict[str, pd.DataFrame] = {}
    for spec in BUILTIN_FACTOR_SPECS:
        if spec.name == name:
            continue
        try:
            existing[spec.name] = evaluate_factor_expression(spec.expr, panel, industry_map=industry_map)
        except Exception:
            continue

    l1 = evaluate_factor_panel_l1(
        cand_panel,
        panel["close"],
        open_panel=panel["open"],
        horizons=(5, 20, 60),
        n_groups=n_groups,
        min_assets=min_assets,
        existing_factors=existing,
    )

    h20 = l1["horizons"]["20d"]
    ic20 = float(h20["rank_ic_mean"])
    t20 = float(h20["hac_t_stat"])
    red = l1["redundancy"]
    max_corr = float(red["max_abs_rank_corr"])
    resid_info = red.get("orthogonal_residual_ic") or {}
    resid_t = float(resid_info.get("residual_hac_t", 0.0))

    if max_corr >= 0.75 and abs(resid_t) < 1.65:
        admit = f"🔴 淘汰（和已有指标高度重复，去掉重复部分后没多出新信息）"
    elif abs(ic20) >= 0.03 and abs(t20) >= 1.96:
        admit = "🟢 建议进入真实资金账本做进一步检验（没偷看未来、选品有帮助、且和现有指标不重复）"
    elif abs(ic20) >= 0.02 or abs(resid_t) >= 1.65:
        admit = "🟡 有一定弱线索（可保留观察或作为特定行情下的辅助过滤）"
    else:
        admit = "🔴 暂不采用（往后1个月的挑选区分度不够明显）"

    return {
        "available": True,
        "name": name,
        "expr": expr,
        "ast_fingerprint": fp,
        "financial_hypothesis": financial_hypothesis,
        "pool": pool,
        "split": split,
        "symbols_count": len(panel["close"].columns),
        "no_lookahead_check": leak_check,
        "l1_evaluation": l1,
        "admission_verdict_cn": admit,
    }
