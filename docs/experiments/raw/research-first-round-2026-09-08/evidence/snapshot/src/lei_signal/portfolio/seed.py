"""持仓快照种子数据（2026-09-04 养基宝截图录入）。

数据来源：7 张持仓截图（IMG_4739~4745）逐只识别，共 29 只场外基金、
合计 ¥85,613.10。基金代码截图未显示，全部留空待补。

分组结论（verdict_cn）是系统已验证回测结论的大白话翻译，措辞红线：
不使用内部速记词（腿/轨道/择时/档位等），第一次出现的概念就地解释。
结论依据（verdict_basis）是给下一个开发者看的文档指针，允许技术表述。
"""
from __future__ import annotations

import json
import sqlite3

from lei_signal.portfolio.models import (
    MARKET_CN,
    MARKET_HK,
    MARKET_OTHER,
    MARKET_US,
    META_AS_OF,
    META_DATA_SOURCE,
    META_OBSERVATIONS,
    PortfolioGroup,
    PortfolioHolding,
)
from lei_signal.portfolio.store import holding_id_for, set_meta, upsert_group, upsert_holding

AS_OF = "2026-09-04"

DATA_SOURCE_CN = "养基宝 App 截图录入（7 张，2026-09-04）；基金代码截图未显示，待补"

SEED_GROUPS: tuple[PortfolioGroup, ...] = (
    PortfolioGroup(
        group_key="us_index",
        name="海外·纳指/标普指数",
        market=MARKET_US,
        sort_order=1,
        verdict_cn=(
            "系统对美股最硬的一条结论：拿着不动最好。各种「挑时机加减仓」的方法"
            "用 40 年美股数据检验，全部跑不赢简单持有（14 只美股标的无一例外）。"
            "这组是纳指100、标普500 的被动指数基金，操作纪律就一条：不因市场涨跌"
            "调仓，定投/持有；系统唯一会做的提醒是恐慌期别割在坑里。"
        ),
        verdict_basis=(
            "us-stocks-timing-boundary-2026-09-04（12 只美股个股+SPY/QQQ，两引擎 14/14 输定投）；"
            "证伪清单「美股任何形式的闸」（SYSTEM-VALUE-SUMMARY-2026-08-31）"
        ),
    ),
    PortfolioGroup(
        group_key="us_tech_active",
        name="海外·全球科技主动",
        market=MARKET_US,
        sort_order=2,
        verdict_cn=(
            "主动基金，重仓全球科技（以美股为主，占本组合金额四成）。海外市场不跟"
            "A股冷热走，「挑时机」在这里没有优势，纪律同样是拿着不动、不做波段。"
            "后续待做「季报穿透」（拆开看每只基金的前十大持仓，确认美股占比和具体"
            "赛道），穿透后结论预计不变，但能看住基金经理有没有偷偷换风格。"
        ),
        verdict_basis=(
            "AW/AJ 择时有效边界（美股全境不配宽度择时）；季报穿透为已登记的后续钩子"
        ),
    ),
    PortfolioGroup(
        group_key="us_growth_em",
        name="海外·全球成长与新兴市场",
        market=MARKET_US,
        sort_order=3,
        verdict_cn=(
            "全球分散的主动基金（含新兴市场、亚洲机会），和上一组的区别是地域更散、"
            "风险本身更平。同样适用「海外=拿着不动」：不调仓、不挑时机。"
        ),
        verdict_basis=(
            "bform「美股=持有资产」多轮确认；cross-market-pairing（跨市场分散才有增量）"
        ),
    ),
    PortfolioGroup(
        group_key="cn_info",
        name="A股·信息产业/半导体/AI",
        market=MARKET_CN,
        sort_order=4,
        verdict_cn=(
            "这就是你的「A股通信/科技」仓位（易方达信息产业重仓通信电子，一只扛起九成）。"
            "已验证的规律：A股行业类标的不跟随大盘冷热——大盘涨它可能照跌。加减仓依据"
            "是行业自身的趋势状态：通信/半导体板块趋势向上→拿住；趋势破坏→按规则减。"
            "系统的行业板块页和四种买卖点提示（趋势回调/横盘突破/破底翻/假摔反转）适用。"
        ),
        verdict_basis=(
            "AY 81 只 A 股个股面板（独立行业三档更稳）；AU 扩展面板（行业域三档优于二元）；"
            "LEI 四模块规格 trading-spec-v1.md"
        ),
    ),
    PortfolioGroup(
        group_key="cn_metal",
        name="A股·有色金属",
        market=MARKET_CN,
        sort_order=5,
        verdict_cn=(
            "有色金属是独立行情行业，加减仓同样看行业自身趋势（自选池已有色板块指数，"
            "每日机会扫描已覆盖，无需额外配置）。"
        ),
        verdict_basis="独立行业边界（AU 扩展面板：消费/医药/半导体等行业三档明显更稳）",
    ),
    PortfolioGroup(
        group_key="cn_green_other",
        name="A股·绿电与其他",
        market=MARKET_CN,
        sort_order=6,
        verdict_cn=(
            "绿电（注：截图里没有电池基金，天弘绿色电力是唯一新能源类持仓）按独立行业"
            "趋势参考。消费、红利两只合计不足 10 元，属于清仓残留的观察尾仓，建议清理"
            "合并减少碎片（这是管理建议，不是系统结论）。"
        ),
        verdict_basis="独立行业边界；尾仓清理为管理建议（非回测结论）",
    ),
    PortfolioGroup(
        group_key="hk_tech",
        name="港股·恒生科技/互联网",
        market=MARKET_HK,
        sort_order=7,
        verdict_cn=(
            "系统有恒生科技指数的日线数据，但从未对港股做过历史检验——这组属于"
            "「未验证区域」：只提供看图参考（趋势阶段标注），不产生买卖指令，"
            "也不要拿 A 股或美股的结论往它身上套。"
        ),
        verdict_basis="系统回测池不含港股（诚实边界，docs/system-architecture §1）",
    ),
    PortfolioGroup(
        group_key="stable",
        name="稳健·偏债混合",
        market=MARKET_OTHER,
        sort_order=8,
        verdict_cn=(
            "偏债混合（6 个月持有期），波动小、有持有期锁定，技术判断不适用。放着就好。"
        ),
        verdict_basis="—",
    ),
)


def _h(group_key: str, name: str, value: float, ret: float | None,
       tags: tuple[str, ...] = (), note: str = "") -> PortfolioHolding:
    return PortfolioHolding(
        holding_id=holding_id_for(name),
        group_key=group_key,
        name=name,
        code=None,
        market_value=value,
        return_pct=ret,
        tags=tags,
        note=note,
        as_of=AS_OF,
    )


SEED_HOLDINGS: tuple[PortfolioHolding, ...] = (
    # ── 海外·纳指/标普指数 ──
    _h("us_index", "摩根纳斯达克100指数(QDII)A", 842.37, 9.40, ("QDII", "定投")),
    _h("us_index", "摩根纳斯达克100指数(QDII)C", 240.41, 0.17, ("QDII",)),
    _h("us_index", "摩根标普500指数(QDII)A", 1889.55, 8.91, ("QDII",)),
    _h("us_index", "摩根标普500指数(QDII)C", 190.04, 0.02, ("QDII",)),
    _h("us_index", "南方纳斯达克100指数(QDII)A", 1274.04, 7.97, ("QDII", "定投")),
    _h("us_index", "大成纳斯达克100ETF联接(QDII)C", 259.60, 0.00, ("QDII", "定投")),
    _h("us_index", "易方达标普500指数(QDII-LOF)A", 280.79, 7.99, ("QDII",)),
    _h("us_index", "天弘标普500(QDII-FOF)A", 200.00, 0.00, ("QDII", "定投")),
    # ── 海外·全球科技主动 ──
    _h("us_tech_active", "国富全球科技互联混合(QDII)C", 3412.91, -6.75, ("QDII",)),
    _h("us_tech_active", "国富全球科技互联混合(QDII)A", 4094.96, -8.18, ("QDII", "定投")),
    _h("us_tech_active", "富国全球科技互联网股票(QDII)A", 9910.71, -12.46, ("QDII",)),
    _h("us_tech_active", "富国全球科技互联网股票(QDII)C", 17182.14, -13.29, ("QDII",)),
    # ── 海外·全球成长与新兴市场 ──
    _h("us_growth_em", "易方达全球成长精选混合(QDII)A", 8441.53, 23.24, ("QDII", "定投")),
    _h("us_growth_em", "易方达全球优质企业混合(QDII)A", 2478.91, -6.54, ("QDII",)),
    _h("us_growth_em", "天弘全球高端制造混合(QDII)A", 3239.64, -7.44, ("QDII",)),
    _h("us_growth_em", "嘉实全球产业升级股票(QDII)A", 82.89, 2.68, ("QDII",)),
    _h("us_growth_em", "建信新兴市场优选混合(QDII)C", 1164.16, -4.59, ("QDII", "定投")),
    _h("us_growth_em", "国富亚洲机会股票(QDII)A", 935.98, -6.40, ("QDII",)),
    # ── A股·信息产业/半导体/AI ──
    _h("cn_info", "易方达信息产业混合A", 16558.71, 8.35, (),
       note="组合内单一最大持仓；重仓通信/电子，即「A股通信」仓位主体"),
    _h("cn_info", "财通集成电路产业股票C", 4418.73, -16.38, ()),
    _h("cn_info", "东方人工智能主题混合C", 1453.93, -3.07, ()),
    # ── A股·有色金属 ──
    _h("cn_metal", "南方有色金属ETF联接A", 2452.43, -15.72, ()),
    _h("cn_metal", "汇添富中证细分有色金属产业主题ETF联接C", 481.07, -3.79, ()),
    # ── A股·绿电与其他 ──
    _h("cn_green_other", "天弘国证绿色电力ETF联接C", 1442.21, -3.85, (),
       note="截图内唯一新能源类持仓（绿电，非电池）"),
    _h("cn_green_other", "嘉实中证主要消费ETF发起联接C", 4.49, -10.14, (), note="清仓残留尾仓"),
    _h("cn_green_other", "华夏中证红利质量ETF联接C", 4.67, -0.51, (), note="清仓残留尾仓"),
    # ── 港股·恒生科技/互联网 ──
    _h("hk_tech", "华夏恒生科技ETF联接(QDII)C", 1846.03, -7.60, ("QDII",)),
    _h("hk_tech", "华夏恒生互联网科技业ETF联接(QDII)A", 268.04, -18.09, ("QDII", "定投")),
    # ── 稳健·偏债混合 ──
    _h("stable", "融通稳信增益6个月持有期混合A", 562.16, 16.87, (), note="偏债混合，6个月持有期"),
)

#: 组合级提示（大白话；百分比按快照计算后写死，快照更新时随 seed 重写）
SEED_OBSERVATIONS: tuple[str, ...] = (
    "海外合计约 65.5%（全球科技主动 + 全球成长 + 纳指标普指数）：系统验证结论是"
    "「海外市场不挑时机、拿着不动最好」，所以接近三分之二的仓位操作纪律就是不动，"
    "系统只负责恐慌时提醒你别割肉。",
    "A股合计约 33%，其中九成集中在信息产业（通信/电子/半导体）单一赛道：加减仓看"
    "行业自身趋势，不是大盘——这是已验证的规律（行业不跟随大盘冷热）。",
    "组合里目前没有宽基（沪深300/创业板这类）：系统历史验证最强的是「宽基篮子」"
    "方案（二十年数据：比拿着不动每年约多 12 个百分点、最深亏损少三分之一），"
    "当前仓位为零。要不要把一部分行业仓位换成宽基篮子，是待你拍板的第一问题。",
    "港股恒生科技约 2.5%：系统从未对港股做过历史检验，这组只看参考、不听指挥。",
    "两只不足 5 元的清仓残留尾仓（消费、红利）建议清理，减少碎片。",
)


def seed(conn: sqlite3.Connection) -> dict[str, int]:
    """幂等写入全部种子数据（UPSERT）。返回写入计数。"""
    for g in SEED_GROUPS:
        upsert_group(conn, g)
    for h in SEED_HOLDINGS:
        upsert_holding(conn, h)
    set_meta(conn, META_AS_OF, AS_OF)
    set_meta(conn, META_DATA_SOURCE, DATA_SOURCE_CN)
    set_meta(conn, META_OBSERVATIONS, json.dumps(list(SEED_OBSERVATIONS), ensure_ascii=False))
    conn.commit()
    return {"groups": len(SEED_GROUPS), "holdings": len(SEED_HOLDINGS)}
