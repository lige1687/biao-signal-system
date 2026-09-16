#!/usr/bin/env python3
"""交易日历核验取数（第二轮，一次性核验脚本）。

只取交易日历及其来源说明，不取行情、财务或公司行动。
每次请求记录：来源、URL、请求与返回时刻、HTTP 状态、响应体哈希与原文。
预算硬上限由 ``--max-requests`` 强制，重试与重定向计入。

产物写入独立目录，目录已存在则拒绝运行（不覆盖旧证据）。
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

SZSE_MONTH = "http://www.szse.cn/api/report/exchange/onepersistenthour/monthList?month={month}&random=0.1"
SZSE_REFERER = "http://www.szse.cn/"


class BudgetExceeded(RuntimeError):
    pass


class Fetcher:
    def __init__(self, max_requests: int, raw_dir: Path, timeout: float = 25.0):
        self.max_requests = max_requests
        self.raw_dir = raw_dir
        self.timeout = timeout
        self.calls: list[dict] = []

    @property
    def used(self) -> int:
        return len(self.calls)

    def get(self, url: str, *, referer: str, tag: str) -> str | None:
        if self.used >= self.max_requests:
            raise BudgetExceeded(f"请求预算 {self.max_requests} 已用尽")
        req = urllib.request.Request(  # noqa: S310 - 固定 http(s) 主机
            url, headers={"User-Agent": "Mozilla/5.0", "Referer": referer}
        )
        requested_at = datetime.now(UTC).isoformat()
        status: int | None = None
        body: str | None = None
        error: str | None = None
        redirects = 0
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                status = resp.status
                redirects = 1 if resp.geturl() != url else 0
                body = resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as exc:
            status = exc.code
            error = f"HTTPError {exc.code}"
        except Exception as exc:  # noqa: BLE001 - 如实记录任何失败
            error = f"{type(exc).__name__}: {exc}"
        returned_at = datetime.now(UTC).isoformat()

        digest = hashlib.sha256(body.encode()).hexdigest() if body else None
        raw_path = None
        if body is not None:
            self.raw_dir.mkdir(parents=True, exist_ok=True)
            p = self.raw_dir / f"{tag}.json"
            p.write_text(body, encoding="utf-8")
            raw_path = p.name
        self.calls.append(
            {
                "tag": tag,
                "url": url,
                "requested_at": requested_at,
                "returned_at": returned_at,
                "http_status": status,
                "redirects": redirects,
                "ok": error is None and body is not None,
                "error": error,
                "body_sha256": digest,
                "body_bytes": len(body.encode()) if body else 0,
                "raw_path": raw_path,
            }
        )
        return body


def months_between(start: str, end: str) -> list[str]:
    y, m = (int(x) for x in start.split("-"))
    ey, em = (int(x) for x in end.split("-"))
    out = []
    while (y, m) <= (ey, em):
        out.append(f"{y:04d}-{m:02d}")
        m += 1
        if m == 13:
            y, m = y + 1, 1
    return out


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--out", required=True)
    p.add_argument("--months", nargs="+", required=True,
                   help="要取的月份 YYYY-MM，或 START..END 区间")
    p.add_argument("--max-requests", type=int, required=True)
    p.add_argument("--already-used", type=int, default=0,
                   help="本轮此前已消耗的外部请求数，计入同一预算")
    args = p.parse_args(argv)

    out = Path(args.out)
    if out.exists():
        print(f"输出目录已存在，拒绝覆盖：{out}", file=sys.stderr)
        return 2
    out.mkdir(parents=True)

    months: list[str] = []
    for spec in args.months:
        if ".." in spec:
            a, b = spec.split("..")
            months.extend(months_between(a, b))
        else:
            months.append(spec)

    remaining = args.max_requests - args.already_used
    f = Fetcher(remaining, out / "raw")
    days: dict[str, dict] = {}
    failed: list[str] = []

    for month in months:
        try:
            body = f.get(
                SZSE_MONTH.format(month=month), referer=SZSE_REFERER, tag=f"szse-{month}"
            )
        except BudgetExceeded as exc:
            print(f"预算用尽，停止：{exc}", file=sys.stderr)
            break
        if not body:
            failed.append(month)
            continue
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            failed.append(month)
            continue
        for rec in payload.get("data", []):
            date = rec.get("jyrq")
            flag = rec.get("jybz")
            if not date or flag is None:
                continue
            days[date] = {
                "is_trading_day": flag == "1",
                "source_flag": flag,
                "source_month": month,
            }

    result = {
        "schema_version": "research-trading-calendar/1.0",
        "authority": "exchange_official",
        "publisher": "深圳证券交易所（SZSE）",
        "endpoint_template": SZSE_MONTH,
        "market": "CN",
        "field_semantics": {
            "jyrq": "日期",
            "jybz": "交易标志：1=交易日，0=非交易日（含周末与法定休市）",
        },
        "months_requested": months,
        "months_failed": failed,
        "requests_used": f.used,
        "budget_remaining_after": remaining - f.used,
        "days": dict(sorted(days.items())),
        "day_count": len(days),
        "trading_day_count": sum(1 for v in days.values() if v["is_trading_day"]),
        "calls": f.calls,
        "limitations": [
            "本次仅按月抽样，未覆盖冻结输入的全部 82 个月；未取月份一律为未知，不得回退为普通工作日",
            "jybz 反映事后确认的开休市结果，不证明该安排在更早时点已经公布",
            "深交所日历不自动等同于上交所日历；跨所差异未在本次核验",
        ],
    }
    (out / "calendar.json").write_text(
        json.dumps(result, indent=1, ensure_ascii=False), encoding="utf-8"
    )
    print(f"months requested: {len(months)} | failed: {len(failed)}")
    print(f"requests used: {f.used} | days collected: {len(days)}")
    print(f"output: {out/'calendar.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
