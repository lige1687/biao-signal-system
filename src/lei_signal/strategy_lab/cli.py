"""极简命令行入口：一行命令完成【底座体检 / 市场指标体检 / 同源真实资金回测 / L1-L3 消融体检 / 声明式因子验货 / 多腿联合模拟 / 前向漂移跟踪 / 收盘漏斗】。

用法示例：
  PYTHONPATH=src python3 -m lei_signal.strategy_lab data-health
  PYTHONPATH=src python3 -m lei_signal.strategy_lab audit-indicators
  PYTHONPATH=src python3 -m lei_signal.strategy_lab backtest-funds
  PYTHONPATH=src python3 -m lei_signal.strategy_lab diagnose-strategy --target funds
  PYTHONPATH=src python3 -m lei_signal.strategy_lab screen-factor --name eff_mom --expr "cs_rank(price_efficiency(close, 20) * risk_adj_mom(close, 40))" --hypothesis "路径效率叠加稳健动量"
  PYTHONPATH=src python3 -m lei_signal.strategy_lab multi-leg
  PYTHONPATH=src python3 -m lei_signal.strategy_lab forward-sync
  PYTHONPATH=src python3 -m lei_signal.strategy_lab forward-report
  PYTHONPATH=src python3 -m lei_signal.strategy_lab daily-funnel --top 10
  PYTHONPATH=src python3 -m lei_signal.strategy_lab one-page --top 10
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json

from .chip_trend import (
    compare_chip_ma_strategies_detailed,
    compare_stock_strategies_detailed,
    rank_top_candidates,
)
from .data_portal import DataPortal, SplitMode
from .diagnostics import run_sector_ablation_and_robustness, run_stock_ablation_and_robustness
from .factor_engine import screen_candidate_factor
from .forward_tracker import ForwardTracker, compute_strategy_code_fingerprint
from .fund_evaluator import compare_fund_strategies_detailed, evaluate_all_fund_opportunities
from .indicator_audit import audit_market_indicators, render_market_weather
from .live_refresh import refresh_live_pool
from .multi_leg import MultiLegConfig, diagnose_strategy_bleeding, simulate_multi_leg_account
from .knowledge_base import KnowledgeBase
from .lifecycle import LifecycleRegistry
from .plain_language_guard import plain_state_label
from .research_cycle import run_monthly_research_proposal, run_weekly_forward_review
from .campaigns import _print_all_campaigns
from .portfolio_doctor import diagnose_user_portfolio
from .universal_prompts import evaluate_idle_cash_harbor
from .validation import HoldoutVault


def _append_trial_ledger(portal: DataPortal, action: str, split: str, payload_summary: dict) -> None:
    """自动追加轻量实验留痕（防暗箱反复调参），写在本机用户数据目录，不污染代码库。"""
    ledger_dir = portal.lab_home / "strategy_lab_ledger"
    ledger_dir.mkdir(parents=True, exist_ok=True)
    rec = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "action": action,
        "split": split,
        "code_fingerprint": compute_strategy_code_fingerprint(portal.repo_root),
        "summary": payload_summary,
    }
    with (ledger_dir / "attempts.jsonl").open("a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")


def _print_real_portfolio_table(results: list, target_label: str, split_label: str) -> None:
    print(f"\n=== {target_label} 真实资金账本 — {split_label}（次日开盘成交，含涨跌停、真实费用与仓位上限）===")
    print(
        f"{'买卖规矩':<26} {'出手':>4} {'胜率':>6} {'均赚/均亏(比)':>18} "
        f"{'年化':>7} {'比沪深300多赚':>10} {'最惨回撤':>8} {'赚亏比':>6} {'去前3赚年化':>10} {'年换手':>6}"
    )
    print("-" * 128)
    for r in results:
        m = r.metrics
        wl = f"{float(m['avg_win_pct'])*100:+4.1f}%/{float(m['avg_loss_pct'])*100:4.1f}%({float(m['payoff_ratio']):.2f})"
        print(
            f"{r.strategy_name:<26} {int(m['trades_count']):>4d} {float(m['win_rate'])*100:>5.1f}% {wl:>18} "
            f"{float(m['cagr'])*100:>+6.2f}% {float(m['excess_cagr'])*100:>+9.2f}% {float(m['max_drawdown'])*100:>7.2f}% "
            f"{float(m['calmar']):>6.2f} {float(m['ex_top3_trades_cagr'])*100:>+9.2f}% {float(m['annual_turnover']):>5.1f}倍"
        )
    if results:
        best = max(results, key=lambda x: float(x.metrics["calmar"]))
        aud = best.overfit_audit
        print(
            f"  [稳健度体检 · {best.strategy_name}] {aud.get('risk_light', '')} "
            f"（累计试错 {aud.get('n_trials_penalized')} 次，最赚前3笔占总利润 {float(best.metrics['top3_profit_share'])*100:.0f}%）"
        )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="LEI Strategy Lab 极简因子研究、真实回测与前向闭环工具")
    sub = parser.add_subparsers(dest="cmd", required=True)

    sub.add_parser("data-health", help="检查本地行情、PIT 财报与市场指标数据底座健康度（确认无外盘依赖）")

    p_ind = sub.add_parser("audit-indicators", help="给系统已有市场观测指标做纯因果大顶/大底真本事体检与尾部去重")
    p_ind.add_argument("--full-history", action="store_true", help="使用全历史体检（默认仅用 <=2023 开发期）")

    for cmd_name, help_text in (
        ("backtest-chip", "对比场内基金【死拿 vs 普通均线 vs 活筹码峰+均线+闲钱避风港】真实资金账本"),
        ("backtest-funds", "对比18只去重行业基金【同源历史共振+离成本+未拥挤+闲钱避风港】真实资金账本"),
        ("backtest-stocks", "对比A股个股【本地PIT好生意+高债排雷+同源两步拿牛法+闲钱避风港】真实资金账本"),
    ):
        p_bt = sub.add_parser(cmd_name, help=help_text)
        p_bt.add_argument("--unlock-holdout", action="store_true", help="解锁跑 2024+ 闭卷考样本外验证（受单次锁箱保护）")
        p_bt.add_argument("--allow-repeek", action="store_true", help="显式复看已消费锁箱（结果强制降级标为【已看历史探索】）")

    p_diag = sub.add_parser("diagnose-strategy", help="一键执行 L1信息 + L2真实账户 + L3消融/参数高原/Walk-Forward/失血诊断")
    p_diag.add_argument("--target", choices=["funds", "stocks"], default="funds", help="体检目标：funds(18行业基金) 或 stocks(A股个股)")
    p_diag.add_argument("--cash-only", action="store_true", help="关闭闲钱黄金红利避风港，仅测纯现金")

    p_fac = sub.add_parser("screen-factor", help="声明式新因子一站式验货（AST安全求值 + 自动无未来函数验漏 + 两级正交查重 + L1 Rank IC）")
    p_fac.add_argument("--name", required=True, help="候选因子英文标识")
    p_fac.add_argument("--expr", required=True, help="纯因果面板表达式，例如 cs_rank(price_efficiency(close, 20) * risk_adj_mom(close, 40))")
    p_fac.add_argument("--hypothesis", required=True, help="先写清金融含义与预期收益来源")
    p_fac.add_argument("--pool", choices=["etf", "stock"], default="etf", help="验货标的池")

    p_ml = sub.add_parser("multi-leg", help="个人账户级多腿联合模拟（压舱石 + 行业波段 + 个股好生意 + 闲钱避风港 + 定投）")
    p_ml.add_argument("--core", type=float, default=0.35, help="压舱石底仓占比（默认 0.35）")
    p_ml.add_argument("--sector", type=float, default=0.40, help="行业右侧波段占比（默认 0.40）")
    p_ml.add_argument("--stock", type=float, default=0.25, help="个股好生意龙头占比（默认 0.25，填0即纯基金组合）")
    p_ml.add_argument("--monthly", type=float, default=0.0, help="每月新增工资定投金额（元，默认 0）")
    p_ml.add_argument("--unlock-holdout", action="store_true", help="解锁查看 2024+ 样本外（受单次锁箱保护）")
    p_ml.add_argument("--allow-repeek", action="store_true", help="显式复看已消费锁箱")

    sub.add_parser("forward-sync", help="冻结最新收盘推荐快照至不可篡改前向账本，并推进自动前向模拟盘对账")
    sub.add_parser("forward-report", help="查看前向实盘 5/20/60 日真实超额表现与 Live-vs-Backtest 漂移监控板")
    sub.add_parser("campaigns", help="运行四场买方标准研究战役（严格锁死 <=2023 开发期）")
    sub.add_parser("lifecycle-status", help="查看策略五态生命周期注册表与机构反例记忆库概况")
    sub.add_parser("weekly-review", help="执行周度前向漂移复盘与生命周期告警检查")
    sub.add_parser("monthly-proposal", help="执行月度失血诊断并经反例库筛重生成下月挖掘提案")

    p_fn = sub.add_parser("daily-funnel", help="输出最新收盘【牛熊天气单 + 场内基金前10名 + 好生意个股前10名】并自动留痕前向快照")
    p_fn.add_argument("--top", type=int, default=10, help="每类筛选前几名尖子生（默认 10）")
    p_fn.add_argument("--refresh", action="store_true", help="先并发拉取今日最新收盘前复权行情再筛选")

    p_op = sub.add_parser("one-page", help="一页看全【左边：手头持仓健康灯与底色诊断 | 右边：今日基金与真龙头尖子生】")
    p_op.add_argument("--top", type=int, default=10, help="右边每类尖子生展示数量（默认 10）")
    p_op.add_argument("--refresh", action="store_true", help="先刷新最新收盘前复权行情")

    args = parser.parse_args(argv)
    portal = DataPortal()

    if args.cmd == "data-health":
        rep = portal.data_health_report()
        print("\n=== LEI Strategy Lab 本地数据底座体检 ===")
        for k, v in rep.items():
            print(f"  - {k}: {v}")
        return 0

    if args.cmd == "audit-indicators":
        split: SplitMode = "full" if args.full_history else "explore"
        rows, dups = audit_market_indicators(portal, split=split)
        print(f"\n=== 市场观测指标纯因果历史真本事体检（区间模式: {split}，严格按60/120日视窗零重叠去重）===")
        print(f"{'市场':<4} {'评级':<12} {'指标名称':<22} {'独立大底(次) 半年胜率/超额':<26} {'独立大顶(次) 3月超额/最深回撤':<28} {'结论'}")
        print("-" * 126)
        for r in rows:
            bot_str = (
                f"({r.bottom_events_nonoverlap:>2d}次) {r.bottom_winrate_120d*100:4.0f}% / {r.bottom_edge_120d*100:+5.1f}%"
                if r.bottom_winrate_120d >= 0
                else f"({r.bottom_events_nonoverlap:>2d}次) 样本不足"
            )
            top_str = (
                f"({r.top_events_nonoverlap:>2d}次) {r.top_edge_60d*100:+5.1f}% / {r.top_worst_dd_60d*100:5.1f}%"
                if r.top_events_nonoverlap > 0
                else "( 0次) 样本不足"
            )
            print(f"{r.market:<4} {r.grade:<12} {r.name_cn:<20} {bot_str:<26} {top_str:<28} {r.verdict_cn}")

        if dups:
            print("\n=== 发现线性与极端尾部双重同源重复指标对（|r|>=0.72 且 尾部Jaccard>=0.45 或 |r|>=0.88）===")
            for a, b, corr in dups:
                print(f"  - {a}  <-->  {b}  (相关系数: {corr:+.2f})")

        _append_trial_ledger(portal, "audit-indicators", split, {"count": len(rows)})
        return 0

    if args.cmd in ("backtest-chip", "backtest-funds", "backtest-stocks"):
        vault = HoldoutVault(portal.lab_home)
        trial_stats = vault.count_family_trials(args.cmd)
        n_trials = max(1, trial_stats["explore_trials"] + 1)
        splits: list[tuple[SplitMode, str]] = [("explore", "开发期 (2023年及以前)")]

        if args.unlock_holdout:
            fp = compute_strategy_code_fingerprint(portal.repo_root)
            gate = vault.check_or_consume(
                args.cmd,
                rule_fingerprint=fp,
                allow_repeek_as_explore=bool(args.allow_repeek),
            )
            print(f"\n[闭卷考锁箱状态] {gate['warning_cn']}")
            if gate["blocked"]:
                return 2
            lbl = (
                "已消耗闭卷考复看 [降级为已看历史探索] (2024年至今)"
                if gate["status"] == "downgraded_to_explore_seen"
                else "首次开封未见闭卷考 (2024年至今)"
            )
            splits.append(("holdout", lbl))

        if args.cmd == "backtest-funds":
            target_label = "18只去重行业代表基金（同源历史共振与真实资金账本）"
            runner = compare_fund_strategies_detailed
        elif args.cmd == "backtest-chip":
            target_label = "场内基金池（真实资金账本）"
            runner = compare_chip_ma_strategies_detailed
        else:
            target_label = "A股个股池（本地PIT好生意+高债排雷+同源两步拿牛法）"
            runner = compare_stock_strategies_detailed

        for sp, label in splits:
            res = runner(portal, split=sp, n_trials=n_trials)
            _print_real_portfolio_table(res, target_label, label)
            _append_trial_ledger(
                portal,
                args.cmd,
                sp,
                {
                    r.strategy_name: {
                        "cagr": r.metrics["cagr"],
                        "excess_cagr": r.metrics["excess_cagr"],
                        "mdd": r.metrics["max_drawdown"],
                        "win_rate": r.metrics["win_rate"],
                        "ex_top3_cagr": r.metrics["ex_top3_trades_cagr"],
                    }
                    for r in res
                },
            )
        return 0

    if args.cmd == "diagnose-strategy":
        mode = "cash" if args.cash_only else "gold_dividend_harbor"
        if args.target == "funds":
            rep = run_sector_ablation_and_robustness(portal, split="explore", idle_cash_mode=mode)
            title = "18只去重行业基金（右侧同源策略）"
        else:
            rep = run_stock_ablation_and_robustness(portal, split="explore", idle_cash_mode=mode)
            title = "A股好生意龙头（同源两步拿牛策略）"

        if not rep.get("available"):
            print(f"体检无法执行：{rep.get('reason')}")
            return 1

        print(f"\n=== {title} 综合体检（严格仅看 2023 年及以前历史）===")
        l1 = rep["l1_factor_info"]
        print(f"  [挑品眼光准不准] {l1['l1_verdict_cn']}")
        for h_key, h_val in l1["horizons"].items():
            q = h_val["quantiles"]
            top_ex = q["top_vs_pool_excess"]
            top_ex_s = f"{top_ex*100:+.2f}%" if top_ex is not None else "暂无"
            print(
                f"      往后{h_key.replace('d', '个交易日')}: 排序相关={h_val['rank_ic_mean']:+.4f} | "
                f"排最前面一组比平均多赚={top_ex_s} | 高低分组顺不顺={q['monotonicity_spearman']}"
            )
        bm = rep["l2_base_metrics"]
        print(
            f"  [真实资金账本] 每年收益={bm['cagr']*100:+.2f}% | 比沪深300多赚={bm['excess_cagr']*100:+.2f}% | "
            f"最惨回撤={bm['max_drawdown']*100:.2f}% | 赚亏性价比={bm['calmar']:.2f} | 去最赚3笔年化={bm['ex_top3_trades_cagr']*100:+.2f}%"
        )
        print(f"  [是不是碰巧] {rep['l2_overfit_audit'].get('risk_light')}")
        print("\n  [去掉单个条件看谁真管用]：")
        for row in rep["l3_ablation"]:
            print(
                f"      {row['variant']:<28} 每年收益={row['cagr']*100:+6.2f}% | 比大盘多赚={row['excess_cagr']*100:+6.2f}% | "
                f"回撤={row['max_drawdown']*100:6.2f}% | 相对基准差={row['delta_cagr_vs_base']*100:+5.2f}%  {row.get('verdict_cn', '')}"
            )
        if "l3_parameter_plateau" in rep:
            pl = rep["l3_parameter_plateau"]
            print(f"\n  [改参数两成稳不稳] {pl['verdict_cn']}")
        if rep.get("l3_walk_forward"):
            print("\n  [按时间一段段往后滚动验证]：")
            for wf in rep["l3_walk_forward"]:
                print(
                    f"      第 {wf['fold_id']} 段 ({wf['test_window']}): 每年收益={wf['cagr']*100:+6.2f}% | "
                    f"比大盘多赚={wf['excess_cagr']*100:+6.2f}% | 最惨回撤={wf['max_drawdown']*100:6.2f}%"
                )
        if rep.get("l2_by_regime"):
            print("\n  [不同牛熊环境拆解]：")
            for rg in rep["l2_by_regime"]:
                print(
                    f"      {rg['regime']:<8} ({rg['days']:>4d}日): 每年收益={rg['cagr']*100:+6.2f}% | "
                    f"比大盘多赚={rg['excess_return']*100:+6.2f}% | 最惨回撤={rg['max_drawdown']*100:6.2f}%"
                )
        _append_trial_ledger(portal, f"diagnose-{args.target}", "explore", {"cagr": bm["cagr"], "calmar": bm["calmar"]})
        return 0

    if args.cmd == "screen-factor":
        rep = screen_candidate_factor(
            portal,
            name=args.name,
            expr=args.expr,
            financial_hypothesis=args.hypothesis,
            pool=args.pool,
            split="explore",
        )
        if not rep.get("available"):
            print(f"验货失败：{rep.get('reason')}")
            return 1
        print(f"\n=== 新指标自动验货：{rep['name']}（测试范围=2023年及以前）===")
        print(f"  金融道理：{rep['financial_hypothesis']}")
        print(f"  有没有偷看未来：{rep['no_lookahead_check']['verdict_cn']}")
        if "l1_evaluation" in rep:
            l1 = rep["l1_evaluation"]
            red = l1["redundancy"]
            print(f"  跟已有指标重不重复：{red['status']}（最高排序相似度={red['max_abs_rank_corr']}）")
            for hk, hv in l1["horizons"].items():
                q = hv["quantiles"]
                top_ex = q["top_vs_pool_excess"]
                top_ex_s = f"{top_ex*100:+.2f}%" if top_ex is not None else "暂无"
                print(
                    f"  往后{hk.replace('d', '个交易日')}检验：排序相关={hv['rank_ic_mean']:+.4f} | "
                    f"排最前面一组比平均多赚={top_ex_s} | 高低分组顺不顺={q['monotonicity_spearman']}"
                )
        print(f"  >>> 最终判定：{rep['admission_verdict_cn']}")
        _append_trial_ledger(portal, "screen-factor", "explore", {"name": args.name, "fp": rep["ast_fingerprint"], "verdict": rep["admission_verdict_cn"]})
        return 0

    if args.cmd == "multi-leg":
        sp_ml: SplitMode = "explore"
        if args.unlock_holdout:
            vault = HoldoutVault(portal.lab_home)
            gate = vault.check_or_consume(
                "multi-leg",
                rule_fingerprint=compute_strategy_code_fingerprint(portal.repo_root),
                allow_repeek_as_explore=bool(args.allow_repeek),
            )
            print(f"\n[闭卷考锁箱状态] {gate['warning_cn']}")
            if gate["blocked"]:
                return 2
            sp_ml = "holdout"
        ml_cfg = MultiLegConfig(
            core_weight=args.core,
            sector_etf_weight=args.sector,
            stock_leader_weight=args.stock,
            monthly_contribution=args.monthly,
        )
        rep = simulate_multi_leg_account(portal, split=sp_ml, config=ml_cfg)
        sm = rep["summary_metrics"]
        print(f"\n=== 个人账户多块资金联合实测（时间范围: {rep['date_range']}）===")
        print(f"  资金搭配：稳健底仓 {rep['weights']['core']*100:.0f}% + 行业基金波段 {rep['weights']['sector_etf']*100:.0f}% + 个股好生意 {rep['weights']['stock_leader']*100:.0f}%")
        print(
            f"  总账户成绩：每年收益={sm['cagr']*100:+.2f}%（沪深300={sm['bench_hs300_cagr']*100:+.2f}%，比大盘多赚={sm['excess_cagr_vs_hs300']*100:+.2f}%）| "
            f"最惨回撤={sm['max_drawdown']*100:.2f}%（沪深300={sm['bench_hs300_mdd']*100:.2f}%）| 赚亏性价比={sm['calmar']:.2f}"
        )
        print(f"  稳健度体检：{rep['overfit_audit'].get('risk_light')}")
        print("  几块资金是不是同涨同跌（越接近 0 越分散）：")
        for leg_k, corr_row in rep["leg_correlation_matrix"].items():
            row_s = "  ".join(f"{k}:{v:+.2f}" for k, v in corr_row.items())
            print(f"      {leg_k:<16} -> {row_s}")
        bd = rep["bleeding_diagnosis"]
        if bd.get("top3_drawdown_episodes"):
            print("  历史最痛的 3 次回撤：")
            for ep in bd["top3_drawdown_episodes"]:
                print(
                    f"      {ep['peak_date']}~{ep['trough_date']}（{ep['dominant_regime']}）："
                    f"回撤 {ep['drawdown_pct']*100:.1f}%（同期大盘 {ep['bench_return_during_dd']*100:+.1f}%，回本日期 {ep['recovered_date']}）"
                )
        print("  下一步优先改进建议：")
        for hyp in bd.get("next_mining_hypotheses", []):
            print(f"      • {hyp}")
        return 0

    if args.cmd == "forward-sync":
        tracker = ForwardTracker(portal)
        rec = tracker.record_snapshot(top_n=10)
        recon = tracker.reconcile()
        print("\n=== 今日收盘推荐已自动冻结存档与模拟对账 ===")
        print(f"  存档结果：信号日期={rec.get('signal_date')}，本次新冻推荐={rec.get('recommendations_frozen', 0)}条")
        print(f"  对账结果：账目核对={'通过' if recon.get('reconciled') else '异常'}，最新日期={recon.get('as_of')}")
        return 0

    if args.cmd == "forward-report":
        tracker = ForwardTracker(portal)
        recon = tracker.reconcile()
        rep = tracker.drift_report()
        print(f"\n=== 实盘跟盘观察复盘（截至 {recon.get('as_of')}）===")
        print(f"  已记录交易日数：{rep['snapshots_frozen']} 天 | 累计跟踪推荐：{rep['total_recommendations']} 条")
        sleeve_cn = {"sector_etf": "行业基金推荐", "stock_leader": "行业真龙头个股", "stock_small_giant": "细分小巨人个股"}
        for sleeve, st in rep["sleeve_forward_stats"].items():
            e20 = f"{st['mean_excess_20d']*100:+.2f}%" if st["mean_excess_20d"] is not None else "还没满1个月"
            r20 = f"{st['mean_ret_20d']*100:+.2f}%" if st["mean_ret_20d"] is not None else "还没满1个月"
            print(
                f"  [{sleeve_cn.get(sleeve, sleeve):<10}] 累计推荐={st['total_recommendations']:>3d} | 满1个月={st['matured_20d']:>3d} "
                f"(平均涨跌={r20}, 比沪深300多赚={e20}) | {st['drift_status']}"
            )
        print("  自动模拟跟盘账户（次日开盘价成交，每天核对现金+持仓=总资产）：")
        for acc in rep["paper_accounts"]:
            ret_pct = (float(acc["equity"]) / float(acc["initial_cash"]) - 1.0) * 100.0
            print(
                f"      {sleeve_cn.get(acc['sleeve'], acc['sleeve']):<10} 总资产={acc['equity']:>10.2f}元（现金={acc['cash']:>10.2f}元，累计 {ret_pct:+.2f}%）"
            )
        return 0

    if args.cmd == "campaigns":
        _print_all_campaigns()
        return 0

    if args.cmd == "lifecycle-status":
        reg = LifecycleRegistry(portal.repo_root).load()
        kb = KnowledgeBase(portal.repo_root).load()
        print("\n=== 策略当前所处阶段清单 ===")
        for e in reg.get("entries", []):
            st_cn = plain_state_label(str(e.get("state", "")))
            print(f"  [{st_cn:<14}] {e['name']}")
        print(f"\n=== 历史避坑与有效经验库（已淘汰雷区 {len(kb.get('anti_patterns', []))} 条 | 已证实有效办法 {len(kb.get('verified_edges', []))} 条）===")
        return 0

    if args.cmd == "weekly-review":
        rep = run_weekly_forward_review(portal)
        print(f"\n=== 本周实盘跟盘复盘（截至 {rep.get('as_of')}）===")
        print(f"  结论：{rep['verdict_cn']}")
        cn_summary = {plain_state_label(k): v for k, v in rep["lifecycle_summary"].items()}
        print(f"  各阶段策略数：{cn_summary}")
        for al in rep["drift_alerts"]:
            print(f"  ⚠️ {al}")
        return 0

    if args.cmd == "monthly-proposal":
        rep = run_monthly_research_proposal(portal)
        print(f"\n=== 下月定向改进提案（已对照 {rep['total_anti_patterns_guarded']} 条历史踩坑记录筛查）===")
        for p_item in rep["screened_proposals"]:
            print(f"  • {p_item['proposal']}")
            if p_item["related_anti_patterns"]:
                print(f"    └─ 注意避开同类老坑：{'; '.join(p_item['related_anti_patterns'])}")
        return 0

    if args.cmd == "daily-funnel":
        refresh_stats = None
        if args.refresh:
            refresh_stats = refresh_live_pool(portal)
            print(
                f"\n[全市场精选池已同步至最新完整收盘日 {refresh_stats['latest_complete_date']}] "
                f"共纳管 {refresh_stats['total_universe']} 个标的"
                f"（场内基金 {refresh_stats['etf_count']} 只 + 行业真龙头 {refresh_stats['leader_pool_count']} 只 "
                f"+ 细分小巨人 {refresh_stats['small_giant_pool_count']} 只；"
                f"本次拉取更新 {refresh_stats['updated']} 只，已是最新 {refresh_stats['already_fresh']} 只）"
            )
        weather = render_market_weather(portal)
        fund_opps = evaluate_all_fund_opportunities(portal)
        leader_picks = rank_top_candidates(portal, top_n=args.top, pool="leader", split="full")
        small_picks = rank_top_candidates(portal, top_n=args.top, pool="small_giant", split="full")

        print("\n=== 第一步：牛熊极端警报与连续风险温度计（平时静音不打架，极端才响）===")
        print(
            f"  [A股大势] {weather['cn_plain_verdict']} "
            f"（风险温度={weather['cn_risk_temperature']}/100，建议权益上限={int(weather['cn_suggested_equity_cap']*100)}%）"
        )
        print(
            f"  [美股底仓] {weather['us_plain_verdict']} "
            f"（风险温度={weather['us_risk_temperature']}/100，建议权益上限={int(weather['us_suggested_equity_cap']*100)}%）"
        )

        print("\n=== 第二步（基金甲·底仓全景）：10只去重宽基与海外商品压舱石位置与动作 ===")
        for b in fund_opps["broad_compass"]:
            print(
                f"  {b['code']} {b['name']:<10} | 收盘 {b['close']:<6} | 近两年高低分位 {b['pos_2y_pct']:>4} "
                f"| 距一年高点 {b['drawdown_from_1y_high']:>6} | {b['action_verdict']}"
            )

        print("\n=== 第二步（基金乙·右侧波段）：行业代表基金起势尖子生（板块内部真共振 + 离防守近 + 未拥挤）===")
        if not fund_opps["right_side_sector_picks"]:
            print("  当前18个去重行业中暂无同时满足【内部半数股票共振 + 站上均线离成本近 + 未拥挤】的板块。")
        for idx, p in enumerate(fund_opps["right_side_sector_picks"], 1):
            print(f"  第 {idx:>2d} 名：{p['code']} {p['name']}（收盘价 {p['close']}，日期 {p['as_of']}）")
            print(f"         {p['plain_reason']}")

        print("\n=== 第二步（基金丙·左侧潜伏）：跌透刚站回20日均线的黄金坑拐点基金 ===")
        if not fund_opps["left_side_turnaround_picks"]:
            print("  当前暂无处于两年深坑且刚重新站上20日均线拐头的宽基或行业基金。")
        for idx, p in enumerate(fund_opps["left_side_turnaround_picks"], 1):
            print(f"  第 {idx:>2d} 名：{p['code']} {p['name']} [{p['kind']}]（收盘价 {p['close']}，日期 {p['as_of']}）")
            print(f"         {p['plain_reason']}")

        if fund_opps["crowded_no_chase_warnings"]:
            print("\n  [基金过热拥挤防追高提醒]：")
            for w in fund_opps["crowded_no_chase_warnings"]:
                print(f"  ⚠️ {w['code']} {w['name']}：{w['note']}")

        print(f"\n=== 第三步（个股甲·重点看）：各行业真龙头前 {args.top} 名尖子生（总市值300亿+/行业一哥二哥 + 业绩稳现金流硬 + 筹码干净）===")
        if not leader_picks:
            print("  今日暂无同时过关的行业大龙头，耐心等待企稳。")
        for idx, p in enumerate(leader_picks, 1):
            print(f"  第 {idx:>2d} 名：{p['code']} {p['name']}（收盘价 {p['close']}，日期 {p['as_of']}）")
            print(f"         {p['plain_reason']}")

        print(f"\n=== 第三步（个股乙·弹性补充）：细分行业小巨人前 {args.top} 名尖子生（80~300亿 + 高回报高增长 + 现金流硬 + 筹码干净）===")
        if not small_picks:
            print("  今日暂无同时过关的细分小巨人。")
        for idx, p in enumerate(small_picks, 1):
            print(f"  第 {idx:>2d} 名：{p['code']} {p['name']}（收盘价 {p['close']}，日期 {p['as_of']}）")
            print(f"         {p['plain_reason']}")

        ledger_dir = portal.lab_home / "strategy_lab_ledger"
        ledger_dir.mkdir(parents=True, exist_ok=True)
        snapshot = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "refresh_stats": refresh_stats,
            "market_weather": weather,
            "fund_opportunities": fund_opps,
            "top_industry_leaders": leader_picks,
            "top_small_giants": small_picks,
        }
        (ledger_dir / "latest_daily_funnel.json").write_text(
            json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # 自动幂等冻结当日推荐快照并推进前向对账（零阻断）
        try:
            tracker = ForwardTracker(portal)
            tracker.record_snapshot(snapshot, top_n=args.top)
            tracker.reconcile()
        except Exception:
            pass
        _append_trial_ledger(
            portal,
            "daily-funnel",
            "full",
            {
                "right_sector_funds": [p["code"] for p in fund_opps["right_side_sector_picks"]],
                "left_turn_funds": [p["code"] for p in fund_opps["left_side_turnaround_picks"]],
                "leader_picks": [p["code"] for p in leader_picks],
                "small_giant_picks": [p["code"] for p in small_picks],
            },
        )
        return 0

    if args.cmd == "one-page":
        if args.refresh:
            refresh_live_pool(portal)
        weather = render_market_weather(portal)
        idle_harbor = evaluate_idle_cash_harbor(portal)
        portfolio_diag = diagnose_user_portfolio(portal.lab_home)
        fund_opps = evaluate_all_fund_opportunities(portal)
        leader_picks = rank_top_candidates(portal, top_n=args.top, pool="leader", split="full")
        small_picks = rank_top_candidates(portal, top_n=args.top, pool="small_giant", split="full")

        print("\n=== 【一页总览 · 顶栏】牛熊极端天气与空仓闲钱去向 ===")
        print(f"  [国内大盘] {weather['cn_plain_verdict']}（温度 {weather['cn_risk_temperature']}/100）")
        print(f"  [海外市场] {weather['us_plain_verdict']}（温度 {weather['us_risk_temperature']}/100）")
        print(f"  [空仓闲钱] {idle_harbor['headline_cn']}")
        print(f"             └─ {idle_harbor['allocation_cn']}")

        print("\n=== 【左半屏】我手头持仓的健康灯与真实底色体检（同名A/C份额已合并）===")
        for tip in portfolio_diag["summary_tips"]:
            print(f"  • {tip}")
        print("-" * 118)
        for item in portfolio_diag["items"]:
            d200 = f"{item['dist_ma200_pct']:+.0f}%" if item["dist_ma200_pct"] is not None else "—"
            dd1y = f"{item['drawdown_from_1y_high_pct']:.0f}%" if item["drawdown_from_1y_high_pct"] is not None else "—"
            print(
                f"  {item['health_light']:<18} | {item['fund_name']:<20} ({item['market_value']:>7.0f}元 / 占{item['weight_in_account_pct']:>4.1f}% / 账面{item['account_return_pct']:>+6.1f}%) "
                f"| 离年线 {d200:>5} | 距一年高点 {dd1y:>4}"
            )
            print(f"     └─ 动作：{item['action_advice_cn']}")
            print(f"     └─ 底色：{item['penetration_truth_cn']}")

        print("\n=== 【右半屏】今日收盘筛出的场内基金与真龙头尖子生 ===")
        print("  [行业基金 · 右侧共振起势]：")
        for idx, p in enumerate(fund_opps["right_side_sector_picks"], 1):
            print(f"    {idx}. {p['code']} {p['name']}（现价 {p['close']}）— {p['plain_reason']}")
        print("  [行业基金 · 左侧深坑拐头]：")
        for idx, p in enumerate(fund_opps["left_side_turnaround_picks"], 1):
            print(f"    {idx}. {p['code']} {p['name']}（现价 {p['close']}）— {p['plain_reason']}")
        print(f"  [行业真龙头个股 · 前 {min(len(leader_picks), args.top)} 名]：")
        for idx, p in enumerate(leader_picks[: args.top], 1):
            print(f"    {idx:>2d}. {p['code']} {p['name']}（现价 {p['close']}）— {p['plain_reason']}")
        print(f"  [细分小巨人个股 · 前 {min(len(small_picks), args.top)} 名]：")
        for idx, p in enumerate(small_picks[: args.top], 1):
            print(f"    {idx:>2d}. {p['code']} {p['name']}（现价 {p['close']}）— {p['plain_reason']}")

        ledger_dir = portal.lab_home / "strategy_lab_ledger"
        ledger_dir.mkdir(parents=True, exist_ok=True)
        one_page_payload = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "market_weather": weather,
            "idle_cash_harbor": idle_harbor,
            "left_portfolio_health": portfolio_diag,
            "right_opportunities": {
                "fund_opportunities": fund_opps,
                "top_industry_leaders": leader_picks,
                "top_small_giants": small_picks,
            },
        }
        (ledger_dir / "latest_one_page_dashboard.json").write_text(
            json.dumps(one_page_payload, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        # 每日收盘定时任务跑 one-page 时同步冻结前向快照并自动对账
        try:
            tracker = ForwardTracker(portal)
            tracker.record_snapshot(
                {
                    "fund_opportunities": fund_opps,
                    "top_industry_leaders": leader_picks,
                    "top_small_giants": small_picks,
                },
                top_n=args.top,
            )
            tracker.reconcile()
        except Exception:
            pass
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
