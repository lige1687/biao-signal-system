"""LEI Strategy Lab: 金融含义优先、防穿透闭卷考、真实资金账本、前向漂移闭环的极简因子与策略研究底座。

核心模块分工：
1. data_portal: 本地化 PIT 财报/资本纪律底座 + 统一行情/观测面板入口（彻底解耦外盘路径）。
2. indicator_audit: 纯因果滚动分位 + 视窗匹配非重叠事件 + 尾部 Jaccard 查重 + 连续风险温度计。
3. validation: Purged Walk-Forward 滚动切分 + 纯因果市场体制切片 + 单次消耗 Holdout 锁箱 + HAC/Bootstrap/DSR 过拟合体检。
4. portfolio_sim: 真实单账户资金账本（持仓/行业上限、风险预算、A股涨跌停与停牌约束、闲钱避风港联动、去Top3盈利集中度压测）。
5. signals: 同源信号层（历史回测、每日收盘漏斗、前向跟踪共享同一份严格因果规则，消除回测/生产漂移）。
6. diagnostics: L1 面板信息体检（多期Rank IC/HAC + 两级正交查重）+ L3 组件消融与参数±20%高原稳健检验。
7. factor_engine: 声明式安全 AST 因子算子库 + 自动化前缀不变性防未来函数门禁。
8. forward_tracker: 不可篡改每日推荐快照冻结 + 自动前向模拟袖套对账 + Live-vs-Backtest 漂移监控。
9. multi_leg: 个人账户级多腿联合模拟器（压舱石 + 行业波段 + 个股好生意 + 闲钱避风港 + 定投现金流）与弱项失血诊断器。
"""
from __future__ import annotations

from .data_portal import DataPortal, HOLDOUT_START
from .indicator_audit import audit_market_indicators, render_market_weather
from .validation import (
    HoldoutVault,
    WalkForwardFold,
    build_purged_walk_forward_folds,
    classify_market_regimes,
    overfitting_risk_audit,
    slice_performance_by_year_and_regime,
)
from .portfolio_sim import (
    PortfolioBacktestResult,
    PortfolioSimConfig,
    simulate_real_portfolio,
)
from .signals import (
    DEFAULT_SECTOR_WEIGHTS,
    DEFAULT_STOCK_WEIGHTS,
    build_sector_etf_signal_panels,
    build_stock_funnel_signal_panels,
    compute_sector_resonance_panel,
    make_two_stage_stock_exit_callback,
)
from .chip_trend import (
    compute_live_chip_metrics,
    compare_chip_ma_strategies,
    compare_chip_ma_strategies_detailed,
    compare_stock_quality_chip_strategies,
    compare_stock_strategies_detailed,
    rank_top_candidates,
)
from .fund_evaluator import (
    compare_fund_strategies,
    compare_fund_strategies_detailed,
    evaluate_all_fund_opportunities,
)
from .diagnostics import (
    check_factor_redundancy,
    evaluate_factor_panel_l1,
    run_sector_ablation_and_robustness,
    run_stock_ablation_and_robustness,
)
from .factor_engine import (
    BUILTIN_FACTOR_SPECS,
    FactorSpec,
    evaluate_factor_expression,
    expression_fingerprint,
    screen_candidate_factor,
    verify_expression_no_lookahead,
)
from .forward_tracker import ForwardTracker, compute_strategy_code_fingerprint
from .multi_leg import MultiLegConfig, diagnose_strategy_bleeding, simulate_multi_leg_account
from .knowledge_base import KnowledgeBase
from .lifecycle import LifecycleRegistry
from .research_cycle import run_monthly_research_proposal, run_weekly_forward_review
from .campaigns import (
    build_bear_regime_cap_series,
    build_sector_etf_v2_signals,
    run_campaign1_sector_etf_v2,
    run_campaign2_bear_gate,
    run_campaign3_stock_mechanisms,
    run_campaign4_asset_allocation,
)
from .portfolio_doctor import classify_off_exchange_health_light, diagnose_user_portfolio
from .universal_prompts import (
    build_one_page_overview,
    evaluate_idle_cash_harbor,
    evaluate_portfolio_smart_prompts,
    evaluate_symbol_smart_prompt,
)

__all__ = [
    "DataPortal",
    "HOLDOUT_START",
    "audit_market_indicators",
    "render_market_weather",
    "HoldoutVault",
    "WalkForwardFold",
    "build_purged_walk_forward_folds",
    "classify_market_regimes",
    "overfitting_risk_audit",
    "slice_performance_by_year_and_regime",
    "PortfolioSimConfig",
    "PortfolioBacktestResult",
    "simulate_real_portfolio",
    "DEFAULT_SECTOR_WEIGHTS",
    "DEFAULT_STOCK_WEIGHTS",
    "compute_sector_resonance_panel",
    "build_sector_etf_signal_panels",
    "build_stock_funnel_signal_panels",
    "make_two_stage_stock_exit_callback",
    "compute_live_chip_metrics",
    "compare_chip_ma_strategies",
    "compare_chip_ma_strategies_detailed",
    "compare_stock_quality_chip_strategies",
    "compare_stock_strategies_detailed",
    "rank_top_candidates",
    "compare_fund_strategies",
    "compare_fund_strategies_detailed",
    "evaluate_all_fund_opportunities",
    "check_factor_redundancy",
    "evaluate_factor_panel_l1",
    "run_sector_ablation_and_robustness",
    "run_stock_ablation_and_robustness",
    "FactorSpec",
    "BUILTIN_FACTOR_SPECS",
    "evaluate_factor_expression",
    "expression_fingerprint",
    "verify_expression_no_lookahead",
    "screen_candidate_factor",
    "ForwardTracker",
    "compute_strategy_code_fingerprint",
    "MultiLegConfig",
    "diagnose_strategy_bleeding",
    "simulate_multi_leg_account",
    "KnowledgeBase",
    "LifecycleRegistry",
    "run_weekly_forward_review",
    "run_monthly_research_proposal",
    "build_bear_regime_cap_series",
    "build_sector_etf_v2_signals",
    "run_campaign1_sector_etf_v2",
    "run_campaign2_bear_gate",
    "run_campaign3_stock_mechanisms",
    "run_campaign4_asset_allocation",
    "classify_off_exchange_health_light",
    "diagnose_user_portfolio",
    "evaluate_idle_cash_harbor",
    "evaluate_symbol_smart_prompt",
    "evaluate_portfolio_smart_prompts",
    "build_one_page_overview",
]
