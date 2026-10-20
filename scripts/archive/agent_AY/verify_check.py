"""任务 AY：宽度输入源对比——查重后的轻量一致性核对（转述报告的支撑数据）。

预注册（跑前写死，跑后未改）
==============================
任务书规定：若归档查重发现"创业板专属宽度"已参加过评选并被淘汰，本任务
转为结论转述报告，**不重跑策略对比**。本次核对仅做两件事：

C1  两条宽度序列（cn_all / cyb 的 B200）可复现性：加载、对齐共同交易日，
    计算档位一致率（档位线 43.333/56.667，与冠军三档同线，机械映射：
    b200 < 43.333 → 0 档；43.333 ≤ b200 < 56.667 → 1 档；≥ 56.667 → 2 档；
    行有效性过滤 n200 ≥ 50，与 AB 任务脚本一致）。与 AA/AB 报告的
    "档位不一致率 20.2%" 对表（同口径应为同量级）。
C2  两条 B200 序列的水平相关与日变化相关（描述性，转述报告引用）。

判定无关声明：本脚本不产生"哪个输入更好"的任何新证据——该问题由
docs/timing-sweep/execution_playbook_20260827.md 第七轮配对检验在 1bp 费率
+ 5% 最小调仓阈值口径下已回答（全A +4.4%/+4.6% vs 专属 -0.2%/-0.4%）。

输出：docs/experiments/raw/agent_AY/verify_check.json（含 sha256 自校验）
双跑：PYTHONHASHSEED=0 / 42 各跑一遍，输出 JSON 须逐字节一致。
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd

CACHE = Path.home() / ".lei_signal_lab/cache/timing"
RAW = Path(__file__).resolve().parents[2] / "docs/experiments/raw/agent_AY"
MIN_STOCKS = 50
EDGES = (30 + 40 / 3, 30 + 40 * 2 / 3)  # 43.333... / 56.666...，冠军三档档位线


def tier(b200: pd.Series) -> pd.Series:
    return pd.Series(np.digitize(b200.to_numpy(), EDGES), index=b200.index)


def main() -> None:
    RAW.mkdir(parents=True, exist_ok=True)
    cn = pd.read_parquet(CACHE / "breadth_cn_all.parquet")
    cyb = pd.read_parquet(CACHE / "breadth_cyb.parquet")

    def valid(df: pd.DataFrame) -> pd.DataFrame:
        return df[df["b200"].notna() & (df["n200"] >= MIN_STOCKS)]

    cn, cyb = valid(cn), valid(cyb)
    joined = pd.concat(
        {"cn_all": cn["b200"], "cyb": cyb["b200"]}, axis=1, join="inner"
    ).dropna()

    t_cn, t_cyb = tier(joined["cn_all"]), tier(joined["cyb"])
    agree = float((t_cn == t_cyb).mean())
    lvl_corr = float(joined["cn_all"].corr(joined["cyb"]))
    chg_corr = float(joined["cn_all"].diff().corr(joined["cyb"].diff()))

    out = {
        "task": "AY verify_check (transcription-report support, no strategy rerun)",
        "dedup_verdict": "已测过被淘汰（execution_playbook_20260827.md 第七轮配对检验）",
        "original_numbers_cited": {
            "cn_all_excess_annual": {"指数": "+4.4%", "ETF": "+4.6%"},
            "cyb_specific_excess_annual": {"指数": "-0.2%", "ETF": "-0.4%"},
            "original_fees_and_threshold": "1bp 费率 + 5% 最小调仓阈值",
        },
        "check_C1_tier_agreement": {
            "common_days": int(len(joined)),
            "window": [str(joined.index.min().date()), str(joined.index.max().date())],
            "tier_lines": [43.3333, 56.6667],
            "min_stocks_filter": MIN_STOCKS,
            "agreement_rate": round(agree, 4),
            "disagreement_rate": round(1 - agree, 4),
            "ab_reported_disagreement": 0.202,
            "same_order_of_magnitude_expected": True,
        },
        "check_C2_descriptive": {
            "b200_level_pearson": round(lvl_corr, 4),
            "b200_daily_change_pearson": round(chg_corr, 4),
        },
    }
    payload = json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True)
    (RAW / "verify_check.json").write_text(payload + "\n")
    print(payload)
    print(
        "sha256:",
        hashlib.sha256((RAW / "verify_check.json").read_bytes()).hexdigest(),
    )


if __name__ == "__main__":
    main()
