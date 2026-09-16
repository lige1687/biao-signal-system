"""归置检查只读 runner（agent-continuity-zcode-closeout-2026-09-17）。

本开发分支没有 scripts/check_repo_hygiene.py（治理未同步）。按主控先例，
借用运行仓 /Users/yongbiaoli/Desktop/lei-signal-lab/scripts/check_repo_hygiene.py
的**原检查函数与白名单**，把 REPO 指向本开发工作区做只读检查：
不搬家、不改历史文件、不产出任何写操作；输出仅落本实验 raw 目录。

判定方式：与主控二轮基线
docs/experiments/raw/controller-agent-continuity-cfix-review-2026-09-16/hygiene.log
（299 项）逐条对比，区分「治理前基线违规」与「本次任务新增」。
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

RUNTIME_SCRIPT = "/Users/yongbiaoli/Desktop/lei-signal-lab/scripts/check_repo_hygiene.py"
DEV = Path("/Users/yongbiaoli/lei-agent-main-consolidation-20260915")
OUT = Path(__file__).parent

spec = importlib.util.spec_from_file_location("check_repo_hygiene", RUNTIME_SCRIPT)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)
mod.REPO = DEV  # 只读重定向：检查对象改为开发工作区

problems: list[str] = []
mod.check_layer(mod.REPO, mod.ROOT_KEEP_FILES, mod.ROOT_KEEP_DIRS, "仓库根层", problems)
mod.check_layer(mod.REPO / "scripts", mod.SCRIPTS_KEEP, mod.SCRIPTS_KEEP_DIRS,
                "scripts/ 根层", problems)
mod.check_layer(mod.REPO / "docs", mod.DOCS_KEEP, mod.DOCS_KEEP_DIRS, "docs/ 根层", problems)
mod.check_layer(mod.REPO / "tests", mod.TESTS_KEEP_FILES, mod.TESTS_KEEP_DIRS,
                "tests/ 根层", problems)
tracked = mod._git_tracked_files()
for rel in mod.MUST_TRACK:
    if rel not in tracked:
        problems.append(f"[跟踪] {rel} 未被 git 跟踪但被代码按默认路径依赖")

baseline_path = DEV / "docs/experiments/raw/controller-agent-continuity-cfix-review-2026-09-16/hygiene.log"
baseline_lines = [
    ln.strip().removeprefix("- ").strip()
    for ln in baseline_path.read_text().splitlines() if ln.strip().startswith("- ")
]
baseline_set = set(baseline_lines)

new_items = [p for p in problems if p not in baseline_set]
resolved = sorted(baseline_set - set(problems))
(OUT / "hygiene-r3.log").write_text(
    "✗ 归置自检发现 "
    f"{len(problems)} 处违规（治理前基线 {len(baseline_lines)} 项，"
    f"本次任务新增 {len(new_items)} 项，基线中已解决 {len(resolved)} 项）"
    "——方法：运行仓 check_repo_hygiene.py 原函数只读重定向到开发工作区"
    "（不搬迁、不治理、不为全绿扩项）：\n"
    + "\n".join(f"  - {p}" for p in problems) + "\n"
    + "\n基线中已解决（本分支先前提名修复，非本轮）：\n"
    + "\n".join(f"  - {p}" for p in resolved) + "\n")
summary = {
    "method": "runtime repo check_repo_hygiene.py functions, REPO->dev workspace, read-only",
    "baseline_items": len(baseline_lines),
    "current_items": len(problems),
    "new_items_this_task": new_items,
    "baseline_items_resolved_since": resolved,
    "runtime_repo_untouched": True,
}
(OUT / "hygiene-r3-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=1))
print(json.dumps(summary, ensure_ascii=False, indent=1))
