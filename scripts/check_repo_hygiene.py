#!/usr/bin/env python3
"""仓库归置自检：任务结案前跑一次，非零退出即有放错位置的内容。

对应 AGENTS.md「文件归置规约（2026-09-16 起强制）」。检查项：

1. 仓库根层白名单（新文件不落根层）；
2. scripts/ 根层白名单（一次性脚本进 archive/ 或实验 raw/）；
3. docs/ 根层白名单（过程文档进 archive/handoffs-plans/ 等）；
4. tests/ 根层只允许 __init__.py 与标准子目录（夹具进 fixtures/）；
5. configs/ 与 docs/experiments 关键数据文件必须被 git 跟踪
   （防止部署依赖悬空——2026-09-16 治理时曾发现 dca_evidence.json 未跟踪）。

用法：python3 scripts/check_repo_hygiene.py [--quiet]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]

#: 仓库根层白名单（文件）。工具配置目录（.streamlit 等）单独列。
ROOT_KEEP_FILES = {
    ".DS_Store", ".env", ".env.example", ".gitignore", ".plan.md",
    "AGENTS.md", "CLAUDE.md", "README.md", "pyproject.toml",
    "project.config.json", "project.private.config.json",
}
ROOT_KEEP_DIRS = {
    ".git", ".agents", ".streamlit", ".claude", ".superpowers", ".workbuddy", ".zcode",
    ".mypy_cache", ".pytest_cache", ".ruff_cache", ".biao",
    "configs", "data", "docs", "logs", "miniapp", "scripts", "src", "tests", "web",
}

#: scripts/ 根层白名单：生产脚本（launchd 引用）、研究工具链（契约/测试引用）、
#: backfill 运维工具、安装/控制脚本。2026-09-16 治理时按引用闭包核定。
SCRIPTS_KEEP = {
    "backfill_a_share_klines.py", "backfill_bars_history.py",
    "backfill_breadth_full.py", "backfill_csi300_breadth.py",
    "backfill_nonpositive_retry.py", "backfill_sp500_breadth.py",
    "backfill_tencent_paged.py", "backfill_tencent_windows.py",
    "backfill_timing_data.py", "biao-ctl.sh", "breadth_data.py",
    "build_module_winrate.py", "check_factor_unit_readiness.py",
    "check_module_e_signals.py", "check_research_input.py",
    "copilot_daily.py", "copilot_weekly.py", "daily_nag.py", "daily_scan.py",
    "export_flagship_data.py", "fetch_sentiment_weekly.py",
    "install_app_autostart.sh", "install_launchd.sh", "intraday_check.py",
    "paper_account.py", "precompute_a_share_ma.py", "precompute_daily_brief.py",
    "precompute_factor_panel.py", "precompute_newsfeed.py",
    "precompute_sector_trend.py", "precompute_us_sector_breadth.py",
    "prepare_momentum_qualified_inputs.py", "refresh_timing_matrix.py",
    "retail_mania_backtest.py", "run_b1_dual_ma_description.py",
    "run_breadth_overlay.py", "run_factor_evidence_reliability.py",
    "run_factor_lab.py", "run_factor_library_v0.py", "run_final_form_v2.py",
    "run_full_stack_sim.py", "run_momentum_research_prototype.py",
    "run_portfolio_split.py", "run_research_data_snapshot.py",
    "run_siphon_detector.py", "run_symbol_tilt.py", "seed_portfolio.py",
    # 2026-09-01 事故后恢复的组合实验脚本（run_bform_mini/global 为
    # 字节码重建并经归档结果验证，其余三个恢复自悬空 blob；根层副本供
    # export_flagship_data 等依赖 import，legacy_recovery/ 留档）
    "run_ashare_axes.py", "run_bform_dynamic.py", "run_bform_mini.py",
    "run_bform_global.py", "run_m5_walkforward.py",
    "sentiment_journal.py", "signal_scan.py", "start_backend.sh",
    "start_feishu_tunnel.sh", "start_frontend.sh", "timing_daily.sh",
    "timing_scorecard.py", "update_portfolio_funds.py",
    "verify_research_definitions.py", "watch_check.py",
    # 本脚本自身
    "check_repo_hygiene.py",
    # 生产 plist 的活日志输出（gitignore 覆盖，仅本机存在）
    "precompute_a_share_ma.log", "precompute_a_share_ma.err",
}
SCRIPTS_KEEP_DIRS = {
    "__pycache__",  # 含源码遗失脚本的恢复线索，勿动（见 legacy_recovery/README.md）
    "archive", "launchd", "legacy_recovery", "logs", "round5_repro", "sync",
    "agents",  # 子代理工作区（验收后删除）
}

#: docs/ 根层白名单：被 RESEARCH_GLOBS / registry.json / AGENTS.md 消费的权威文档。
DOCS_KEEP = {
    "README.md",
    "trading-spec-v1.md", "trading-spec-audit.md",
    "research-playbook.md", "research-overview.md",
    "research-round5-cross-market.md", "research-round6-semantics.md",
    "research-round7-integration.md", "research-sentiment-us.md",
    "research-ma-deviation-us.md", "research-momentum-and-system-integration.md",
    "research-factor-backtest.md",
    "system-architecture-and-decisions-2026-09-04.md",
    "next-steps-master-plan-2026-09-02.md",
    "plan-sector-trend-page.md",       # AGENTS.md 引用
    "plan-agent-superentry-v1.md",     # copilot/sentiment.py 注释锚定
}
DOCS_KEEP_DIRS = {
    "progress",  # 2026-10-03 用户明确要求的持续任务进展。
    "archive", "artifacts", "experiments", "literature-learning", "okr",
    "ops", "prompts", "reports", "research", "superpowers", "timing-sweep",
}

TESTS_KEEP_FILES = {"__init__.py", "conftest.py"}
TESTS_KEEP_DIRS = {
    "__pycache__", "fixtures", "golden", "integration", "no_lookahead", "unit",
}

#: 被 src/ 代码按默认路径读取、必须入库的配置与数据文件。
MUST_TRACK = [
    "configs/rules.v2.yaml",
    "configs/newsfeed.json",
    "configs/dca_evidence.json",
    "configs/semantic_states.v1.json",
    "configs/sentiment_evidence.json",
    "docs/experiments/registry.json",
    "docs/experiments/experience.json",
    "docs/experiments/module_winrate.json",
    "docs/research/definitions.v1.json",
]


def _git_tracked_files() -> set[str]:
    out = subprocess.run(
        ["git", "ls-files"], cwd=REPO, capture_output=True, text=True, check=True
    ).stdout
    return {line for line in out.splitlines() if line}


def check_layer(base: Path, keep_files: set[str], keep_dirs: set[str], label: str,
                problems: list[str]) -> None:
    if not base.is_dir():
        return
    for entry in sorted(base.iterdir()):
        name = entry.name
        # 系统垃圾与本机密钥备份（.DS_Store、.env.bak.* 等）不按白名单报
        if name == ".DS_Store" or (base == REPO and name.startswith(".env")):
            continue
        if entry.is_dir():
            if name not in keep_dirs:
                problems.append(f"[{label}] 多出目录: {name}/（白名单外，归档或删除）")
        elif name not in keep_files:
            hint = ""
            if base.name == "scripts":
                hint = "（一次性脚本放 scripts/archive/ 或实验 raw/，生产脚本先登记再留根层）"
            elif base.name == "docs":
                hint = "（过程文档放 docs/archive/handoffs-plans/，报告放 docs/experiments/）"
            elif base.name == "tests":
                hint = "（夹具放 tests/fixtures/<类别>/）"
            else:
                hint = "（新文件按目录地图进子目录，见 docs/README.md）"
            problems.append(f"[{label}] 多出文件: {name} {hint}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--quiet", action="store_true", help="只输出违规项数")
    args = parser.parse_args()

    problems: list[str] = []

    check_layer(REPO, ROOT_KEEP_FILES, ROOT_KEEP_DIRS, "仓库根层", problems)
    check_layer(REPO / "scripts", SCRIPTS_KEEP, SCRIPTS_KEEP_DIRS, "scripts/ 根层", problems)
    check_layer(REPO / "docs", DOCS_KEEP, DOCS_KEEP_DIRS, "docs/ 根层", problems)
    check_layer(REPO / "tests", TESTS_KEEP_FILES, TESTS_KEEP_DIRS, "tests/ 根层", problems)

    tracked = _git_tracked_files()
    for rel in MUST_TRACK:
        if rel not in tracked:
            problems.append(f"[跟踪] {rel} 未被 git 跟踪但被代码按默认路径依赖")

    if problems:
        print(f"✗ 归置自检发现 {len(problems)} 处违规（规约见 AGENTS.md「文件归置规约」）：")
        for p in problems:
            print(f"  - {p}")
        return 1
    if not args.quiet:
        print("✓ 归置自检通过：根层四层均在白名单内，关键配置均已入库。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
