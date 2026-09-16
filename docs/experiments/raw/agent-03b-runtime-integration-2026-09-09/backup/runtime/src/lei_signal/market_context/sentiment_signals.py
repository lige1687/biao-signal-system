"""散户情绪终版信号（冰点机会 / 强势散户热警报）· 预计算层。

实验依据：docs/experiments/retail-sentiment-ts-2026-09-05.md（§10/§11 终裁）
- 信号1 冰点机会（C4）：全A情绪冰点 × 板块 60 日跌幅≤-10% × 散户流入
  z≥1.5（自身120日基准）× b50<30 → 10日超额 +6.5~7.8%（79% 板块同向）；
- 信号2 强势散户热警报：散户流入 z≥1.5 × b50>70 × b200>70（全面强势
  板块的散户涌入）→ 10日 -9.3%（29 例 0 板块幸免）。

定位：research_proxy 叙事标注——只提示、不判定、不出买卖点；单年双
事件样本，多年复验（Tushare）为最终确认前提（实验报告 §10 诚实声明）。
数据源：tx_sector_flow_pilot.json（腾讯个股聚合，口径与东财一致性 96%+，
自身 120 日 z 基准要求序列同源，不与东财混用；新板块缺失时信号置 None
不冒充）。b200 由本模块从个股 close 全量自算（冻结口径 b200 留痕不落盘，
此处仅内部使用并标注有效天数）。
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from lei_signal.domain.rules_config import get_rule


def _cfg() -> dict:
    """阈值读账本（retail_heat 段共用窗口/z；冰点/警报档位随实验结论参数化）。"""
    defaults = {
        "z_threshold": 1.5,
        "retail_window": 20,
        "z_base_window": 120,
        "ice_r60_max": -10.0,   # 60日跌幅 ≤ -10%
        "ice_b50_max": 30.0,
        "alarm_b50_min": 70.0,
        "alarm_b200_min": 70.0,
    }
    try:
        rule = get_rule("retail_heat")
        return {
            "z_threshold": float(rule.param("ts_z_threshold", defaults["z_threshold"])),
            "retail_window": int(rule.param("window_days", defaults["retail_window"])),
            "z_base_window": int(rule.param("ts_z_base_window", defaults["z_base_window"])),
            **{k: float(rule.param(k, v)) for k, v in defaults.items()
               if k not in ("z_threshold", "retail_window", "z_base_window")},
        }
    except Exception:  # noqa: BLE001 - 账本缺省按默认口径运行
        return defaults


def load_tx_flows(cache: Path) -> dict[str, list[dict]]:
    """读腾讯聚合资金流（字段统一为东财五档名；large 由 main-jumbo 推导）。"""
    p = cache / "tx_sector_flow_pilot.json"
    if not p.exists():
        return {}
    try:
        raw = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    out: dict[str, list[dict]] = {}
    for code, pts in (raw.get("boards") or {}).items():
        rows = []
        for q in pts:
            main, jumbo = q.get("main_yi"), q.get("jumbo_yi")
            rows.append({
                "date": q["date"], "main_yi": main, "small_yi": q.get("small_yi"),
                "medium_yi": q.get("mid_yi"),
                "large_yi": round(main - jumbo, 2)
                if main is not None and jumbo is not None else None,
                "super_large_yi": jumbo,
            })
        out[code] = rows
    return out


def compute_b200_last(wide: pd.DataFrame, members: dict[str, dict],
                      canonical: set[str]) -> dict[str, float | None]:
    """各板块 b200 尾值（成分股站上 MA200 比例；有效成分日数 ≥60 才给值）。"""
    ma200 = wide.rolling(200, min_periods=200).mean()
    above = (wide > ma200).where(wide.notna())
    out: dict[str, float | None] = {}
    tail = slice(-60, None)
    for code, info in members.items():
        if code not in canonical:
            continue
        mem = [s for s in info.get("members", []) if s in wide.columns]
        if len(mem) < 5:
            continue
        sub = above[mem].dropna(how="all").tail(60)
        if len(sub) < 55 or sub.empty:
            out[code] = None
            continue
        last = sub.iloc[-1]  # 最后一个有效交易日（当日缺K线的行不取）
        n = last.notna().sum()
        out[code] = round(float(last.sum() / n * 100), 1) if n >= 5 else None
    return out


def retail_z(points: list[dict] | None, close: pd.Series | None,
             mv_today: float | None, *, window: int, base: int,
             metric: str = "small_yi") -> float | None:
    """散户流入强度 20 日均值的自身 base 日 z（同 retail_sentiment_ts 口径）。"""
    if not points or close is None or close.dropna().empty or not mv_today:
        return None
    last_close = float(close.dropna().iloc[-1])
    if last_close <= 0:
        return None
    s = {str(c.date()): v for c, v in close.dropna().items()}
    vals = {}
    for p in points:
        c = s.get(str(p.get("date"))[:10])
        v = p.get(metric)
        if c is None or v is None:
            continue
        mv_t = mv_today * c / last_close
        if mv_t > 0:
            vals[p["date"]] = v / mv_t
    ser = pd.Series(vals).sort_index()
    rolled = ser.rolling(window, min_periods=window).mean()
    mu = rolled.rolling(base, min_periods=base).mean().shift(1)
    sd = rolled.rolling(base, min_periods=base).std().shift(1)
    if rolled.empty or pd.isna(mu.iloc[-1]) or pd.isna(sd.iloc[-1]) or sd.iloc[-1] == 0:
        return None
    return round(float((rolled.iloc[-1] - mu.iloc[-1]) / sd.iloc[-1]), 2)


def signal_state(*, z: float | None, r60_pct: float | None, b50: float | None,
                 b200: float | None, cn_cold: bool | None, cfg: dict | None) -> dict:
    """由各分量得两条信号（缺任一输入→对应信号 False 且标注缺什么）。"""
    cfg = cfg or _cfg()
    out = {"sig_retail_z": z, "sig_icepoint_pick": False, "sig_heat_alarm": False,
           "sig_note_cn": None}
    if z is None:
        return out
    hot = z >= cfg["z_threshold"]
    # 信号2：全面强势板块的散户热（不依赖大盘环境）
    if hot and b50 is not None and b200 is not None \
            and b50 > cfg["alarm_b50_min"] and b200 > cfg["alarm_b200_min"]:
        out["sig_heat_alarm"] = True
        out["sig_note_cn"] = (
            f"强势板块散户涌入警报：散户流入强度 z={z}（自身历史高位）且宽度 "
            f"b50={b50:.0f}/b200={b200:.0f} 全面偏强——历史同条件：10 日 -9.3%、"
            "29 例 0 板块幸免（p=0.0009，单年样本）；边界：仅 50&200 同高档，"
            "反弹初档散户热为正向勿报；research_proxy，非买卖点")
    # 信号1：全A冰点 × 深弱 × 散户逆势涌入
    if cn_cold and hot and r60_pct is not None and b50 is not None \
            and r60_pct <= cfg["ice_r60_max"] and b50 < cfg["ice_b50_max"]:
        out["sig_icepoint_pick"] = True
        out["sig_note_cn"] = (
            f"冰点机会标注：全A情绪冰点 × 板块60日{r60_pct:.0f}% × 散户逆势涌入"
            f"（z={z}）× b50={b50:.0f}——历史同条件：10日超额 +5.9~7.8%、"
            "92% 板块同向（154 例，p<0.0001，单年双事件验证、多年终审待做）；"
            "适用边界：仅冰点环境×深弱板块；research_proxy，非买卖点")
    return out
