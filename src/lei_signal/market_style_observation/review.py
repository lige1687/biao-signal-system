"""Five explicit answers; source facts are separate from unanswerable fields."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from .conditions import NFCI, OVERLAY_URL, market_volatility
from .evidence import _get_json, _sources_for
from .portfolio_review import summarize_portfolio

STYLE_FACTS = json.loads(Path(__file__).with_name("style_facts.json").read_text())
QUESTIONS = [
    "风格自己赚钱了吗？收益、下跌和波动怎样？",
    "有没有跑赢母指数？",
    "集中在哪些行业和股票？收益由谁贡献？",
    "当前表现与估值处在什么位置？",
    "我们的策略是否重复承担同一种风险？",
]


def portfolio_answer(portfolio: dict) -> str:
    if not portfolio.get("available"):
        return "策略比较尚未取得，不能回答共同亏损与重叠。"
    h = portfolio["history"]
    if not h["common_valid_return_days"]:
        return "已取得账户结构，但没有共同有效收益记录，不能回答一起涨跌或共同亏损。"
    months = h["monthly"]
    corr = h["return_correlation_recomputed"]
    corr_text = f"{corr:.3f}" if corr is not None else "未取得"
    label = "A股" if portfolio["market"] == "CN" else "美股"
    return (f"{label}两方案历史日收益相关{corr_text}；"
            f'{h["common_valid_return_days"]}个共同有效收益日中{h["both_down_days"]}日同跌，'
            f'{months["common_months"]}个月中{months["both_down_months"]}月同跌'
            f'（{h["period_start"]}至{h["period_end"]}）。')


def question_cards(portfolio: dict, market: str) -> list[dict]:
    styles, parent = STYLE_FACTS["styles"], STYLE_FACTS["parent"]
    def card(n, fact, reading, missing, sources, data_date=STYLE_FACTS["asof"]):
        return {"id": f"q{n}", "topic": f"q{n}", "title": QUESTIONS[n-1],
                "fact": fact, "reading": reading, "watch": missing,
                "data_date": data_date, "available": True,
                "coverage": "限定月末已回答" if n == 2 else "部分回答",
                "source_ids": sources}
    names = "、".join(s["name"] for s in styles)
    sources = ["msci_momentum", "msci_quality", "msci_value", "msci_minvol"]
    returns = "、".join(f'{s["returnsPct"]["oneYear"]:+.2f}%' for s in styles)
    vols = "、".join(f'{s["threeYearAnnualizedVolPct"]:.2f}%' for s in styles)
    drawdowns = "、".join(f'{s["historicalMaximumDrawdown"]["lossPct"]:.2f}%' for s in styles)
    differences = "、".join(f'{s["returnDifferencePoints"]["oneYear"]:+.2f}' for s in styles)
    concentration = "；".join(
        f'{s["name"]}：{max(((k,v) for k,v in s["sectorWeightsPct"].items() if v is not None), key=lambda kv:kv[1])[0]}'
        f'{max(v for v in s["sectorWeightsPct"].values() if v is not None):.2f}%，前十{s["topTenTotalPct"]:.2f}%'
        for s in styles)
    pe = "、".join(f'{s["pe"]:.2f}' for s in styles)
    q5_fact = portfolio_answer(portfolio)
    cards = [
        card(1, f"截至9月末，近1年四类都上涨：{names}依次{returns}；近3年年化波动依次{vols}，母指数{parent['threeYearAnnualizedVolPct']:.2f}%。",
             f"最小波动起伏较小，也少赚；动量近1年涨幅最高，起伏也最大。各自长期最深跌幅依次{drawdowns}；起始年份不同，不能作为同期间比较，具体日期见风格详情。",
             "当前离高点跌幅、统一期间最大跌幅与恢复时间仍缺连续日/月总回报；不能用年度折线估算。", sources),
        card(2, f"近1年相对MSCI World（+{parent['returnsPct']['oneYear']:.2f}%），{names}差额依次{differences}个百分点。",
             "这一期间动量、价值领先，质量略落后，最小波动明显落后；近3个月价值领先，而动量落后，期限会改变结论。",
             "四种期间的同口径差额已在风格表列齐；周/月连续风格切换仍不能由年度端点判断。", sources),
        card(3, concentration + "。",
             "质量的前十集中度最高；这说明当前依赖哪些行业和股票，不能据此断言过去收益由谁贡献。",
             "收益贡献仍未回答：缺各期完整成分权重、成分回报与调仓记录；母指数行业权重差额也尚未核齐。", sources),
        card(4, f"同日市盈率：{names}依次{pe}倍，母指数{parent['pe']:.2f}倍；市净率和股息率也已并列。",
             "质量、动量的市盈率高于母指数；价值、最小波动低于母指数。这只是当期相对估值，不证明处于自身历史高位或低位。",
             "历史估值分位、连续相对走势的位置和当前离高点幅度仍未回答，缺对应历史序列。", sources),
        card(5, q5_fact,
             "两个方案都含低波动选择规则；同跌与相关描述历史共同风险，尚不能分清低波、市场和行业各解释多少。",
             "实际持仓权重、行业/风格收益分解与真实账户共同亏损仍未取得；历史模拟、目标名单和实际持仓必须分开。",
             ["strategy_portfolios"], None),
    ]
    if not portfolio.get("available") or not portfolio.get("history", {}).get("common_valid_return_days"):
        cards[4]["available"] = False
        cards[4]["reading"] = "缺少共同有效收益资料，暂不能判断一起涨跌或分散风险的效果。"
    short_answers = [
        "近1年四类均上涨；动量涨幅最高，波动也最大。",
        "近1年动量、价值领先；质量略落后，最小波动明显落后。",
        "质量前十最集中（39.24%）；历史收益贡献仍未回答。",
        "质量、动量市盈率高于母指数；自身历史位置仍未回答。",
        portfolio.get("conclusion", "缺少策略比较，暂不能回答。"),
    ]
    for item, short in zip(cards, short_answers):
        item["short_answer"] = short
    return cards


def apply_daily_answers(cards: list[dict], daily: dict) -> None:
    """Update price-based answers only; monthly holdings/valuations stay dated."""
    if not daily.get("available"):
        return
    styles = [s for s in daily["series"] if s["id"] != "world"]
    parent = next(s for s in daily["series"] if s["id"] == "world")
    def metric(key, unit):
        return "、".join(f'{s["name"]}{s[key]:+.2f}{unit}' if s[key] is not None else f'{s["name"]}资料不齐' for s in styles)
    period = f'{daily["start"]}至{daily["end"]}'
    warning = " 日线更新失败或日期落后，先核资料日。" if daily.get("stale") or daily.get("refresh_failed") else ""
    cards[0].update(
        fact=f'{period}，收益：{metric("return_pct", "%")}；同期间最大下跌：{metric("max_drawdown_pct", "%")}；年化波动：{metric("volatility_pct", "%")}。',
        reading="统一期间，用每日收盘值比较；波动按252个交易日换算，最大下跌是从期间内某个高点到随后低点的跌幅。",
        short_answer=f'近1年收益：{metric("return_pct", "%")}。',
        watch="已答近1年自身收益、期间内回撤和波动；未计算更长历史的恢复时间与真实产品费税。" + warning,
        coverage="近1年日线已回答", data_date=daily["end"], source_ids=["msci_daily"])
    cards[1].update(
        fact=f'{period}，母指数收益{parent["return_pct"]:+.2f}%；风格减母指数的收益差额：{metric("excess_pp", "个百分点")}。',
        reading="正值表示这一段跑赢，负值表示落后；下方日线可切三个月、一年、三年，观察相对强弱如何变化。",
        short_answer=f'近1年较母指数：{metric("excess_pp", "个百分点")}。',
        watch="本行固定近1年；图表所选期间不同，排序可能变化。历史领先不保证继续领先。" + warning,
        coverage="同期间日线已回答", data_date=daily["end"], source_ids=["msci_daily"])
    cards[3]["fact"] += f' 日线截至{daily["end"]}，距近1年内已见高点：{metric("current_drawdown_pct", "%")}。'
    cards[3]["watch"] = "当前相对表现与近1年内高点距离已可观察；完整历史估值分位仍缺资料。近1年高点不是历史最高点。" + warning
    cards[3]["short_answer"] = "日线可看当前相对表现及近1年高点距离；自身历史估值位置仍未回答。"
    cards[3]["source_ids"] = [*cards[3]["source_ids"], "msci_daily"]
    cards[3]["data_date"] = f'日线 {daily["end"]} / 估值 {STYLE_FACTS["asof"]}'


def build_review(market: str, *, get_json=_get_json, daily: dict | None = None) -> dict:
    portfolio = summarize_portfolio(get_json("http://127.0.0.1:8028/api/strategy-portfolios") or {}, market)
    cards = question_cards(portfolio, market)
    apply_daily_answers(cards, daily or {})
    return {
        "asof": datetime.now(timezone.utc).isoformat(),
        "market": market,
        "questions": cards,
        "style_daily_date": daily.get("end") if daily and daily.get("available") else None,
        "portfolio": portfolio,
        "volatility": market_volatility(get_json(OVERLAY_URL), market),
        "nfci": NFCI,
        "sources": _sources_for(market),
        "completion": "partial",
        "missing": ([] if daily and daily.get("available") else ["风格连续日/月总回报"]) + ["完整历史成分及权重与收益贡献",
                    "历史估值分位", "策略实际持仓权重与风格收益分解",
                    "持续自动资料更新与许可资格"],
    }
