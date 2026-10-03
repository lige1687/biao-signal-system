"""Stage only task-owned public differences; no checkout, push or shared index writes."""
from pathlib import Path
import hashlib
import json
import subprocess

ROOT = Path(__file__).resolve().parents[4]
STAGE = ROOT / "docs/ops/recovery/market-observation-sync-2026-10-03/public-tree"
BASE = "d7da6cb0f9c127606b6faa572fabc9ee93f104f7"
HERE = Path(__file__).resolve().parent


def baseline(path):
    return subprocess.check_output(["git", "show", BASE + ":" + path], cwd=ROOT)


def put(path, data):
    out = STAGE / path
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(data)


code = [
    "configs/market-observations.v1.json",
    "src/lei_signal/fundamentals/observations.py",
    "src/lei_signal/fundamentals/turnover_snapshot.py",
    "tests/unit/test_market_observations.py",
    "tests/unit/test_turnover_snapshot.py",
    "web/src/components/MarketObservationCards.tsx",
    "web/src/components/ObservationSourceNote.tsx",
    "web/src/components/trend/zones.ts",
    "web/src/pages/SentimentPage.tsx",
    "web/src/pages/SectorsPage.tsx",
    # Small public exchange observations, not licensed survey input or a bulk dataset.
    "data/market_observations/stock-turnover-20260929.json",
    "docs/experiments/raw/market-turnover-21day-2026-10-01/qualified-21day-input-values.json",
    "docs/experiments/raw/market-turnover-21day-2026-10-01/independent-final-21day-acceptance.json",
]
for path in code:
    put(path, (ROOT / path).read_bytes())

# The shared CommodityCard change belongs to a different task. Keep that whole
# function from the existing public base; retain this task's other page blocks.
path = "web/src/pages/FundamentalsPage.tsx"
current = (ROOT / path).read_text()
old = baseline(path).decode()
start = "function CommodityCard("
end = "// ── 消费面板"
assert current.count(start) == old.count(start) == 1
public = current[:current.index(start)] + old[old.index(start):old.index(end, old.index(start))] + current[current.index(end, current.index(start)):]
put(path, public.encode())
assert "const meta = data?.meta" not in public

reports = [
    "nasdaq-sentiment-retrospective-2026-10-02",
    "vxn-qqq-risk-information-2026-10-02",
    "fundamentals-independent-review-2026-10-02",
    "fundamentals-official-qualification-2026-10-02",
    "fundamentals-series-readiness-2026-10-02",
]
registry = json.loads(baseline("docs/experiments/registry.json"))
local_registry = json.loads((ROOT / "docs/experiments/registry.json").read_text())
for name in reports:
    path = f"docs/experiments/{name}.md"
    put(path, (ROOT / path).read_bytes())
    registry["entries"][path] = local_registry["entries"][path]
put("docs/experiments/registry.json", (json.dumps(registry, ensure_ascii=False, indent=2) + "\n").encode())
index = baseline("docs/experiments/INDEX.md").decode()
index += "\n## 市场观察安全同步（2026-10-03）\n\n" + "\n".join(f"- [{n}]({n}.md)：第一方结论随分支同步；原始输入与许可缺口见任务进展。" for n in reports) + "\n"
put("docs/experiments/INDEX.md", index.encode())

put("docs/progress/market-observation.md", (ROOT / "docs/progress/market-observation.md").read_bytes())
put("docs/ops/work-progress/market-observation.md", (
    "# 市场观察阶段进度\n\n2026-10-03（Asia/Shanghai）用户明确改为持续负责的进展同步，非接管。"
    "本任务继续由原负责人执行，独立分支 task/market-observation-progress。\n\n"
    "当前计划、已完成、正在做、暂停、设备、基础commit、验证与并行避让范围统一维护于"
    "[任务进展](../../progress/market-observation.md)。原本地交接包只作历史快照，"
    "其停止执行安排已被最新用户指令取代，冻结字节不改写。\n").encode())

selection = []
for p in sorted(STAGE.rglob("*")):
    if p.is_file():
        rel = p.relative_to(STAGE).as_posix()
        selection.append({"path": rel, "bytes": p.stat().st_size,
                          "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                          "source": "derived task-only snapshot" if rel in ["web/src/pages/FundamentalsPage.tsx", "docs/experiments/registry.json", "docs/experiments/INDEX.md", "docs/ops/work-progress/market-observation.md"] else "current task file exact bytes"})
(HERE / "selection.json").write_text(json.dumps({"base_commit": BASE, "files": selection,
    "excluded_shared_changes": ["CommodityCard", "fetch_commodity_ratios", "CommodityRatios.meta"],
    "source_worktree_untouched": True}, ensure_ascii=False, indent=2) + "\n")

withheld = []
local = ROOT / "docs/archive/handoffs-plans/market-observation-handoff-2026-10-03"
for p in [local / "source-documents/LEI 技术交易体系.md", local / "source-documents/LEI 技术实现.md",
          ROOT / "data/sentiment/aaii.csv", ROOT / "data/sentiment/naaim.csv"]:
    if p.exists():
        withheld.append({"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
                         "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "uploaded": False,
                         "reason": "full strategy original or survey source; public redistribution permission not established"})
artifacts = json.loads((local / "records/artifacts.json").read_text())
withheld += [x for x in artifacts["local_artifacts"] if "/20261002-linux/" in x["path"]]
for x in artifacts["withheld_evidence"]:
    withheld.append(x)
# Fingerprint every other archived input/result without shipping its contents.
for n in reports:
    raw = ROOT / "docs/experiments/raw" / n
    for p in raw.rglob("*"):
        if p.is_file() and p.name != ".DS_Store":
            withheld.append({"path": p.relative_to(ROOT).as_posix(), "bytes": p.stat().st_size,
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(), "uploaded": False,
                "reason": "raw input/result or original version snapshot retained locally; only first-party report and small validation summary published"})
(HERE / "withheld.json").write_text(json.dumps({"items": withheld,
    "database_credentials": "no export; not needed for reading progress; runtime DB and secrets not uploaded",
    "old_handoff_branch": "local only; not used as public parent to avoid carrying withheld documents in history"}, ensure_ascii=False, indent=2) + "\n")
print(json.dumps({"publication_files": len(selection), "bytes": sum(x["bytes"] for x in selection), "withheld_records": len(withheld)}))
