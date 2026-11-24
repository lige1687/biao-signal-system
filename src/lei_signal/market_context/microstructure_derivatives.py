"""Build a dated derivatives observation packet from saved public source responses.

This module only publishes observations. It does not create trading signals.
"""

from __future__ import annotations

import csv
import io
import json
import math
import re
from datetime import date, datetime, timezone
from pathlib import Path


SOURCE_DIR = Path("/Volumes/win+mac通用/LeiSignal-新实验结果/microstructure-observations-20261108/derivatives")
OUTPUT = Path("web/public/research/microstructure-observations-20261108/derivatives.json")
SSE_PCR_URL = "https://www.sse.com.cn/assortment/options/date/"
SSE_IV_URL = "https://www.sse.com.cn/assortment/options/risk/"
CBOE_PCR_URL = "https://www.cboe.com/markets/us/options/market-statistics/daily"
CBOE_COR_URL = "https://cdn.cboe.com/api/global/us_indices/daily_prices/COR3M_History.csv"
CFFEX_RULES = {
    "IF": "https://www.cffex.com.cn/u/cms/www/202003/27165505w3j5.pdf",
    "IC": "https://www.cffex.com.cn/u/cms/www/202003/27165958okn6.pdf",
    "IH": "https://www.cffex.com.cn/u/cms/www/202003/27165822h30l.pdf",
    "IM": "https://www.cffex.com.cn/u/cms/www/202207/182020307zry.pdf",
}


def _number(value: object) -> float | None:
    try:
        result = float(str(value).replace(",", ""))
        return result if math.isfinite(result) else None
    except (ValueError, TypeError):
        return None


def put_call_ratios(row: dict) -> tuple[float | None, float | None]:
    """Return put/call ratios by traded contracts and by open contracts."""
    put_volume, call_volume = _number(row.get("PUT_VOLUME")), _number(row.get("CALL_VOLUME"))
    put_oi, call_oi = _number(row.get("LEAVES_PUT_QTY")), _number(row.get("LEAVES_CALL_QTY"))
    return (
        put_volume / call_volume if put_volume is not None and put_volume >= 0 and call_volume and call_volume > 0 else None,
        put_oi / call_oi if put_oi is not None and put_oi >= 0 and call_oi and call_oi > 0 else None,
    )


def _fourth_wednesday(year: int, month: int) -> date:
    first_wednesday = next(day for day in range(1, 8) if date(year, month, day).weekday() == 2)
    return date(year, month, first_wednesday + 21)


def atm_iv_proxy(rows: list[dict], observation_date: str, underlying: str) -> tuple[float, str, str] | None:
    """Nearest listed monthly expiry, same-strike call/put with delta nearest ±0.5.

    This is a deliberately labelled ATM proxy, never a constant-maturity QVIX.
    """
    day = date.fromisoformat(observation_date)
    pairs: dict[tuple[str, str], dict[str, tuple[float, float]]] = {}
    for row in rows:
        code = str(row.get("CONTRACT_ID", ""))
        match = re.fullmatch(rf"{underlying}([CP])(\d{{4}})M(\d+)", code)
        if not match:
            continue
        expiry_code = match.group(2)
        expiry = _fourth_wednesday(2000 + int(expiry_code[:2]), int(expiry_code[2:]))
        if day > expiry:
            continue
        side = match.group(1)
        delta, iv = _number(row.get("DELTA_VALUE")), _number(row.get("IMPLC_VOLATLTY"))
        if delta is None or iv is None or iv <= 0 or iv > 5:
            continue
        pairs.setdefault((match.group(2), match.group(3)), {})[side] = (delta, iv)
    candidates = []
    for (expiry, strike), pair in pairs.items():
        if "C" in pair and "P" in pair:
            cd, civ = pair["C"]
            pd, piv = pair["P"]
            score = abs(cd - 0.5) + abs(pd + 0.5)
            candidates.append((expiry, score, strike, 100 * (civ + piv) / 2))
    if not candidates:
        return None
    expiry, _, strike, value = min(candidates)
    return round(value, 3), expiry, strike


def annualized_basis(future: float, spot: float, future_at: str, spot_at: str, expiry: str) -> float | None:
    """Simple annualized F/S basis in percent, requiring exact quote alignment."""
    try:
        ft, st = datetime.fromisoformat(future_at), datetime.fromisoformat(spot_at)
        remaining = (date.fromisoformat(expiry) - ft.date()).days
        if ft != st or ft.tzinfo is None or st.tzinfo is None or remaining <= 0 or spot <= 0 or future <= 0:
            return None
        value = (future / spot - 1) * (365 / remaining) * 100
        return value if math.isfinite(value) else None
    except (ValueError, TypeError, ZeroDivisionError):
        return None


def _card(id: str, title: str, market: str, unit: str, scope: str, meaning: str,
          source_name: str, source_url: str, points: list[dict], limitations: list[str],
          details: list[dict] | None = None, lines: list[dict] | None = None) -> dict:
    return {
        "id": id, "title": title, "market": market, "unit": unit,
        "frequency": "daily", "scope": scope, "meaning": meaning,
        "sourceName": source_name, "sourceUrl": source_url,
        "refreshedAt": datetime.now(timezone.utc).isoformat(), "refreshMode": "snapshot",
        "points": points, "limitations": limitations,
        "percentileWindow": None,
        **({"latestDetails": details} if details else {}),
        **({"lines": lines} if lines else {}),
    }


def _sse_rows(source_dir: Path, kind: str) -> dict[str, list[dict]]:
    result = {}
    for path in sorted(source_dir.glob(f"sse_{kind}_*.json")):
        day = path.stem.split("_")[-1]
        if re.fullmatch(r"\d{8}", day):
            try:
                file_day = date(int(day[:4]), int(day[4:6]), int(day[6:]))
            except ValueError:
                continue
            if file_day > date.today():
                continue
            doc = json.loads(path.read_text())
            rows = doc.get("result", [])
            if isinstance(rows, list) and rows and all(row.get("TRADE_DATE") == file_day.isoformat() for row in rows):
                result[f"{day[:4]}-{day[4:6]}-{day[6:]}"] = rows
    return result


def _cboe_ratio(html: str, label: str) -> float | None:
    match = re.search(r'\\"name\\":\\"' + re.escape(label) + r'\\",\\"value\\":\\"([0-9.]+)\\"', html)
    return _number(match.group(1)) if match else None


def _cboe_json_ratio(doc: dict, label: str) -> float | None:
    for item in doc.get("ratios") or []:
        if item.get("name") == label:
            return _number(item.get("value"))
    return None


def _cboe_date(html: str) -> str | None:
    match = re.search(r'\\"selectedDate\\":\\"(\d{4}-\d{2}-\d{2})\\"', html)
    return match.group(1) if match else None


def strict_prior_percentiles(points: list[dict], window: int) -> list[dict]:
    """Prior-window midrank percentile; ties receive half weight.

    A missing observation within the requested window invalidates that day's
    percentile. The current observation is never in its own reference set.
    """
    if window < 1:
        raise ValueError("window must be positive")
    result = []
    for index, point in enumerate(points):
        prior = [item["value"] for item in points[max(0, index - window):index]]
        current = point["value"]
        value = None
        if current is not None and len(prior) == window and all(x is not None for x in prior):
            below = sum(x < current for x in prior)
            tied = sum(x == current for x in prior)
            value = round(100 * (below + tied / 2) / window, 2)
        result.append({"date": point["date"], "value": value})
    return result


def _third_friday(year: int, month: int) -> date:
    first_friday = next(day for day in range(1, 8) if date(year, month, day).weekday() == 4)
    return date(year, month, first_friday + 14)


def _front_month_expiry(day: date) -> date:
    """CFFEX front-month expiry: third Friday, roll forward after expiry."""
    expiry = _third_friday(day.year, day.month)
    if day > expiry:
        expiry = _third_friday(day.year + 1, 1) if day.month == 12 else _third_friday(day.year, day.month + 1)
    return expiry


def _main_futures_basis_points(source_dir: Path, product: str, index: str) -> tuple[list[dict], str | None]:
    """Main-contract continuous series (max open interest) vs same-session spot close."""
    main_path = source_dir / f"main_{product.lower()}_daily.json"
    spot_path = source_dir / f"eastmoney_{index}_daily.json"
    if not main_path.exists() or not spot_path.exists():
        return [], None
    spot_doc = json.loads(spot_path.read_text())
    spot = {line.split(",")[0]: _number(line.split(",")[2])
            for line in (spot_doc.get("data") or {}).get("klines") or [] if len(line.split(",")) >= 3}
    points, last_contract = [], None
    for row in json.loads(main_path.read_text()):
        day = row.get("date")
        close, expiry = _number(row.get("close")), row.get("expiry")
        if not day or close is None or not expiry or day < "2024-11-01" or day >= date.today().isoformat():
            continue
        if date.fromisoformat(day).weekday() >= 5 or _number(spot.get(day)) is None:
            continue
        remaining = (date.fromisoformat(expiry) - date.fromisoformat(day)).days
        if remaining <= 0:
            continue
        value = (close / spot[day] - 1) * 365 / remaining * 100
        points.append({"date": day, "value": round(value, 3)})
        last_contract = row.get("contract")
    return points, last_contract


def build_packet(source_dir: Path = SOURCE_DIR) -> dict:
    cards: list[dict] = []
    unavailable: list[dict] = []
    sse_stats, sse_risk = _sse_rows(source_dir, "pcr"), _sse_rows(source_dir, "iv")
    volume_points, oi_points, iv_points = [], [], []
    iv_detail = None
    for day, rows in sorted(sse_stats.items()):
        row = next((r for r in rows if r.get("SECURITY_CODE") == "510300" and r.get("TRADE_DATE") == day), None)
        if row:
            volume, oi = put_call_ratios(row)
            volume_points.append({"date": day, "value": round(volume, 4) if volume is not None else None})
            oi_points.append({"date": day, "value": round(oi, 4) if oi is not None else None})
    for day, rows in sorted(sse_risk.items()):
        result = atm_iv_proxy(rows, day, "510300")
        if result:
            value, expiry, strike = result
            iv_points.append({"date": day, "value": value})
            iv_detail = [{"label": "合约月份", "value": f"20{expiry[:2]}-{expiry[2:]}"},
                         {"label": "同档行权价代码", "value": strike}]
    if volume_points:
        scope = "上交所华泰柏瑞沪深300ETF（510300）期权，所有挂牌合约"
        cards.extend([
            _card("cn-300etf-pcr-volume", "沪深300ETF 期权成交量 PCR", "cn", "倍", scope,
                  "认沽成交张数相对认购成交张数；看当日期权交易构成。", "上交所每日统计", SSE_PCR_URL,
                  volume_points, ["成交量反映交易，不区分开仓、平仓与交易动机；仅覆盖该ETF期权。"]),
            _card("cn-300etf-pcr-oi", "沪深300ETF 期权持仓量 PCR", "cn", "倍", scope,
                  "认沽未平仓张数相对认购未平仓张数；看日末存量构成。", "上交所每日统计", SSE_PCR_URL,
                  oi_points, ["持仓量是日末存量，与当日成交量PCR不同；仅覆盖该ETF期权。"]),
        ])
    else:
        unavailable.append({"id": "cn-300etf-pcr", "title": "沪深300ETF期权PCR", "market": "cn", "reason": "未取得有效上交所510300每日统计", "nextRequirement": "取得含成交和未平仓认购、认沽张数的同日官方统计"})
    if iv_points:
        cards.append(_card("cn-300etf-atm-iv", "沪深300ETF 近月平值隐含波动代理", "cn", "%",
                           "上交所华泰柏瑞沪深300ETF（510300）近月同档认购、认沽期权",
                           "近月接近平值的两侧隐含波动均值；看期权对波动幅度的定价。", "上交所期权风险指标", SSE_IV_URL,
                           iv_points, ["同档认购/认沽按Delta接近±0.5选取并等权平均；不是恒定期限QVIX，换月可跳变。", "ETF期权通常第四个周三到期，法定假日或休市顺延；本包无顺延公告时保守按常规日排除过期合约。", "零或缺失隐含波动不填补；不指示指数涨跌方向。"], iv_detail))
    else:
        unavailable.append({"id": "cn-300etf-atm-iv", "title": "沪深300ETF期权隐含波动", "market": "cn", "reason": "无可配对的近月同档有效认购认沽风险指标", "nextRequirement": "取得同一交易日的上交所合约隐含波动与Delta"})
    by_day: dict[str, tuple[float, float]] = {}
    for path in sorted(source_dir.glob("cboe_daily_*.json")):
        day = path.stem.replace("cboe_daily_", "", 1)
        if not re.fullmatch(r"\d{4}-\d{2}-\d{2}", day) or date.fromisoformat(day) > date.today():
            continue
        try:
            doc = json.loads(path.read_text())
        except (OSError, json.JSONDecodeError):
            continue
        equity = _cboe_json_ratio(doc, "EQUITY PUT/CALL RATIO")
        total = _cboe_json_ratio(doc, "TOTAL PUT/CALL RATIO")
        if equity is not None and total is not None and equity >= 0 and total >= 0:
            by_day[day] = (equity, total)
    if by_day:
        days = sorted(by_day)
        cards.append(_card(
            "us-option-pcr-volume", "美国期权成交量 PCR · 股票与总体", "us", "倍",
            "Cboe日统计 Equity Options 与 Total Options",
            "认沽成交张数相对认购成交张数；双线对比股票期权与总体期权交易构成。",
            "Cboe每日市场统计历史", CBOE_PCR_URL,
            [{"date": day, "value": round(by_day[day][0], 4)} for day in days],
            ["仅是Cboe成交量口径，不是持仓PCR，也不直接代表投资者净看空敞口。",
             "股票期权与总体期权的分母不同（总口径含指数与ETF），两条线的水平不可直接相减。",
             "美股与中国ETF期权市场、分母不同，不能合并比较。"],
            [{"label": "股票期权最新", "value": f"{by_day[days[-1]][0]:.3f}"},
             {"label": "总体期权最新", "value": f"{by_day[days[-1]][1]:.3f}"},
             {"label": "历史区间", "value": f"{days[0]} 至 {days[-1]}（{len(days)}个交易日）"}],
            [
                {"key": "equity", "label": "股票期权", "values": [round(by_day[day][0], 4) for day in days]},
                {"key": "total", "label": "总体期权", "values": [round(by_day[day][1], 4) for day in days]},
            ],
        ))
    else:
        html_path = source_dir / "cboe_daily.html"
        if html_path.exists():
            html = html_path.read_text()
            day = _cboe_date(html)
            equity, total = _cboe_ratio(html, "EQUITY PUT/CALL RATIO"), _cboe_ratio(html, "TOTAL PUT/CALL RATIO")
            if day and date.fromisoformat(day) <= date.today() and equity is not None and total is not None:
                cards.append(_card(
                    "us-option-pcr-volume", "美国期权成交量 PCR · 股票与总体", "us", "倍",
                    "Cboe日统计 Equity Options 与 Total Options",
                    "认沽成交张数相对认购成交张数；双线对比股票期权与总体期权交易构成。",
                    "Cboe每日市场统计", CBOE_PCR_URL,
                    [{"date": day, "value": equity}],
                    ["当前仅有一个交易日快照；不是持仓PCR，也不直接代表投资者净看空敞口。"],
                    lines=[{"key": "equity", "label": "股票期权", "values": [equity]},
                           {"key": "total", "label": "总体期权", "values": [total]}],
                ))
        else:
            unavailable.append({"id": "us-option-pcr-volume", "title": "美国期权成交量PCR", "market": "us",
                                "reason": "未取得Cboe每日统计历史", "nextRequirement": "取得Cboe Equity与Total成交量PCR的同日历史"})
    cor_path = source_dir / "cboe_cor3m.csv"
    if cor_path.exists():
        by_date: dict[str, float | None] = {}
        for row in csv.DictReader(io.StringIO(cor_path.read_text())):
            try:
                day = datetime.strptime(row["DATE"], "%m/%d/%Y").date().isoformat()
                value = _number(row["CLOSE"])
                if date.fromisoformat(day) <= date.today():
                    by_date[day] = round(value, 3) if value is not None else None
            except (KeyError, ValueError):
                continue
        points = [{"date": day, "value": by_date[day]} for day in sorted(by_date)]
        if points:
            cor_percentiles = strict_prior_percentiles(points, 756)
            last_percentile = cor_percentiles[-1]["value"]
            card = _card("us-cor3m", "标普500 三个月隐含相关 COR3M", "us", "%",
                               "Cboe COR3M；标普500中按市值选取的50只股票期权与指数期权",
                               "观察期权市场定价的共同波动程度；升高表示预期分散收益减少。", "Cboe COR3M官方历史", CBOE_COR_URL,
                               points, ["隐含相关不是已实现的逐股相关，也不是对未来涨跌的预测。", "2006年起的回溯历史早于COR3M于2021年公开推出，早期读数不能冒充当时可得。", "756交易日历史位置只用前756个完整读数，同值按半权并列；缺值窗口留空。"])
            card["percentileWindow"] = 756
            card["percentiles"] = cor_percentiles
            if last_percentile is not None:
                card["latestDetails"] = [{"label": "此前756个交易日历史位置", "value": f"{last_percentile:.2f}%"}]
            cards.append(card)
    basis_series: dict[str, tuple[str, list[dict], str | None]] = {}
    for product, index, name in (("IF", "csi300_sh", "沪深300"), ("IC", "000905", "中证500"),
                                 ("IH", "000016", "上证50"), ("IM", "000852", "中证1000")):
        basis_points, contract = _main_futures_basis_points(source_dir, product, index)
        if basis_points:
            basis_series[product] = (name, basis_points, contract)
    if len(basis_series) == 4:
        common_days = sorted(set.intersection(*(set(point["date"] for point in points) for _, points, _ in basis_series.values())))
        by_symbol = {product: {point["date"]: point["value"] for point in points} for product, (_, points, _) in basis_series.items()}
        lines = [
            {"key": product, "label": f"{product} {name}", "values": [by_symbol[product][day] for day in common_days]}
            for product, (name, _, _) in basis_series.items()
        ]
        last_day = common_days[-1]
        cards.append(_card(
            "cn-index-futures-basis", "A股四大股指期货主力连续年化基差", "cn", "%",
            "中金所IF/IC/IH/IM按当日持仓量最大合约拼接的主力连续，相对各自现货指数；IH/IF看大盘、IC/IM看小盘",
            "同日收盘期货相对现货的价差按剩余自然日年化；负值为贴水，正值为升水。",
            "新浪财经各月份合约收盘与持仓量、东方财富指数收盘；中金所合约规则", CFFEX_RULES["IF"],
            [{"date": day, "value": by_symbol["IF"][day]} for day in common_days],
            ["主力连续按当日持仓量最大合约拼接，换月点存在合约跳变；不是可持有单合约的连续收益。",
             "期货与现货两源仅有交易日收盘栏，缺逐笔最后成交时间；按共同15:00收市配对，是日收盘近似值。",
             "未经股息、融资、交易费用和可交割现金流调整，不是无风险套利收益。",
             "年化按剩余自然日折算，临近到期仍会放大微小价差；比较时优先看方向与区间，不把单日极值当套利空间。",
             "IH/IF与IC/IM的贴水差只描述大小盘定价差异，不含风格择时结论。"],
            [{"label": "最新交易日", "value": last_day},
             {"label": "IF 沪深300", "value": f"{by_symbol['IF'][last_day]:.3f}%（{basis_series['IF'][2]}）"},
             {"label": "IC 中证500", "value": f"{by_symbol['IC'][last_day]:.3f}%（{basis_series['IC'][2]}）"},
             {"label": "IH 上证50", "value": f"{by_symbol['IH'][last_day]:.3f}%（{basis_series['IH'][2]}）"},
             {"label": "IM 中证1000", "value": f"{by_symbol['IM'][last_day]:.3f}%（{basis_series['IM'][2]}）"},
             {"label": "历史区间", "value": f"{common_days[0]} 至 {last_day}（{len(common_days)}个交易日）"}],
            lines,
        ))
    else:
        unavailable.append({"id": "cn-index-futures-basis", "title": "A股四大股指期货年化基差", "market": "cn",
                            "reason": "未能同时配齐IF/IC/IH/IM主力连续与对应现货的同日收盘",
                            "nextRequirement": "取得四组月份合约持仓量、收盘与现货的同日数据及合约到期规则"})
    return {"schemaVersion": 1, "generatedAt": datetime.now(timezone.utc).isoformat(), "cards": cards, "unavailable": unavailable}


def main() -> None:
    packet = build_packet()
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n")
    print(f"{OUTPUT}: {len(packet['cards'])} cards, {len(packet['unavailable'])} unavailable")


if __name__ == "__main__":
    main()
