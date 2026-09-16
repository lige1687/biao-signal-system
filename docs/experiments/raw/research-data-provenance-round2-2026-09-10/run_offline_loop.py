#!/usr/bin/env python3
"""第二轮小型离线闭环运行器：产出机器结果与实验元数据。不运行收益账户。"""
import hashlib, json, sys
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.dont_write_bytecode = True

from lei_signal.research import data_quality as q          # noqa: E402
from lei_signal.research import definitions as d            # noqa: E402
from lei_signal.research.data_snapshot import bind_definitions, load_snapshot  # noqa: E402
from lei_signal.research.symbol_identity import audit_mapping, build_mapping   # noqa: E402
from lei_signal.research.trading_calendar import TradingCalendar               # noqa: E402

R1 = ROOT / "docs/experiments/raw/research-data-provenance-2026-09-10"
R2 = ROOT / "docs/experiments/raw/research-data-provenance-round2-2026-09-10"
out = R2 / "offline-loop"
if out.exists():
    sys.exit(f"输出目录已存在，拒绝覆盖：{out}")
out.mkdir(parents=True)

def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for c in iter(lambda: f.read(1 << 20), b""): h.update(c)
    return h.hexdigest()

started = datetime.now(UTC).isoformat()

# 1) 快照 + 指纹
loaded = load_snapshot(R1 / "example-fullpool")
# 2) 身份映射
mapping = build_mapping(loaded.frames)
audit = audit_mapping(loaded.frames, mapping,
                      counterpart_symbols=["510300.SS", "515300.SS"])
# 3) 日历
cal = TradingCalendar.from_file(R2 / "calendar-szse/calendar.json")
coverage = cal.coverage("2019-09-02", "2026-06-30")
# 4) 质量 + 行动
actions = json.loads((ROOT / "docs/experiments/raw/research-rotation-clean-2026-09-09"
                      / "full-pool-preparation/action-sources/normalized-actions.json"
                      ).read_text())["events"]
report = q.merge_reports(
    q.check_prices(loaded.frames, declared_basis="nominal_close", calendar=cal,
                   evaluation_start="2019-09-02", evaluation_end="2026-06-30",
                   warmup_rows=273),
    q.check_actions(actions, declared_symbols=list(loaded.frames)),
)
# 5) 定义绑定
binding = bind_definitions(registry=d.load_registry(),
                           refs=["mixed.price.economic@1.0.0",
                                 "mixed.momentum.raw@1.0.0",
                                 "trend.sma200@1.0.0"],
                           purpose="description")
# 6) 用途请求：一个放行、一个被拒
use_requests = {}
for use in q.USES:
    try:
        q.require_use(report, use)
        use_requests[use] = {"granted": True, "verdict": "usable"}
    except q.UseNotPermitted as e:
        use_requests[use] = {"granted": False, "verdict": e.verdict,
                             "reasons": list(e.reasons)}

result = {
    "schema_version": "research-offline-loop/1.0",
    "protocol": "research-data-provenance-round2-2026-09-10",
    "started_at": started,
    "finished_at": datetime.now(UTC).isoformat(),
    "accounts_run": 0,
    "step1_snapshot": {"source": str((R1 / "example-fullpool").relative_to(ROOT)),
                       "verified": loaded.verified,
                       "instruments": len(loaded.frames),
                       "rows": sum(len(f) for f in loaded.frames.values())},
    "step2_identity": {"audit": audit.to_dict(),
                       "mapping": {k: v.to_dict() for k, v in mapping.items()}},
    "step3_calendar": {"source": cal.to_source_record(), "coverage": coverage.to_dict()},
    "step4_quality": report.to_dict(),
    "step5_binding": binding,
    "step6_use_requests": use_requests,
    "code_identity": {n: sha(ROOT / p) for n, p in {
        "symbol_identity": "src/lei_signal/research/symbol_identity.py",
        "trading_calendar": "src/lei_signal/research/trading_calendar.py",
        "data_quality": "src/lei_signal/research/data_quality.py",
        "data_snapshot": "src/lei_signal/research/data_snapshot.py",
    }.items()},
    "authorization": {"production_trade": False,
                      "note": "数据与接口验证；不构成策略有效或获准交易"},
}
(out / "loop-result.json").write_text(json.dumps(result, indent=1, ensure_ascii=False, default=str))
print("verified:", loaded.verified, "| instruments:", len(loaded.frames),
      "| rows:", result["step1_snapshot"]["rows"])
print("identity balanced:", audit.balanced, "|", audit.note)
print("calendar covered/missing months:", len(coverage.covered_months), "/", len(coverage.missing_months))
print("binding directly_satisfiable:",
      {k: v["directly_satisfiable"] for k, v in binding["bindings"].items()})
print("use requests:", {k: v["granted"] for k, v in use_requests.items()})
print("output:", out / "loop-result.json")
