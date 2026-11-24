#!/usr/bin/env python3
"""每周自动抓取 NAAIM / AAII 情绪读数并落盘（launchd: com.lei.sentiment.weekly）。

数据源（均为官方公开页面，纯 HTTP 可达，无需登录）：
  - NAAIM 暴露指数：index.naaim.org/embeddable/number 只有数字没有观测日期；仅诊断，不入库
  - AAII 多空调查：www.aaii.com/sentimentsurvey（页面含最新一期 Bullish/Neutral/Bearish 与
    "Week ending <Month DD, YYYY>"，调查周以周三收尾、周四发布）

设计约束：
  - 只写真实抓到的数，抓不到就告警跳过，绝不编造；
  - 幂等：复用 ingest_sentiment.py 的 append_observation（按 survey_week 去重，keep last），
    同一周重复跑安全，手动录入同周可覆盖自动值；
  - 单序列失败不影响另一序列；两序列都失败才返回非零（便于 launchd/监控感知）。

用法：
  python3 scripts/fetch_sentiment_weekly.py [--dry-run]
"""

from __future__ import annotations

import argparse
import importlib.util
import re
import sys
import urllib.request
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
INGEST_SCRIPT = REPO_ROOT / "scripts" / "round5_repro" / "ingest_sentiment.py"
SENTIMENT_ROOT = Path(
    __import__("os").environ.get("LEI_SENTIMENT_ROOT", str(REPO_ROOT / "data" / "sentiment")),
)

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko)"
NAAIM_URL = "https://index.naaim.org/embeddable/number"
AAII_URL = "https://www.aaii.com/sentimentsurvey"
TIMEOUT = 30


def log(msg: str) -> None:
    print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)


def http_get(url: str, retries: int = 2) -> str:
    last_exc: Exception | None = None
    for _ in range(retries + 1):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "en-US"})
            with urllib.request.urlopen(req, timeout=TIMEOUT) as resp:
                return resp.read().decode("utf-8", errors="ignore")
        except Exception as exc:  # noqa: BLE001 — 网络抖动重试
            last_exc = exc
    raise RuntimeError(f"GET {url} 失败: {last_exc}")


def _load_ingest_module():
    spec = importlib.util.spec_from_file_location("ingest_sentiment_mod", str(INGEST_SCRIPT))
    mod = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(mod)
    return mod


def monday_of_week(d: date) -> date:
    """该日期所在周的周一（调查周标签约定，与前端表单默认值一致）。"""
    return d - timedelta(days=d.weekday())


def fetch_naaim() -> tuple[date, float] | None:
    html = http_get(NAAIM_URL)
    m = re.search(r'<div class="h1 text-center">\s*([+-]?[0-9]{1,3}(?:\.[0-9]+)?)\s*</div>', html)
    if not m:
        log(f"NAAIM: 页面解析失败（数值组件结构变化？），跳过。长度={len(html)}")
        return None
    value = float(m.group(1))
    # NAAIM 问卷可表达空头及杠杆仓位，指数并非 0–100 的百分比。
    if not (-200 <= value <= 200):
        log(f"NAAIM: 数值越界 {value}，疑似解析错误，跳过。")
        return None
    # embeddable/number 只有读数而没有观测日期；按运行日猜周会把旧值贴上新日期。
    log(f"NAAIM: 读到 {value}，但组件没有观测日期；仅诊断，不写入最新周")
    return None


def fetch_aaii() -> tuple[date, float, float, float] | None:
    html = http_get(AAII_URL)
    vals: dict[str, float] = {}
    for key, cls in (("bull", "bull"), ("neut", "neut"), ("bear", "bear")):
        # 注意：rf-string 里 {1,2} 会被当成格式化字段，必须写成 {{1,2}}
        m = re.search(
            rf'ssv2-slabel {cls}">\s*(Bullish|Neutral|Bearish)\s*</div>\s*'
            rf'<div class="ssv2-snum {cls}">\s*([0-9]{{1,2}}(?:\.[0-9]+)?)%',
            html,
        )
        if not m:
            log(f"AAII: {key} 解析失败（页面结构变化？），跳过整条。")
            return None
        vals[key] = float(m.group(2))
    total = vals["bull"] + vals["neut"] + vals["bear"]
    if not (97 <= total <= 103):
        log(f"AAII: 三值合计 {total} 异常（应≈100），跳过。")
        return None
    dm = re.search(r"Week ending\s+([A-Z][a-z]+ \d{1,2}, \d{4})", html)
    if not dm:
        log("AAII: 找不到 'Week ending' 日期，跳过。")
        return None
    ending = datetime.strptime(dm.group(1), "%B %d, %Y").date()
    week = monday_of_week(ending)
    log(
        f"AAII: 多 {vals['bull']} / 中 {vals['neut']} / 空 {vals['bear']}"
        f"（week ending {ending} → 调查周 {week}）"
    )
    return week, vals["bull"], vals["neut"], vals["bear"]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true", help="只抓取解析，不写盘")
    args = ap.parse_args()

    mod = _load_ingest_module()
    ok_any = False

    naaim = fetch_naaim()
    if naaim:
        ok_any = True
        week, exposure = naaim
        if not args.dry_run:
            row = mod.build_naaim_row(week, exposure, source="auto:naaim.org")
            path = mod.append_observation(SENTIMENT_ROOT, "naaim", row, mod.NAAIM_COLUMNS, mod.NAAIM_FILENAME)
            log(f"NAAIM: 已写入 {path}")
    else:
        log("NAAIM: 本周未入库（下周四自动重试）")

    aaii = fetch_aaii()
    if aaii:
        ok_any = True
        week, bull, neut, bear = aaii
        if not args.dry_run:
            row = mod.build_aaii_row(
                week, bull, neut, bear, source="auto:aaii.com",
                first_fetched_at=datetime.now(UTC).isoformat(),
            )
            path = mod.append_observation(SENTIMENT_ROOT, "aaii", row, mod.AAII_COLUMNS, mod.AAII_FILENAME)
            log(f"AAII: 已写入 {path}")
    else:
        log("AAII: 本周未入库（下周四自动重试）")

    if not ok_any:
        log("两个序列都抓取失败，返回非零")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
