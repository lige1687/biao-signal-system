"""散户热度口径（research_proxy 纯函数）。

策略定位：资金面属「路牌」性质预警（docs/trading-spec-v1.md §2.2 先判断道路
再观察路牌；路牌只预警不必然反向）。散户过热只做叙事标注与预警展示，
不参与技术判定、不做硬过滤、不出买卖点（与 Round 4 市场环境层
「独立分组研究、不硬挡信号」同一原则）。

口径事实（2026-09-04 实测本地 sector_flow_history.json 17931 板块日）：
- 东财五档满足 main = super_large + large（定义关系，偏差 ≤ 舍入）；
- main + medium + small ≈ 0（中位偏差 0.01 亿）——资金流零和，
  「散户净流入」与「主力净流出」是同一数字的正反面；
- 因此散户热度的独立信息量在档位结构：小单（最小资金代理）与
  超大单（最大资金代理）的净占比分化（diverge）。

单位约定：净流入亿元 / 流通市值亿元 → ratio 为无量纲强度。
「机构」为超大单近似（单据规模代理，非真实机构/散户身份，页面须如实标注）；
「国家队」（汇金/证金等）无数据口径，不冒充。
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from lei_signal.domain.rules_config import get_rule

# 口径注册表：预计算层与回测共用同一份定义（阈值不硬编码，登记在
# configs/rules.v2.yaml 的 retail_heat 段，回测校准后走账本更新）
METRIC_LABELS: dict[str, str] = {
    "retail": "散户档净流入强度（中单+小单，相对流通市值）",
    "small": "小单净流入强度（最纯散户代理）",
    "super_large": "超大单净流入强度（最大资金代理）",
    "diverge": "小单−超大单分化（筹码下移强度）",
}


def point_ratios(point: dict, mv_yi: float | None) -> dict[str, float] | None:
    """单日净占比（净流入/流通市值）。任一输入缺失返回 None（不可用不冒充）。"""
    if mv_yi is None or mv_yi <= 0:
        return None
    small = point.get("small_yi")
    medium = point.get("medium_yi")
    super_large = point.get("super_large_yi")
    if small is None or medium is None or super_large is None:
        return None
    return {
        "retail": (medium + small) / mv_yi,
        "small": small / mv_yi,
        "super_large": super_large / mv_yi,
        "diverge": (small - super_large) / mv_yi,
    }


def heat_config() -> dict:
    """读 rules.v2.yaml 的 retail_heat 段。账本缺失该段时按占位默认运行
    （研究与页面仍可用，阈值以账本为准）。"""
    defaults = {
        "metric": "diverge",
        "window_days": 20,
        "hot_pctile": 90.0,
        "cold_pctile": 10.0,
        "warn_stages": ("markup", "distribution"),
    }
    try:
        rule = get_rule("retail_heat")
        cfg = {
            "metric": rule.param("metric", defaults["metric"]),
            "window_days": int(rule.param("window_days", defaults["window_days"])),
            "hot_pctile": float(rule.param("hot_pctile", defaults["hot_pctile"])),
            "cold_pctile": float(rule.param("cold_pctile", defaults["cold_pctile"])),
            "pctile_pool": rule.param("pctile_pool", "l1_l2"),
            "warn_stages": tuple(rule.param("warn_stages", list(defaults["warn_stages"]))),
            "version": rule.version,
        }
    except Exception:  # noqa: BLE001 - 账本未登记时按默认口径运行并显式标注版本
        cfg = {**defaults, "version": "default"}
    if cfg["metric"] not in METRIC_LABELS:
        cfg["metric"] = defaults["metric"]
    return cfg


def window_metric(
    points: list[dict] | None,
    idx_close: pd.Series | None,
    mv_today_yi: float | None,
    *,
    metric: str,
    window: int,
) -> float | None:
    """口径 N 日均值（与 scripts/retail_mania_backtest.py 同定义）。

    市值分母回溯：mv(t) = mv_today × close(t)/close(最新)（股本不变近似）。
    只统计能对上板块指数日期的资金流点（K 线未到的当日点跳过）；
    有效点不足 window 个返回 None。
    """
    if metric not in METRIC_LABELS or mv_today_yi is None or mv_today_yi <= 0:
        return None
    if not points or idx_close is None or idx_close.dropna().empty:
        return None
    close_by_date = {
        (d.date().isoformat() if hasattr(d, "date") else str(d)): float(v)
        for d, v in idx_close.dropna().items()
    }
    if not close_by_date:
        return None
    last_close = close_by_date[max(close_by_date)]
    if last_close <= 0:
        return None
    vals: list[float] = []
    for p in points:
        c = close_by_date.get(str(p.get("date"))[:10])
        if c is None:
            continue
        r = point_ratios(p, mv_today_yi * c / last_close)
        if r is not None:
            v = r.get(metric)
            if v is not None:
                vals.append(v)
    if len(vals) < window:
        return None
    return float(sum(vals[-window:]) / window)


def cross_section_pctile(value: float | None, values: list[float]) -> float | None:
    """横截面分位（0-100，并列取平均秩）。有效样本 < 20 不比分位（不冒充）。"""
    if value is None or len(values) < 20:
        return None
    arr = np.asarray(values, dtype=float)
    return round(
        ((arr < value).sum() + 0.5 * (arr == value).sum()) / len(arr) * 100.0, 1
    )


def heat_pool_values(
    rows: list[dict], pool_mode: str = "l1_l2"
) -> list[float]:
    """分位排名池：l1_l2 = 仅一、二级行业板块的 heat_value（rules.v2.yaml
    retail_heat.pctile_pool）。三级细分板块成分少、行为极端、用户不可操作，
    进池会霸占两端（2026-09-05 用户反馈）；L3 仍按池定位显示分位但不进池。
    池空时回落全部有效值（防御，不冒充）。
    """
    vals_all = [r.get("heat_value") for r in rows]
    vals_all = [v for v in vals_all if v is not None]
    if pool_mode != "l1_l2":
        return vals_all
    pool = [
        r.get("heat_value")
        for r in rows
        if (r.get("level") or 3) <= 2 and r.get("heat_value") is not None
    ]
    return pool if pool else vals_all


def heat_state(
    heat_pctile: float | None, stage: str | None, cfg: dict
) -> dict:
    """由分位 + 阶段得出热度档与情境化警示（只标注，不构成买卖点）。

    - hot（风险区）：分位 ≥ hot_pctile——散户狂买·超大单派发；
      其中阶段 ∈ warn_stages 时升级为 warning（情境化警示）。
    - cold（机会区）：分位 ≤ cold_pctile——散户割肉·超大单吸筹，
      反向关注信号（有效性由回测校准，页面标注研究代理）。
    """
    out = {"hot": False, "cold": False, "warning": False, "note_cn": None}
    if heat_pctile is None:
        return out
    if heat_pctile >= cfg["hot_pctile"]:
        out["hot"] = True
        if stage in cfg["warn_stages"]:
            out["warning"] = True
            stage_cn = {"markup": "上升", "distribution": "派发"}.get(stage, stage)
            out["note_cn"] = (
                f"散户过热（热度分位 {heat_pctile:.0f}）× {stage_cn}阶段："
                "小单涌入、超大单派发的路牌预警（研究代理，非买卖点）"
            )
    elif heat_pctile <= cfg.get("cold_pctile", 0.0):
        out["cold"] = True
        out["note_cn"] = (
            f"散户冰点（热度分位 {heat_pctile:.0f}）：小单割肉、超大单吸筹的"
            "反向关注区（研究代理，机会含义待回测校准）"
        )
    return out
