import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import AddSymbolDialog from "../components/AddSymbolDialog";
import AssessmentPanel from "../components/AssessmentPanel";
import CollapsiblePanel, { type CollapsiblePanelHandle } from "../components/CollapsiblePanel";
import ChartControls from "../components/ChartControls";
import ColorBacktestPanel from "../components/ColorBacktestPanel";
import PullbackBacktestPanel from "../components/PullbackBacktestPanel";
import PullbackOpportunityPanel from "../components/PullbackOpportunityPanel";
import ConditionalScenarioPanel from "../components/ConditionalScenarioPanel";
import ExitSignalPanel from "../components/ExitSignalPanel";
import ScenarioBacktestPanel from "../components/ScenarioBacktestPanel";
import TradabilityPanel from "../components/TradabilityPanel";
import ColorBadge from "../components/ColorBadge";
import ExplanationPanel, { type Selection } from "../components/ExplanationPanel";
import CrossSectionComparePanel from "../components/CrossSectionComparePanel";
import HomeEnvironmentStrip from "../components/HomeEnvironmentStrip";
import SymbolQuickReadCard from "../components/SymbolQuickReadCard";
import SmartSymbolPromptCard from "../components/smart-prompts/SmartSymbolPromptCard";
import KlineChart, {
  DEFAULT_DISPLAY,
  effectiveDisplay,
  type ChartDisplay,
  type MarkPick,
  type RangePreset,
} from "../components/KlineChart";
import { scopeMarkCounts } from "../components/klineStructureMarks";
import { loadTimeframe } from "../components/klineTimeframe";
import ResizeHandle from "../components/ResizeHandle";
import TodayOverviewPanel from "../components/TodayOverviewPanel";
import TodaySignalBanner from "../components/TodaySignalBanner";
import CrisisBanner from "../components/CrisisBanner";
import TradeOpportunityPanel from "../components/TradeOpportunityPanel";
import { prefillFromOpportunity } from "../components/CreatePlanDialog";
import PlanCreateFlow from "../components/PlanCreateFlow";
import BuyPointDrawer, { annoToIndex } from "../components/BuyPointDrawer";
import WatchlistSidebar, { type SidebarSignalBadge } from "../components/WatchlistSidebar";
import { useBuyPointCoord } from "../hooks/useBuyPointCoord";
import type { Explanation, StructureBrief, SymbolDetail } from "../types";

const MARK_SOURCE_CN: Record<MarkPick["kind"], string> = {
  bottom_mark: "图上标记 · 底部结构确认",
  top_mark: "图上标记 · 顶部结构确认",
  invalidated_mark: "图上标记 · 结构失效",
  key_volatility: "图上标记 · 关键性波动",
  b1_line: "图上参考线 · B1 第一阻力",
  bottom_line: "图上参考线 · C 点失效线",
  top_line: "图上参考线 · 顶部颈线",
  highlight_price: "买点分析 · 价位标注",
  macd_event: "MACD 副图标记 · 强度事件",
  news_mark: "K线标记 · 消息日（参考层）",
};

const LINE_KINDS: ReadonlySet<MarkPick["kind"]> = new Set([
  "b1_line",
  "bottom_line",
  "top_line",
]);

function resolveSelection(pick: MarkPick, detail: SymbolDetail): Selection {
  const source = MARK_SOURCE_CN[pick.kind];
  const all: StructureBrief[] = [...detail.live_structures, ...detail.closed_structures];
  const structure =
    all.find((s) => s.structure_id === pick.structureId) ??
    all.find((s) => s.structure_type === pick.structureType) ??
    null;

  let explanation: Explanation | null = null;
  if (pick.kind === "key_volatility") {
    explanation = detail.concepts["key_volatility"] ?? null;
  } else if (pick.kind === "macd_event") {
    explanation = detail.concepts["macd_strength"] ?? null;
  } else if (LINE_KINDS.has(pick.kind)) {
    explanation = detail.concepts[detail.mark_concepts[pick.kind] ?? ""] ?? null;
  } else {
    explanation =
      structure?.explanation ??
      detail.concepts[detail.mark_concepts[pick.kind] ?? ""] ??
      null;
  }

  const macdEvent =
    pick.kind === "macd_event"
      ? detail.chart.macdEvents?.find((e) => e.date === pick.date)
      : undefined;
  return {
    source:
      pick.kind === "macd_event" && pick.macdStatusCn
        ? `MACD 副图标记 · ${pick.macdStatusCn}（研究代理）`
        : source,
    date: pick.date,
    price: pick.price ?? pick.level,
    explanation,
    structure,
    b1PivotDate: pick.pivotDate ?? undefined,
    b1DistancePct: pick.distancePct ?? undefined,
    macdEvent,
    events: undefined,
    eventsLoading: pick.kind !== "macd_event", // MACD 不产生事件，无需查询
  };
}

/**
 * 三栏看盘工作台：左自选分组 / 中 K线+今日概述 / 右解释。
 *
 * 关键设计：切换标的只改 URL 查询参数与中栏数据，**不跳转页面**。
 * 这样右栏解释、图表开关（标记显隐、着色模式、均线）都不会因为
 * 「退回首页再点进来」而重置——这是原双页结构最大的使用摩擦。
 */
export default function WorkspacePage() {
  const queryClient = useQueryClient();
  const [params, setParams] = useSearchParams();
  const [selection, setSelection] = useState<Selection | null>(null);
  const [viewMode, setViewMode] = useState<"chart" | "compare">(() =>
    params.get("view") === "compare" ? "compare" : "chart",
  );
  const [detailsDrawerOpen, setDetailsDrawerOpen] = useState(false);
  const [signalsOpen, setSignalsOpen] = useState(false);
  // 与 TodaySignalBanner 共享同一 queryKey，零额外请求；用于顶条胶囊计数 + 左侧自选卡片异动小徽标
  const signalsQuery = useQuery({
    queryKey: ["signalsToday"],
    queryFn: () => api.signalsToday(),
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
  const signalSummary = useMemo(() => {
    const s = signalsQuery.data;
    const isSector = (sym: string) => sym.toUpperCase().endsWith(".SECTOR");
    const buyA = s?.actionable ?? [];
    const buyW = s?.waiting ?? [];
    const sellH = (s?.sell_hard ?? []).filter((x) => !isSector(x.symbol));
    const sellWarn = (s?.sell_warn ?? []).filter((x) => !isSector(x.symbol));
    const badges = new Map<string, SidebarSignalBadge>();
    for (const it of sellWarn) {
      badges.set(it.symbol, { kind: "sell", label: "弱", title: `转弱预警：${it.reason_cn || it.title || it.kind_cn}` });
    }
    for (const it of sellH) {
      badges.set(it.symbol, { kind: "sell", label: "退", title: `退出提醒：${it.reason_cn || it.title || it.kind_cn}` });
    }
    for (const it of buyW) {
      if (!badges.has(it.symbol)) {
        badges.set(it.symbol, { kind: "watch", label: "待", title: `等待买点：${it.missing_summary_cn || it.best_scenario_cn || it.verdict_cn}` });
      }
    }
    for (const it of buyA) {
      badges.set(it.symbol, { kind: "buy", label: "买", title: `可行动买点：${it.best_scenario_cn || it.verdict_cn}` });
    }
    return {
      scanned: s?.as_of != null,
      buyA: buyA.length,
      buyW: buyW.length,
      sellCount: sellH.length + sellWarn.length,
      badges,
    };
  }, [signalsQuery.data]);
  // 周期默认日线，但沿用用户上次的选择（localStorage 持久化）。
  const [display, setDisplay] = useState<ChartDisplay>(() => ({
    ...DEFAULT_DISPLAY,
    timeframe: loadTimeframe(),
  }));
  const [rangePreset, setRangePreset] = useState<RangePreset | null>("6M");
  const [rangeRequest, setRangeRequest] = useState<{ preset: RangePreset; seq: number } | null>(null);
  const handleRangePreset = useCallback((preset: RangePreset) => {
    setRangePreset(preset);
    setRangeRequest((prev) => ({ preset, seq: (prev?.seq ?? 0) + 1 }));
  }, []);
  const handleRangeCustom = useCallback(() => setRangePreset(null), []);
  // 图例只描述「图上真的画了什么」：周/月线下日线专属项已隐藏，故读生效开关。
  const legend = effectiveDisplay(display);
  const anyMarkShown =
    legend.bottomMarks ||
    legend.topMarks ||
    legend.invalidatedMarks ||
    legend.keyVolatility ||
    legend.levels;
  const [addDialogGroup, setAddDialogGroup] = useState<number | null | undefined>(undefined);
  const [showCreatePlan, setShowCreatePlan] = useState(false);
  const [showBuyPoint, setShowBuyPoint] = useState(false);
  // 右侧解释面板是否收起。默认收起以给 K 线主图留出更大空间；
  // 点图上标记时自动展开以便看解释。买点分析打开时面板自动隐藏。
  const [expCollapsed, setExpCollapsed] = useState(true);
  const expVisible = !showBuyPoint && !expCollapsed && viewMode === "chart";
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const showSidebar = sidebarOpen && viewMode === "chart";
  // KlineChart 把「下载当前图为 PNG」的闭包回传到这里，按钮点的时候调它
  const downloadPngRef = useRef<(() => void) | null>(null);
  // 摘要条跳转：四个面板的命令式句柄（点击摘要段 → 展开并滚到对应面板）
  const eventsPanelRef = useRef<CollapsiblePanelHandle>(null);
  const tradePanelRef = useRef<CollapsiblePanelHandle>(null);
  const exitPanelRef = useRef<CollapsiblePanelHandle>(null);
  const tradabilityPanelRef = useRef<CollapsiblePanelHandle>(null);
  // 左栏宽度。读取 localStorage 让用户拖完一次后下次打开保持。
  const [sidebarWidth, setSidebarWidth] = useState<number>(() => {
    if (typeof window === "undefined") return 268;
    const raw = window.localStorage.getItem("ws.sidebarWidth");
    const n = raw ? Number(raw) : NaN;
    return Number.isFinite(n) ? Math.max(200, Math.min(480, n)) : 268;
  });
  useEffect(() => {
    window.localStorage.setItem("ws.sidebarWidth", String(sidebarWidth));
  }, [sidebarWidth]);

  const { data: dashboard, isLoading: cardsLoading, isError: cardsError, error: cardsLoadError, refetch: refetchCards, isFetching: cardsFetching } = useQuery({
    queryKey: ["cards"],
    queryFn: () => api.dashboard(),
  });

  const cards = dashboard?.cards ?? [];
  const urlSymbol = params.get("symbol") ?? "";
  const urlView = params.get("view");
  // 未指定标的时默认选第一张可用卡片（通常是上证指数）
  const selected = urlSymbol || cards.find((c) => !c.error)?.symbol || "";

  useEffect(() => {
    if (urlView === "compare" && viewMode !== "compare") setViewMode("compare");
  }, [urlView, viewMode]);

  const switchViewMode = useCallback(
    (next: "chart" | "compare") => {
      setViewMode(next);
      const nextParams: Record<string, string> = {};
      if (selected) nextParams.symbol = selected;
      if (next === "compare") nextParams.view = "compare";
      setParams(nextParams, { replace: true });
    },
    [selected, setParams],
  );

  useEffect(() => {
    if (!urlSymbol && selected && !cardsError) {
      const nextParams: Record<string, string> = { symbol: selected };
      if (params.get("view") === "compare") nextParams.view = "compare";
      setParams(nextParams, { replace: true });
    }
  }, [urlSymbol, selected, cardsError, params, setParams]);

  const selectSymbol = useCallback(
    (symbol: string) => {
      setViewMode("chart");
      setParams({ symbol }, { replace: true });
      setSelection(null); // 换标的时清空右栏，避免张冠李戴
    },
    [setParams],
  );

  const handleSignalPick = useCallback(
    (symbol: string, side: "buy" | "sell") => {
      selectSymbol(symbol);
      if (side === "buy") {
        setShowBuyPoint(true); // 买点行直接打开买点分析抽屉
      } else {
        setExpCollapsed(false); // 卖点行展开右栏解释
      }
    },
    [selectSymbol],
  );

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["detail", selected],
    queryFn: () => api.detail(selected),
    enabled: Boolean(selected),
  });

  // 买点分析联动：review 查询 + 高亮指令 + 当前候选。打开时主图与抽屉并列（不覆盖），
  // 双向高亮（点图上价位线 <-> 点候选卡片）。逻辑与 DetailPage 共用同一 hook。
  const {
    review,
    reviewLoading,
    setActiveCand,
    activeAnnoId,
    highlightSpec,
  } = useBuyPointCoord(selected, data?.chart, showBuyPoint);

  const [refreshError, setRefreshError] = useState<string | null>(null);
  const refreshAll = useMutation({
    mutationFn: () => api.refresh(),
    onSuccess: (fresh) => {
      setRefreshError(null);
      queryClient.setQueryData(["cards"], fresh);
      queryClient.invalidateQueries({ queryKey: ["detail", selected] });
    },
    onError: (e) => setRefreshError(e instanceof Error ? e.message : String(e)),
  });

  const onPick = useCallback(
    (pick: MarkPick) => {
      // 买点联动（图 -> 卡）：带 annoId 的点击高亮对应候选卡片
      if (pick.annoId) {
        const idx = annoToIndex(pick.annoId);
        if (idx != null) setActiveCand(idx);
      }
      // 价位标注线只联动卡片，不开解释面板
      if (pick.kind === "highlight_price") return;
      // 买点对话栏打开时解释面板不显示，其余点击也不触发后台事件查询
      if (showBuyPoint) return;
      if (!data) return;
      // 点了图上标记 -> 自动展开解释面板（用户可能先收起了它）
      setExpCollapsed(false);
      const base = resolveSelection(pick, data);
      setSelection(base);

      const opts: { structureId?: string; onDate?: string; ruleId?: string; limit?: number } =
        pick.kind === "key_volatility"
          ? { onDate: pick.date, ruleId: "lei_color", limit: 20 }
          : { structureId: pick.structureId, limit: 30 };
      if (!opts.structureId && !opts.onDate) {
        setSelection({ ...base, events: [], eventsLoading: false });
        return;
      }
      api
        .events(selected, opts)
        .then((events) =>
          setSelection((cur) =>
            cur && cur.source === base.source && cur.date === base.date
              ? { ...cur, events, eventsLoading: false }
              : cur,
          ),
        )
        .catch(() =>
          setSelection((cur) =>
            cur && cur.source === base.source && cur.date === base.date
              ? { ...cur, events: [], eventsLoading: false }
              : cur,
          ),
        );
    },
    [data, selected, showBuyPoint, setActiveCand],
  );

  const pickConcept = useCallback(
    (key: string, sourceCn: string) => {
      if (!data) return;
      setSelection({
        source: sourceCn,
        explanation: data.concepts[key] ?? null,
        events: [],
        eventsLoading: false,
      });
    },
    [data],
  );

  // 徽章计数按口径过滤（仅存活时只数 live），markTotals 提供总数显示「n/total」。
  const markTotals = useMemo(() => {
    const c = data?.chart;
    return c
      ? {
          bottomMarks: c.bottomMarks.length,
          topMarks: c.topMarks.length,
          invalidatedMarks: c.invalidatedMarks.length,
        }
      : undefined;
  }, [data]);
  const counts = useMemo(() => {
    const c = data?.chart;
    const scoped = c ? scopeMarkCounts(c, display.marksScope) : null;
    return {
      bottomMarks: scoped ? scoped.bottomMarks : 0,
      topMarks: scoped ? scoped.topMarks : 0,
      invalidatedMarks: scoped ? scoped.invalidatedMarks : 0,
      keyVolatility: c ? c.keyVolatility.length : 0,
      levels: c ? (c.b1Line ? 1 : 0) + c.bottomLines.length + c.topLines.length : 0,
    };
  }, [data, display.marksScope]);

  const { lastClose, changePct, changeCls } = useMemo(() => {
    const close = data?.chart.lastClose ?? null;
    const ohlc = data?.chart.ohlc;
    const prev = ohlc && ohlc.length >= 2 ? ohlc[ohlc.length - 2][1] : null;
    const pct = close != null && prev ? (close / prev - 1) * 100 : null;
    return {
      lastClose: close,
      changePct: pct,
      changeCls: pct == null ? "flat" : pct > 0 ? "up" : pct < 0 ? "down" : "flat",
    };
  }, [data]);

  // 今日摘要条：聚合既有数据（不新增任何判定）。
  const digest = useMemo(() => {
    const a = data?.assessment;
    return {
      events: data?.new_events.length ?? 0,
      activeBuys: a?.trade_opportunities.filter((o) => o.is_active).length ?? 0,
      exitSignals: a?.exit_signals.length ?? 0,
      tradability: a?.tradability ?? null,
    };
  }, [data]);

  const weeklyTrendText = useMemo(() => {
    const m = data?.today?.technical?.find((item) => item.key === "weekly_long_trend");
    return m?.text ?? null;
  }, [data]);

  const backtestCount = useMemo(() => {
    if (!data) return 0;
    return (
      (data.first_ma_pullback_backtest ? 1 : 0) +
      data.scenario_backtests.length +
      (data.color_backtest ? 1 : 0)
    );
  }, [data]);

  // 摘要段点击 → 切回单标的视图、打开下方明细抽屉、展开对应面板并平滑滚到其位置。
  const jumpToPanel = useCallback(
    (key: "events" | "buys" | "exits" | "tradability") => {
      const map = {
        events: ["ws-panel-events", eventsPanelRef],
        buys: ["ws-panel-trade", tradePanelRef],
        exits: ["ws-panel-exit", exitPanelRef],
        tradability: ["ws-panel-tradability", tradabilityPanelRef],
      } as const;
      const [id, ref] = map[key];
      setViewMode("chart");
      setDetailsDrawerOpen(true);
      requestAnimationFrame(() => {
        ref.current?.expand();
        requestAnimationFrame(() => {
          document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "center" });
        });
      });
    },
    [],
  );

  // 键盘上下键在当前可见列表中切换标的
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.target instanceof HTMLInputElement) return;
      if (e.key !== "ArrowDown" && e.key !== "ArrowUp") return;
      const list = cards.filter((c) => !c.error).map((c) => c.symbol);
      const i = list.indexOf(selected);
      if (i < 0) return;
      const next = e.key === "ArrowDown" ? i + 1 : i - 1;
      if (next >= 0 && next < list.length) {
        e.preventDefault();
        selectSymbol(list[next]);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [cards, selected, selectSymbol]);

  return (
    <div className="workspace">
      <header className="ws-top">
        <div className="ws-quote-row ws-top-single">
          <div className="ws-entry-group ws-entry-primary">
            <button
              className="btn small ws-sidebar-toggle"
              onClick={() => setSidebarOpen(!sidebarOpen)}
              aria-expanded={sidebarOpen}
              title={sidebarOpen ? "收起自选栏" : "展开自选栏"}
            >
              {sidebarOpen ? "◀" : "▶"}
            </button>
            {data ? (
              <>
                <div className="ws-instrument ws-instrument-inline">
                  <span className="ws-symbol">{data.display_name}</span>
                  <span className="ws-instrument-meta">
                    {data.symbol}{data.market_cn ? ` · ${data.market_cn}` : ""}
                  </span>
                </div>
                <div className="ws-quote" aria-label="最新价格与涨跌幅">
                  <span className={`price ${changeCls}`}>{lastClose != null ? lastClose.toFixed(2) : "--"}</span>
                  <span className={`change ${changeCls}`}>
                    {changePct != null ? `${changePct > 0 ? "+" : ""}${changePct.toFixed(2)}%` : "--"}
                  </span>
                </div>
                <button
                  className="ws-state ws-state-inline"
                  onClick={() => pickConcept("signal_color", "顶栏 · BIAO 颜色")}
                  title="查看道路状态的解释"
                >
                  <ColorBadge color={data.assessment.color} colorCn={data.assessment.color_cn} descriptive />
                </button>
              </>
            ) : (
              <h1 className="ws-fallback-title">看盘</h1>
            )}
          </div>
          {data && (
            <div className="ws-entry-group ws-entry-context">
              {weeklyTrendText && weeklyTrendText !== "数据不足" && (
                <span className="ws-entry-item" title="基于已完成周线的长期趋势方向">
                  <span className="ws-entry-k">周线</span>
                  <b>{weeklyTrendText}</b>
                </span>
              )}
              <span
                className="ws-entry-item"
                title={
                  data.assessment.stage_change_reason_cn
                    ? `当前阶段：${data.assessment.stage_change_reason_cn}`
                    : "当前阶段，详细依据见下方速读卡"
                }
              >
                <span className="ws-entry-k">阶段</span>
                <b>{data.assessment.stage_cn}</b>
              </span>
              {data.market_badge && data.market_badge.summary_cn && !data.market_badge.summary_cn.includes("未知") && (
                <span className="ws-entry-item" title={data.market_badge.reasons_cn.join("\n") || undefined}>
                  <span className="ws-entry-k">环境</span>
                  <b>{data.market_badge.summary_cn}</b>
                </span>
              )}
            </div>
          )}
          <div className="ws-quote-actions">
            {dashboard && (
              <span
                className="ws-data-time"
                title={`行情时间：${data?.meta.data_time ? new Date(data.meta.data_time).toLocaleString("zh-CN", { hour12: false }) : "--"}（${data?.meta.is_intraday_forming ? "盘中" : "已收盘"}）\n信号判定日：${data?.assessment.as_of ?? "--"}`}
              >
                {data?.meta.is_intraday_forming ? "盘中" : "收盘"}{" "}
                {data?.meta.data_time
                  ? new Date(data.meta.data_time).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit", hour12: false })
                  : "--"}
                {data ? ` · 判定 ${data.assessment.as_of.slice(5)}` : ""}
              </span>
            )}
            <button
              className="btn small"
              disabled={refreshAll.isPending}
              onClick={() => refreshAll.mutate()}
              title="刷新自选行情与分析"
            >
              {refreshAll.isPending ? "刷新中…" : "刷新"}
            </button>
            {data && (
              <>
                <span className="ws-action-sep" aria-hidden="true" />
                <button
                  className="btn small"
                  onClick={() => setShowCreatePlan(true)}
                  title="基于当前信号建立执行计划"
                >
                  建计划
                </button>
                <button
                  className="btn small primary"
                  onClick={() => setShowBuyPoint(true)}
                  title="买点分析"
                >
                  买点分析
                </button>
                {!showBuyPoint && (
                  <button
                    className="btn small"
                    onClick={() => setExpCollapsed((c) => !c)}
                    aria-expanded={!expCollapsed}
                    title={expCollapsed ? "展开右侧解释面板" : "收起右侧解释面板"}
                  >
                    {expCollapsed ? "解释" : "收起解释"}
                  </button>
                )}
              </>
            )}
          </div>
        </div>
      </header>

      {refreshError && (
        <div className="error-banner">
          全量刷新失败：{refreshError}
          <button className="btn small" style={{ marginLeft: 8 }} onClick={() => setRefreshError(null)}>
            知道了
          </button>
        </div>
      )}

      <HomeEnvironmentStrip />
      {/* 危机管理状态机（V4 刚崩警示/V3 出清企稳，研究代理，首页仅激活时渲染，隐藏未知噪音） */}
      <CrisisBanner hideUnknown />

      <div
        className={`ws-body ${showSidebar ? "" : "no-sidebar"}${expVisible ? "" : " exp-collapsed"}`}
        style={
          showSidebar
            ? ({
                ["--sidebar-w" as string]: `${sidebarWidth}px`,
              } as React.CSSProperties)
            : ({
                ["--sidebar-w" as string]: "0px",
              } as React.CSSProperties)
        }
      >
        {showSidebar && (
          <WatchlistSidebar
            cards={cards}
            selected={selected}
            onSelect={selectSymbol}
            onAddClick={(gid) => setAddDialogGroup(gid)}
            signalBadges={signalSummary.badges}
          />
        )}
        {showSidebar && (
          <ResizeHandle
            width={sidebarWidth}
            min={200}
            max={520}
            onChange={setSidebarWidth}
            title="拖动调整左栏宽度"
          />
        )}

        <main className="ws-center">
          {cardsLoading && <div className="loading">正在加载自选与大盘…</div>}
          {cardsError && (
            <div className="error-banner" role="alert">
              自选与大盘读取失败：{cardsLoadError instanceof Error ? cardsLoadError.message : String(cardsLoadError)}。
              {dashboard && "下方显示上次成功读取的资料，当前结果尚未更新。"}
              <button className="btn small" disabled={cardsFetching} onClick={() => void refetchCards()}>重新读取</button>
            </div>
          )}
          {!cardsLoading && !cardsError && cards.length === 0 && (
            <div className="panel" style={{ padding: 32, textAlign: "center" }}>
              <div style={{ fontSize: 16, marginBottom: 8 }}>自选列表还是空的</div>
              <div className="muted" style={{ marginBottom: 16 }}>
                添加第一个标的后，这里会显示 K 线图、今日信号与解释面板。
              </div>
              <button className="btn primary" onClick={() => setAddDialogGroup(null)}>
                添加自选标的
              </button>
            </div>
          )}
          {!cardsLoading && cards.length > 0 && !selected && (
            <div className="panel" style={{ padding: 32, textAlign: "center" }}>
              <div className="muted">
                所有自选标的当前都不可用（数据源异常）。稍后点右上角「刷新」重试。
              </div>
            </div>
          )}
          {error && (
            <div className="error-banner">
              {selected} 加载失败：
              {error instanceof Error ? error.message : String(error)}
            </div>
          )}
          {isLoading && viewMode === "chart" && <div className="loading">正在分析 {selected} …</div>}

          {cards.length > 0 && (
            <div className="ws-view-switch">
              <div className="ws-view-tabs" role="tablist" aria-label="看盘主区视图切换">
                <button
                  type="button"
                  role="tab"
                  aria-selected={viewMode === "chart"}
                  className={`ws-view-tab${viewMode === "chart" ? " active" : ""}`}
                  onClick={() => switchViewMode("chart")}
                >
                  单标的 K 线与速览
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={viewMode === "compare"}
                  className={`ws-view-tab${viewMode === "compare" ? " active" : ""}`}
                  onClick={() => switchViewMode("compare")}
                >
                  横向比强弱 ({cards.filter((c) => !c.error && !c.symbol.endsWith(".SECTOR")).length})
                </button>
              </div>
              <div className="ws-inline-digest" aria-label="自选异动与当前标的摘要">
                <button
                  type="button"
                  className={`ws-digest-pill${signalSummary.buyA > 0 ? " buy" : ""}${signalsOpen ? " is-open" : ""}`}
                  aria-expanded={signalsOpen}
                  onClick={() => setSignalsOpen((v) => !v)}
                  title="展开全自选买卖异动扫描列表（含历史回放与刷新）"
                >
                  自选异动：买 <b>{signalSummary.buyA}</b> · 待 <b>{signalSummary.buyW}</b> · 弱 <b>{signalSummary.sellCount}</b> {signalsOpen ? "▴" : "▾"}
                </button>
                {viewMode === "chart" && data && (
                  <>
                    {digest.activeBuys > 0 && (
                      <button
                        type="button"
                        className="ws-digest-pill buy"
                        onClick={() => jumpToPanel("buys")}
                      >
                        活跃买点 <b>{digest.activeBuys}</b> ▾
                      </button>
                    )}
                    {digest.exitSignals > 0 && (
                      <button
                        type="button"
                        className="ws-digest-pill warn"
                        onClick={() => jumpToPanel("exits")}
                      >
                        退出提醒 <b>{digest.exitSignals}</b> ▾
                      </button>
                    )}
                    {digest.tradability && !digest.tradability.tradable && (
                      <button
                        type="button"
                        className="ws-digest-pill warn"
                        onClick={() => jumpToPanel("tradability")}
                        title={digest.tradability.blocking_reasons[0]}
                      >
                        暂不宜追 ▾
                      </button>
                    )}
                    {digest.events > 0 && (
                      <button
                        type="button"
                        className="ws-digest-pill"
                        onClick={() => jumpToPanel("events")}
                      >
                        当期事件 {digest.events} ▾
                      </button>
                    )}
                  </>
                )}
              </div>
            </div>
          )}

          {signalsOpen && (
            <div className="ws-firstlook-group">
              <TodaySignalBanner onPick={handleSignalPick} defaultOpen />
            </div>
          )}

          {viewMode === "compare" ? (
            <CrossSectionComparePanel
              cards={cards}
              selected={selected}
              onSelectSymbol={selectSymbol}
            />
          ) : (
            data && (
            <>
              {data.meta.persist_warning && (
                <div className="panel warn-panel">
                  <span className="stale-chip">未写入研究库</span>{" "}
                  <span className="muted">
                    分析结果正常展示，但研究库拒绝写入（事件身份字段与历史冲突）。
                  </span>
                </div>
              )}

              <div className={`ws-chart-row${showBuyPoint ? " bp-open" : ""}`}>
              <div className="kline-wrap">
                <ChartControls
                  display={display}
                  onChange={setDisplay}
                  counts={counts}
                  markTotals={markTotals}
                  onDownloadPng={() => downloadPngRef.current?.()}
                  rangePreset={rangePreset}
                  onRangePreset={handleRangePreset}
                />
                <KlineChart
                  payload={data.chart}
                  display={display}
                  onPick={onPick}
                  highlight={highlightSpec}
                  onDownload={(fn) => (downloadPngRef.current = fn)}
                  rangeRequest={rangeRequest}
                  defaultRangePreset={rangePreset ?? "6M"}
                  onRangeCustom={handleRangeCustom}
                />
                <div className="chart-legend">
                  {anyMarkShown && (
                    <div className="cl-group">
                      <span className="cl-group-k">标记</span>
                      {legend.bottomMarks && (
                        <span>
                          <span className="mk mk-bottom">◆</span> 底部确认
                        </span>
                      )}
                      {legend.topMarks && (
                        <span>
                          <span className="mk mk-top">◆</span> 顶部确认
                        </span>
                      )}
                      {legend.invalidatedMarks && (
                        <span>
                          <span className="mk mk-dead">✕</span> 结构失效
                        </span>
                      )}
                      {legend.keyVolatility && (
                        <span>
                          <span className="mk mk-kv">▲</span> 关键性波动
                        </span>
                      )}
                      {legend.levels && (
                        <>
                          <span>
                            <span className="mk mk-b1">●</span> 前高阻力(B1)
                          </span>
                          <span>
                            <span className="mk mk-cline">●</span> 前低支撑(C)
                          </span>
                          <span>
                            <span className="mk mk-neck">●</span> 顶部颈线
                          </span>
                        </>
                      )}
                    </div>
                  )}
                  <div className="cl-group vol-legend">
                    <span className="cl-group-k">量能</span>
                    <span className="vol-sw vol-surged" />
                    <span>≥2×放量</span>
                    <span className="vol-sw vol-warm" />
                    <span>温和</span>
                    <span className="vol-sw vol-normal" />
                    <span>正常</span>
                    <span className="vol-sw vol-shrunk" />
                    <span>&lt;0.8×缩量</span>
                    <span className="vol-ma-line" />
                    <span>20日均量</span>
                  </div>
                  {anyMarkShown && (
                    <span className="muted cl-hint">点图上标记或参考线圆点 → 右栏看解释</span>
                  )}
                </div>
              </div>
              {showBuyPoint && (
                <BuyPointDrawer
                  symbol={data.symbol}
                  review={review}
                  reviewLoading={reviewLoading}
                  activeAnnoId={activeAnnoId}
                  onActivateCandidate={(i) => setActiveCand(i)}
                  onClose={() => setShowBuyPoint(false)}
                />
              )}
              </div>

              {/* 第 3 步：单标的 30 秒速读卡（整合趋势方向、均线/C点位置与动作条件） */}
              <SymbolQuickReadCard
                assessment={data.assessment}
                today={data.today ?? null}
                chart={data.chart}
                onPickConcept={pickConcept}
                onSelect={(sel) => {
                  setExpCollapsed(false);
                  setSelection(sel);
                }}
              />

              {/* 通用实战大白话提示卡（排雷底色 + 买点补仓判断 + 填入买进价自动切换两步拿牛保护线） */}
              <SmartSymbolPromptCard symbol={data.symbol} />

              {/* 二级抽屉 1：当期规则拆解与盘口完整表（默认收起，点上方摘要条可自动定位展开） */}
              <details
                className="ws-deep-drawer"
                open={detailsDrawerOpen}
                onToggle={(e) => setDetailsDrawerOpen(e.currentTarget.open)}
              >
                <summary>
                  <span>当期规则拆解与盘口明细（支持/冲突因素 · 盘口四价与市值 · 完整门禁表）</span>
                </summary>
                <div className="ws-deep-drawer-body">
                  {data.assessment.trade_opportunities.length > 0 && (
                    <CollapsiblePanel id="ws-panel-trade" ref={tradePanelRef} title="潜在买点明细" storageKey="ws.card.trade" defaultCollapsed={false}>
                      <TradeOpportunityPanel
                        opportunities={data.assessment.trade_opportunities}
                        onSelect={(sel) => {
                          setExpCollapsed(false);
                          setSelection(sel);
                        }}
                      />
                    </CollapsiblePanel>
                  )}

                  {data.assessment.pullback_opportunities.length > 0 && (
                    <CollapsiblePanel title="首次回撤机会明细" storageKey="ws.card.pullback" defaultCollapsed={false}>
                      <PullbackOpportunityPanel
                        opportunities={data.assessment.pullback_opportunities}
                        onSelect={(sel) => {
                          setExpCollapsed(false);
                          setSelection(sel);
                        }}
                      />
                    </CollapsiblePanel>
                  )}

                  {data.assessment.conditional_scenarios.length > 0 && (
                    <CollapsiblePanel title="条件化场景明细" storageKey="ws.card.conditional" defaultCollapsed={true}>
                      <ConditionalScenarioPanel
                        scenarios={data.assessment.conditional_scenarios}
                        onSelect={(sel) => {
                          setExpCollapsed(false);
                          setSelection(sel);
                        }}
                      />
                    </CollapsiblePanel>
                  )}

                  {data.assessment.exit_signals.length > 0 && (
                    <CollapsiblePanel id="ws-panel-exit" ref={exitPanelRef} title="持仓退出条件明细" storageKey="ws.card.exit" defaultCollapsed={false}>
                      <ExitSignalPanel
                        exitSignals={data.assessment.exit_signals}
                        onSelect={(sel) => {
                          setExpCollapsed(false);
                          setSelection(sel);
                        }}
                      />
                    </CollapsiblePanel>
                  )}

                  {data.assessment.tradability && (
                    <CollapsiblePanel id="ws-panel-tradability" ref={tradabilityPanelRef} title="可交易性 9 项门禁明细" storageKey="ws.card.tradability" defaultCollapsed={true}>
                      <TradabilityPanel tradability={data.assessment.tradability} />
                    </CollapsiblePanel>
                  )}

                  <CollapsiblePanel title="支持与冲突因素拆解" storageKey="ws.card.assessment" defaultCollapsed={true}>
                    <AssessmentPanel assessment={data.assessment} onPickConcept={pickConcept} />
                  </CollapsiblePanel>

                  {data.today && (
                    <CollapsiblePanel title="盘口四价、换手与市值明细" storageKey="ws.card.today" defaultCollapsed={true}>
                      <TodayOverviewPanel today={data.today} onPickConcept={pickConcept} />
                    </CollapsiblePanel>
                  )}

                  {data.new_events.length > 0 && (
                    <CollapsiblePanel id="ws-panel-events" ref={eventsPanelRef} title={`今日新事件（${data.new_events.length}）`} storageKey="ws.card.newevents" defaultCollapsed={false}>
                      <div className="panel">
                        {data.new_events.map((e) => (
                          <div
                            key={e.event_id}
                            className="new-event-row"
                            onClick={() => {
                              setExpCollapsed(false);
                              setSelection({
                                source: "今日新事件",
                                date: e.available_date,
                                explanation: e.explanation,
                                events: [e],
                                eventsLoading: false,
                              });
                            }}
                            title="点击查看解释"
                          >
                            <span className={`sev-chip ${e.severity}`}>{e.severity_cn}</span>
                            <b>
                              {e.rule_cn}
                              {e.sub_rule_cn ? ` · ${e.sub_rule_cn}` : ""}
                            </b>
                            <span className="muted">{e.reason_cn}</span>
                          </div>
                        ))}
                      </div>
                    </CollapsiblePanel>
                  )}
                </div>
              </details>

              {/* 二级抽屉 2：单标的历史回测统计（与日常看盘物理隔离，避免15个折叠条刷屏） */}
              {backtestCount > 0 && (
                <details className="ws-deep-drawer">
                  <summary>
                    <span>单标的历史回测统计（研究参考，非买卖建议 · 共 {backtestCount} 项）</span>
                  </summary>
                  <div className="ws-deep-drawer-body">
                    {data.first_ma_pullback_backtest && (
                      <PullbackBacktestPanel report={data.first_ma_pullback_backtest} />
                    )}
                    {data.scenario_backtests.map((report) => (
                      <ScenarioBacktestPanel key={report.scenario_id} report={report} />
                    ))}
                    {data.color_backtest && <ColorBacktestPanel report={data.color_backtest} />}
                  </div>
                </details>
              )}

              <div className="disclaimer">
                {data.disclaimer_cn}
                {isFetching && " · 正在刷新…"}
              </div>
            </>
            )
          )}
        </main>

        {expVisible && (
          <ExplanationPanel selection={selection} onClose={() => setSelection(null)} />
        )}
      </div>

      {addDialogGroup !== undefined && (
        <AddSymbolDialog
          groupId={addDialogGroup}
          onClose={() => setAddDialogGroup(undefined)}
          onAdded={() => {
            queryClient.invalidateQueries({ queryKey: ["cards"] });
            queryClient.invalidateQueries({ queryKey: ["groups"] });
          }}
        />
      )}
      {showCreatePlan && data && (
        <PlanCreateFlow
          symbol={data.symbol}
          prefill={prefillFromOpportunity(
            data.assessment.trade_opportunities.find((o) => o.is_active) ?? null,
          )}
          onClose={() => setShowCreatePlan(false)}
        />
      )}
    </div>
  );
}
