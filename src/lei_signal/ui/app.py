"""LEI 技术信号研究系统 —— Streamlit 界面。

四个页面：当前观察、技术事件时间轴、结构诊断、历史信号研究。

界面只调用 compose.pipeline 与 research 模块，不重复实现任何业务规则。
所有提示都显示规则 ID、版本与来源，research_proxy 明确标注。
"""
from __future__ import annotations

import os
from contextlib import suppress

import pandas as pd
import streamlit as st

from lei_signal.compose.pipeline import AnalysisResult, analyze
from lei_signal.data.cache import DEFAULT_CACHE_DIR
from lei_signal.data.calendar import DEFAULT_TRADING_CALENDAR
from lei_signal.data.validation import DataUnavailableError
from lei_signal.domain.types import (
    COLOR_CN,
    LONG_TREND_CN,
    STAGE_CN,
    STAGE_RANK,
    Provenance,
    StructureInstance,
)
from lei_signal.state.machine import DayState
from lei_signal.ui.charts import (
    build_price_figure,
    build_stage_history_figure,
    build_volume_profile_figure,
)
from lei_signal.market_context.mapping import map_reference_markets

DISCLAIMER = (
    "本系统是技术信号识别、解释与历史有效性研究工具，**不是自动交易系统**。"
    "不下单、不计算仓位、不管理资金，也不输出确定性买卖建议。"
    "颜色、阶段与风险提示都只是观察信息。"
)


# 修复 7：把行情缓存与 SQLite 持久化接入普通 UI 分析路径。
# 默认沿用 ParquetCache 的默认目录（~/.lei_signal_lab/cache）与同目录下的 lab.db；
# 可用环境变量覆盖（容器/多用户部署时指向专用路径）。analyze 内部对写缓存与
# 写库的错误做了精确抑制（OSError/ImportError/ValueError/sqlite3.Error），
# 因此即使磁盘不可写也不会阻断分析结果返回，只会失去持久化。
_CACHE_ROOT = os.environ.get("LEI_CACHE_ROOT", str(DEFAULT_CACHE_DIR))
_SQLITE_PATH = os.environ.get(
    "LEI_SQLITE_PATH", str(DEFAULT_CACHE_DIR.parent / "lab.db")
)

# Round 3 修复 D5：界面两条分析路径（普通行情 / CSV-Parquet 上传）必须使用
# **同一个**交易日历常量，否则同一份数据在两个入口会得到不同的周线完成时点。
# 默认仍是保守的 WeekdayCalendar()（周一至周五、无节假日表）：内置一份手写
# 节假日表一旦写错，会把「本周最后交易日」判早，让周线在真正收盘前就被判完成
# ——那是错误结论，比「晚一天」严重得多。界面会明示当前口径。
_TRADING_CALENDAR = DEFAULT_TRADING_CALENDAR
_CALENDAR_NOTE = (
    "周线完成口径：默认交易日历只认周一至周五，**不含节假日表**。"
    "逢 A 股节假日短周，周线完成判定会晚于实际最后交易日收盘（保守方向，"
    "不会提前完成）。接入真实交易所休市日历后可消除该延迟。"
)


_RISK_STATE_CN = {
    "normal": "正常",
    "gray_watch": "转灰观察",
    "active_top": "有效顶部",
    "black": "黑色",
    "top_plus_black": "Top+Black",
    "c_invalidated": "C 失效",
}

#: 风险状态排序权重，用于阶段历史图的风险线（与机会阶段同量级、独立 y 轴）。
_RISK_RANK = {
    "normal": 0,
    "gray_watch": 1,
    "active_top": 2,
    "black": 3,
    "top_plus_black": 4,
    "c_invalidated": 5,
}


def _risk_state_label(value: str) -> str:
    return _RISK_STATE_CN.get(value, value)


def _load(symbol: str, build_history: bool) -> AnalysisResult:
    import os
    fixture_path = os.environ.get("LEI_FIXTURE_PATH")
    if fixture_path:
        import pandas as pd

        from lei_signal.compose.pipeline import analyze_bars
        from lei_signal.data.providers import PriceData
        from lei_signal.data.validation import ValidationReport
        bars = pd.read_parquet(fixture_path)
        report = ValidationReport(
            rows=len(bars), first_date=bars.index[0], last_date=bars.index[-1],
            adjusted=True, provider="fixture", duplicates_removed=0, warnings=(),
        )
        from lei_signal.data.symbols import resolve_symbol
        info = resolve_symbol(symbol)
        price = PriceData(
            symbol=info.symbol,
            display_name=os.environ.get("LEI_FIXTURE_NAME", info.symbol),
            bars=bars, report=report, info=info,
        )
        return analyze_bars(symbol, bars, display_name=price.display_name,
                            price_data=price, build_history=build_history,
                            calendar=_TRADING_CALENDAR)
    # 普通 UI 路径：行情成功获取后写入 Parquet 缓存，并把事件/结构/评估
    # 持久化到 SQLite（analyze 内部幂等写入、错误精确抑制）。
    return analyze(
        symbol,
        build_history=build_history,
        cache_root=_CACHE_ROOT,
        sqlite_path=_SQLITE_PATH,
        run_id=f"ui-{symbol}",
        calendar=_TRADING_CALENDAR,
    )


@st.cache_data(show_spinner=False, ttl=900)
def _cached_analysis(symbol: str, build_history: bool) -> AnalysisResult:
    return _load(symbol, build_history)


def _analyze_upload(upload_file, symbol: str, build_history: bool) -> AnalysisResult:
    """从用户上传的 CSV/Parquet 加载行情（修复 9），并接入缓存与 SQLite 持久化。"""
    from lei_signal.compose.pipeline import analyze
    from lei_signal.data.providers import PriceData
    from lei_signal.data.symbols import resolve_symbol
    from lei_signal.data.validation import ValidationReport

    # 上传文件可能没有 seek/tell 全部支持；pandas 会用 read(n) 多次调用，
    # 因此把数据全部读入内存后再交给 pandas。
    if hasattr(upload_file, "seek"):
        # 不可 seek 的流抛 io.UnsupportedOperation（OSError 子类）；
        # 只吞这一类，其余异常照抛，避免把真实的读取错误掩盖成空文件。
        with suppress(OSError):
            upload_file.seek(0)
    raw_bytes = upload_file.read()
    from io import BytesIO
    if upload_file.name.endswith(".parquet"):
        bars = pd.read_parquet(BytesIO(raw_bytes))
    else:
        # 解析 CSV：date 可能是列名，也可能是 index；用 first column
        sample = pd.read_csv(BytesIO(raw_bytes), nrows=2)
        buf = BytesIO(raw_bytes)
        if "date" in sample.columns:
            bars = pd.read_csv(buf, parse_dates=["date"], index_col="date")
        else:
            bars = pd.read_csv(buf, index_col=0, parse_dates=True)
    bars.index = pd.to_datetime(bars.index).tz_localize(None).normalize()
    bars = bars.sort_index()
    bars = bars[["open", "high", "low", "close", "volume"]]
    info = resolve_symbol(symbol)
    report = ValidationReport(
        rows=len(bars), first_date=bars.index[0], last_date=bars.index[-1],
        adjusted=True, provider="local_upload", duplicates_removed=0,
        warnings=("local_upload", f"上传文件 {upload_file.name}"),
    )
    price = PriceData(
        symbol=info.symbol, display_name=info.symbol,
        bars=bars, report=report, info=info,
    )
    # 用包装 provider 让 analyze 走统一持久化路径（缓存 + SQLite），
    # 而不是 analyze_bars（无持久化）。上传数据同样写入缓存与研究库。
    class _UploadProvider:
        name = "upload"

        def fetch(self, _symbol: str, *, min_rows: int = 21) -> PriceData:
            return price

    return analyze(
        info.symbol,
        provider=_UploadProvider(),
        build_history=build_history,
        cache_root=_CACHE_ROOT,
        sqlite_path=_SQLITE_PATH,
        run_id=f"upload-{info.symbol}",
        calendar=_TRADING_CALENDAR,
    )


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
        # 修复 9：允许上传本地 CSV/Parquet 作为可复现实盘数据导入
        with st.expander("导入本地行情（CSV / Parquet）", expanded=False):
            st.caption(
                "数据获取失败时可上传本地保存的日线；"
                "文件必须含 date/open/high/low/close/volume 列。"
                "CSV 需含日期与 OHLCV 列表头。"
            )
            upload = st.file_uploader(
                "选择本地文件",
                type=["csv", "parquet"],
                key="local_upload",
            )
            use_upload = st.checkbox("使用上传文件代替远程拉取", value=False)
        run = st.button("分析", type="primary", use_container_width=True)
        st.divider()
        st.caption(DISCLAIMER)
        st.caption(
            f"本地持久化已接入：缓存 `{_CACHE_ROOT}` · 数据库 `{_SQLITE_PATH}`"
        )
        st.caption(_CALENDAR_NOTE)

    if not run and "analysis" not in st.session_state:
        st.info("在左侧输入代码后点击「分析」。首次加载会自动下载复权日线行情。")
        _render_rule_reference()
        return

    if run:
        if "use_upload" in dir() and use_upload and upload is not None:
            st.session_state["analysis"] = _analyze_upload(
                upload, symbol, build_history
            )
        else:
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

    tab_current, tab_timeline, tab_diagnostics, tab_research, tab_market = st.tabs(
        ["当前观察", "技术事件时间轴", "结构诊断", "历史信号研究", "市场环境"]
    )
    with tab_current:
        _render_current(result)
    with tab_timeline:
        _render_timeline(result)
    with tab_diagnostics:
        _render_diagnostics(result)
    with tab_research:
        _render_research(result)
    with tab_market:
        _render_market_context_tab(result)


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
    if getattr(result, "cache_fallback_used", False):
        age_hours = (result.cache_age_seconds or 0) / 3600.0
        st.warning(
            f"网络行情获取失败，**正在使用本地 Parquet 缓存**（{age_hours:.1f} 小时前）。"
            f"陈旧数据可能产生过时信号；请尽快恢复网络后重新拉取。"
        )
    # 研究库持久化状态必须可见：失败要明确提示，不能静默让用户以为已写入。
    sqlite_persisted = getattr(result, "sqlite_persisted", None)
    if sqlite_persisted is True:
        st.success("事件 / 结构 / 评估已成功持久化到本地 SQLite 研究库。")
    elif sqlite_persisted is False:
        st.error(
            "SQLite 研究库写入**失败**（磁盘不可写或库被锁）；本次分析未持久化。"
            "界面与缓存结果不受影响，请检查数据库路径权限后重试。"
        )

    columns = st.columns(5)
    columns[0].metric("机会阶段", STAGE_CN[a.opportunity_stage.value])
    columns[1].metric("风险状态", _risk_state_label(a.risk_state.value))
    columns[2].metric("最新颜色", COLOR_CN[a.color.value])
    columns[3].metric("最新收盘", f"{float(latest['close']):.4f}")
    columns[4].metric("数据日期", a.as_of.strftime("%Y-%m-%d"))

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


# Round 3 修复 D6：档位中文化（保持与既有研究层 STAGE_CN 一致的口径）。
_TIER_CN = {
    "early_watch": "候选观察档",
    "structure_confirmed": "结构确认档",
    "joint_confirmed": "共同确认档",
    "long_trend_improved": "长周期改善档",
}
# 档位说明
_TIER_DESC_CN = {
    "early_watch": "已出现 EMA20 早期转强，但底部结构尚未确认。**仅作观察，不构成买入信号。**",
    "structure_confirmed": "同一底部结构已确认，**具备买入参考意义**。",
    "joint_confirmed": "双均线当前共同向上，沿用同一观察实例的升级。",
    "long_trend_improved": "日线或周线长周期支持/改善，已升级至最高档。",
}
# 失效原因（按优先级）
_TIER_INVALID_REASON = {
    "black": "颜色转黑关闭转强生命周期（结构本身仍存活）",
    "c_invalidated": "触及 C 永久失效，结构已死亡",
    "structure_c_invalidation": "结构触及 C 永久失效",
}
# 档位下一步等待条件
_TIER_NEXT_STEP = {
    "early_watch": "等待同一结构被确认 → 升级为「结构确认档」",
    "structure_confirmed": "等待双均线共同向上 → 升级为「共同确认档」",
    "joint_confirmed": "等待长周期支持/改善 → 升级为「长周期改善档」",
    "long_trend_improved": "已是最高档；继续观察：触及 C → 永久失效；转黑 → 关闭本条转强",
}


def _collect_structure_observations(
    state: DayState,
    structures: list[StructureInstance],
) -> list[dict[str, object]]:
    """把 ``DayState.observations`` 展成 UI 行。

    同时纳入没有观察档的「纯候选 / 纯已确认」结构，避免多结构并存时
    只展示主结构而隐藏其他有效观察链（任务书第八节硬要求）。
    """
    structure_by_id = {s.structure_id: s for s in structures}
    rows: list[dict[str, object]] = []

    # 1) 有观察档的结构（先按 tier rank 降序）
    active_rows: list[dict[str, object]] = []
    for sid, obs in state.observations.items():
        structure = structure_by_id.get(sid)
        if structure is None:
            continue
        tier = obs.tier
        if tier is None:
            # 关闭中的观察实例：显示「已关闭」+ 关闭原因
            active_rows.append({
                "结构ID": sid[-12:],
                "结构状态": structure.status.value,
                "档位": "已关闭",
                "生命周期ID": obs.lifecycle_id,
                "开启日": str(obs.opened_on),
                "最近升级日": str(obs.last_upgraded_on),
                "当前是否有效": False,
                "失效原因": _describe_inactive_reason(state, structure, obs),
                "下一步等待条件": "（无；等待价格脱离转黑或该结构复活）",
            })
            continue
        tier_cn = _TIER_CN.get(tier, tier)
        if state.color.value == "black":
            invalid_reason = _describe_inactive_reason(state, structure, obs)
        else:
            invalid_reason = ""
        active_rows.append({
            "结构ID": sid[-12:],
            "结构状态": structure.status.value,
            "档位": tier_cn,
            "档位说明": _TIER_DESC_CN.get(tier, ""),
            "生命周期ID": obs.lifecycle_id,
            "开启日": str(obs.opened_on),
            "最近升级日": str(obs.last_upgraded_on),
            "当前是否有效": True,
            "失效原因": invalid_reason or "—",
            "下一步等待条件": _TIER_NEXT_STEP.get(tier, ""),
        })

    # 2) 没有观察档但仍 live 的结构（候选 / 纯已确认无转强）
    observed = set(state.observations.keys())
    for structure in state.live_bottoms:
        if structure.structure_id in observed:
            continue
        rows.append({
            "结构ID": structure.structure_id[-12:],
            "结构状态": structure.status.value,
            "档位": "无观察档",
            "档位说明": (
                "结构已确认但暂无 EMA20 早期转强事件。"
                if structure.confirmed_date is not None
                else "底部结构候选中，尚未出现 EMA20 早期转强。"
            ),
            "生命周期ID": "—",
            "开启日": "—",
            "最近升级日": "—",
            "当前是否有效": True,
            "失效原因": "—",
            "下一步等待条件": (
                "等待 EMA20 重新站上且向上 → 开启观察实例"
                if structure.confirmed_date is None
                else "等待 EMA20 重新站上且向上 → 升级到「结构确认档」"
            ),
        })

    # 排序：有观察档的按档位 rank 降序；其余保持原顺序
    tier_rank = {tier: idx for idx, tier in enumerate(
        ["long_trend_improved", "joint_confirmed", "structure_confirmed", "early_watch"]
    )}

    def _sort_key(row: dict[str, object]) -> tuple[int, str]:
        tier_cn = str(row.get("档位", ""))
        rank = min(
            (rank for t, rank in tier_rank.items() if _TIER_CN.get(t) == tier_cn),
            default=99,
        )
        return (rank, str(row.get("结构ID", "")))

    return sorted(active_rows, key=_sort_key) + rows


def _describe_inactive_reason(
    state: DayState,
    structure: StructureInstance,
    obs: object,
) -> str:
    """描述观察实例被关闭的原因（结构失效 / 转黑）。"""
    if state.color.value == "black":
        return _TIER_INVALID_REASON["black"]
    if structure.invalidated_date is not None:
        return _TIER_INVALID_REASON["c_invalidated"]
    return "观察实例已关闭（无活跃档位）"


def _render_per_structure_observations(
    state: DayState,
    structures: list[StructureInstance],
) -> None:
    """按结构展示观察链（Round 3 修复 D6）。

    任务书硬要求：
      * 按结构展示当前状态，不得只展示全局布尔值；
      * 至少显示：结构ID、当前档位、生命周期开启日、最近升级日、
        当前是否有效、失效原因、下一步等待条件；
      * 只有 candidate 阶段的结构才能显示「尚未确认」文案；
      * 已确认结构不得继续出现在 early_watch 块；
      * ``early_watch`` 使用中性信息样式，不得用绿色成功样式；
      * 共同确认和趋势增强必须说明绑定的是哪一个结构；
      * 多结构并存时不得只显示主结构而隐藏其他有效观察链。
    """
    rows = _collect_structure_observations(state, structures)
    if not rows:
        st.info("当前没有有效底部结构，也没有任何观察档。")
        return

    st.markdown("#### 逐结构观察链（Round 3 修复 D6）")
    df = pd.DataFrame(rows)
    st.dataframe(df, use_container_width=True, hide_index=True)

    # 关键文案：每行都要可被 grep 验证
    # 1) early_watch 不得用 success；改用 info
    # 2) 已确认结构不会同时出现在 early_watch
    early_watch_rows = [r for r in rows if r.get("档位") == "候选观察档"]
    if early_watch_rows:
        ids = "、".join(f"`{r['结构ID']}`" for r in early_watch_rows)
        # 用 info 不用 success：候选观察档不构成买入信号
        st.info(
            f"**候选结构·观察档（{len(early_watch_rows)} 个）**：{ids}。"
            "这些底部结构**尚未确认**，早期转强仅作观察记录，"
            "**不计入结构确认，也不构成买入信号**，不会抬升上方的机会阶段。"
        )

    # 3) 已确认结构必须出现在「结构确认档」或更高，且不能混进 early_watch
    # 已在 _collect_structure_observations 的 tier 映射里显式排除 candidate 阶段
    # 的早期转强

    # 4) 共同确认和趋势增强必须说明绑定的是哪一个结构
    higher_rows = [r for r in rows if r.get("档位") in ("共同确认档", "长周期改善档")]
    if higher_rows:
        ids = "、".join(
            f"{r['档位']}→`{r['结构ID']}`" for r in higher_rows
        )
        st.caption(
            f"**高档观察档绑定结构**：{ids}。"
            "这些档位已沿用同一结构同一观察实例升级，"
            "而非由全局双均线或长周期条件单独触发。"
        )


def _render_early_watch(state: DayState) -> None:
    """保留旧入口：仅展示候选结构上的 EMA20 观察档（用 info 不用 success）。

    观察档刻意不进入上面的「✅成立 / ⚠️不成立」核对表：那张表读起来像
    「条件达成」，而观察档的口径是「看到了，但不算数」——它既不等于结构
    确认，也不构成买入。放在这里单独说明，是为了让它可见而不被误读。
    """
    watching = sorted(
        sid for sid, active in state.early_watch_by_structure.items() if active
    )
    if not watching:
        return
    st.info(
        f"**候选结构·观察档（early_watch）**：{len(watching)} 个 —— "
        + "、".join(f"`{sid}`" for sid in watching)
        + "\n\n这些底部结构**尚未确认**，但已出现 EMA20 早期转强。"
        "该档仅作观察记录，**不计入结构确认，也不构成买入信号**，"
        "因此不会抬升上方的机会阶段。"
        "只有等结构确认后，同一结构才会沿 结构确认 → 共同确认 → 长周期改善 "
        "逐级升级为可交易档位；若价格触及 C 点低点，该结构永久失效。"
    )


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
            "EMA20 早期转强（已确认结构）",
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

    # Round 3 修复 D6：先按结构展示观察链（不得只展示全局布尔值），
    # 再保留旧的 early_watch 中性提示块作为补充说明。
    _render_per_structure_observations(state, result.structures)
    _render_early_watch(state)

    st.success(
        f"**机会阶段**：{STAGE_CN[a.opportunity_stage.value]}；"
        f"**风险状态**：{_risk_state_label(a.risk_state.value)}。"
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
        st.markdown("#### 阶段演进（蓝=机会阶段，红=风险状态，两线独立）")
        history_frame = pd.DataFrame(
            [
                {
                    "date": pd.Timestamp(s.day),
                    # 机会阶段线：使用独立的 opportunity_stage，不再用兼容 stage 字段，
                    # 避免风险状态覆盖机会阶段显示。
                    "stage_rank": STAGE_RANK.get(s.opportunity_stage.value, 0),
                    "stage_cn": STAGE_CN[s.opportunity_stage.value],
                    # 风险状态线（次 y 轴）
                    "risk_rank": _RISK_RANK.get(s.risk_state.value, 0),
                    "risk_cn": _risk_state_label(s.risk_state.value),
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
        build_risk_transitions,
        gray_transition_stats,
        summarize_by_rule,
        top_transition_stats,
    )
    from lei_signal.research.stability import (
        baseline_comparison,
        block_bootstrap_ci,
        cluster_by_structure,
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
    # 详情页统一使用「方向调整后」口径（看多=原始、看空=取反），与汇总表一致，
    # 避免看空信号下跌时命中率正确但均值负数的两套口径冲突。
    return_column = f"direction_adjusted_return_{horizon}"

    st.markdown("#### 各原子信号与组合阶段的后续表现")
    summary = summarize_by_rule(outcomes, horizon=horizon)
    st.dataframe(summary, use_container_width=True, hide_index=True)
    st.caption(
        "同时展示原子信号与组合阶段，不只展示表现最好的组合。"
        "「方向命中率」按信号方向调整：看空信号以下跌为命中。"
        "样本数少于 20 的结果只能作为参考。"
    )

    signals = sorted(outcomes["signal_key"].unique())
    chosen = st.selectbox("选择一个信号或阶段做深入研究", signals)
    subset = outcomes[outcomes["signal_key"] == chosen]

    metric_columns = st.columns(5)
    metric_columns[0].metric("样本数", len(subset))
    valid = subset[return_column].dropna()
    if not valid.empty:
        metric_columns[1].metric("方向调整均值", f"{valid.mean():.2f}%")
        metric_columns[2].metric("方向调整中位数", f"{valid.median():.2f}%")
        # 看空/风险信号：方向命中率 = 后续下跌比例（即对信号方向有利）。
        # 列名明确写「方向命中」，避免把 bearish 信号后下跌显示为 0% 胜率。
        hit_col = f"direction_hit_{horizon}"
        if hit_col in subset.columns:
            valid_hit = subset[hit_col].dropna().astype(bool)
            rate = float(valid_hit.mean()) if not valid_hit.empty else 0.0
            label = "方向命中"
        else:
            rate = float((valid > 0).mean())
            label = "后续上涨比例"
        metric_columns[3].metric(label, f"{rate:.1%}")
        low, high = block_bootstrap_ci(subset, column=return_column)
        if low is not None:
            metric_columns[4].metric("95%区间", f"{low:.2f}% ~ {high:.2f}%")

    st.markdown("#### MFE / MAE 与 ATR 目标达成（方向调整后口径）")
    path_columns = [
        f"mfe_adjusted_{horizon}", f"mae_adjusted_{horizon}",
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

    st.markdown("#### 同结构多次升级聚类")
    cluster = cluster_by_structure(outcomes)
    if not cluster.empty:
        st.dataframe(cluster, use_container_width=True, hide_index=True)
        st.caption(
            "同一底部结构在生命周期内可能产生多次阶段升级。聚类后避免把这些升级"
            "当作完全独立样本。"
        )
    else:
        st.caption("该信号未与任何结构关联，无聚类信息。")

    st.markdown("#### 大赢家依赖检查（删除最大 1/3/5 个事件）")
    st.dataframe(
        drop_top_k_analysis(subset, column=return_column),
        use_container_width=True,
        hide_index=True,
    )

    st.markdown("#### 分组稳定性（按年份 / 市场状态 / 资产类别）")
    for group in ("year", "market_state", "asset_class"):
        if group in subset.columns:
            st.write(f"**按 {group} 拆分**")
            st.dataframe(
                split_by_group(subset, group=group, column=return_column),
                use_container_width=True,
                hide_index=True,
            )

    st.markdown("#### 风险状态转换（与机会阶段分表，不污染收益研究）")
    risk_transitions = build_risk_transitions(result)
    if risk_transitions.empty:
        st.write("本次分析未出现风险状态转换。")
    else:
        st.dataframe(risk_transitions, use_container_width=True, hide_index=True)
        st.caption(
            "风险状态转换只记录事实（何时、从/到哪种风险状态），不进入收益统计；"
            "其同日机会阶段见 opportunity_stage 列，两条线独立。"
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


# ---------------- 市场环境页 (Round 4) ----------------

def _render_market_context_tab(result: AnalysisResult) -> None:
    """Render the independent market context dashboard.

    Displays reference-market mapping, breadth values, drawdown,
    sentiment status, and any data quality warnings. Does NOT modify
    or interact with Round 3 state machine outputs.
    """
    st.subheader("市场环境 · Round 4")
    st.caption(
        "市场环境层回答的是「当前市场是否为该技术机会提供顺风」，不是"
        "「这个标的的技术信号是否成立」。市场环境不改变技术信号阶段。"
    )

    # Show mapping
    mapping = map_reference_markets(result.symbol)
    st.markdown("#### 参考市场映射")
    if mapping.mapping_incomplete:
        st.warning(
            f"标的 `{result.symbol}` 的参考市场映射不完整（mapping_incomplete）。"
            f"\n原因：{mapping.reason_cn}"
        )
    else:
        st.info(
            f"主参考市场：**{mapping.primary_market_id.value if mapping.primary_market_id else '无'}**\n\n"
            f"次参考市场：{'、'.join(m.value for m in mapping.secondary_market_ids) if mapping.secondary_market_ids else '无'}\n\n"
            f"映射原因：{mapping.reason_cn}"
        )

    # Data environment status
    st.markdown("#### 数据环境")
    env_vars = ["LEI_UNIVERSE_ROOT", "LEI_COMPONENT_BARS_ROOT",
                "LEI_INDEX_BARS_ROOT", "LEI_SENTIMENT_ROOT"]
    env_status = {}
    for var in env_vars:
        val = os.environ.get(var)
        env_status[var] = val if val else "未设置"

    env_df = pd.DataFrame(
        [{"环境变量": k, "状态": v} for k, v in env_status.items()]
    )
    st.dataframe(env_df, use_container_width=True, hide_index=True)

    if any(v == "未设置" for v in env_status.values()):
        st.warning(
            "部分市场环境数据路径未设置。市场宽度、指数回撤与情绪数据不可用。"
            "请设置上述环境变量指向本地数据目录后刷新。"
        )
        st.info(
            "**市场环境不改变该技术信号阶段**。"
        )
        return

    # Breadth summary placeholder
    st.markdown("#### 市场宽度")
    st.info(
        "市场宽度需要真实的成分股和行情数据。当前为占位显示。\n\n"
        "设置环境变量后：\n"
        "- Breadth20 / Breadth50 / Breadth200 及覆盖率\n"
        "- LEI固定阈值事件（A股标记 research_proxy）\n"
        "- 长期底色、热度、扩散方向\n"
        "- 顺风/中性/逆风/未知 摘要"
    )

    # Drawdown placeholder
    st.markdown("#### 指数回撤")
    st.info("需要指数行情数据（LEI_INDEX_BARS_ROOT）")

    # Sentiment placeholder
    st.markdown("#### 情绪数据（NAAIM / AAII）")
    st.info("需要情绪数据文件（LEI_SENTIMENT_ROOT）。NAAIM/AAII按实际发布时间可见。")

    # Key disclaimer
    st.markdown("---")
    st.success(
        "**市场环境不改变该技术信号阶段。**\n\n"
        "标的技术状态与市场环境并列展示，不互相覆盖。\n"
        "市场环境为提示信息，不构成买入卖出建议。\n"
        "A股LEI固定阈值标记为 `lei_threshold_research`，未经A股样本外验证。"
    )


if __name__ == "__main__":
    render()
