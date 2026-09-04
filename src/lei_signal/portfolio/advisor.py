"""调仓建议引擎 v1（R1~R7，纯函数）。

原则（写死，改前先读）：
- 建议不是新发明的信号，是「系统已验证结论」对照「用户实际持仓」的差距
  清单。每条 = 现状 + 动作 + 证据（回测出处）+ 强度 + 触发条件。
- 强度分级：certified=已认证结论（多轮回测+对照过线）；candidate=边界
  结论已验证但本次映射是新的组合层应用；observation=叙事/观察级；
  management=管理建议（无回测依据，纯属打理常识）。
- 时机分两类：配置类（换仓）不挑时机、默认分批（一次性是已验证的无代价
  基准，分批是「用V型损失换过程型更低成本」的交换）；信号类挂在板块
  阶段判定上（research_proxy 口径，提示不挡信号）。
- 措辞遵守 AGENTS.md 说人话红线；证据 ref 给开发者溯源用。
"""
from __future__ import annotations

from dataclasses import dataclass, field

STRENGTH_CN = {
    "certified": "已认证",
    "candidate": "候选",
    "observation": "观察",
    "management": "管理建议",
}

#: 行业分组 -> 板块快照里的板块名（R7 用；板块名对齐 sector_trend_snapshot）
GROUP_SECTORS: dict[str, list[str]] = {
    "cn_info": ["通信设备", "半导体", "消费电子"],
    "cn_metal": ["有色金属", "工业金属"],
    "cn_green_other": ["电力"],
}

STAGE_CN = {
    "markup": "上升", "accumulation": "筑底",
    "distribution": "高位转弱", "decline": "下降",
}

#: 阶段 -> R7 建议动作（提示级，非指令）
_STAGE_ADVICE = {
    "markup": ("持有", "板块趋势向上：拿住，离场线跟紧即可，不加仓追高。"),
    "accumulation": ("等待", "板块筑底中：等标志性动作（放量突破/均线密集突破）再动，现在不动。"),
    "distribution": ("收紧",
                    "板块高位转弱：不新增仓位；已有仓位建议收紧离场线，跌破关键位按纪律减。"),
    "decline": ("减仓提示", "板块趋势向下：按纪律降低这组敞口；没有离场纪律的话先补一条计划再说。"),
}


@dataclass(slots=True)
class Advice:
    advice_id: str
    priority: int                      # 越小越靠前
    strength: str                      # certified / candidate / observation / management
    title_cn: str
    detail_cn: str
    evidence: list[dict] = field(default_factory=list)   # [{label, ref}]
    trigger_cn: str = ""               # 什么条件下执行/生效
    execution_cn: str = ""             # 执行方式（分批/一次性/无需动作）

    def to_dict(self) -> dict:
        return {
            "advice_id": self.advice_id,
            "priority": self.priority,
            "strength": self.strength,
            "strength_cn": STRENGTH_CN.get(self.strength, self.strength),
            "title_cn": self.title_cn,
            "detail_cn": self.detail_cn,
            "evidence": self.evidence,
            "trigger_cn": self.trigger_cn,
            "execution_cn": self.execution_cn,
        }


def _ev(label: str, ref: str) -> dict:
    return {"label": label, "ref": ref}


def build_advices(
    *,
    groups: list[dict],                # [{group_key,name,market,amount,pct,holding_ids}]
    holdings: list[dict],              # [{holding_id,group_key,name,market_value,pct}]
    exposures: dict,                   # holding_id -> FundExposure
    group_market_share: dict,          # group_key -> {market: pct} | None
    sector_stages: dict[str, dict],
) -> list[Advice]:
    """全部规则跑一遍，返回按 priority 排序的建议列表。"""
    advices: list[Advice] = []
    total = sum(h["market_value"] for h in holdings) or 1.0
    by_group: dict[str, list[dict]] = {g["group_key"]: [] for g in groups}
    for h in holdings:
        by_group.setdefault(h["group_key"], []).append(h)

    # ── R1 宽基缺位（certified）──
    has_broad = any(g["group_key"] == "cn_broad" for g in groups)
    if not has_broad:
        cn_industry_pct = sum(
            g["pct"] for g in groups
            if g["market"] == "cn" and g["group_key"] != "cn_broad"
        )
        advices.append(Advice(
            advice_id="R1_no_broad_base",
            priority=1,
            strength="certified",
            title_cn="组合里没有宽基——考虑把一部分行业仓位换成宽基篮子",
            detail_cn=(
                f"现状：A股仓位约 {cn_industry_pct:.0f}%，全部集中在行业/主题，宽基为零。"
                "系统二十年历史检验里最强的方案是「9 只宽基凑一篮子、按市场整体冷热调节奏」："
                "比拿着不动每年约多赚 12 个百分点，最深亏损从接近腰斩降到约 -35%，"
                "并通过 8 道对照检验（不是运气）。要不要换、换多少，由你拍板；"
                "篮子名单系统里已有（已认证配置），不需要新研究。"
            ),
            evidence=[
                _ev("宽基篮子二十年回测：年化 +12pp vs 拿着不动、回撤 -49.6%→-34.7%",
                    "experiments/SYSTEM-VALUE-SUMMARY-2026-08-31.md §二；8 道终审"),
                _ev("选池靠结构分散（宽基+缓周期+成长异质），不靠押单一行业",
                    "SYSTEM-VALUE-SUMMARY §四 元规律 2"),
            ],
            trigger_cn="配置类建议，不挑时机：认了就排期执行，不用等信号。",
            execution_cn=(
                "默认分批 2~3 个月（每批 1/3 左右）；一次性也站得住——已有验证结论是"
                "「一次性是无代价基准，分批是拿V型反弹的损失换更低的平均成本」，两种都是合理选择。"
            ),
        ))

    # ── R2 单一重仓（certified 纪律 + management 动作）──
    top = max(holdings, key=lambda h: h["market_value"], default=None)
    if top and top["market_value"] / total > 0.15:
        advices.append(Advice(
            advice_id="R2_single_fund_concentration",
            priority=2,
            strength="certified",
            title_cn=(f"「{top['name']}」一只占组合 "
                      f"{top['market_value'] / total * 100:.0f}%——建议设集中度上限"),
            detail_cn=(
                f"现状：这只主动基金市值 {top['market_value']:,.0f} 元，是组合第一大单一持仓。"
                "系统的组合规律是「结构分散优于押注」：单只主动基金同时承担赛道风险和基金经理风险，"
                "超过组合 15% 就值得拆。方向：一部分换宽基篮子（见上一条），或换同赛道指数基金"
                "（去掉经理风险，保留赛道观点）。"
            ),
            evidence=[
                _ev("单只占比上限 15%（结构分散纪律）", "SYSTEM-VALUE-SUMMARY §四 元规律 2"),
                _ev("主动基金 vs 指数：经理风险无回测对冲手段（叙事层判断）",
                    "AGENTS.md 基本面=叙事标注层原则"),
            ],
            trigger_cn="与 R1 同批执行即可，不单独择时。",
            execution_cn="分批换出（卖出侧分 2~3 批），避免一天内大额申赎。",
        ))

    # ── R3 真实暴露修正（observation，依赖季报穿透）──
    # 亚洲/新兴市场类基金含 A股+港股是产品设计，不算「名不副实」，排除。
    fake_global: list[tuple[dict, float]] = []
    for h in holdings:
        if not h["group_key"].startswith("us_"):
            continue
        if any(k in h["name"] for k in ("亚洲", "新兴市场")):
            continue
        exp = exposures.get(h["holding_id"])
        if exp is None:
            continue
        cn_hk = exp.by_market_pct.get("cn", 0.0) + exp.by_market_pct.get("hk", 0.0)
        share = cn_hk / exp.top10_total_pct * 100 if exp.top10_total_pct > 0 else 0
        if share >= 40:
            fake_global.append((h, share))
    if fake_global:
        worst_name, worst_share = fake_global[0][0]["name"], fake_global[0][1]
        names = "、".join(f"{h['name']}（约 {s:.0f}%）" for h, s in fake_global[:3])
        advices.append(Advice(
            advice_id="R3_real_exposure_correction",
            priority=1,
            strength="observation",
            title_cn=f"「全球」基金名不副实：{worst_name}前十大里 A股+港股约占 {worst_share:.0f}%",
            detail_cn=(
                f"季报穿透发现：{names}——这些「全球」基金实际重仓中国资产。"
                "含义：你真实的中国资产敞口比页面名义分组（海外 66%）更高，"
                "做「换宽基」决策时要以穿透后的真实暴露为准（页面分组卡上已标注真实分布）。"
                "这不改变任何买卖信号，只修正「我到底拿着什么」的认知。"
            ),
            evidence=[
                _ev("基金季报前十大持仓（占净值比例），天天基金公开数据",
                    "portfolio_fund_top10 表；穿透=叙事标注层红线（AGENTS.md）"),
            ],
            trigger_cn="每季度季报发布后自动刷新（约 1/4/7/10 月下旬）。",
            execution_cn="无需交易动作：修正认知与统计口径即可。",
        ))

    # ── R4 尾仓清理（management）──
    tiny = [h for h in holdings if h["market_value"] < 100]
    if tiny:
        names = "、".join(f"{h['name']}（{h['market_value']:.0f} 元）" for h in tiny)
        advices.append(Advice(
            advice_id="R4_tiny_positions",
            priority=4,
            strength="management",
            title_cn=f"{len(tiny)} 只不足百元的尾仓建议清掉",
            detail_cn=(
                f"现状：{names}。碎片仓位没有任何管理价值（涨跌对组合影响可忽略，"
                "却占注意力），清掉换成任意一只主仓。纯打理建议，与回测无关。"
            ),
            evidence=[_ev("管理建议（无回测依据）", "—")],
            trigger_cn="任意交易日。",
            execution_cn="一次性赎回即可。",
        ))

    # ── R5 海外纪律（observation，常驻 info）──
    us_pct = sum(g["pct"] for g in groups if g["market"] == "us")
    if us_pct > 0:
        advices.append(Advice(
            advice_id="R5_overseas_hold_discipline",
            priority=5,
            strength="certified",
            title_cn=f"海外仓位（约 {us_pct:.0f}%）：不调、不择时，唯一纪律是恐慌时别割",
            detail_cn=(
                "系统用 40 年美股数据反复验证过：对海外市场做任何「挑时机加减仓」"
                "都跑不赢简单拿着不动（14 只美股标的无一例外）。所以这组的操作纪律就是不动；"
                "系统对它的唯一价值是市场恐慌时提醒你「这正是不该卖的时候」。"
            ),
            evidence=[
                _ev("美股择时全输持有（12 只个股 + SPY/QQQ，两引擎 14/14 输定投）",
                    "experiments/us-stocks-timing-boundary-2026-09-04.md"),
                _ev("证伪清单：美股任何形式的闸", "SYSTEM-VALUE-SUMMARY §三"),
            ],
            trigger_cn="无需动作；市场极端恐慌时系统会出提醒。",
            execution_cn="持有 + 按既约定投继续。",
        ))

    # ── R6 港股边界（observation，常驻 info）──
    hk_pct = sum(g["pct"] for g in groups if g["market"] == "hk")
    if hk_pct > 0:
        advices.append(Advice(
            advice_id="R6_hk_unverified_zone",
            priority=6,
            strength="observation",
            title_cn=f"港股仓位（约 {hk_pct:.0f}%）：未验证区域，只看参考、不听指挥",
            detail_cn=(
                "系统从未对港股做过历史检验，A 股和美股的结论都不能往它身上套。"
                "这组只提供看图参考（趋势阶段标注），不产生买卖建议；"
                "若有加减仓想法，按你自己的判断走，系统不背书。"
            ),
            evidence=[_ev("系统回测池不含港股（诚实边界）",
                          "docs/system-architecture-and-decisions-2026-09-04.md §1")],
            trigger_cn="—",
            execution_cn="—",
        ))

    # ── R7 行业时机（candidate，挂板块阶段）──
    stages_asof = str(sector_stages.get("_as_of", ""))
    for g in groups:
        sector_names = GROUP_SECTORS.get(g["group_key"])
        if not sector_names:
            continue
        found = [(n, sector_stages[n]) for n in sector_names
                 if isinstance(sector_stages.get(n), dict)]
        if not found:
            continue
        # 取「最警惕」的板块：rank 越大越警惕（decline > distribution > accumulation > markup）
        worst = max(found, key=lambda kv: (
            {"markup": 0, "accumulation": 1, "distribution": 2, "decline": 3}
            .get(kv[1]["stage"], 1)
        ))
        action, action_detail = _STAGE_ADVICE[worst[1]["stage"]]
        rs = worst[1].get("rs_pctile")
        rs_txt = f"、相对强弱第 {rs:.0f} 分位" if rs is not None else ""
        advices.append(Advice(
            advice_id=f"R7_{g['group_key']}_stage",
            priority=3,
            strength="candidate",
            title_cn=f"{g['name']}：板块「{worst[0]}」处于{STAGE_CN[worst[1]['stage']]}期——{action}",
            detail_cn=(
                f"{action_detail}（板块阶段快照 {stages_asof}{rs_txt}）。"
                "依据的边界结论：行业类标的看自身趋势、不跟随大盘冷热。"
                "注意：这是提示不是指令——板块阶段判定是研究代理口径，"
                "最终动作仍由你按计划纪律决定。"
            ),
            evidence=[
                _ev("行业不跟随大盘；行业域「三档调仓」比全进全出稳",
                    "experiments/astock-panel-timing-2026-09-04.md；AU 扩展面板"),
                _ev("板块阶段判定口径（research_proxy）",
                    "docs/plan-sector-trend-page.md；sector_trend_snapshot.json"),
            ],
            trigger_cn="板块阶段变化时本条自动更新（每日收盘后刷新）。",
            execution_cn="减仓类动作分批执行；加仓类动作等标志性信号确认。",
        ))

    advices.sort(key=lambda a: a.priority)
    return advices
