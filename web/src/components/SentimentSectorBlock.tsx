import { useEffect, useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { api, sentimentApi } from "../api/client";
import type { SectorBoardRow, SectorBoardsView, SectorRecommendation } from "../types";

/* ── 情绪页·板块主区块（2026-09-07 二次重做）──────────────────────────
 * 用户口径：板块是重点、要大、要图表不要文字墙；只优先展示持仓相关板块，
 * 其他行业不认识不关心；阈值（机会位/压力位）要看得见；要有一个
 * "推荐加入观察"的地方，自己决定加不加（观察列表存浏览器本地）。
 *
 * 阈值框架与基本面页宽度卡一致：b50 ≤20% 机会位（深度弱势）、
 * ≥80% 压力位（过热拥挤）、中间常态区。b50 = 板块内站上 50 日线
 * （约半年均线）的股票占比。 */

const WATCH_KEY = "lei.sentiment.watchBoards";

function useWatchBoards() {
  const [watch, setWatch] = useState<Set<string>>(() => {
    try {
      return new Set<string>(JSON.parse(localStorage.getItem(WATCH_KEY) ?? "[]"));
    } catch {
      return new Set<string>();
    }
  });
  const toggle = (code: string) => {
    setWatch((prev) => {
      const next = new Set(prev);
      if (next.has(code)) next.delete(code);
      else next.add(code);
      try {
        localStorage.setItem(WATCH_KEY, JSON.stringify([...next]));
      } catch { /* 私密模式等场景忽略 */ }
      return next;
    });
  };
  return { watch, toggle };
}

/* ── 板块「价格 × 情绪」对照图抽屉（点开板块卡；us=美股行业模式） ──────
 * 双轴：左=板块指数涨跌（起点=100），右=情绪强度 b50（0-100 带 20/80 阈值
 * 与色带）；A股加散户小单净流入柱，美股加标普500等权参考线。 */
function BoardChartDrawer({ code, name, onClose, us }: { code: string; name: string; onClose: () => void; us?: boolean }) {
  const ref = useRef<HTMLDivElement>(null);
  const { data, isLoading, error } = useQuery({
    queryKey: ["sentBoardChart", us ? "us" : "cn", code],
    queryFn: () => (us ? sentimentApi.usBoardChart(code) : sentimentApi.boardChart(code)),
    staleTime: 30 * 60_000,
  });

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  useEffect(() => {
    if (!ref.current || !data?.available || data.dates.length < 2) return;
    const inst = echarts.init(ref.current, undefined, { renderer: "canvas" });
    const ro = new ResizeObserver(() => inst.resize());
    ro.observe(ref.current);
    // 涨跌幅口径：以窗口内第一个有效收盘为 100（直观比较涨跌幅度）
    const first = data.close.find((v) => v != null) ?? null;
    const rebase = data.close.map((v) => (v != null && first ? Number(((v / first) * 100).toFixed(2)) : null));
    // 美股模式：标普500等权参考线（同样起点=100，看形态谁在上谁跑赢）
    const refRaw = data.ref_close ?? [];
    const refFirst = refRaw.find((v) => v != null) ?? null;
    const refSeries = refRaw.some((v) => v != null) && refFirst
      ? refRaw.map((v) => (v != null ? Number(((v / refFirst) * 100).toFixed(2)) : null))
      : null;
    inst.setOption({
      animation: false,
      grid: { left: 56, right: 52, top: 34, bottom: 52 },
      tooltip: { trigger: "axis", order: "valueDesc" },
      legend: { top: 2, textStyle: { fontSize: 11 }, itemWidth: 16 },
      xAxis: { type: "category", data: data.dates, axisLabel: { fontSize: 10 } },
      yAxis: [
        { type: "value", name: "指数(起点100)", nameTextStyle: { fontSize: 10 }, scale: true },
        { type: "value", name: "情绪强度%", min: 0, max: 100, nameTextStyle: { fontSize: 10 }, splitLine: { show: false } },
        { type: "value", show: false, scale: true }, // 散户净流入柱的隐藏轴
      ],
      dataZoom: [
        { type: "inside" },
        { type: "slider", height: 14, bottom: 10 },
      ],
      series: [
        {
          name: "板块指数", type: "line", yAxisIndex: 0, data: rebase, showSymbol: false,
          lineStyle: { width: 2.2, color: "#2563eb" }, itemStyle: { color: "#2563eb" }, z: 10,
        },
        ...(refSeries
          ? [{
              name: us ? "标普500等权(对照)" : "参考线", type: "line" as const, yAxisIndex: 0,
              data: refSeries, showSymbol: false,
              lineStyle: { width: 1.2, type: "dashed" as const, color: "#9aa4b2" },
              itemStyle: { color: "#9aa4b2" }, z: 8,
            }]
          : []),
        {
          name: "情绪强度b50", type: "line", yAxisIndex: 1, data: data.b50, showSymbol: false, connectNulls: true,
          lineStyle: { width: 1.8, color: "#b45309" }, itemStyle: { color: "#b45309" }, z: 9,
          markLine: {
            silent: true, symbol: "none", label: { fontSize: 10, position: "insideEndTop" },
            data: [
              { yAxis: 80, lineStyle: { color: "#d24a43", type: "dashed" }, label: { formatter: "压力位80", color: "#d24a43" } },
              { yAxis: 20, lineStyle: { color: "#15803d", type: "dashed" }, label: { formatter: "机会位20", color: "#15803d" } },
            ],
          },
          markArea: {
            silent: true,
            data: [
              [{ yAxis: 80, itemStyle: { color: "rgba(210,74,67,0.06)" } }, { yAxis: 100 }],
              [{ yAxis: 0, itemStyle: { color: "rgba(21,128,61,0.06)" } }, { yAxis: 20 }],
            ],
          },
        },
        ...(!us
          ? [{
              name: "散户净流入(20日,亿)", type: "bar" as const, yAxisIndex: 2, data: data.retail20,
              barMaxWidth: 6, itemStyle: { color: "rgba(77,127,196,0.35)" }, z: 2,
            }]
          : []),
      ],
    });
    return () => {
      ro.disconnect();
      inst.dispose();
    };
  }, [data, us]);

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-panel trend-drawer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <h2>{name} · 价格 × 情绪对照{us ? "（美股行业）" : ""}</h2>
          <button type="button" className="btn mini" onClick={onClose}>关闭</button>
        </div>
        <div className="drawer-body trend-drawer-body">
          {isLoading && <div className="muted" style={{ padding: 20 }}>加载板块历史中…</div>}
          {error && <div className="muted" style={{ padding: 20 }}>加载失败：{(error as Error).message}</div>}
          {data && !data.available && <div className="muted" style={{ padding: 20 }}>该板块暂无历史数据。</div>}
          {data?.available && (
            <>
              <div ref={ref} style={{ width: "100%", height: 440 }} />
              <div className="muted mood-note">{data.note_cn}</div>
              {!us && (
                <div className="muted mood-note">
                  散户净流入数据点 {data.n_retail} 个（腾讯资金流，2021 起；部分板块覆盖不全时柱会断续）。
                  情绪强度 b50 数据自 2025-08 起（板块趋势历史重建后覆盖更长）。全部为研究参考，不构成买卖点。
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

/* ── 市场宽度图（从基本面叠图搬来的口径：3条宽度线 + 20/80 阈值 + 色带） ── */
function MarketBreadthChart({ marketId, height = 250 }: { marketId: "CN_ALL_A" | "SP500"; height?: number }) {
  const ref = useRef<HTMLDivElement>(null);
  const { data, isLoading } = useQuery({
    queryKey: ["sentBreadthHistory", marketId],
    queryFn: () => api.marketContextBreadthHistory(marketId, 1260),
    staleTime: 12 * 3600_000,
    retry: 1,
  });
  const hist = useMemo(() => data?.history ?? [], [data]);

  useEffect(() => {
    if (!ref.current || hist.length < 2) return;
    const inst = echarts.init(ref.current, undefined, { renderer: "canvas" });
    const ro = new ResizeObserver(() => inst.resize());
    ro.observe(ref.current);
    const dates = hist.map((p) => p.date);
    inst.setOption({
      animation: false,
      grid: { left: 44, right: 16, top: 26, bottom: 44 },
      tooltip: {
        trigger: "axis",
        valueFormatter: (v: unknown) => (v == null ? "—" : `${Number(v).toFixed(1)}%`),
        order: "valueDesc",
      },
      legend: { top: 0, textStyle: { fontSize: 11 }, itemWidth: 16 },
      xAxis: { type: "category", data: dates, axisLabel: { fontSize: 10 } },
      yAxis: { type: "value", min: 0, max: 100, name: "占比%", nameTextStyle: { fontSize: 10 } },
      dataZoom: [
        { type: "inside", start: Math.max(0, 100 - (500 / dates.length) * 100), end: 100 },
        { type: "slider", height: 14, bottom: 8 },
      ],
      series: [
        {
          name: "50日宽度", type: "line", data: hist.map((p) => p.breadth_50), showSymbol: false,
          lineStyle: { width: 2.4, color: "#2563eb" }, itemStyle: { color: "#2563eb" }, z: 5,
          markLine: {
            silent: true, symbol: "none", label: { fontSize: 10, position: "insideEndTop" },
            data: [
              { yAxis: 80, lineStyle: { color: "#d24a43", type: "dashed" }, label: { formatter: "压力位 80%", color: "#d24a43" } },
              { yAxis: 20, lineStyle: { color: "#15803d", type: "dashed" }, label: { formatter: "机会位 20%", color: "#15803d" } },
            ],
          },
          markArea: {
            silent: true,
            data: [
              [{ yAxis: 80, itemStyle: { color: "rgba(210,74,67,0.07)" } }, { yAxis: 100 }],
              [{ yAxis: 0, itemStyle: { color: "rgba(21,128,61,0.07)" } }, { yAxis: 20 }],
            ],
          },
        },
        {
          name: "20日宽度", type: "line", data: hist.map((p) => p.breadth_20), showSymbol: false,
          lineStyle: { width: 1, color: "#9aa4b2", opacity: 0.7 }, itemStyle: { color: "#9aa4b2" },
        },
        {
          name: "200日宽度", type: "line", data: hist.map((p) => p.breadth_200), showSymbol: false,
          lineStyle: { width: 1, type: "dashed", color: "#b45309", opacity: 0.75 }, itemStyle: { color: "#b45309" },
        },
      ],
    });
    return () => {
      ro.disconnect();
      inst.dispose();
    };
  }, [hist]);

  if (isLoading) return <div className="muted" style={{ height, display: "grid", placeItems: "center" }}>宽度历史加载中…</div>;
  if (hist.length < 2) return <div className="muted" style={{ height, display: "grid", placeItems: "center" }}>宽度历史暂不可用</div>;
  return <div ref={ref} style={{ width: "100%", height }} />;
}

/* ── 0–100 位置条：色带标机会/常态/压力区，游标 = 当前 b50 ── */
function PositionBar({ b50 }: { b50: number }) {
  return (
    <div className="sb-posbar" title={`板块内 ${b50.toFixed(0)}% 的股票站上半年线（50日均线）`}>
      <div className="sb-posbar-mark" style={{ left: `${Math.min(100, Math.max(0, b50))}%` }} />
      <span className="sb-posbar-tick" style={{ left: "20%" }} />
      <span className="sb-posbar-tick" style={{ left: "80%" }} />
    </div>
  );
}

const STAGE_TONE: Record<string, string> = {
  上涨: "up", 派发: "warn", 下跌: "down", 筑底: "info",
  领先大盘: "up", 落后大盘: "down", 与大盘同步: "neutral",
};
function StageBadge({ stageCn }: { stageCn: string }) {
  // stage_cn 可能带括号后缀（"派发（冲高回落）"），按前缀匹配色调
  const key = Object.keys(STAGE_TONE).find((k) => stageCn.startsWith(k));
  const tone = key ? STAGE_TONE[key] : undefined;
  if (!tone) return <span className="macro-chip neutral">阶段待定</span>;
  const cls = tone === "up" ? "opportunity" : tone === "down" ? "danger" : tone === "warn" ? "caution" : tone === "info" ? "info" : "neutral";
  return <span className={`macro-chip ${cls}`}>{stageCn}</span>;
}

function ZoneChip({ zone }: { zone: SectorBoardRow["zone"] }) {
  if (zone === "opportunity") return <span className="macro-chip info">机会位</span>;
  if (zone === "risk") return <span className="macro-chip danger">压力位</span>;
  return <span className="macro-chip neutral">常态区</span>;
}

/** 系统术语轻度人话化：SMA60/EMA20 → 60日/20日均线（阶段体系语言保留）。 */
function humanize(text: string): string {
  return text.replace(/SMA60/g, "60日均线").replace(/EMA20/g, "20日均线");
}

/* ── 板块卡（A股持仓卡与美股行业卡共用；pctLabel 区分口径） ── */
function BoardCard({ b, onOpen, pctLabel = "今日" }: { b: SectorBoardRow; onOpen: () => void; pctLabel?: string }) {
  return (
    <div
      className={`sb-hold-card clickable${b.zone === "risk" ? " z-risk" : b.zone === "opportunity" ? " z-opp" : ""}`}
      onClick={onOpen}
      title="点开：价格 × 情绪对照图"
    >
      <div className="sb-card-head">
        <b>{b.name}</b>
        {b.etf && <span className="mood-etf-badge">{b.etf}</span>}
        <StageBadge stageCn={b.stage_cn} />
        {b.sig_heat_alarm && <span className="macro-chip danger">⚠散户过热</span>}
        {b.sig_icepoint_pick && <span className="macro-chip info">❄冰点关注</span>}
      </div>
      <div className="sb-big-row">
        <span className="sb-big-num">{b.b50.toFixed(0)}<i>%</i></span>
        <ZoneChip zone={b.zone} />
        <span className="muted sb-pct">{b.pct_change != null ? `${b.pct_change > 0 ? "+" : ""}${b.pct_change.toFixed(1)}% ${pctLabel}` : ""}</span>
      </div>
      <PositionBar b50={b.b50} />
      <div className="sb-next">
        {humanize(b.sig_note_cn ?? b.next_watch ?? `${b.member_count ?? "?"} 只成分股 · 点卡片看对照图`)}
      </div>
    </div>
  );
}

// 兼容旧引用（A股持仓区）
const HoldingBoardCard = BoardCard;

/* ── 推荐观察卡 ── */
const REC_META: Record<SectorRecommendation["kind"], { icon: string; label: string; cls: string }> = {
  opportunity: { icon: "💰", label: "机会位", cls: "info" },
  risk: { icon: "⚠", label: "压力位", cls: "danger" },
  upgrade_watch: { icon: "📈", label: "接近转强", cls: "neutral" },
};

function RecommendationCard({ r, watched, onToggle, onOpen }: {
  r: SectorRecommendation; watched: boolean; onToggle: () => void; onOpen: () => void;
}) {
  const meta = REC_META[r.kind];
  return (
    <div
      className={`sb-rec-card clickable${watched ? " watched" : ""}`}
      onClick={onOpen}
      title="点开：价格 × 情绪对照图"
    >
      <div className="sb-card-head">
        <b>{meta.icon} {r.name}</b>
        <span className={`macro-chip ${meta.cls}`}>{meta.label}</span>
        {r.holding && <span className="mood-hold-tag">持仓相关</span>}
        <span className="spacer" />
        <button
          type="button"
          className={`btn mini${watched ? "" : " primary"}`}
          onClick={(e) => { e.stopPropagation(); onToggle(); }}
        >
          {watched ? "✓ 已观察 · 移除" : "+ 加入观察"}
        </button>
      </div>
      <div className="sb-rec-body">{r.reason_cn}</div>
      <div className="sb-rec-meta">强度指标 {r.b50.toFixed(0)}% · 阶段{r.stage_cn}</div>
    </div>
  );
}

/* ── 全部大板块排行图（横向条形 + 20/80 阈值线 + 持仓/观察高亮） ── */
function AllBoardsChart({ boards, watch, onOpen, height = 560 }: {
  boards: SectorBoardRow[]; watch: Set<string>; onOpen: (b: SectorBoardRow) => void; height?: number;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const sorted = useMemo(() => [...boards].sort((a, b) => b.b50 - a.b50), [boards]);

  useEffect(() => {
    if (!ref.current || sorted.length === 0) return;
    const inst = echarts.init(ref.current, undefined, { renderer: "canvas" });
    const ro = new ResizeObserver(() => inst.resize());
    ro.observe(ref.current);
    const onBarClick = (params: { dataIndex?: number }) => {
      const b = sorted[params.dataIndex ?? -1];
      if (b) onOpen(b);
    };
    inst.on("click", onBarClick);
    inst.setOption({
      animation: false,
      grid: { left: 6, right: 40, top: 10, bottom: 40, containLabel: true },
      tooltip: {
        trigger: "item",
        formatter: (p: { dataIndex: number }) => {
          const b = sorted[p.dataIndex];
          if (!b) return "";
          return [
            `<b>${b.name}</b>${b.holding ? " · 持仓相关" : ""}${watch.has(b.code) ? " · ★已观察" : ""}`,
            `强度：${b.b50.toFixed(0)}%（站上半年线的股票占比）`,
            `阶段：${b.stage_cn} · 今日 ${b.pct_change != null ? `${b.pct_change > 0 ? "+" : ""}${b.pct_change.toFixed(1)}%` : "—"}`,
            b.sig_note_cn ?? b.next_watch ?? "",
          ].filter(Boolean).join("<br/>");
        },
      },
      xAxis: {
        type: "value", min: 0, max: 100,
        axisLabel: { fontSize: 10, formatter: "{value}%" },
        splitLine: { lineStyle: { color: "rgba(0,0,0,0.05)" } },
      },
      yAxis: {
        type: "category", inverse: true,
        data: sorted.map((b) => b.name + (b.holding ? "（持）" : watch.has(b.code) ? " ★" : "")),
        axisLabel: { fontSize: 10.5 },
      },
      dataZoom: [{ type: "slider", orient: "vertical", right: 6, start: 0, end: Math.min(100, (34 / sorted.length) * 100) }],
      series: [{
        type: "bar",
        data: sorted.map((b) => ({
          value: b.b50,
          itemStyle: {
            color: watch.has(b.code) ? "#0891b2"
              : b.zone === "opportunity" ? "#4d7fc4"
              : b.zone === "risk" ? "#d24a43"
              : b.holding ? "#2563eb" : "#c3cad4",
            borderColor: b.holding ? "#1e40af" : "transparent",
            borderWidth: b.holding ? 1.4 : 0,
            borderRadius: 2,
          },
        })),
        barMaxWidth: 15,
        label: { show: true, position: "right", fontSize: 10, formatter: (p: { value: number }) => `${Number(p.value).toFixed(0)}` },
        markLine: {
          silent: true, symbol: "none",
          label: { fontSize: 10, position: "end", rotate: 0 },
          lineStyle: { type: "dashed" },
          data: [
            { xAxis: 20, lineStyle: { color: "#15803d" }, label: { formatter: "机会位20", color: "#15803d" } },
            { xAxis: 80, lineStyle: { color: "#d24a43" }, label: { formatter: "压力位80", color: "#d24a43" } },
          ],
        },
        z: 3,
      }],
    });
    return () => {
      inst.off("click", onBarClick);
      ro.disconnect();
      inst.dispose();
    };
  }, [sorted, watch, onOpen]);

  return <div ref={ref} style={{ width: "100%", height }} />;
}

/* ── 主区块 ── */
export default function SentimentSectorBlock({ view, heatAvailable, heatHint }: {
  view: SectorBoardsView; heatAvailable: boolean; heatHint: string;
}) {
  const { watch, toggle } = useWatchBoards();
  const [breadthTab, setBreadthTab] = useState<"CN_ALL_A" | "SP500">("CN_ALL_A");
  const [openBoard, setOpenBoard] = useState<{ code: string; name: string } | null>(null);
  const holdings = useMemo(() => view.boards.filter((b) => b.holding).sort((a, b) => b.b50 - a.b50), [view.boards]);
  const watchedBoards = useMemo(
    () => view.boards.filter((b) => watch.has(b.code)).sort((a, b) => b.b50 - a.b50),
    [view.boards, watch],
  );
  const open = (b: { code: string; name: string }) => setOpenBoard(b);

  if (!view.available) {
    return (
      <section className="sx-rail-card" style={{ marginTop: 14 }}>
        <div className="sx-rail-head"><span className="sx-rail-title">板块情绪</span></div>
        <div className="muted">板块快照暂不可用（收盘后预计算未运行？）。</div>
      </section>
    );
  }

  return (
    <section className="sx-rail-card sb-main" style={{ marginTop: 14 }}>
      <div className="sx-rail-head">
        <span className="sx-rail-title">板块情绪</span>
        <span className="sx-rail-sub">
          大板块（成分股≥30只）· 更新 {view.as_of ?? "—"} · 强度 = 板块内站上半年线的股票占比
        </span>
      </div>

      {/* 市场宽度图（基本面叠图同款口径搬过来） */}
      <div className="sb-breadth-block">
        <div className="sb-breadth-head">
          <span className="sb-sub-title">整体市场冷热（宽度图）</span>
          <button type="button" className={`ma-toggle${breadthTab === "CN_ALL_A" ? " on" : ""}`} onClick={() => setBreadthTab("CN_ALL_A")}>全A</button>
          <button type="button" className={`ma-toggle${breadthTab === "SP500" ? " on" : ""}`} onClick={() => setBreadthTab("SP500")}>标普500</button>
        </div>
        <MarketBreadthChart marketId={breadthTab} />
        <div className="muted mood-note">
          怎么看：蓝线 = 站上半年线的股票占比。掉进绿区（≤20%，超卖）历史常对应阶段底部、
          冲进红区（≥80%，过热）常对应阶段顶部。虚线是 20/80 阈值；灰/橙细线是 20日/200日口径。
        </div>
      </div>

      {/* 持仓相关板块（优先展示） */}
      <div className="sb-sub-title" style={{ marginTop: 14 }}>持仓相关板块（{holdings.length} 个 · 点卡片看对照图）</div>
      <div className="sb-hold-grid">
        {holdings.map((b) => <HoldingBoardCard key={b.code} b={b} onOpen={() => open(b)} />)}
      </div>

      {/* 我的观察（用户自己选的） */}
      {watchedBoards.length > 0 && (
        <>
          <div className="sb-sub-title" style={{ marginTop: 14 }}>我的观察（{watchedBoards.length} 个 · 自己选的，可随时移除 · 点卡片看对照图）</div>
          <div className="sb-hold-grid">
            {watchedBoards.map((b) => (
              <div key={b.code} className="sb-hold-card watched-card clickable" onClick={() => open(b)} title="点开：价格 × 情绪对照图">
                <div className="sb-card-head">
                  <b>★ {b.name}</b>
                  <StageBadge stageCn={b.stage_cn} />
                  <span className="spacer" />
                  <button type="button" className="btn mini" onClick={(e) => { e.stopPropagation(); toggle(b.code); }}>移除</button>
                </div>
                <div className="sb-big-row">
                  <span className="sb-big-num">{b.b50.toFixed(0)}<i>%</i></span>
                  <ZoneChip zone={b.zone} />
                </div>
                <PositionBar b50={b.b50} />
                <div className="sb-next">{humanize(b.sig_note_cn ?? b.next_watch ?? "")}</div>
              </div>
            ))}
          </div>
        </>
      )}

      {/* 推荐观察（阈值触发，用户决定加不加） */}
      <div className="sb-sub-title" style={{ marginTop: 14 }}>
        推荐观察（{view.recommendations.length} 条 · 按阈值筛选，是否关注由你定）
      </div>
      {view.recommendations.length === 0 ? (
        <div className="muted" style={{ padding: "4px 2px" }}>当前没有触发阈值的板块（既没有跌进机会位的，也没有冲进压力位派发的）。</div>
      ) : (
        <div className="sb-rec-list">
          {view.recommendations.map((r) => (
            <RecommendationCard
              key={`${r.kind}-${r.code}`}
              r={r}
              watched={watch.has(r.code)}
              onToggle={() => toggle(r.code)}
              onOpen={() => open(r)}
            />
          ))}
        </div>
      )}

      {/* 全部大板块排行 */}
      <div className="sb-sub-title" style={{ marginTop: 16 }}>
        全部大板块排行（{view.n_boards} 个 · 强度从高到低 · 蓝边=持仓相关 · ★=我的观察 · 点柱子看对照图）
      </div>
      <AllBoardsChart boards={view.boards} watch={watch} onOpen={open} />

      <div className="muted mood-note">
        {view.zone_note_cn}
        {!heatAvailable && ` · ${heatHint}`}
      </div>

      {openBoard && (
        <BoardChartDrawer
          code={openBoard.code}
          name={openBoard.name}
          onClose={() => setOpenBoard(null)}
        />
      )}
    </section>
  );
}

/* ══════════════ 美股板块情绪（11 GICS 行业，对标 A股，2026-09-07） ══════════════ */
export function UsSectorBlock({ view }: { view: SectorBoardsView }) {
  const { watch, toggle } = useWatchBoards();
  const [openBoard, setOpenBoard] = useState<{ code: string; name: string } | null>(null);
  const boards = useMemo(() => [...view.boards].sort((a, b) => b.b50 - a.b50), [view.boards]);
  const watched = useMemo(
    () => boards.filter((b) => watch.has(b.code)),
    [boards, watch],
  );
  const open = (b: { code: string; name: string }) => setOpenBoard(b);

  if (!view.available) {
    return (
      <section className="sx-rail-card" style={{ marginTop: 14 }}>
        <div className="sx-rail-head">
          <span className="sx-rail-title">美股板块情绪</span>
          <span className="sx-rail-sub">数据待生成（scripts/precompute_us_sector_breadth.py）</span>
        </div>
      </section>
    );
  }

  return (
    <section className="sx-rail-card sb-main" style={{ marginTop: 14 }}>
      <div className="sx-rail-head">
        <span className="sx-rail-title">美股板块情绪</span>
        <span className="sx-rail-sub">
          11 个行业（标普500成分股）· 更新 {view.as_of ?? "—"} · 强度 = 行业内站上半年线的股票占比
        </span>
      </div>

      {/* 全部行业卡（点开看对照图） */}
      <div className="sb-sub-title" style={{ marginTop: 4 }}>全部行业（点卡片看「价格 × 情绪」对照图）</div>
      <div className="sb-hold-grid">
        {boards.map((b) => (
          <BoardCard key={b.code} b={b} onOpen={() => open(b)} pctLabel="近20日" />
        ))}
      </div>

      {/* 我的观察 */}
      {watched.length > 0 && (
        <>
          <div className="sb-sub-title" style={{ marginTop: 14 }}>我的观察（{watched.length} 个 · 与 A股共用观察列表）</div>
          <div className="sb-hold-grid">
            {watched.map((b) => (
              <div key={b.code} className="sb-hold-card watched-card clickable" onClick={() => open(b)} title="点开：价格 × 情绪对照图">
                <div className="sb-card-head">
                  <b>★ {b.name}</b>
                  {b.etf && <span className="mood-etf-badge">{b.etf}</span>}
                  <StageBadge stageCn={b.stage_cn} />
                  <span className="spacer" />
                  <button type="button" className="btn mini" onClick={(e) => { e.stopPropagation(); toggle(b.code); }}>移除</button>
                </div>
                <div className="sb-big-row">
                  <span className="sb-big-num">{b.b50.toFixed(0)}<i>%</i></span>
                  <ZoneChip zone={b.zone} />
                </div>
                <PositionBar b50={b.b50} />
              </div>
            ))}
          </div>
        </>
      )}

      {/* 推荐观察 */}
      <div className="sb-sub-title" style={{ marginTop: 14 }}>
        推荐观察（{view.recommendations.length} 条 · 阈值触发，是否关注由你定）
      </div>
      {view.recommendations.length === 0 ? (
        <div className="muted" style={{ padding: "4px 2px" }}>当前没有行业触发阈值。</div>
      ) : (
        <div className="sb-rec-list">
          {view.recommendations.map((r) => (
            <RecommendationCard
              key={`${r.kind}-${r.code}`}
              r={r}
              watched={watch.has(r.code)}
              onToggle={() => toggle(r.code)}
              onOpen={() => open(r)}
            />
          ))}
        </div>
      )}

      {/* 强度排行 */}
      <div className="sb-sub-title" style={{ marginTop: 16 }}>
        行业强度排行（强→弱 · ★=我的观察 · 点柱子看对照图）
      </div>
      <AllBoardsChart boards={boards} watch={watch} onOpen={open} height={380} />

      <div className="muted mood-note">
        {view.zone_note_cn}
        · 散户维度说明：美股没有分档资金流数据，散户情绪看上方 AAII/NAAIM 问卷卡；本区看行业间强弱与拥挤度。
      </div>

      {openBoard && (
        <BoardChartDrawer
          code={openBoard.code}
          name={openBoard.name}
          us
          onClose={() => setOpenBoard(null)}
        />
      )}
    </section>
  );
}
