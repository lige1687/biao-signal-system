"""输入包恢复演练：临时目录内只读核验原字节与完整依赖，不调用真实研究入口。

核验：
1. 包内每个文件哈希 == manifest.file_hashes；集合双向一致；
2. 七份原件哈希 == fetch-manifest 逐条记录；fetch-manifest/日历/协议/assemble.py
   原字节 == 仓库原件；
3. prices.csv 逐日覆盖 == 已核日历 2019-09-02..2026-02-03 逐日推导（完整性闸门）；
4. prices.csv 字符串价格全部正有限、日期递增唯一（只读结构核验，不算收益）；
5. quality 声明齐全（data_mode=real、historical_reconstruction_only、
   available_at=null、anchor unknown）。
用法：python3 restore_check.py run-01
"""
from __future__ import annotations

import csv
import hashlib
import json
import shutil
import sys
import tempfile
from pathlib import Path

RAW = Path(__file__).resolve().parent
ROOT = RAW.parents[3]
sys.path.insert(0, str(ROOT / "src"))

FETCH_DIR = ROOT / "docs/experiments/raw/research-third-2026-09-08/06"
CALENDAR = ROOT / ("docs/experiments/raw/research-calendar-completion-2026-09-10/"
                   "calendar-merged/calendar.json")
COVER_START, COVER_END = "2019-09-02", "2026-02-03"


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def main() -> int:
    run_id = sys.argv[1] if len(sys.argv) > 1 else "run-01"
    src_pack = RAW / run_id
    errors, oks = [], []
    manifest = json.loads((src_pack / "manifest.json").read_text())
    quality = json.loads((src_pack / "quality.json").read_text())

    with tempfile.TemporaryDirectory(prefix="lei-510300-restore-") as td:
        pack = Path(td) / "pack"
        shutil.copytree(src_pack, pack)

        # 1. manifest 双向一致
        actual = {str(f.relative_to(pack)) for f in pack.rglob("*")
                  if f.is_file() and f.name != "manifest.json"}
        bad = [rel for rel, h in manifest["file_hashes"].items()
               if not (pack / rel).is_file() or sha(pack / rel) != h]
        if bad or set(manifest["file_hashes"]) != actual:
            errors.append(f"包内文件身份/集合不符: {bad} "
                          f"diff={set(manifest['file_hashes']) ^ actual}")
        else:
            oks.append(f"包内 {len(actual)} 项文件哈希与集合双向一致")

        # 2. 原件与仓库原件逐条一致
        fm = json.loads((pack / "fetch-manifest.json").read_text())
        for e in [e for e in fm if e.get("symbol") == "sh510300"]:
            p = pack / "originals" / e["file"]
            if not p.is_file() or sha(p) != e["sha256"]:
                errors.append(f"原件身份不符: {e['file']}")
            if sha(FETCH_DIR / e["file"]) != e["sha256"]:
                errors.append(f"仓库原件已漂移: {e['file']}")
        for rel, repo in (("fetch-manifest.json", FETCH_DIR / "fetch-manifest.json"),
                          ("calendar.json", CALENDAR),
                          ("task-protocol.md", RAW / "task-protocol.md"),
                          ("assemble.py", RAW / "assemble.py")):
            if sha(pack / rel) != sha(repo):
                errors.append(f"归档原字节与仓库原件不符: {rel}")
        oks.append("七份原件+fetch-manifest+日历+协议+assemble.py 原字节一致")

        # 3. 逐日覆盖 == 日历推导（完整性闸门，非行数）
        from lei_signal.research.trading_calendar import TradingCalendar
        cal = TradingCalendar.from_file(CALENDAR)
        required = list(cal.trading_days(COVER_START, COVER_END))
        with (pack / "prices.csv").open(newline="") as f:
            rd = list(csv.DictReader(f))
        dates = [r["date"] for r in rd]
        if dates != required:
            errors.append("prices.csv 逐日覆盖与日历推导不一致")
        else:
            oks.append(f"prices.csv 逐日覆盖==日历推导（{len(required)} 个交易日）")

        # 4. 结构核验：唯一递增、价格正有限（原字符串解析只用于核验，不回写）
        import math
        if len(set(dates)) != len(dates) or dates != sorted(dates):
            errors.append("日期不唯一或不递增")
        bad_px = [r["date"] for r in rd
                  if not all(math.isfinite(float(r[k])) and float(r[k]) > 0
                             for k in ("open", "close", "high", "low"))]
        if bad_px:
            errors.append(f"非正/非有限价格: {bad_px[:5]}")
        else:
            oks.append("全部价格正有限、日期唯一递增")

        # 5. 声明齐全
        decl = quality.get("declarations", {})
        need = {"data_mode": "real", "historical_reconstruction_only": True,
                "historical_available_at": None, "adjustment_anchor": "unknown（精确复权锚点未证）"}
        for k, v in need.items():
            if decl.get(k) != v:
                errors.append(f"声明缺失/漂移: {k}={decl.get(k)!r}")
        oks.append("quality 声明齐全（real/历史重构/available_at=null/anchor unknown）")

    for line in oks:
        print(f"OK: {line}")
    for line in errors:
        print(f"FAIL: {line}", file=sys.stderr)
    if errors:
        print("恢复演练：失败", file=sys.stderr)
        return 1
    print("恢复演练：通过 —— 仅只读身份/依赖核验，未调用真实研究入口")
    return 0


if __name__ == "__main__":
    sys.exit(main())
