"""宽度择时回测预设参数组。

source 字段标注来源：初始预设由人工设定；参数扫描胜出组以扫描报告路径标注，
历史最优不等于未来最优（页面同步展示该警示）。
"""
from __future__ import annotations

_PRESET_SOURCE = "初始预设 2026-08-27"

PRESETS: list[dict] = [
    {
        "key": "cn_b200_ladder5",
        "label": "沪深300 · B200 五档逆势",
        "description": "宽度低多、宽度高空（<20 满仓 … ≥80 空仓），档位触发式分批",
        "source": _PRESET_SOURCE,
        "params": {"symbol": "000300", "strategy": "ladder", "indicator": "b200", "n_bands": 5},
    },
    {
        "key": "us_b200_ladder5",
        "label": "标普500 · B200 五档逆势",
        "description": "同上，美股费率 1bp",
        "source": _PRESET_SOURCE,
        "params": {"symbol": "^GSPC", "strategy": "ladder", "indicator": "b200", "n_bands": 5},
    },
    {
        "key": "cn_b50_ladder5",
        "label": "沪深300 · B50 五档逆势",
        "description": "更快的宽度指标，调仓更频繁",
        "source": _PRESET_SOURCE,
        "params": {"symbol": "000300", "strategy": "ladder", "indicator": "b50", "n_bands": 5},
    },
    {
        "key": "cn_b200_ladder9",
        "label": "沪深300 · B200 九档细颗粒",
        "description": "每 11 个宽度点一档，分批更细",
        "source": _PRESET_SOURCE,
        "params": {"symbol": "000300", "strategy": "ladder", "indicator": "b200", "n_bands": 9},
    },
    {
        "key": "cn_b200_ladder5_momentum",
        "label": "沪深300 · B200 五档顺势（对照）",
        "description": "宽度高多、宽度低空——与逆势互为对照",
        "source": _PRESET_SOURCE,
        "params": {
            "symbol": "000300", "strategy": "ladder", "indicator": "b200",
            "n_bands": 5, "direction": "momentum",
        },
    },
    {
        "key": "cn_b200_reversal_time5",
        "label": "沪深300 · B200 极值反转 · 时间分批",
        "description": "跌破 20 回升确认买入 / 升破 80 回落确认卖出，5 日每日一批",
        "source": _PRESET_SOURCE,
        "params": {
            "symbol": "000300", "strategy": "reversal", "indicator": "b200",
            "batch_mode": "time", "batches": 5,
        },
    },
    {
        "key": "cn_b200_reversal_band5",
        "label": "沪深300 · B200 极值反转 · 档位分批",
        "description": "触发后每回升/回落 10 个宽度点调一批",
        "source": _PRESET_SOURCE,
        "params": {
            "symbol": "000300", "strategy": "reversal", "indicator": "b200",
            "batch_mode": "band", "batches": 5,
        },
    },
    {
        "key": "cn_b200_ladder5_gate",
        "label": "沪深300 · B200 五档 + MA200 趋势闸门",
        "description": "阶梯打分 × 指数跌破 MA200 强制空仓的组合",
        "source": _PRESET_SOURCE,
        "params": {
            "symbol": "000300", "strategy": "ladder", "indicator": "b200",
            "n_bands": 5, "gate_mode": "ma200", "gate_cap": 0.0,
        },
    },
]
