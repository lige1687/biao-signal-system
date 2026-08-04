import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useCallback, useMemo, useRef, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import AssessmentPanel from "../components/AssessmentPanel";
import ColorBadge from "../components/ColorBadge";
import ChartControls from "../components/ChartControls";
import ColorBacktestPanel from "../components/ColorBacktestPanel";
import PullbackBacktestPanel from "../components/PullbackBacktestPanel";
import PullbackOpportunityPanel from "../components/PullbackOpportunityPanel";
import ExplanationPanel, { type Selection } from "../components/ExplanationPanel";
import TradeOpportunityPanel from "../components/TradeOpportunityPanel";
import KlineChart, {
  DEFAULT_DISPLAY,
  type ChartDisplay,
  type MarkPick,
} from "../components/KlineChart";
import type { Explanation, StructureBrief, SymbolDetail } from "../types";

const MARK_SOURCE_CN: Record<MarkPick["kind"], string> = {
  bottom_mark: "图上标记 · 底部结构确认",
  top_mark: "图上标记 · 顶部结构确认",
  invalidated_mark: "图上标记 · 结构失效",
  key_volatility: "图上标记 · 关键性波动",
  b1_line: "图上参考线 · B1 第一阻力",
  bottom_line: "图上参考线 · C 点失效线",
  top_line: "图上参考线 · 顶部颈线",
};

/** 横线类点击（B1 / C 点 / 颈线）：只有价位，没有日期。 */
const LINE_KINDS: ReadonlySet<MarkPick["kind"]> = new Set([
  "b1_line",
  "bottom_line",
  "top_line",
]);

/** 把点击的标记解析成右侧面板要显示的内容。 */
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
  } else if (LINE_KINDS.has(pick.kind)) {
    // 横线优先解释「这条线是什么」（B1 / C 点 / 颈线概念），
    // 而不是它所属结构的形态——用户点的是线，不是菱形。
    explanation = detail.concepts[detail.mark_concepts[pick.kind] ?? ""] ?? null;
  } else {
    explanation =
      structure?.explanation ??
      detail.concepts[detail.mark_concepts[pick.kind] ?? ""] ??
      null;
  }

  // 相关事件不在此处过滤：详情只带最近 60 条，点多年前的标记会得到空列表。
  // 改由 DetailPage 按 structure_id / 日期向 /events 端点按需查询后回填。
  return {
    source,
    date: pick.date,
    price: pick.price ?? pick.level,
    explanation,
    structure,
    b1PivotDate: pick.pivotDate ?? undefined,
    b1DistancePct: pick.distancePct ?? undefined,
    events: undefined,
    eventsLoading: true,
  };
}

export default function DetailPage() {
  const { symbol = "" } = useParams();
  const queryClient = useQueryClient();
  const [selection, setSelection] = useState<Selection | null>(null);
  // 标记默认全关（见 DEFAULT_DISPLAY）：历史标记可达数百个，会严重干扰看盘。
  const [display, setDisplay] = useState<ChartDisplay>(DEFAULT_DISPLAY);
  // KlineChart 把「下载当前图为 PNG」的闭包回传到这里，按钮点的时候调它
  const downloadPngRef = useRef<(() => void) | null>(null);

  const { data, isLoading, error, isFetching } = useQuery({
    queryKey: ["detail", symbol],
    queryFn: () => api.detail(symbol),
    enabled: Boolean(symbol),
  });

  const onPick = useCallback(
    (pick: MarkPick) => {
      if (!data) return;
      const base = resolveSelection(pick, data);
      setSelection(base);

      // 按需拉该结构/该日的绑定事件（全量 4800+ 条不能塞进详情响应）
      const opts: { structureId?: string; onDate?: string; ruleId?: string; limit?: number } =
        pick.kind === "key_volatility"
          ? { onDate: pick.date, ruleId: "lei_color", limit: 20 }
          : { structureId: pick.structureId, limit: 30 };
      // B1 线不属于任何结构，无可查事件；直接给空列表，不发无意义请求。
      if (!opts.structureId && !opts.onDate) {
        setSelection({ ...base, events: [], eventsLoading: false });
        return;
      }
      api
        .events(symbol, opts)
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
    [data, symbol],
  );

  const doRefresh = async () => {
    const fresh = await api.detail(symbol, true);
    queryClient.setQueryData(["detail", symbol], fresh);
    queryClient.invalidateQueries({ queryKey: ["cards"] });
    setSelection(null);
  };

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

  const counts = useMemo(() => {
    const c = data?.chart;
    return {
      bottomMarks: c ? c.bottomMarks.length : 0,
      topMarks: c ? c.topMarks.length : 0,
      invalidatedMarks: c ? c.invalidatedMarks.length : 0,
      keyVolatility: c ? c.keyVolatility.length : 0,
      levels: c ? (c.b1Line ? 1 : 0) + c.bottomLines.length + c.topLines.length : 0,
    };
  }, [data]);

  /** 点徽章也能看解释（颜色/阶段/风险/生命周期）。 */
  const pickConcept = (key: string, sourceCn: string) => {
    if (!data) return;
    const explanation = data.concepts[key] ?? null;
    setSelection({ source: sourceCn, explanation, events: [], eventsLoading: false });
  };

  return (
    <div className="page detail-page">
      <div className="detail-header">
        <Link to="/">← 返回看盘</Link>
        {data && (
          <>
            <h1>{data.display_name}</h1>
            <span style={{ color: "var(--text-faint)", fontSize: 11 }}>{data.symbol}</span>
            {data.market_cn && <span className="tag">{data.market_cn}</span>}
            <span className={`price ${changeCls}`}>
              {lastClose != null ? lastClose.toFixed(2) : "--"}
            </span>
            <span className={`change ${changeCls}`}>
              {changePct != null ? `${changePct > 0 ? "+" : ""}${changePct.toFixed(2)}%` : "--"}
            </span>
            <span
              onClick={() => pickConcept("signal_color", "徽章 · LEI 颜色")}
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
            <span style={{ flex: 1 }} />
            <span style={{ color: "var(--text-faint)", fontSize: 12 }}>
              数据时间{" "}
              {data.meta.data_time
                ? new Date(data.meta.data_time).toLocaleString("zh-CN", { hour12: false })
                : "--"}{" "}
              · {data.meta.is_intraday_forming ? "盘中" : "已收盘"}
              {data.meta.cache_fallback_used && " · 缓存兜底"}
            </span>
            <button className="btn" disabled={isFetching} onClick={doRefresh}>
              {isFetching ? "刷新中…" : "刷新"}
            </button>
          </>
        )}
      </div>

      {error && (
        <div className="error-banner">
          加载失败：{error instanceof Error ? error.message : String(error)}
          <div style={{ marginTop: 8 }}>
            <Link to="/">← 返回看盘</Link>
          </div>
        </div>
      )}
      {isLoading && <div className="loading">正在分析 {symbol} …</div>}

      {data && (
        <>
          {data.meta.persist_warning && (
            <div className="panel" style={{ borderColor: "var(--warn)", marginBottom: 12 }}>
              <span className="stale-chip">未写入研究库</span>{" "}
              <span className="muted">
                本次分析结果正常展示，但研究库拒绝写入（事件身份字段与历史记录冲突）。
                信号解释可照常参考；研究统计需另行排查该标的历史入库数据。
              </span>
            </div>
          )}

          {/* 主区：左图右解释。图是主角，解释按需展开，两者并列不遮挡。 */}
          <div className="detail-main">
            <div className="kline-wrap">
              <ChartControls
                display={display}
                onChange={setDisplay}
                counts={counts}
                onDownloadPng={() => downloadPngRef.current?.()}
              />
              <KlineChart
                payload={data.chart}
                display={display}
                onPick={onPick}
                onDownload={(fn) => (downloadPngRef.current = fn)}
              />
              <div className="chart-legend">
                {display.bottomMarks && (
                  <span>
                    <span className="mk mk-bottom">◆</span> 底部确认
                  </span>
                )}
                {display.topMarks && (
                  <span>
                    <span className="mk mk-top">◆</span> 顶部确认
                  </span>
                )}
                {display.invalidatedMarks && (
                  <span>
                    <span className="mk mk-dead">✕</span> 结构失效
                  </span>
                )}
                {display.keyVolatility && (
                  <span>
                    <span className="mk mk-kv">▲</span> 关键性波动
                  </span>
                )}
                {display.levels && (
                  <>
                    <span>
                      <span className="mk mk-b1">●</span> B1 阻力线
                    </span>
                    <span>
                      <span className="mk mk-cline">●</span> C 点失效线
                    </span>
                    <span>
                      <span className="mk mk-neck">●</span> 顶部颈线
                    </span>
                  </>
                )}
                {display.colorMode === "lei_state" && (
                  <span className="muted">
                    LEI 着色模式：K 线颜色 = 当日绿/灰/黑状态（实体不再分空心/实心）
                  </span>
                )}
                <span className="muted">
                  {display.bottomMarks ||
                  display.topMarks ||
                  display.invalidatedMarks ||
                  display.keyVolatility ||
                  display.levels
                    ? "点标记或线右端圆点 → 右侧看解释"
                    : "信号标记默认隐藏，按上方开关按需显示"}
                </span>
              </div>
            </div>

            <ExplanationPanel selection={selection} onClose={() => setSelection(null)} />
          </div>

          <TradeOpportunityPanel
            opportunities={data.assessment.trade_opportunities}
            onSelect={setSelection}
          />

          <PullbackOpportunityPanel
            opportunities={data.assessment.pullback_opportunities}
            onSelect={setSelection}
          />

          {/* 当前观察保留在图下方：它是「今天怎么看」的总结，不是逐点明细。 */}
          <AssessmentPanel
            assessment={data.assessment}
            onPickConcept={(key, src) => pickConcept(key, src)}
          />

          {data.first_ma_pullback_backtest && (
            <PullbackBacktestPanel report={data.first_ma_pullback_backtest} />
          )}

          {data.color_backtest && <ColorBacktestPanel report={data.color_backtest} />}

          {data.new_events.length > 0 && (
            <div className="panel">
              <h3>今日新事件（{data.new_events.length}）</h3>
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
          )}

          <div className="disclaimer">
            {data.disclaimer_cn}
            <div style={{ marginTop: 6 }}>{data.meta.calendar_note_cn}</div>
          </div>
        </>
      )}
    </div>
  );
}
