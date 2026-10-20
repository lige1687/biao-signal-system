import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api, sectorsApi } from "../api/client";
import { sectorKeywordsForEtf } from "../data/sectorEtfMap";
import AddSymbolDialog from "../components/AddSymbolDialog";
import AssessmentPanel from "../components/AssessmentPanel";
import CollapsiblePanel, { type CollapsiblePanelHandle } from "../components/CollapsiblePanel";
import ChartControls from "../components/ChartControls";
import TrendChecklist from "../components/TrendChecklist";
import ColorBacktestPanel from "../components/ColorBacktestPanel";
import PullbackBacktestPanel from "../components/PullbackBacktestPanel";
import PullbackOpportunityPanel from "../components/PullbackOpportunityPanel";
import ConditionalScenarioPanel from "../components/ConditionalScenarioPanel";
import ExitSignalPanel from "../components/ExitSignalPanel";
import ScenarioBacktestPanel from "../components/ScenarioBacktestPanel";
import TradabilityPanel from "../components/TradabilityPanel";
import ColorBadge from "../components/ColorBadge";
import ExplanationPanel, { type Selection } from "../components/ExplanationPanel";
import MarketBreadthBadge from "../components/MarketBreadthBadge";
import TodayDigestBar from "../components/TodayDigestBar";
import KlineChart, {
  DEFAULT_DISPLAY,
  effectiveDisplay,
  type ChartDisplay,
  type MarkPick,
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
import WatchlistSidebar from "../components/WatchlistSidebar";
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

/** 板块阶段 chip 文案与色调（与 SectorsPage 的 STAGE_CN/STAGE_TONE 同口径）。 */
const SECTOR_CHIP_CN: Record<string, string> = {
  markup: "上升",
  accumulation: "筑底",
  distribution: "派发",
  decline: "下降",
};
const SECTOR_CHIP_TONE: Record<string, string> = {
  markup: "sector-up",
  accumulation: "sector-base",
  distribution: "sector-dist",
  decline: "sector-down",
};

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
  const navigate = useNavigate();
  const [params, setParams] = useSearchParams();
  const [selection, setSelection] = useState<Selection | null>(null);
  // 周期默认日线，但沿用用户上次的选择（localStorage 持久化）。
  const [display, setDisplay] = useState<ChartDisplay>(() => ({
    ...DEFAULT_DISPLAY,
    timeframe: loadTimeframe(),
  }));
  // 图例只描述「图上真的画了什么」：周/月线下日线专属项已隐藏，故读生效开关。
  const legend = effectiveDisplay(display);
  const [addDialogGroup, setAddDialogGroup] = useState<number | null | undefined>(undefined);
  const [showCreatePlan, setShowCreatePlan] = useState(false);
  const [showBuyPoint, setShowBuyPoint] = useState(false);
  // 右侧解释面板是否收起。默认收起以给 K 线主图留出更大空间；
  // 点图上标记时自动展开以便看解释。买点分析打开时面板自动隐藏。
  const [expCollapsed, setExpCollapsed] = useState(true);
  const expVisible = !showBuyPoint && !expCollapsed;
  const [sidebarOpen, setSidebarOpen] = useState(true);
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

  const { data: dashboard, isLoading: cardsLoading } = useQuery({
    queryKey: ["cards"],
    queryFn: () => api.dashboard(),
  });

  const cards = dashboard?.cards ?? [];
  const urlSymbol = params.get("symbol") ?? "";
  // 未指定标的时默认选第一张可用卡片（通常是上证指数）
  const selected = urlSymbol || cards.find((c) => !c.error)?.symbol || "";

  const selectSymbol = useCallback(
    (symbol: string) => {
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

  // 反向联动：当前标的是映射内的行业 ETF 时，顶栏显示其所属板块的阶段。
  // 只读板块趋势快照（已预计算、有缓存），点击跳板块页看完整判定。
  const sectorKeywords = useMemo(
    () => (selected ? sectorKeywordsForEtf(selected) : null),
    [selected],
  );
  const { data: sectorTrend } = useQuery({
    queryKey: ["sectorsTrend"],
    queryFn: () => sectorsApi.trend(false, "all"),
    staleTime: 5 * 60_000,
    enabled: sectorKeywords != null,
  });
  const sectorChip = useMemo(() => {
    if (!sectorKeywords || !sectorTrend?.boards) return null;
    // 命中多级板块时取最宏观的（level 最小）；同 level 取第一个。
    const hit = sectorTrend.boards
      .filter((b) => sectorKeywords.some((k) => b.name.includes(k)))
      .sort((a, b) => a.level - b.level)[0];
    if (!hit) return null;
    return { name: hit.name, stage: hit.stage as string | null };
  }, [sectorKeywords, sectorTrend]);

  // 摘要段点击 → 展开对应面板并平滑滚到其位置。
  const jumpToPanel = useCallback(
    (key: "events" | "buys" | "exits" | "tradability") => {
      const map = {
        events: ["ws-panel-events", eventsPanelRef],
        buys: ["ws-panel-trade", tradePanelRef],
        exits: ["ws-panel-exit", exitPanelRef],
        tradability: ["ws-panel-tradability", tradabilityPanelRef],
      } as const;
      const [id, ref] = map[key];
      ref.current?.expand();
      requestAnimationFrame(() => {
        document.getElementById(id)?.scrollIntoView({ behavior: "smooth", block: "center" });
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
      <div className="ws-top">
        <button
          className="btn small"
          onClick={() => setSidebarOpen(!sidebarOpen)}
          title={sidebarOpen ? "收起自选栏" : "展开自选栏"}
        >
          {sidebarOpen ? "◀" : "▶"}
        </button>
        <strong>LEI 看盘系统</strong>
        <MarketBreadthBadge />
        {data && (
          <>
            <span className="ws-symbol">{data.display_name}</span>
            <span className="muted">{data.symbol}</span>
            {data.market_cn && <span className="tag">{data.market_cn}</span>}
            <span className={`price ${changeCls}`}>
              {lastClose != null ? lastClose.toFixed(2) : "--"}
            </span>
            <span className={`change ${changeCls}`}>
              {changePct != null ? `${changePct > 0 ? "+" : ""}${changePct.toFixed(2)}%` : "--"}
            </span>
            <span
              onClick={() => pickConcept("signal_color", "顶栏 · LEI 颜色")}
              style={{ cursor: "pointer" }}
              title="点击查看解释"
            >
              <ColorBadge color={data.assessment.color} colorCn={data.assessment.color_cn} />
            </span>
            {data.market_badge && (
              <span
                className={`badge-chip ${data.market_badge.summary}`}
                title={data.market_badge.reasons_cn.join("\n") || undefined}
              >
                市场环境：{data.market_badge.summary_cn}
              </span>
            )}
            {sectorChip && (
              <button
                type="button"
                className={`badge-chip sector-link-chip ${SECTOR_CHIP_TONE[sectorChip.stage ?? ""] ?? ""}`}
                onClick={() => navigate("/sectors")}
                title={`「${sectorChip.name}」板块阶段 · 点击打开板块趋势工作台（research_proxy）`}
              >
                {sectorChip.name} · {SECTOR_CHIP_CN[sectorChip.stage ?? ""] ?? "样本不足"}
              </button>
            )}
          </>
        )}
        <span style={{ flex: 1 }} />
        {data && (
          <button
            className="btn small"
            onClick={() => setShowCreatePlan(true)}
            title="基于当前信号建立执行计划"
          >
            建立执行计划
          </button>
        )}
        {data && (
          <button
            className="btn small"
            onClick={() => setShowBuyPoint(true)}
            title="买点分析"
          >
            买点分析
          </button>
        )}
        {data && !showBuyPoint && (
          <button
            className="btn small"
            onClick={() => setExpCollapsed((c) => !c)}
            title={expCollapsed ? "展开右侧解释面板" : "收起右侧解释面板"}
          >
            {expCollapsed ? "解释" : "收起解释"}
          </button>
        )}
        {dashboard && (
          <span className="muted" style={{ fontSize: 11 }}>
            {data?.meta.data_time
              ? new Date(data.meta.data_time).toLocaleTimeString("zh-CN", { hour12: false })
              : "--"}{" "}
            · {data?.meta.is_intraday_forming ? "盘中" : "已收盘"}
          </span>
        )}
        <button
          className="btn small primary"
          disabled={refreshAll.isPending}
          onClick={() => refreshAll.mutate()}
        >
          {refreshAll.isPending ? "刷新中…" : "刷新"}
        </button>
      </div>

      {refreshError && (
        <div className="error-banner">
          全量刷新失败：{refreshError}
          <button className="btn small" style={{ marginLeft: 8 }} onClick={() => setRefreshError(null)}>
            知道了
          </button>
        </div>
      )}

      {/* 危机管理状态机（V4 刚崩警示/V3 出清企稳，研究代理，零触发不渲染） */}
      <CrisisBanner />

      <div
        className={`ws-body ${sidebarOpen ? "" : "no-sidebar"}${expVisible ? "" : " exp-collapsed"}`}
        style={
          sidebarOpen
            ? ({
                ["--sidebar-w" as string]: `${sidebarWidth}px`,
              } as React.CSSProperties)
            : ({
                ["--sidebar-w" as string]: "0px",
              } as React.CSSProperties)
        }
      >
        {sidebarOpen && (
          <WatchlistSidebar
            cards={cards}
            selected={selected}
            onSelect={selectSymbol}
            onAddClick={(gid) => setAddDialogGroup(gid)}
          />
        )}
        {sidebarOpen && (
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
          {!cardsLoading && cards.length === 0 && (
            <div className="panel" style={{ padding: 32, textAlign: "center" }}>
              <div style={{ fontSize: 15, marginBottom: 8 }}>自选列表还是空的</div>
              <div className="muted" style={{ marginBottom: 16 }}>
                添加第一个标的后，这里会显示 K 线图、今日信号与解释面板。
              </div>
              <button className="btn primary" onClick={() => setAddDialogGroup(undefined)}>
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
          {isLoading && <div className="loading">正在分析 {selected} …</div>}

          <TodaySignalBanner onPick={handleSignalPick} />

          {data && (
            <>
              <TodayDigestBar
                events={digest.events}
                activeBuys={digest.activeBuys}
                exitSignals={digest.exitSignals}
                tradability={digest.tradability}
                onJump={jumpToPanel}
              />

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
                />
                <KlineChart
                  payload={data.chart}
                  display={display}
                  onPick={onPick}
                  highlight={highlightSpec}
                  onDownload={(fn) => (downloadPngRef.current = fn)}
                />
                <CollapsiblePanel
                  title="趋势转折 5 条件"
                  defaultCollapsed={true}
                  storageKey="ws.card.trendcheck"
                >
                  <TrendChecklist payload={data.chart} assessment={data.assessment} />
                </CollapsiblePanel>
                <div className="chart-legend">
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
                        <span className="mk mk-b1">●</span> B1 第一阻力
                      </span>
                      <span>
                        <span className="mk mk-cline">●</span> C 点失效线
                      </span>
                      <span>
                        <span className="mk mk-neck">●</span> 顶部颈线
                      </span>
                    </>
                  )}
                  {legend.colorMode === "lei_state" && (
                    <span className="muted">
                      LEI 着色：颜色=当日状态（绿/灰/黑）；涨跌方向看「今日概述」开高低收
                    </span>
                  )}
                  {/* 量能颜色图例：与下方柱状图一一对应 */}
                  <span className="vol-legend">
                    <span className="muted">量能</span>
                    <span className="vol-sw vol-surged" />
                    <span>≥2× 放量</span>
                    <span className="vol-sw vol-warm" />
                    <span>温和</span>
                    <span className="vol-sw vol-normal" />
                    <span>正常</span>
                    <span className="vol-sw vol-shrunk" />
                    <span>&lt;0.8× 缩量</span>
                  </span>
                  <span className="muted">
                    {counts.bottomMarks ||
                    counts.topMarks ||
                    counts.invalidatedMarks ||
                    counts.keyVolatility ||
                    counts.levels
                      ? legend.bottomMarks ||
                        legend.topMarks ||
                        legend.invalidatedMarks ||
                        legend.keyVolatility ||
                        legend.levels
                        ? "点标记/线右端圆点 → 右栏看解释"
                        : "信号标记默认隐藏，按上方开关显示"
                      : ""}
                  </span>
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

              {data.today && (
                <CollapsiblePanel title="今日概述" storageKey="ws.card.today" defaultCollapsed={true}>
                  <TodayOverviewPanel today={data.today} onPickConcept={pickConcept} />
                </CollapsiblePanel>
              )}

              {data.assessment.trade_opportunities.length > 0 && (
                <CollapsiblePanel id="ws-panel-trade" ref={tradePanelRef} title="潜在买点" storageKey="ws.card.trade" defaultCollapsed={true}>
                  <TradeOpportunityPanel
                    opportunities={data.assessment.trade_opportunities}
                    onSelect={setSelection}
                  />
                </CollapsiblePanel>
              )}

              {data.assessment.pullback_opportunities.length > 0 && (
                <CollapsiblePanel title="首次回撤机会" storageKey="ws.card.pullback" defaultCollapsed={true}>
                  <PullbackOpportunityPanel
                    opportunities={data.assessment.pullback_opportunities}
                    onSelect={setSelection}
                  />
                </CollapsiblePanel>
              )}

              {data.assessment.conditional_scenarios.length > 0 && (
                <CollapsiblePanel title="条件化场景" storageKey="ws.card.conditional" defaultCollapsed={true}>
                  <ConditionalScenarioPanel
                    scenarios={data.assessment.conditional_scenarios}
                    onSelect={setSelection}
                  />
                </CollapsiblePanel>
              )}

              {data.assessment.exit_signals.length > 0 && (
                <CollapsiblePanel id="ws-panel-exit" ref={exitPanelRef} title="持仓退出" storageKey="ws.card.exit" defaultCollapsed={true}>
                  <ExitSignalPanel
                    exitSignals={data.assessment.exit_signals}
                    onSelect={setSelection}
                  />
                </CollapsiblePanel>
              )}

              {data.assessment.tradability && (
                <CollapsiblePanel id="ws-panel-tradability" ref={tradabilityPanelRef} title="可交易性门禁" storageKey="ws.card.tradability" defaultCollapsed={true}>
                  <TradabilityPanel tradability={data.assessment.tradability} />
                </CollapsiblePanel>
              )}

              <CollapsiblePanel title="当前观察" storageKey="ws.card.assessment" defaultCollapsed={true}>
                <AssessmentPanel assessment={data.assessment} onPickConcept={pickConcept} />
              </CollapsiblePanel>

              {data.first_ma_pullback_backtest && (
                <PullbackBacktestPanel report={data.first_ma_pullback_backtest} />
              )}

              {data.scenario_backtests.map((report) => (
                <ScenarioBacktestPanel key={report.scenario_id} report={report} />
              ))}

              {data.color_backtest && <ColorBacktestPanel report={data.color_backtest} />}

              {data.new_events.length > 0 && (
                <CollapsiblePanel id="ws-panel-events" ref={eventsPanelRef} title={`今日新事件（${data.new_events.length}）`} storageKey="ws.card.newevents" defaultCollapsed={true}>
                  <div className="panel">
                    {data.new_events.map((e) => (
                      <div
                        key={e.event_id}
                        className="new-event-row"
                        onClick={() =>
                          setSelection({
                            source: "今日新事件",
                            date: e.available_date,
                            explanation: e.explanation,
                            events: [e],
                            eventsLoading: false,
                          })
                        }
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

              <div className="disclaimer">
                {data.disclaimer_cn}
                {isFetching && " · 正在刷新…"}
              </div>
            </>
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
