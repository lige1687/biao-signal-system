#!/usr/bin/env python3
"""Build a local market panel from qualified inputs and existing fundamentals APIs.

Run after collecting any new derivative or stock cross-section observations.
Input overrides supply complete dated series, never replacements for frozen evidence.
"""

from __future__ import annotations

import argparse
import csv
import fcntl
import hashlib
import io
import json
import os
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta
from pathlib import Path
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from lei_signal.market_context.observation_panel import (  # noqa: E402
    build_card,
    nowcast,
    volatility,
)

PUBLIC = ROOT / "web/public/research"
MICRO = PUBLIC / "microstructure-observations-20261108"
LIBRARY = PUBLIC / "observation-library-20261026"
AAII_HISTORY = (
    ROOT
    / "docs/experiments/raw/sentiment-aaii-extremes-increment-2026-09-29"
    / "inputs/aaii-candidate-values.csv"
)
NAAIM_HISTORY = Path.home() / ".lei_signal_lab/cache/sentiment_research_2026-09/naaim_clean.csv"
CBOE = "https://www.cboe.com/tradable-products/vix/vix-historical-data/"
CBOE_CSV = "https://cdn.cboe.com/api/global/us_indices/daily_prices/"
OFR = "https://www.financialresearch.gov/financial-stress-index/"
OUTPUT = PUBLIC / "market-observation-panel/panel.v1.json"


def read_json(path: Path) -> dict:
    return json.loads(path.read_text())


def get(url: str) -> str:
    request = Request(url, headers={"User-Agent": "LeiSignal local market observation"})
    with urlopen(request, timeout=45) as response:
        return response.read().decode("utf-8-sig")


def read_inputs(api: str, snapshot: Path | None) -> dict:
    urls = {
        "overlay.json": api + "/api/fundamentals/overlay-history?years=3",
        "us-macro.json": api + "/api/fundamentals/us-macro",
        "VIX.csv": CBOE_CSV + "VIX_History.csv",
        "VIX3M.csv": CBOE_CSV + "VIX3M_History.csv",
        "ofr.csv": OFR + "data/fsi.csv",
    }

    def read(item: tuple[str, str]) -> tuple[str, str]:
        name, url = item
        data = (snapshot / name).read_text(encoding="utf-8-sig") if snapshot else get(url)
        return name, data

    with ThreadPoolExecutor(max_workers=len(urls)) as pool:
        return dict(pool.map(read, urls.items()))


def point(day: str, value: float | None) -> dict:
    return {"date": day, "value": value}


def series(
    rows: list[dict], frequency: str, unit: str, source: str, note: str, url: str = "", **extra
) -> dict:
    return {
        "points": rows,
        "frequency": frequency,
        "unit": unit,
        "sourceName": source,
        "note": note,
        **({"sourceUrl": url} if url else {}),
        **extra,
    }


def api_points(payload: dict, key: str) -> list[dict]:
    row = payload["series"][key]
    return [point(day, value) for day, value in zip(row["dates"], row["values"], strict=True)]


def cboe_prices(text: str) -> list[dict]:
    return [
        point(datetime.strptime(row["DATE"], "%m/%d/%Y").date().isoformat(), float(row["CLOSE"]))
        for row in csv.DictReader(io.StringIO(text))
    ]


def survey(path: Path, name: str, as_of: date) -> list[dict]:
    rows = []
    with path.open(newline="") as handle:
        for row in csv.DictReader(handle):
            available = row["available_at"]
            if not available or date.fromisoformat(available[:10]) > as_of:
                continue
            is_proxy = row.get("license_status") == "public_proxy"
            value = (
                float(row["bullish"]) - float(row["bearish"])
                if name == "aaii"
                else float(row["exposure_index"])
            )
            # Digitized chart values were verified in this packet on November 9.
            # Their exact original public timestamp is unknown.
            if is_proxy:
                available = max(available, "2026-11-09")
            if date.fromisoformat(available[:10]) <= as_of:
                rows.append(
                    {
                        **point(row["survey_week"], value),
                        "available_at": available,
                        "proxy": is_proxy,
                    }
                )
    return sorted(rows, key=lambda row: row["date"])


def extend_survey(history: Path, current: list[dict], name: str, as_of: date) -> list[dict]:
    if not history.is_file():
        return current
    old = {}
    with history.open(newline="") as handle:
        for row in csv.DictReader(handle):
            day = date.fromisoformat(row["date"])
            # The archive labels NAAIM's Wednesday survey. One Sunday entry
            # conflicts with the dated Wednesday in that same week.
            if name == "naaim" and day.weekday() != 2:
                continue
            monday = day - timedelta(days=day.weekday())
            week = monday.isoformat()
            value = float(row["spread_pp"] if name == "aaii" else row["naaim"])
            available = max(day, monday + timedelta(days=3))
            if week in old:
                raise ValueError(f"Duplicate {name} survey week {week}")
            if available <= as_of:
                old[week] = {**point(week, value), "available_at": available.isoformat()}
    current_by_week = {row["date"]: row for row in current}
    overlap = old.keys() & current_by_week.keys()
    tolerance = 0.11 if name == "aaii" else 0.02
    if current and (
        not overlap
        or any(abs(old[k]["value"] - current_by_week[k]["value"]) > tolerance for k in overlap)
    ):
        raise ValueError(f"{name} survey sources disagree on overlapping weeks")
    # Retain the fuller official spreadsheet precision for AAII. For NAAIM,
    # the archive extends the live series without replacing any recent read.
    merged = {**current_by_week, **old} if name == "aaii" else {**old, **current_by_week}
    return [merged[day] for day in sorted(merged)]


def from_micro(card: dict) -> dict:
    points = card["points"]
    limitations = card["limitations"]
    if card.get("id") == "us-cor3m":
        # The source packet's prior-756-day percentile is not this panel's statistic.
        limitations = [item for item in limitations if "756交易日历史位置" not in item]
        limitations.append(
            "面板统计为本地计算：最近252个有效日含当期，标准差为总体标准差；"
            "分位=100×(低于当期数+(等于当期数−1)/2)/(252−1)，按收盘值保留3位小数判同值。"
        )
    lines = [
        {
            "id": line["key"].lower(),
            "label": line["label"],
            "points": [
                point(p["date"], value) for p, value in zip(points, line["values"], strict=True)
            ],
        }
        for line in card.get("lines", [])
    ]
    main_label = lines[0]["label"] if lines else None
    return series(
        points,
        card["frequency"],
        card["unit"],
        card["sourceName"],
        " ".join([card["scope"], *limitations]),
        card.get("sourceUrl") or "",
        lines=lines[1:],
        **({"mainLabel": main_label} if main_label else {}),
    )


def cards_from_sources(inputs: dict, aaii: list[dict], naaim: list[dict], as_of: date) -> dict:
    overlay = json.loads(inputs["overlay.json"])
    macro = json.loads(inputs["us-macro.json"])
    cards = {}
    for market, key, source, url in (
        ("cn", "sse", "腾讯行情 · 上证指数收盘价", "https://gu.qq.com/sh000001"),
        ("us", "sp500", "S&P Dow Jones Indices / FRED", "https://fred.stlouisfed.org/series/SP500"),
    ):
        # The FRED price feed includes non-trading holidays as explicit nulls.
        prices = [
            row
            for row in api_points(overlay, key)
            if row["value"] is not None and row["date"] <= as_of.isoformat()
        ]
        short, long = volatility(prices)
        cards[f"hv-{market}"] = series(
            short,
            "daily",
            "%",
            source,
            "收盘对数收益的20／60个交易日样本标准差，乘以√252年化。两条线均使用已取得的日收盘。",
            url,
            mainLabel="20日波动率",
            lines=[{"id": "hv60", "label": "60日波动率", "points": long}],
        )

    vix = cboe_prices(inputs["VIX.csv"])
    vix3m = {row["date"]: row["value"] for row in cboe_prices(inputs["VIX3M.csv"])}
    cards["vix"] = series(
        vix, "daily", "指数点", "Cboe 官方收盘", "标普500期权定价的未来约30日预期波动。", CBOE
    )
    cards["vix-term-structure"] = series(
        [
            point(p["date"], p["value"] / vix3m[p["date"]])
            for p in vix
            if vix3m.get(p["date"], 0) > 0
        ],
        "daily",
        "倍",
        "Cboe 官方收盘",
        "取同日 VIX 与 VIX3M 收盘，按约30日波动预期除以约3个月波动预期。",
        CBOE,
    )
    cards["hy-oas"] = series(
        [row for row in api_points(macro, "hy_oas") if row["value"] is not None],
        "daily",
        "%",
        "ICE BofA / FRED",
        "美高收益债期权调整利差，单位为百分点。FRED公开区间约三年。",
        "https://fred.stlouisfed.org/series/BAMLH0A0HYM2",
    )
    cards["ofr-fsi"] = series(
        [
            point(row["Date"], float(row["OFR FSI"]))
            for row in csv.DictReader(io.StringIO(inputs["ofr.csv"]))
        ],
        "daily",
        "指数点",
        "美国金融研究办公室 OFR",
        "全球金融压力，相对历史平均为零。通常滞后两个交易日。",
        OFR,
    )

    for packet, ids in (
        (
            "derivatives",
            {
                "cn-300etf-pcr-volume",
                "cn-300etf-pcr-oi",
                "cn-300etf-atm-iv",
                "us-option-pcr-volume",
                "us-cor3m",
                "cn-index-futures-basis",
            },
        ),
        (
            "equity",
            {
                "cn-daily-amount-top5",
                "cn-current-members-pairwise-correlation",
                "us-current-members-pairwise-correlation",
            },
        ),
        ("funding", {"cn-margin-buy-share-a-stocks"}),
    ):
        cards.update(
            (c["id"], from_micro(c))
            for c in read_json(MICRO / f"{packet}.json")["cards"]
            if c["id"] in ids
        )
    financing = cards.pop("cn-margin-buy-share-a-stocks")
    margin_ratio = [
        row
        for row in api_points(overlay, "margin_rzyezb")
        if row["value"] is not None and row["date"] <= as_of.isoformat()
    ]
    if margin_ratio:
        financing["auxiliary"] = [
            {**margin_ratio[-1], "label": "融资余额占流通市值", "unit": "%"},
        ]
    financing["note"] += " 融资余额占比采用东方财富供应商口径，按其资料日期单列。"
    cards["cn-financing"] = financing

    for key, value in read_json(LIBRARY / "reused-series.json")["series"].items():
        if key in {"vxn", "nfci", "finra-margin"}:
            cards[key] = series(
                value["points"],
                value["frequency"],
                value["unit"],
                value["sourceName"],
                "历史观测按资料所属期。FINRA金额为融资借款存量。"
                if key == "finra-margin"
                else "按来源所示资料日。金融条件历史可能修订。",
                value["sourceUrl"],
            )

    candidate = read_json(PUBLIC / "observation-candidates/history.v1.json")
    for key, value in candidate["series"].items():
        cards[key] = series(
            value["points"],
            "daily",
            value["unit"],
            candidate["sourceName"],
            candidate["scopeLabel"] + "。 " + value["definition"],
            candidate["sourceUrl"],
        )

    focus = read_json(PUBLIC / "focus-momentum/observation.v1.json")
    continuation = read_json(PUBLIC / "focus-momentum/continuation.v1.json")
    if continuation["definitionId"] != focus["definitionId"] or not continuation["overlapVerified"]:
        raise ValueError("Focus momentum continuation does not match the fixed universe")
    history = {r["date"]: r["focus"] for r in focus["series"]}
    for row in continuation["series"]:
        day, value = row["date"], row["focus"]
        if day in history and abs(history[day] - value) > 1e-9:
            raise ValueError(f"Conflicting focus observations: {day}")
        history[day] = value
    cards["focus-momentum"] = series(
        [point(day, value * 100) for day, value in sorted(history.items())],
        "daily",
        "%",
        "BaoStock · 固定300股样本",
        "固定300股中，按近20日平均成交额选合格股票的前5%，取它们20日复权收益的等权平均。"
        "历史回看受固定样本约束。",
        "https://www.baostock.com/",
    )
    cards["aaii"] = series(
        aaii,
        "weekly",
        "%",
        "AAII 每周个人投资者问卷",
        "看涨比例减看跌比例，按调查周展示。复用已核官方工作簿历史与公开周读数。",
        "https://www.aaii.com/sentimentsurvey",
    )
    cards["naaim"] = series(
        naaim,
        "weekly",
        "%",
        "NAAIM、MacroMicro 历史与公开图表",
        "自报股票敞口。官方公开表延迟三个月，2026-10-19、10-26及11-02调查周为公开图表估读，约±0.1个百分点。",
        "https://naaim.org/programs/naaim-exposure-index/",
        **({"latestQualifier": "公开图表估读"} if naaim and naaim[-1].get("proxy") else {}),
    )

    bw = read_json(LIBRARY / "baker.json")
    official_end = date.fromisoformat(bw["asOf"])
    proxy = nowcast(cards["finra-margin"]["points"], aaii, naaim, official_end, as_of)
    cards["baker-wurgler"] = series(
        bw["series"],
        "monthly",
        bw["unit"],
        bw["sourceName"],
        " ".join(
            [
                bw["definition"],
                f"作者历史至{official_end:%Y-%m}。虚线为本地实时代理延伸，采用FINRA融资同比、AAII净看涨60日均值、NAAIM仓位60日均值各自标准化后等权平均。",
                "各项使用此前最多60个所属月、至少24个可用月做基准。调查按可用日期，FINRA保守按次月底可用。代理和作者序列各自读数，不跨接计算历史分位。",
                "历史调查发布时间含估计，NAAIM末端有图表估读。当前月为截至资料日的暂估。",
            ]
        ),
        bw["sourceUrl"],
        mainLabel="作者历史",
        lines=[{"id": "nowcast", "label": "实时代理延伸", "dashed": True, "points": proxy}],
    )
    return cards


def assemble(inputs: dict, overrides: list[Path], as_of: date, naaim_history: Path) -> dict:
    aaii = extend_survey(
        AAII_HISTORY, survey(ROOT / "data/sentiment/aaii.csv", "aaii", as_of), "aaii", as_of
    )
    naaim = extend_survey(
        naaim_history, survey(ROOT / "data/sentiment/naaim.csv", "naaim", as_of), "naaim", as_of
    )
    cards = cards_from_sources(inputs, aaii, naaim, as_of)
    for path in overrides:
        for key, replacement in read_json(path).items():
            if (
                key not in cards
                or replacement["frequency"] != cards[key]["frequency"]
                or replacement["unit"] != cards[key]["unit"]
            ):
                raise ValueError(f"Incompatible replacement series {key} in {path.name}")
            baseline = cards[key]
            replacement = dict(replacement)
            if replacement.pop("incremental", False):
                old = {r["date"]: r for r in baseline["points"]}
                for row in replacement["points"]:
                    if row["date"] in old and old[row["date"]]["value"] != row["value"]:
                        raise ValueError(
                            f"Conflicting incremental observation: {key} {row['date']}"
                        )
                    old[row["date"]] = row
                replacement["points"] = [old[day] for day in sorted(old)]
            if replacement.get("note") and replacement["note"] != baseline.get("note"):
                replacement["note"] = f"{baseline['note']} {replacement['note']}"
            cards[key] = {**baseline, **replacement}
    for card in cards.values():
        for line in [card, *card.get("lines", [])]:
            line["points"] = [
                point(row["date"], row["value"])
                for row in line["points"]
                if row["date"][:10] <= as_of.isoformat()
            ]
        if not any(p["value"] is not None for p in card["points"]):
            raise ValueError(f"No usable observations from {card['sourceName']}")
    return {
        "schemaVersion": 1,
        "generatedAt": datetime.now(ZoneInfo("Asia/Shanghai")).isoformat(),
        "asOf": as_of.isoformat(),
        "cards": {key: build_card(card) for key, card in cards.items()},
    }


def write_packet(output: Path, payload: dict) -> None:
    """Preserve a valid previous packet when an incomplete refresh would regress coverage."""
    output.parent.mkdir(parents=True, exist_ok=True)
    identity = hashlib.sha256(os.fsencode(output.resolve())).hexdigest()[:24]
    lock_path = Path(tempfile.gettempdir()) / f"lei-observation-panel-{identity}.lock"
    with lock_path.open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        _replace_packet(output, payload)


def _replace_packet(output: Path, payload: dict) -> None:
    if output.is_file():
        previous = read_json(output)
        for key, old in previous["cards"].items():
            new = payload["cards"][key]
            if new["points"][-1]["date"] < old["points"][-1]["date"] or new["observations"] < min(
                old["observations"], new["window"]
            ):
                raise ValueError(f"Refresh would regress verified coverage: {key}")
    with tempfile.NamedTemporaryFile(
        dir=output.parent, mode="w", encoding="utf-8", delete=False
    ) as handle:
        json.dump(payload, handle, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())
        temp = Path(handle.name)
    os.replace(temp, output)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument(
        "--snapshot-dir", type=Path, help="Replay captured CSV/JSON source responses"
    )
    parser.add_argument("--overrides", action="append", type=Path, default=[])
    parser.add_argument(
        "--naaim-history",
        type=Path,
        default=NAAIM_HISTORY,
        help="Verified local NAAIM archive in date,naaim CSV format",
    )
    parser.add_argument(
        "--as-of", type=date.fromisoformat, default=datetime.now(ZoneInfo("Asia/Shanghai")).date()
    )
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args()
    inputs = read_inputs(args.api_base.rstrip("/"), args.snapshot_dir)
    packet = assemble(inputs, args.overrides, args.as_of, args.naaim_history)
    write_packet(args.output, packet)
    for key, row in packet["cards"].items():
        print(f"{key}: {row['points'][-1]['date']}, {row['observations']} valid observations")


if __name__ == "__main__":
    main()
