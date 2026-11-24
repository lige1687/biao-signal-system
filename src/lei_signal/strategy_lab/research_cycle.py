"""周度前向漂移复盘与月度弱项驱动提案引擎（research_cycle）。

把单次问答研究升级为可自动运转的异步飞轮：
1. `run_weekly_forward_review`：汇总前向跟踪器实盘超额 + 检查 LIVE 策略漂移 + 自动触发降级提醒；
2. `run_monthly_research_proposal`：结合多腿失血诊断 + 结构化反例知识库自动筛掉历史死胡同，输出下月定向挖掘提案。
"""
from __future__ import annotations

from datetime import datetime, timezone

from .data_portal import DataPortal
from .forward_tracker import ForwardTracker
from .knowledge_base import KnowledgeBase
from .lifecycle import LifecycleRegistry
from .multi_leg import simulate_multi_leg_account


def run_weekly_forward_review(portal: DataPortal) -> dict[str, object]:
    """执行周度前向复盘：推进对账、扫描负漂移，并对照五态生命周期表输出处置建议。"""
    tracker = ForwardTracker(portal)
    recon = tracker.reconcile()
    drift = tracker.drift_report()
    registry = LifecycleRegistry(portal.repo_root)
    reg_entries = registry.load().get("entries", [])

    alerts: list[str] = []
    sleeve_cn = {"sector_etf": "行业基金推荐", "stock_leader": "行业真龙头个股", "stock_small_giant": "细分小巨人个股"}
    for sleeve, st in drift["sleeve_forward_stats"].items():
        if "🔴" in str(st.get("drift_status", "")):
            alerts.append(f"【{sleeve_cn.get(sleeve, sleeve)}】近期实盘跟盘表现明显低于历史预期，建议降级暂停并复查原因。")

    state_counts: dict[str, int] = {}
    for e in reg_entries:
        s = str(e.get("state", "UNKNOWN"))
        state_counts[s] = state_counts.get(s, 0) + 1

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "as_of": recon.get("as_of"),
        "reconciled": recon.get("reconciled"),
        "snapshots_frozen": drift["snapshots_frozen"],
        "sleeve_forward_stats": drift["sleeve_forward_stats"],
        "lifecycle_summary": state_counts,
        "drift_alerts": alerts,
        "verdict_cn": (
            f"⚠️ 发现 {len(alerts)} 项前向漂移告警，需要主控介入复核"
            if alerts
            else "🟢 本周前向跟踪账目核对无误，暂无负漂移告警"
        ),
    }


def run_monthly_research_proposal(portal: DataPortal) -> dict[str, object]:
    """执行月度弱项驱动提案：从开发期失血诊断出发，自动交叉比对反例记忆库，防止重复踩坑。"""
    kb = KnowledgeBase(portal.repo_root)
    ml = simulate_multi_leg_account(portal, split="explore")
    bleeding = ml["bleeding_diagnosis"]
    raw_hyps = list(bleeding.get("next_mining_hypotheses", []))

    checked_proposals: list[dict[str, object]] = []
    for hyp in raw_hyps:
        hits = kb.query(hyp)
        checked_proposals.append({
            "proposal": hyp,
            "related_anti_patterns": [a["title"] for a in hits["anti_patterns"][:3]],
            "reusable_verified_edges": [v["title"] for v in hits["verified_edges"][:3]],
        })

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "explore_multi_leg_metrics": ml["summary_metrics"],
        "top_drawdown_episodes": bleeding.get("top3_drawdown_episodes", []),
        "screened_proposals": checked_proposals,
        "total_anti_patterns_guarded": len(kb.load().get("anti_patterns", [])),
    }
