"""基本面页市场观察事实；所有指标仅供叙事说明。"""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Callable

from lei_signal.fundamentals import sources
from lei_signal.fundamentals.observation_meta import observation_item


def _series_item(
    raw: dict[str, float], *, metric_id: str, label: str, universe: str,
    unit: str, source_name: str, source_url: str, reading: str,
    limitations: list[str], fetched_at: str | None, change_steps: int = 1,
) -> dict[str, Any]:
    points = sorted((day, float(value)) for day, value in raw.items())
    if not points:
        raise sources.FundamentalsSourceError(f"{metric_id} 没有有效观测")
    day, value = points[-1]
    change = round(value - points[-1 - change_steps][1], 3) if len(points) > change_steps else None
    return observation_item(
        metric_id=metric_id, label=label, market="us", universe=universe,
        value=value, unit=unit, change=change,
        comparison_period=f"前{change_steps}个有效观测日" if change is not None else None,
        observation_date=day, fetched_at=fetched_at, source_name=source_name,
        source_url=source_url, source_access="public_with_source_terms",
        history_start=points[0][0], history_end=day,
        observation_count=len(points), valid_count=len(points),
        eligible_count=None, reading=reading, limitations=limitations,
        evidence_refs=[source_url],
    )


def _missing(spec: dict[str, Any], reason: str) -> dict[str, Any]:
    return observation_item(**spec, quality_reason=reason)


def build_observations(market: str, fetch: Callable[[str, Callable[[], Any]], Any]) -> dict[str, Any]:
    """按项抓取与降级；fetch 由 service 注入 TTL 缓存。"""
    generated = datetime.now(UTC).isoformat()
    items: list[dict[str, Any]] = []
    errors: list[str] = []

    def add(spec: dict[str, Any], loader: Callable[[], dict[str, Any]]) -> None:
        try:
            items.append(loader())
        except (sources.FundamentalsSourceError, ValueError, OSError) as exc:
            errors.append(f"{spec['metric_id']}: {exc}")
            items.append(_missing(spec, "来源读取或校验失败，目前没有合格读数"))

    if market == "cn":
        base = {"market": "cn", "universe": "沪深交易所融资标的证券（可能含基金）",
                "unit": "亿元", "source_name": "东方财富融资融券历史汇总",
                "source_url": "https://data.eastmoney.com/rzrq/total.html",
                "source_access": "public_web", "reading": "只描述融资活动，不代表全部散户",
                "limitations": ["融资标的可能包括基金，不与股票成交额相除", "交易所范围和发布时间未逐日复核"]}
        for metric_id, label, key in (
            ("margin_balance", "融资余额", "rzye_yi"),
            ("margin_buy", "融资买入额", "buy_yi"),
        ):
            spec = {**base, "metric_id": metric_id, "label": label}

            def load_margin(key: str = key, spec: dict[str, Any] = spec) -> dict[str, Any]:
                hist = fetch("margin_hist:observations", lambda: sources.fetch_margin_history(90))
                points = sorted((d, float(v[key])) for d, v in hist.items() if v.get(key) is not None)
                if not points:
                    raise sources.FundamentalsSourceError("没有有效融资日值")
                day, value = points[-1]
                steps = 20 if key == "rzye_yi" else 1
                change = round(value - points[-1 - steps][1], 2) if len(points) > steps else None
                return observation_item(
                    **{**spec, "reading": ("尚未偿还的融资金额，变化反映融资余额增减，不代表全部投资者的态度。" if key == "rzye_yi" else "当日使用融资买入的金额，变化反映这类交易活跃程度。")}, value=value, change=change,
                    comparison_period=f"前{steps}个有效观测日" if change is not None else None,
                    observation_date=day, fetched_at=None,
                    history_start=points[0][0], history_end=day,
                    observation_count=len(hist), valid_count=len(points),
                    evidence_refs=[spec["source_url"]],
                )

            add(spec, load_margin)
        items.append(_missing({"metric_id": "stock_turnover", "label": "A股股票成交额",
            "market": "cn", "universe": "沪深A股股票，排除B股、基金与北交所", "unit": "亿元",
            "source_name": "沪深交易所每日成交统计（核验中）", "source_url": "https://www.sse.com.cn/market/stockdata/overview/day/", "source_access": "unverified",
            "reading": "待取得同一股票范围、同一交易日的可靠原始成交额",
            "limitations": ["已取得两日分类样本，尚缺上交所明确金额单位与深交所表内日期证明", "连续20个完整交易日资料不足，不能展示20日比较", "不可相加父子分类；不能用含基金的融资额除以股票成交额"],
            "evidence_refs": ["https://www.sse.com.cn/market/stockdata/overview/day/", "https://www.szse.cn/market/overview/index.html"]},
            "已找到交易所统计；金额单位、所属日期和连续历史仍待核实，暂不展示合计"))
    else:
        series_specs = [
            ("vix", "标普500预期波动率 VIX", "标普500期权", "指数点", "Yahoo / Cboe",
             "https://finance.yahoo.com/quote/%5EVIX/", lambda: sources.fetch_vix_history(45),
             ["期权预期波动不表示涨跌方向", "Yahoo 转发数据未核实首次发布时间"]),
            ("vxn", "纳斯达克100预期波动率 VXN", "Nasdaq-100 期权", "指数点", "FRED / Cboe",
             "https://fred.stlouisfed.org/series/VXNCLS", lambda: sources._fetch_fred_series("VXNCLS", cosd=(datetime.now(UTC).date() - timedelta(days=90)).isoformat()),
             ["期权预期波动不表示涨跌方向", "Cboe 数据再分发需遵守来源条款"]),
            ("real_yield_10y", "美国10年实际利率", "美国10年通胀保值国债", "%", "FRED / 美国财政部",
             "https://fred.stlouisfed.org/series/DFII10", lambda: sources._fetch_fred_series("DFII10", cosd=(datetime.now(UTC).date() - timedelta(days=90)).isoformat()),
             ["实际利率与股价可同涨", "不是名义利率减当月 CPI"]),
            ("hy_oas", "美国高收益债信用利差", "美国高收益债", "%", "FRED / ICE",
             "https://fred.stlouisfed.org/series/BAMLH0A0HYM2", lambda: sources._fetch_fred_series("BAMLH0A0HYM2", cosd=(datetime.now(UTC).date() - timedelta(days=90)).isoformat()),
             ["ICE 授权及历史窗口限制", "不是科技股专属指标"]),
        ]
        for metric_id, label, universe, unit, source_name, url, loader, limits in series_specs:
            spec = {"metric_id": metric_id, "label": label, "market": "us",
                    "universe": universe, "unit": unit, "source_name": source_name,
                    "source_url": url, "source_access": "public_with_source_terms",
                    "reading": {
                        "vix": "标普500期权反映的预期波动。读数上升表示预期波动加大，不表示价格一定下跌。",
                        "vxn": "纳斯达克100期权反映的预期波动。与VIX的股票范围不同，不能混称全市场恐慌。",
                        "real_yield_10y": "美国10年通胀保值国债收益率，观察实际利率水平；变化以百分点表示。",
                        "hy_oas": "高收益企业债相对国债的利差，观察借款风险补偿要求；它不是违约率。",
                    }[metric_id], "limitations": limits}
            add(spec, lambda spec=spec, loader=loader: _series_item(
                fetch(f"observations:{spec['metric_id']}", loader),
                metric_id=spec["metric_id"], label=spec["label"], universe=spec["universe"],
                unit=spec["unit"], source_name=spec["source_name"], source_url=spec["source_url"],
                reading=spec["reading"], limitations=spec["limitations"], fetched_at=None,
                change_steps=20 if spec["metric_id"] == "real_yield_10y" else 1,
            ))
        _surveys(items, errors, generated)
    if market == "us":
        # 仅解释原体系参数出处，不据原值重新分类情绪或生成交易条件。
        notes = _survey_reference_notes()
        for item in items:
            if item["metric_id"] in notes:
                item["reference_note"] = notes[item["metric_id"]]
    return {"market": market, "generated_at": generated, "items": items, "errors": errors}


def _surveys(items: list[dict[str, Any]], errors: list[str], fetched_at: str) -> None:
    from lei_signal.market_context import sentiment

    root = Path(os.environ.get("LEI_SENTIMENT_ROOT") or Path(__file__).resolve().parents[3] / "data" / "sentiment")
    for series_id, label, filename, loader, attr, unit in (
        ("naaim", "NAAIM 主动管理人自报股票敞口", "naaim.csv", sentiment.load_naaim_observations, "exposure_index", "%"),
        ("aaii", "AAII 会员未来六个月看涨减看跌", "aaii.csv", sentiment.load_aaii_observations, "bull_bear", "百分点"),
    ):
        url = "https://www.naaim.org/programs/naaim-exposure-index/" if series_id == "naaim" else "https://www.aaii.com/sentimentsurvey"
        universe = "美国主动投资管理人自报股票敞口" if series_id == "naaim" else "AAII会员未来六个月美股方向调查"
        spec = {"metric_id": series_id, "label": label, "market": "us", "universe": universe,
                "unit": unit, "source_name": series_id.upper(), "source_url": url,
                "source_access": "unknown", "reading": ("看涨比例减去看跌比例：正值说明看涨人数比例较高，负值相反；问的是未来六个月。" if series_id == "aaii" else "受访管理人自报股票敞口，可以为负或超过100%；不能读成全体机构持股比例。"),
                "limitations": ["历史文件的首次公开时间未经逐期核实，不能用于历史交易", "本地历史资料，来源声明尚未逐期核实"]}
        path = root / filename
        if not path.exists():
            items.append(_missing(spec, "未提供本地问卷历史文件"))
            continue
        try:
            observations = loader(path)
            if not observations:
                raise ValueError("文件中没有有效观测")
            # 旧采集器把无日期 NAAIM 组件贴上运行周且默认 licensed：这些行不能用于最新值。
            eligible = [o for o in observations if not (series_id == "naaim" and o.source.startswith("auto:naaim.org"))]
            if not eligible:
                items.append(_missing(spec, "仅有旧采集器推测调查周的 NAAIM 数值；没有可确认日期的观测"))
                continue
            last = eligible[-1]
            values = [float(getattr(o, attr)) for o in eligible if getattr(o, attr) is not None]
            if not values:
                raise ValueError("没有有效问卷数值")
            item = observation_item(
                **{**spec, "source_access": "local_source_claim_unverified"}, value=values[-1],
                change=round(values[-1] - values[-2], 2) if len(values) > 1 else None,
                comparison_period="上一期" if len(values) > 1 else None,
                observation_date=last.survey_week.isoformat(),
                fetched_at=None, history_start=eligible[0].survey_week.isoformat(),
                history_end=last.survey_week.isoformat(), observation_count=len(observations),
                valid_count=len(values), eligible_count=0,
                quality_reason="本地文件的授权声明和逐期首次公开时间未经核实；只供观察，不能用于历史交易回放",
                evidence_refs=[url],
            )
            if series_id == "aaii":
                item["components"] = {
                    "bullish_pct": float(last.bullish), "neutral_pct": float(last.neutral),
                    "bearish_pct": float(last.bearish),
                }
            items.append(item)
        except (ValueError, OSError) as exc:
            errors.append(f"{series_id}: {exc}")
            items.append(_missing(spec, "问卷历史资料未通过校验，无法确认合格读数"))


def _survey_reference_notes() -> dict[str, str]:
    from lei_signal.domain.rules_config import get_rule

    fallback = "原体系调查确认参考值暂不可读取；本页不按调查值判断短期顶底。"
    try:
        rule = get_rule("module_e_sentiment_extreme")
        aaii_low, aaii_high = rule.param("aaii_extreme")
        naaim_low, naaim_high = rule.param("naaim_extreme")
        suffix = "源自LEI模块E，须结合市场宽度（股票站上均线的比例）；尚未证明能定位纳斯达克短期顶底。"
        return {
            "aaii": f"原体系确认参考：看涨减看跌≤{aaii_low * 100:g}或≥{aaii_high * 100:g}个百分点。{suffix}",
            "naaim": f"原体系确认参考：自报股票敞口≤{naaim_low * 100:g}%或≥{naaim_high * 100:g}%。{suffix}",
        }
    except (KeyError, TypeError, ValueError, FileNotFoundError):
        return {"aaii": fallback, "naaim": fallback}
