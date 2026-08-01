"""LEI 技术信号研究系统 —— Streamlit 界面。

四个页面：当前观察、技术事件时间轴、结构诊断、历史信号研究。

界面只调用 compose.pipeline 与 research 模块，不重复实现任何业务规则。
所有提示都显示规则 ID、版本与来源，research_proxy 明确标注。
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from lei_signal.compose.pipeline import AnalysisResult, analyze
from lei_signal.data.validation import DataUnavailableError
from lei_signal.domain.types import (
    COLOR_CN,
    LONG_TREND_CN,
    STAGE_CN,
    STAGE_RANK,
    Provenance,
)
from lei_signal.ui.charts import (
    build_price_figure,
    build_stage_history_figure,
    build_volume_profile_figure,
)

DISCLAIMER = (
    "本系统是技术信号识别、解释与历史有效性研究工具，**不是自动交易系统**。"
    "不下单、不计算仓位、不管理资金，也不输出确定性买卖建议。"
    "颜色、阶段与风险提示都只是观察信息。"
)


def _load(symbol: str, build_history: bool) -> AnalysisResult:
    return analyze(symbol, build_history=build_history)


@st.cache_data(show_spinner=False, ttl=900)
def _cached_analysis(symbol: str, build_history: bool) -> AnalysisResult:
    return _load(symbol, build_history)


def render() -> None:
    st.set_page_config(page_title="LEI 技术信号研究系统", layout="wide")
    st.title("LEI 技术信号研究系统")
    st.caption(
        "复权日线 · 三色 + 结构 + 状态机 + 历史有效性研究 · "
        "信号研究工具，不是自动交易系统"
    )

    with st.sidebar:
        st.header("输入")
        symbol = st.text_input(
            "股票或ETF代码",
            value="QQQ",
            help="例如 QQQ、AAPL、0700.HK、159915、510300",
        )
        build_history = st.checkbox(
            "构建逐日解释历史（较慢，研究页需要）", value=True
        )
        run = st.button("分析", type="primary", use_container_width=True)
        st.divider()
        st.caption(DISCLAIMER)

    if not run and "analysis" not in st.session_state:
        st.info("在左侧输入代码后点击「分析」。首次加载会自动下载复权日线行情。")
        _render_rule_reference()
        return

    if run:
        try:
            with st.spinner(f"正在获取并分析 {symbol} ..."):
                st.session_state["analysis"] = _cached_analysis(symbol, build_history)
        except DataUnavailableError as exc:
            st.error(f"**DATA_UNAVAILABLE**：{exc}")
            st.caption("数据问题不会被静默处理为「无信号」。请检查代码、市场后缀或稍后重试。")
            return
        except ValueError as exc:
            st.error(str(exc))
            return

    result: AnalysisResult | None = st.session_state.get("analysis")
    if result is None:
        return

    tab_current, tab_timeline, tab_diagnostics, tab_research = st.tabs(
        ["当前观察", "技术事件时间轴", "结构诊断", "历史信号研究"]
    )
    with tab_current:
        _render_current(result)
    with tab_timeline:
        _render_timeline(result)
    with tab_diagnostics:
        _render_diagnostics(result)
    with tab_research:
        _render_research(result)


# ---------------- 当前观察页 ----------------


def _render_current(result: AnalysisResult) -> None:
    a = result.assessment
    frame = result.frame
    latest = frame.iloc[-1]

    st.subheader(f"{result.display_name}（{result.symbol}）")

    report = result.price_data.report if result.price_data else None
    if report is not None:
        # first_date/last_date 在 ValidationReport 中是 Optional，但校验通过的报告
        # 一定有值；此处仍显式兜底，避免界面因元数据缺失而崩溃。
        span = (
            f"{report.first_date.date()} 至 {report.last_date.date()}"
            if report.first_date is not None and report.last_date is not None
            else "日期范围不可用"
        )
        st.caption(
            f"数据源 {report.provider} · {'复权' if report.adjusted else '未复权'}日线 · "
            f"{report.rows} 根 · {span}"
        )
        for warning in report.warnings:
            st.warning(f"数据提示：{warning}")
    if result.suspicious_gaps:
        st.warning(
            f"检测到 {len(result.suspicious_gaps)} 个疑似未复权跳空日，"
            f"最近一次 {result.suspicious_gaps[-1].date()}（仅提示，未修改价格）"
        )

    columns = st.columns(5)
    columns[0].metric("机会阶段", STAGE_CN[a.stage.value])
    columns[1].metric("最新颜色", COLOR_CN[a.color.value])
    columns[2].metric("最新收盘", f"{float(latest['close']):.4f}")
    columns[3].metric("数据日期", a.as_of.strftime("%Y-%m-%d"))
    columns[4].metric("规则账本版本", a.rule_ruleset_version)

    st.info(f"**阶段说明**：{a.stage_change_reason_cn}")

    # 三色判断依据
    with st.expander("三色判断依据（可逐值核对）", expanded=True):
        st.write(
            f"收盘 **{float(latest['close']):.4f}** ／ "
            f"EMA20 **{float(latest['ema20']):.4f}** ／ "
            f"20个交易日前收盘 **{float(latest['close_lag20']):.4f}**"
        )
        st.write(f"判定理由：{latest['signal_reason']}")
        st.caption(
            "绿色 = 收盘 > EMA20 且 收盘 > 20日前收盘；"
            "黑色 = 两者均小于；灰色 = 已就绪但两组条件均不成立（方向分歧，需要关注，不等于卖出）"
        )

    # 五维度
    st.markdown("#### 维度概览")
    dimension_columns = st.columns(len(a.dimensions))
    for column, (name, value) in zip(dimension_columns, a.dimensions.items(), strict=True):
        column.metric(name, value)

    # 结构与 B1
    left, right = st.columns(2)
    with left:
        st.markdown("#### 有效底部结构")
        if a.all_live_structures:
            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "结构类型": s.structure_type,
                            "C": s.c_price,
                            "颈线": s.neckline,
                            "候选日": s.detected_date,
                            "确认日": s.confirmed_date,
                            "是否主结构": s is a.primary_structure,
                            "来源规则": s.source_rule_id or "-",
                        }
                        for s in a.all_live_structures
                    ]
                ),
                use_container_width=True,
                hide_index=True,
            )
            st.caption("多个来源的结构同时保留；主结构是最近确认的有效结构，其他不会被删除。")
        else:
            st.write("当前没有有效底部结构。")

    with right:
        st.markdown("#### B1 第一阻力")
        if a.b1_price is not None:
            st.write(f"B1 = **{a.b1_price:.4f}**（距离 {a.distance_to_b1_pct:.2f}%）")
            st.write(f"拐点日 {a.b1_pivot_date} ／ 确认可用日 {a.b1_available_date}")
            if a.distance_to_b1_r is not None:
                st.write(f"以主结构C计的距离：{a.distance_to_b1_r:.2f}R")
            st.caption("B1 是第一阻力，不是强制止盈目标，也不是入场门槛。")
        else:
            st.write("过去两年内没有已确认且高于当前价的摆动高点，**B1 不存在**。")
            st.caption("B1 不存在不会阻止信号产生。")

        if a.active_top is not None:
            st.warning(
                f"存在有效顶部警报：颈线 {a.active_top.neckline:.4f}，"
                f"第一高点 {a.active_top.reference_high:.4f}。"
                "顶部与底部可暂时并存，此处显示冲突而不是覆盖。"
            )

    # 风险
    if a.risks:
        st.markdown("#### 风险提示（按优先级排序，排序不代表自动卖出）")
        for index, alert in enumerate(a.risks, start=1):
            st.error(
                f"{index}. **{alert.label_cn}** — {alert.detail_cn}　"
                f"`{alert.rule_id}@{alert.rule_version}`"
            )

    # 支持与冲突并排
    st.markdown("#### 支持因素 / 冲突因素（并排显示，不隐藏不利信息）")
    support_column, conflict_column = st.columns(2)
    with support_column:
        st.markdown("**支持**")
        _render_factors(a.supports)
    with conflict_column:
        st.markdown("**冲突**")
        _render_factors(a.conflicts)

    # 事件三栏
    st.markdown("#### 今日新增 / 仍然有效 / 已经失效")
    new_column, active_column, dead_column = st.columns(3)
    with new_column:
        st.markdown(f"**今日新增（{len(a.new_events)}）**")
        _render_event_list(a.new_events)
    with active_column:
        st.markdown(f"**仍然有效（{len(a.active_events)}）**")
        _render_event_list(a.active_events[-12:])
    with dead_column:
        st.markdown(f"**已经失效（{len(a.invalidated_events)}）**")
        _render_event_list(a.invalidated_events[-12:])

    # 图表
    st.markdown("#### 价格、均线、结构与成交量")
    window = st.slider("显示最近多少根K线", 60, min(1200, len(frame)), min(320, len(frame)))
    st.plotly_chart(
        build_price_figure(
            frame.tail(window),
            structures=result.structures,
            b1_price=a.b1_price,
            profile=result.profile,
        ),
        use_container_width=True,
    )

    if result.profile is not None:
        st.markdown("#### 筹码分布代理")
        st.caption(
            "⚠️ 这是**筹码分布代理**：把成交量按价格区间均匀分配得到的近似分布。"
            "OHLCV 无法得知真实投资者持仓成本，本图不代表真实持仓成本。"
        )
        st.plotly_chart(build_volume_profile_figure(result.profile), use_container_width=True)
        profile_columns = st.columns(4)
        profile_columns[0].metric("POC（代理）", f"{result.profile.poc:.4f}")
        profile_columns[1].metric("VAL（代理）", f"{result.profile.val:.4f}")
        profile_columns[2].metric("VAH（代理）", f"{result.profile.vah:.4f}")
        profile_columns[3].metric(
            "上方套牢代理占比", f"{result.profile.overhead_supply_ratio:.1%}"
        )

    # CSV 导出
    st.markdown("#### 导出")
    export_columns = st.columns(2)
    signal_csv = frame.reset_index().to_csv(index=False).encode("utf-8-sig")
    export_columns[0].download_button(
        "下载完整信号CSV",
        signal_csv,
        f"{result.symbol}-signals.csv",
        "text/csv",
        use_container_width=True,
    )
    event_csv = result.event_frame.to_csv(index=False).encode("utf-8-sig")
    export_columns[1].download_button(
        "下载事件日志CSV",
        event_csv,
        f"{result.symbol}-events.csv",
        "text/csv",
        use_container_width=True,
    )
    st.warning(DISCLAIMER)


def _render_factors(factors: list) -> None:
    if not factors:
        st.write("（无）")
        return
    for factor in factors:
        proxy_tag = "　🔬研究代理" if factor.provenance is Provenance.RESEARCH_PROXY else ""
        with st.container(border=True):
            st.markdown(f"**[{factor.dimension}] {factor.label_cn}**{proxy_tag}")
            st.caption(factor.detail_cn)
            st.caption(
                f"`{factor.rule_id}@{factor.rule_version}` · 来源 {factor.provenance.value}"
            )


def _render_event_list(events: list) -> None:
    if not events:
        st.write("（无）")
        return
    for event in reversed(events):
        proxy = "🔬" if event.provenance is Provenance.RESEARCH_PROXY else ""
        st.caption(
            f"{proxy}**{event.available_date}** {event.rule_id}\n\n{event.reason_cn}"
        )


# ---------------- 时间轴页 ----------------


def _render_timeline(result: AnalysisResult) -> None:
    st.subheader("技术事件时间轴")
    st.caption(
        "event_date 是形态实际发生日，available_date 是系统最早能确认它的日期。"
        "历史研究统计一律使用 available_date。"
    )

    frame = result.event_frame
    if frame.empty:
        st.write("没有事件。")
        return

    rules = sorted(frame["rule_id"].unique())
    selected = st.multiselect("按规则筛选", rules, default=rules)
    severities = st.multiselect(
        "按严重度筛选",
        ["info", "watch", "important", "critical"],
        default=["watch", "important", "critical"],
    )
    filtered = frame[frame["rule_id"].isin(selected) & frame["severity"].isin(severities)]

    st.write(f"共 {len(filtered)} 条事件（全部 {len(frame)} 条）")
    display = filtered.sort_values("available_date", ascending=False).head(400)
    st.dataframe(
        display[
            [
                "available_date", "event_date", "rule_id", "rule_version",
                "direction", "severity", "strength", "reason_cn", "provenance",
                "structure_id", "event_id",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### 事件明细（点击展开可见输入数值与失效条件）")
    for _, row in display.head(30).iterrows():
        with st.expander(
            f"{row['available_date']} · {row['rule_id']} · {row['reason_cn'][:48]}"
        ):
            st.write(f"**规则**：`{row['rule_id']}@{row['rule_version']}`")
            st.write(f"**来源**：{row['provenance']}")
            st.write(
                f"**形态发生日**：{row['event_date']}　"
                f"**最早可用日**：{row['available_date']}"
            )
            st.write(
                f"**方向/严重度/强度**：{row['direction']} / "
                f"{row['severity']} / {row['strength']}"
            )
            st.write("**成立所用数值**：")
            st.json(row["evidence"])
            st.write("**客观失效条件**：")
            st.json(row["invalidation"])
            st.caption(f"事件ID（确定性）：`{row['event_id']}`")


# ---------------- 结构诊断页 ----------------


def _render_diagnostics(result: AnalysisResult) -> None:
    st.subheader("结构诊断")
    st.caption(
        "本页专门解释：为什么系统给出当前阶段，以及哪些条件成立、哪些不成立。"
        "长周期不支持只是冲突标签，不会 Block 原子信号。"
    )

    state = result.history[-1]
    a = result.assessment

    checklist = [
        ("底部结构线索", bool(state.live_bottoms),
         f"{len(state.live_bottoms)} 个有效结构" if state.live_bottoms else "无有效结构"),
        ("底部结构已确认", any(
            s.confirmed_date is not None for s in state.live_bottoms
        ), "存在已确认结构" if any(
            s.confirmed_date is not None for s in state.live_bottoms
        ) else "仅候选或无"),
        (
            "EMA20 早期转强",
            state.early_strength_active,
            f"最近一次 {state.early_strength_date}"
            if state.early_strength_date
            else "未出现或已被否定",
        ),
        (
            "双均线共同确认（当前状态）",
            state.joint_confirmed_now,
            "收盘同时高于EMA20与MA20且两线向上"
            if state.joint_confirmed_now
            else "当前不成立",
        ),
        ("日线长周期", state.daily_long.value not in ("long_bear", "unknown"),
         LONG_TREND_CN[state.daily_long.value]),
        ("周线长周期", state.weekly_long.value not in ("long_bear", "unknown"),
         LONG_TREND_CN[state.weekly_long.value]),
        (
            "有效顶部警报",
            state.active_top is None,
            "无顶部警报"
            if state.active_top is None
            else f"存在（颈线{state.active_top.neckline:.4f}）",
        ),
        ("颜色非黑", a.color.value != "black", COLOR_CN[a.color.value]),
    ]

    st.dataframe(
        pd.DataFrame(
            [
                {"检查项": name, "状态": "✅ 成立" if ok else "⚠️ 不成立", "说明": detail}
                for name, ok, detail in checklist
            ]
        ),
        use_container_width=True,
        hide_index=True,
    )

    st.success(
        f"**结论**：{STAGE_CN[a.stage.value]}。"
        f"{a.stage_change_reason_cn}"
    )
    st.caption(
        "注意：某一项「不成立」不会导致系统输出「无信号」。"
        "只要存在有效底部线索，阶段至少为底部观察。"
    )

    st.markdown("#### 全部结构（含已失效，不删除历史）")
    if result.structures:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "结构ID": s.structure_id[-12:],
                        "方向": "底部" if s.side == "bottom" else "顶部",
                        "类型": s.structure_type,
                        "C": s.c_price,
                        "颈线": s.neckline,
                        "第一高点": s.reference_high,
                        "候选日": s.detected_date,
                        "确认日": s.confirmed_date,
                        "状态": s.status.value,
                        "失效日": s.invalidated_date,
                        "失效原因": s.invalidated_reason,
                        "来源": s.provenance.value,
                    }
                    for s in result.structures
                ]
            ),
            use_container_width=True,
            hide_index=True,
        )
        st.caption(
            "触及C的结构永久失效，后续上涨不会使它复活；"
            "顶部被新高解除后不再参与 Top+Black。"
        )

    if result.history:
        st.markdown("#### 阶段演进")
        history_frame = pd.DataFrame(
            [
                {
                    "date": pd.Timestamp(s.day),
                    "stage_rank": STAGE_RANK.get(s.stage.value, 0),
                    "stage_cn": STAGE_CN[s.stage.value],
                }
                for s in result.history
            ]
        ).set_index("date")
        st.plotly_chart(
            build_stage_history_figure(history_frame.tail(400)), use_container_width=True
        )


# ---------------- 历史信号研究页 ----------------


def _render_research(result: AnalysisResult) -> None:
    from lei_signal.research.outcomes import (
        build_forward_outcomes,
        gray_transition_stats,
        summarize_by_rule,
        top_transition_stats,
    )
    from lei_signal.research.stability import (
        baseline_comparison,
        block_bootstrap_ci,
        drop_top_k_analysis,
        split_by_group,
    )

    st.subheader("历史信号研究")
    st.caption(
        "研究「信号出现后发生了什么」，不模拟真实仓位、不计算资金曲线。"
        "统计一律按 available_date 对齐，连续同色只算一次开始事件。"
    )

    outcomes = build_forward_outcomes(result)
    if outcomes.empty:
        st.write("样本不足，无法统计。")
        return

    horizon = st.selectbox("选择观察期（交易日）", [1, 5, 10, 20, 60, 120], index=3)
    return_column = f"fwd_return_{horizon}"

    st.markdown("#### 各原子信号与组合阶段的后续表现")
    summary = summarize_by_rule(outcomes, horizon=horizon)
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.caption(
        "同时展示原子信号与组合阶段，不只展示表现最好的组合。"
        "样本数少于 20 的结果只能作为参考。"
    )

    signals = sorted(outcomes["signal_key"].unique())
    chosen = st.selectbox("选择一个信号或阶段做深入研究", signals)
    subset = outcomes[outcomes["signal_key"] == chosen]

    metric_columns = st.columns(5)
    metric_columns[0].metric("样本数", len(subset))
    valid = subset[return_column].dropna()
    if not valid.empty:
        metric_columns[1].metric("均值", f"{valid.mean():.2f}%")
        metric_columns[2].metric("中位数", f"{valid.median():.2f}%")
        metric_columns[3].metric("胜率", f"{(valid > 0).mean():.1%}")
        low, high = block_bootstrap_ci(subset, column=return_column)
        if low is not None:
            metric_columns[4].metric("95%区间", f"{low:.2f}% ~ {high:.2f}%")

    st.markdown("#### MFE / MAE 与 ATR 目标达成")
    path_columns = [
        f"mfe_{horizon}", f"mae_{horizon}",
        "days_to_plus_1atr", "days_to_plus_2atr", "days_to_minus_1atr",
    ]
    available_path = [c for c in path_columns if c in subset.columns]
    if available_path:
        st.dataframe(
            subset[available_path].describe().T,
            use_container_width=True,
        )
    reach_columns = st.columns(3)
    for column, label in (
        ("reached_plus_1atr", "达到+1ATR比例"),
        ("reached_plus_2atr", "达到+2ATR比例"),
        ("reached_minus_1atr", "达到-1ATR比例"),
    ):
        if column in subset.columns:
            reach_columns_index = [
                "reached_plus_1atr", "reached_plus_2atr", "reached_minus_1atr"
            ].index(column)
            reach_columns[reach_columns_index].metric(
                label, f"{subset[column].mean():.1%}"
            )

    st.markdown("#### C 失效与 B1 路径")
    c_b1_columns = st.columns(4)
    if "touched_c" in subset.columns:
        c_b1_columns[0].metric("触及C比例", f"{subset['touched_c'].mean():.1%}")
        median_days = subset.loc[subset["touched_c"], "days_to_touch_c"].median()
        c_b1_columns[1].metric(
            "触及C中位天数", "-" if pd.isna(median_days) else f"{median_days:.0f}"
        )
    if "reached_b1" in subset.columns:
        c_b1_columns[2].metric("到达B1比例", f"{subset['reached_b1'].mean():.1%}")
        c_b1_columns[3].metric("突破B1比例", f"{subset['broke_b1'].mean():.1%}")

    st.markdown("#### 匹配基准比较（信号是否带来增量信息）")
    baseline = baseline_comparison(outcomes, result.frame, chosen, horizon=horizon)
    st.dataframe(baseline, use_container_width=True, hide_index=True)
    st.caption(
        "与同标的、相似市场阶段的普通日期比较。"
        "若信号均值与基准接近，说明它可能只是搭上了标的的自然漂移。"
    )

    st.markdown("#### 大赢家依赖检查（删除最大 1/3/5 个事件）")
    st.dataframe(
        drop_top_k_analysis(subset, column=return_column),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### 分组稳定性（按年份 / 市场状态）")
    for group in ("year", "market_state"):
        if group in subset.columns:
            st.write(f"**按 {group} 拆分**")
            st.dataframe(
                split_by_group(subset, group=group, column=return_column),
                use_container_width=True,
                hide_index=True,
            )

    st.markdown("#### 转灰与顶部后续概率")
    gray_columns, top_columns = st.columns(2)
    with gray_columns:
        st.write("**转灰之后**")
        st.dataframe(gray_transition_stats(result.frame), use_container_width=True,
                     hide_index=True)
    with top_columns:
        st.write("**顶部警报之后**")
        st.dataframe(top_transition_stats(result), use_container_width=True, hide_index=True)

    st.download_button(
        "下载研究明细CSV",
        outcomes.to_csv(index=False).encode("utf-8-sig"),
        f"{result.symbol}-research.csv",
        "text/csv",
    )
    st.warning(
        "统计限制：样本来自单一标的的历史，存在数据源、复权口径与生存偏差；"
        "本页不构成任何买卖建议。"
    )


def _render_rule_reference() -> None:
    from lei_signal.domain.rules_config import load_ruleset

    with st.expander("规则账本（全部阈值、版本与来源）"):
        ruleset = load_ruleset()
        st.caption(
            f"规则账本版本 {ruleset['ruleset_version']} · "
            f"参考视频 {ruleset['source_video']}"
        )
        rows = [
            {
                "rule_id": rule_id,
                "version": spec.get("version"),
                "provenance": spec.get("provenance"),
                "是否研究代理": spec.get("provenance") == "research_proxy",
                "说明": spec.get("note_cn", "")[:60],
            }
            for rule_id, spec in ruleset["rules"].items()
        ]
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption(
            "provenance=research_proxy 表示视频未明确定义、由本项目为量化而建立的代理规则，"
            "不冒充 LEI 原始公式。"
        )


if __name__ == "__main__":
    render()
