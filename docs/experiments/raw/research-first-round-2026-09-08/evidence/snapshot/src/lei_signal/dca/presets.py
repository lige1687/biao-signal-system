"""定投组合预设与跟踪池：全部来自定投归档，不发明配置。

来源标注（数字唯一来源 configs/dca_evidence.json，此处只是速览；
旧窗口口径（近五年 15.88%/−9.7% 单路径、进取版旧值 17.08%/−12.6%）
已被第十八轮重定标，勿再当主数字引用）：
- 跨资产四件套（第七/八轮设计，第十八轮重定标）：沪深300 + 成长腿 +
  黄金 + 纳指，等权、季度再平衡。稳健版主数字 = 96 个月度起投点资金
  加权年化中位 13.86% [P10 12.23%, P90 15.70%]（去掉两端各一成的起点
  范围，非最差/最好、非未来保证）、回撤中位 −15.2%；
- 进取版成长腿=科创50：仅 W5 单一窗口 17.57%/−13.1%（single_window，
  含选腿选择效应，讲解必须带「历史单窗成绩，非预期收益」）；
- 分腿角色与止盈菜单（第十五轮）：蓝筹 +30%、成长 +50%、黄金/纳指不止盈
  ——注意该菜单只用于**篮子外独立埋伏交易**（第十六轮：组合内止盈 0/12
  判负，组合内由季度再平衡承担止盈职能）；
- 埋伏模板（第十三轮）：底部区域/惨档触发 → 12 个月周定投建仓 → 分标的止盈
  → 24 个月兜底（「底部区域」触发第十七轮降级弱参照，见账本 trigger_note）；
- 跟踪池（第十一/十五轮状态表宇宙）：用于 /state 与 /triggers 看板。
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Leg:
    code: str            # 可交易代码（场内 ETF）
    name: str
    role: str            # 蓝筹 / 成长 / 黄金 / 美股长持
    state_symbol: str    # 状态计算用的行情代码（timing 缓存口径）
    take_profit: float | None   # 埋伏模板止盈（篮子内不用，见模块 docstring）
    note: str = ""


_BASKET_NOTE = ("等权、周/月平投、季度再平衡（dca-basket-targets / "
                "dca-kc-rebal-core）；数字引用见 /api/dca/evidence")

STANDARD_BASKET: tuple[Leg, ...] = (
    Leg("510300", "沪深300ETF", "蓝筹", "510300", 0.30,
        "分腿止盈菜单 +30%（仅篮子外埋伏用）"),
    Leg("159915", "创业板ETF", "成长", "159915", 0.50,
        "成长腿用 +50% 或等过热（dca-per-target-exits；仅篮子外埋伏用）"),
    Leg("518880", "黄金ETF", "黄金", "518880", None, "不设止盈，再平衡管理"),
    Leg("513100", "纳指ETF", "美股长持", "^IXIC", None,
        "只买不卖+季度再平衡（40 年口径，dca-kc-rebal-core）；"
        "状态代理为纳斯达克综合指数，产品为纳指100，引用预期时注意口径"),
)

AGGRESSIVE_BASKET: tuple[Leg, ...] = (
    STANDARD_BASKET[0],
    Leg("588000", "科创50ETF", "成长", "588000", 0.50,
        "进取版：创业板换科创50（仅单一历史窗口成绩优于稳健版，"
        "预期均值回归，勿当更高预期引用）"),
    STANDARD_BASKET[2],
    STANDARD_BASKET[3],
)

PRESETS: dict[str, dict] = {
    "standard": {
        "plan_id": "preset_standard",
        "name": "跨资产四件套·稳健版",
        "legs": [leg.__dict__ for leg in STANDARD_BASKET],
        "frequency": "weekly",
        "rebalance": "quarterly",
        "note": _BASKET_NOTE,
    },
    "aggressive": {
        "plan_id": "preset_aggressive",
        "name": "跨资产四件套·进取版（换科创50）",
        "legs": [leg.__dict__ for leg in AGGRESSIVE_BASKET],
        "frequency": "weekly",
        "rebalance": "quarterly",
        "note": _BASKET_NOTE,
    },
}

# 状态/触发看板跟踪池（十一/十五轮宇宙；code=行情代码）
TRACKED: tuple[tuple[str, str], ...] = (
    ("SH000001", "上证指数"), ("SZ399001", "深证成指"), ("000300", "沪深300"),
    ("000015", "上证红利"), ("399006", "创业板指"), ("510500", "中证500ETF"),
    ("512100", "中证1000ETF"), ("588000", "科创50ETF"), ("518880", "黄金ETF"),
    ("^GSPC", "标普500"), ("^IXIC", "纳斯达克"),
)

VALID_FREQUENCIES = ("weekly", "monthly")
VALID_REBALANCE = ("quarterly", "monthly", "none")
