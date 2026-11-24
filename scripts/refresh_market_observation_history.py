"""Stage validated observation history without changing the source archive or live data."""

from __future__ import annotations

import argparse
import csv
import io
import json
import math
import os
import re
import subprocess
import tempfile
from datetime import date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

from lei_signal.market_context.microstructure_derivatives import (
    _main_futures_basis_points,
    _third_friday,
    put_call_ratios,
)

ARCHIVE = Path(
    "/Volumes/win+mac通用/LeiSignal-新实验结果/microstructure-observations-20261108/derivatives"
)
SSE = (
    "https://query.sse.com.cn/commonQuery.do?isPagination=false"
    "&sqlId=COMMON_SSE_ZQPZ_YSP_QQ_SJTJ_MRTJ_CX&tradeDate={}"
)
CBOE = "https://www.cboe.com/markets/us/options/market-statistics/daily"
CBOE_DAILY = "https://cdn.cboe.com/data/us/options/market_statistics/daily/{}_daily_options"
VXN_CBOE = "https://cdn.cboe.com/api/global/us_indices/daily_prices/VXN_History.csv"


def fetch(url: str, referer: str | None = None) -> bytes:
    cmd = ["curl", "-fsSL", "--http1.1", "--max-time", "12"]
    if referer:
        cmd += ["-H", f"Referer: {referer}"]
    try:
        result = subprocess.run([*cmd, url], capture_output=True, timeout=15)
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError(f"fetch timed out: {url}") from exc
    if result.returncode or not result.stdout:
        raise RuntimeError(f"fetch failed: {url}")
    return result.stdout


def atomic(path: Path, content: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".staged-", delete=False) as handle:
        temp = Path(handle.name)
        handle.write(content)
        handle.flush()
        os.fsync(handle.fileno())
    try:
        temp.replace(path)
    finally:
        temp.unlink(missing_ok=True)


def fred_points(raw: bytes, field: str, as_of: date, minimum: int) -> list[dict]:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if reader.fieldnames != ["observation_date", field]:
        raise ValueError(f"{field}: unexpected CSV columns")
    points = {}
    for row in reader:
        try:
            day = date.fromisoformat(row["observation_date"])
            value = float(row[field])
        except (TypeError, ValueError):
            continue
        if day <= as_of and math.isfinite(value) and -1000 < value < 1000:
            points[day.isoformat()] = value
    if len(points) < minimum:
        raise ValueError(f"{field}: {len(points)} < {minimum} valid observations")
    return [{"date": day, "value": value} for day, value in sorted(points.items())]


def vxn_with_cboe(points: list[dict], raw: bytes, as_of: date) -> list[dict]:
    reader = csv.DictReader(io.StringIO(raw.decode("utf-8-sig")))
    if reader.fieldnames != ["DATE", "OPEN", "HIGH", "LOW", "CLOSE"]:
        raise ValueError("Cboe VXN: unexpected CSV columns")
    official = {}
    for row in reader:
        try:
            day = datetime.strptime(row["DATE"], "%m/%d/%Y").date()
            value = float(row["CLOSE"])
        except (TypeError, ValueError):
            continue
        if day <= as_of and math.isfinite(value) and value > 0:
            official[day.isoformat()] = value
    fred = {p["date"]: p["value"] for p in points}
    overlap = set(fred) & set(official)
    if len(overlap) < 252 or any(abs(fred[d] - official[d]) > 0.011 for d in overlap):
        raise ValueError("Cboe VXN does not match FRED VXNCLS on overlap")
    for day, value in official.items():
        if day > points[-1]["date"]:
            fred[day] = value
    return [{"date": day, "value": value} for day, value in sorted(fred.items())]


def sse_point(doc: dict, day: date) -> dict | None:
    rows = doc.get("result")
    if not isinstance(rows, list):
        return None
    row = next(
        (
            r
            for r in rows
            if isinstance(r, dict)
            and r.get("SECURITY_CODE") == "510300"
            and r.get("TRADE_DATE") == day.isoformat()
        ),
        None,
    )
    if row is None:
        return None
    volume, oi = put_call_ratios(row)
    if volume is None or oi is None or not (0 <= volume <= 20 and 0 <= oi <= 20):
        return None
    return {"date": day.isoformat(), "volume": round(volume, 6), "oi": round(oi, 6)}


def sse_history(archive: Path, stage: Path, as_of: date) -> list[dict]:
    points = {}
    for path in [*sorted(archive.glob("sse_pcr_*.json")), *sorted(stage.glob("sse_pcr_*.json"))]:
        try:
            day = date(int(path.stem[-8:-4]), int(path.stem[-4:-2]), int(path.stem[-2:]))
            if day > as_of:
                continue
            point = sse_point(json.loads(path.read_text()), day)
        except (OSError, ValueError, json.JSONDecodeError):
            continue
        if point:
            points[point["date"]] = point
    first = min(date.fromisoformat(day) for day in points)
    latest = max(date.fromisoformat(day) for day in points)
    # Probe only the newest few days; an empty exchange response is not a value.
    for offset in range(1, min((as_of - latest).days, 7) + 1):
        day = latest + timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        try:
            raw = fetch(
                SSE.format(day.strftime("%Y%m%d")),
                "https://www.sse.com.cn/assortment/options/date/",
            )
            point = sse_point(json.loads(raw), day)
        except (RuntimeError, json.JSONDecodeError):
            continue
        if point:
            points[point["date"]] = point
            atomic(stage / f"sse_pcr_{day:%Y%m%d}.json", raw)
    for offset in range(1, 32):
        if len(points) >= 252:
            break
        day = first - timedelta(days=offset)
        if day.weekday() >= 5:
            continue
        try:
            raw = fetch(
                SSE.format(day.strftime("%Y%m%d")),
                "https://www.sse.com.cn/assortment/options/date/",
            )
            point = sse_point(json.loads(raw), day)
        except (RuntimeError, json.JSONDecodeError):
            continue
        if point:
            points[point["date"]] = point
            atomic(stage / f"sse_pcr_{day:%Y%m%d}.json", raw)
    if len(points) < 252:
        raise ValueError(f"SSE valid observations {len(points)} < 252")
    return [points[day] for day in sorted(points)]


def cboe_point(raw: bytes, day: str) -> dict | None:
    try:
        rows = json.loads(raw)["ratios"]
        values = {row["name"]: float(row["value"]) for row in rows}
        equity, total = values["EQUITY PUT/CALL RATIO"], values["TOTAL PUT/CALL RATIO"]
    except (ValueError, TypeError, KeyError):
        return None
    if all(math.isfinite(value) and 0 <= value <= 20 for value in (equity, total)):
        return {"date": day, "equity": equity, "total": total}
    return None


def cboe_history(archive: Path, as_of: date, stage: Path | None = None) -> list[dict]:
    points = {}
    paths = sorted(archive.glob("cboe_daily_*.json"))
    if stage is not None:
        paths.extend(sorted(stage.glob("cboe_daily_*.json")))
    for path in paths:
        day = path.stem.removeprefix("cboe_daily_")
        try:
            if date.fromisoformat(day) > as_of:
                continue
            point = cboe_point(path.read_bytes(), day)
        except (OSError, ValueError):
            continue
        if point is not None:
            points[day] = point
    if points and stage is not None:
        latest = date.fromisoformat(max(points))
        for offset in range(1, min((as_of - latest).days, 7) + 1):
            day = latest + timedelta(days=offset)
            if day.weekday() >= 5:
                continue
            try:
                raw = fetch(CBOE_DAILY.format(day.isoformat()))
            except RuntimeError:
                continue
            point = cboe_point(raw, day.isoformat())
            if point is not None:
                points[day.isoformat()] = point
                atomic(stage / f"cboe_daily_{day.isoformat()}.json", raw)
    if len(points) < 252:
        raise ValueError(f"Cboe valid observations {len(points)} < 252")
    return [points[day] for day in sorted(points)]


def basis_history(archive: Path, as_of: date) -> dict[str, list[dict]]:
    series = {}
    for symbol, index in [
        ("IF", "csi300_sh"),
        ("IC", "000905"),
        ("IH", "000016"),
        ("IM", "000852"),
    ]:
        contracts = json.loads((archive / f"main_{symbol.lower()}_daily.json").read_text())
        for row in contracts:
            day, expiry = date.fromisoformat(row["date"]), date.fromisoformat(row["expiry"])
            if (
                row["contract"] != symbol + expiry.strftime("%y%m")
                or expiry != _third_friday(expiry.year, expiry.month)
                or day >= expiry
                or row["oi"] <= 0
                or row["close"] <= 0
            ):
                raise ValueError(f"{symbol}: invalid active contract row {row.get('date')}")
        rows, _ = _main_futures_basis_points(archive, symbol, index)
        series[symbol] = [
            r
            for r in rows
            if date.fromisoformat(r["date"]) <= as_of
            and r["value"] is not None
            and math.isfinite(r["value"])
        ]
    common = set.intersection(*(set(r["date"] for r in rows) for rows in series.values()))
    if len(common) < 252:
        raise ValueError(f"four-product aligned basis observations {len(common)} < 252")
    return {symbol: [r for r in rows if r["date"] in common] for symbol, rows in series.items()}


def latest_basis(
    archive: Path, stage: Path, as_of: date, prior: dict[str, list[dict]]
) -> dict[str, list[dict]]:
    """Add one common session only when all four product and spot closes verify."""
    if as_of.weekday() >= 5 or as_of.isoformat() <= prior["IF"][-1]["date"]:
        return prior
    target = as_of.isoformat()
    # CFFEX's current, next, and two subsequent quarterly contracts.
    month = as_of.month
    next_month = date(as_of.year + (month == 12), month % 12 + 1, 1)
    quarters = [date(as_of.year, m, 1) for m in (3, 6, 9, 12) if m > month]
    quarters += [date(as_of.year + 1, m, 1) for m in (3, 6, 9, 12)]
    months = [date(as_of.year, month, 1), next_month]
    for q in quarters:
        if q not in months:
            months.append(q)
        if len(months) >= 4:
            break
    staged_raw = {}
    values = {}
    for symbol, index in [
        ("IF", "csi300_sh"),
        ("IC", "000905"),
        ("IH", "000016"),
        ("IM", "000852"),
    ]:
        candidates = []
        for contract_month in months:
            code = symbol + contract_month.strftime("%y%m")
            expiry = _third_friday(contract_month.year, contract_month.month)
            if expiry <= as_of:
                continue
            url = (
                f"https://stock2.finance.sina.com.cn/futures/api/jsonp.php/"
                f"var%20_{code}_{as_of.year}_{as_of.month}_{as_of.day}=/"
                f"InnerFuturesNewService.getDailyKLine?symbol={code}"
            )
            try:
                raw = fetch(url)
                match = re.search(rb"=\((\[.*\])\);", raw, re.S)
                if match is None:
                    return prior
                rows = json.loads(match.group(1))
                row = next((r for r in rows if r.get("d") == target), None)
                staged_raw[f"sina_{code}_{as_of:%Y%m%d}.txt"] = raw
                if row is not None and float(row["p"]) > 0 and float(row["c"]) > 0:
                    candidates.append(
                        (
                            float(row["p"]),
                            code,
                            float(row["c"]),
                            expiry,
                        )
                    )
            except (RuntimeError, ValueError, KeyError, json.JSONDecodeError):
                return prior
        if not candidates:
            return prior
        oi, code, future, expiry = max(candidates)
        spot_raw = (archive / f"eastmoney_{index}_daily.json").read_bytes()
        spot_rows = json.loads(spot_raw)["data"]["klines"]
        spot_match = next((row for row in spot_rows if row.startswith(target + ",")), None)
        if spot_match is None:
            code_index = "000300" if index == "csi300_sh" else index
            try:
                spot_raw = fetch(
                    "https://push2his.eastmoney.com/api/qt/stock/kline/get"
                    f"?secid=1.{code_index}&klt=101&fqt=0&beg={as_of:%Y%m%d}&end={as_of:%Y%m%d}"
                    "&fields1=f1,f2,f3,f4,f5,f6&fields2=f51,f52,f53,f54,f55,f56,f57"
                )
                spot_rows = json.loads(spot_raw)["data"]["klines"]
                spot_match = next((row for row in spot_rows if row.startswith(target + ",")), None)
            except (RuntimeError, ValueError, KeyError, TypeError):
                return prior
        if spot_match is None:
            return prior
        spot = float(spot_match.split(",")[2])
        if spot <= 0 or not math.isfinite(spot):
            return prior
        value = round((future / spot - 1) * 365 / (expiry - as_of).days * 100, 3)
        values[symbol] = {"date": target, "value": value}
        staged_raw[f"eastmoney_{index}_{as_of:%Y%m%d}.json"] = spot_raw
        staged_raw[f"selected_{symbol}_{as_of:%Y%m%d}.json"] = json.dumps(
            {
                "date": target,
                "contract": code,
                "expiry": expiry.isoformat(),
                "oi": oi,
                "future_close": future,
                "spot_close": spot,
                "basis_pct": value,
            }
        ).encode()
    for filename, raw in staged_raw.items():
        atomic(stage / filename, raw)
    return {symbol: [*rows, values[symbol]] for symbol, rows in prior.items()}


def replay_basis(stage: Path, as_of: date, prior: dict[str, list[dict]]) -> dict[str, list[dict]]:
    """Retain only previously staged dates with all four valid basis receipts."""
    for path in sorted(stage.glob("selected_IF_*.json")):
        compact = path.stem.removeprefix("selected_IF_")
        try:
            day = date.fromisoformat(compact)
            if not date.fromisoformat(prior["IF"][-1]["date"]) < day <= as_of:
                continue
            values = {}
            for symbol in prior:
                row = json.loads((stage / f"selected_{symbol}_{compact}.json").read_bytes())
                expiry = date.fromisoformat(row["expiry"])
                future, spot = row["future_close"], row["spot_close"]
                if (
                    row["date"] != day.isoformat()
                    or row["contract"] != symbol + expiry.strftime("%y%m")
                    or expiry != _third_friday(expiry.year, expiry.month)
                    or expiry <= day
                    or not all(math.isfinite(x) and x > 0 for x in (row["oi"], future, spot))
                ):
                    raise ValueError("Incomplete or invalid basis receipt")
                value = round((future / spot - 1) * 365 / (expiry - day).days * 100, 3)
                if value != row["basis_pct"]:
                    raise ValueError("Basis receipt calculation mismatch")
                values[symbol] = {"date": day.isoformat(), "value": value}
        except (OSError, TypeError, ValueError, KeyError):
            continue
        prior = {symbol: [*rows, values[symbol]] for symbol, rows in prior.items()}
    return prior


def build(archive: Path, stage: Path, as_of: date) -> dict:
    if not archive.is_dir():
        raise FileNotFoundError(f"archive unavailable: {archive}")
    stage.mkdir(parents=True, exist_ok=True)
    out = {}
    for name, field, minimum, card_id in [
        ("nfci.csv", "NFCI", 156, "nfci"),
        ("vxn.csv", "VXNCLS", 252, "vxn"),
    ]:
        previous = fred_points((archive / name).read_bytes(), field, as_of, minimum)
        points = previous
        try:
            raw = fetch(
                f"https://fred.stlouisfed.org/graph/fredgraph.csv?id={field}&cosd=2023-01-01"
            )
            newer = fred_points(raw, field, as_of, minimum)
            if newer[-1]["date"] >= previous[-1]["date"]:
                atomic(stage / name, raw)
                points = newer
        except (RuntimeError, ValueError):
            pass
        if field == "VXNCLS":
            try:
                official_raw = fetch(VXN_CBOE)
                augmented = vxn_with_cboe(points, official_raw, as_of)
                if len(augmented) > len(points):
                    atomic(stage / "cboe_vxn_history.csv", official_raw)
                    points = augmented
            except (RuntimeError, ValueError):
                pass
        out[card_id] = {
            "frequency": "weekly" if field == "NFCI" else "daily",
            "unit": "指数值" if field == "NFCI" else "指数点",
            "sourceName": "FRED / Chicago Fed" if field == "NFCI" else "Cboe / FRED",
            "sourceUrl": f"https://fred.stlouisfed.org/series/{field}"
            if field == "NFCI"
            else VXN_CBOE,
            "points": points,
            "note": (
                "FRED当前修订版本；历史首次公布值未核。"
                if field == "NFCI"
                else "Cboe官方收盘历史与FRED重合段逐日核对；历史首次公布值未核。"
            ),
        }
    sse = sse_history(archive, stage, as_of)
    for card_id, field in [("cn-300etf-pcr-volume", "volume"), ("cn-300etf-pcr-oi", "oi")]:
        out[card_id] = {
            "frequency": "daily",
            "unit": "倍",
            "sourceName": "上海证券交易所",
            "sourceUrl": "https://www.sse.com.cn/assortment/options/date/",
            "points": [{"date": p["date"], "value": p[field]} for p in sse],
        }
    cboe = cboe_history(archive, as_of, stage)
    out["us-option-pcr-volume"] = {
        "frequency": "daily",
        "unit": "倍",
        "sourceName": "Cboe",
        "sourceUrl": CBOE,
        "points": [{"date": p["date"], "value": p["equity"]} for p in cboe],
        "mainLabel": "股票期权",
        "lines": [
            {
                "id": "total",
                "label": "总体期权",
                "points": [{"date": p["date"], "value": p["total"]} for p in cboe],
            }
        ],
    }
    prior_basis = replay_basis(stage, as_of, basis_history(archive, as_of))
    basis = latest_basis(archive, stage, as_of, prior_basis)
    out["cn-index-futures-basis"] = {
        "frequency": "daily",
        "unit": "%",
        "sourceName": "新浪财经 / 东方财富",
        "sourceUrl": "https://www.cffex.com.cn/",
        "points": basis["IF"],
        "mainLabel": "IF 沪深300",
        "lines": [
            {"id": symbol.lower(), "label": label, "points": basis[symbol]}
            for symbol, label in [("IC", "IC 中证500"), ("IH", "IH 上证50"), ("IM", "IM 中证1000")]
        ],
        "note": "按当日最大持仓量合约拼接；期现取同交易日收盘近似值，按剩余自然日简单年化。"
        "换月和临近到期会放大波动。",
    }
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--archive", type=Path, default=Path(os.getenv("LEI_OBS_RAW_DIR", ARCHIVE)))
    parser.add_argument("--stage", type=Path, required=True)
    parser.add_argument(
        "--as-of", type=date.fromisoformat, default=datetime.now(ZoneInfo("Asia/Shanghai")).date()
    )
    args = parser.parse_args()
    if (
        args.stage.resolve() == args.archive.resolve()
        or args.archive.resolve() in args.stage.resolve().parents
    ):
        parser.error("stage must be outside the immutable archive")
    overrides = build(args.archive, args.stage, args.as_of)
    atomic(
        args.stage / "overrides.json",
        (json.dumps(overrides, ensure_ascii=False, indent=2) + "\n").encode(),
    )
    for key, item in overrides.items():
        points = item["points"]
        print(f"{key}: {len(points)} {points[0]['date']}..{points[-1]['date']}")
    print(f"staged: {args.stage / 'overrides.json'}")
    print("NAAIM: no append; official public values are delayed three months")


if __name__ == "__main__":
    main()
