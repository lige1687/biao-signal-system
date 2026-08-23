import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type {
  BreadthHistoryPoint,
  MarketContextSnapshot,
} from "../types";

interface Props {
  symbol: string;
  onPickConcept?: (key: string, sourceCn: string) => void;
}

// 行业通用宽度参考线：20% 机会位 / 50% 多空分界 / 80% 压力位
// （TradingView 宽度脚本、marketinout %Above50MA、thetrading.tools 等 quant 框架标准）
const RESEARCH_LINES = [20, 50, 80];

const DATA_STATUS_CN: Record<string, string> = {
  complete: "数据完整",
  incomplete: "数据不完整",
  conflict: "数据冲突",
  stale: "数据陈旧",
  unavailable: "数据不可用",
};

const DIRECTION_CN: Record<string, string> = {
  expanding: "扩张",
  contracting: "收缩",
  diverging: "分化",
  unknown: "未知",
};

const REGIME_CN: Record<string, string> = {
  bull: "偏多",
  bear: "偏空",
  unknown: "未知",
};

const HEAT_CN: Record<string, string> = {
  extreme_cold: "极冷",
  cold: "偏冷",
  neutral: "中性",
  hot: "偏热",
  extreme_hot: "过热",
  unknown: "未知",
};

function fmtPct(v: number | null | undefined, digits = 1): string {
  if (v == null) return "--";
  return `${v.toFixed(digits)}%`;
}

function fmtSigned(v: number | null | undefined, digits = 1): string {
  if (v == null) return "--";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(digits)}%`;
}

function fmtDrawdown(v: number | null | undefined): string {
  if (v == null) return "--";
  return `${(v * 100).toFixed(1)}%`;
}

/**
 * Market breadth panel — three sections:
 *   1. Snapshot grid: per-market breadth, deltas, coverage, regime, heat, drawdown
 *   2. 120-day trend chart with 20/50/80 research reference lines
 *   3. Provenance + updated_at
 *
 * `incomplete` / `stale` / `conflict` are always surfaced on the panel
 * (never silently absorbed) and a fixed disclaimer at the bottom states
 * that market context does NOT change the symbol's LEI signal stage.
 */
export default function MarketBreadthPanel({ symbol, onPickConcept }: Props) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["marketContextFull", symbol],
    queryFn: () => api.marketContextFull(symbol),
    enabled: Boolean(symbol),
    staleTime: 60_000,
  });

  const primary = data?.snapshots?.[0];

  const allUnknown = Boolean(
    data && primary && primary.breadth_20 == null && primary.breadth_50 == null,
  );

  return (
    <div className="panel market-breadth-panel">
      <h3>
        市场宽度
        {data && (
          <span className={`data-status-chip status-${data.data_status}`}>
            {DATA_STATUS_CN[data.data_status] ?? data.data_status}
          </span>
        )}
      </h3>
      {isLoading && <div className="loading">正在加载市场宽度…</div>}
      {error && <div className="error-banner">市场宽度加载失败</div>}
      {data && primary && allUnknown && (
        <div className="breadth-unknown">
          <div className="muted">
            当前参考市场未在 LEI 实验室入库（{primary.market_id}），所以没有真实成分股行情。
          </div>
          {data.reasons_cn.length > 0 && (
            <ul className="breadth-reason-list">
              {data.reasons_cn.map((r) => <li key={r}>{r}</li>)}
            </ul>
          )}
          {data.conflicts_cn.length > 0 && (
            <ul className="breadth-conflict-list">
              {data.conflicts_cn.map((c) => <li key={c}>{c}</li>)}
            </ul>
          )}
        </div>
      )}
      {data && primary && !allUnknown && (
        <>
          <SnapshotGrid
            snapshot={primary}
            onPickConcept={onPickConcept}
          />
          <BreadthTrendChart symbol={symbol} />
          {primary.divergence_events.length > 0 && (
            <div className="breadth-divergence-row">
              <span className="muted">指数/宽度背离：</span>
              {primary.divergence_events.map((e) => (
                <span
                  key={e.event_type}
                  className={`divergence-chip ${
                    e.event_type === "negative_breadth_divergence" ? "negative" : "positive"
                  }`}
                  onClick={() => onPickConcept?.(
                    e.event_type,
                    `图例 · 背离事件 ${e.event_type}`,
                  )}
                >
                  {e.event_type === "negative_breadth_divergence"
                    ? "指数涨但宽度收缩（少数标的领涨）"
                    : "指数跌但宽度扩张（少数标的领跌）"}
                </span>
              ))}
            </div>
          )}
          {data.reasons_cn.length > 0 && (
            <div className="factor-list reasons">
              <ul>
                {data.reasons_cn.map((r) => (
                  <li key={r}>{r}</li>
                ))}
              </ul>
            </div>
          )}
          {data.conflicts_cn.length > 0 && (
            <div className="factor-list conflicts">
              <ul>
                {data.conflicts_cn.map((c) => (
                  <li key={c}>{c}</li>
                ))}
              </ul>
            </div>
          )}
          <div className="breadth-provenance muted">
            <span>
              数据来源：{data.source_kind}
              {data.provenance && ` / ${data.provenance}`}
            </span>
            <span>更新时间：{new Date(data.updated_at).toLocaleString("zh-CN", { hour12: false })}</span>
          </div>
          <div className="breadth-disclaimer">
            市场环境不改变该技术信号阶段。
          </div>
        </>
      )}
    </div>
  );
}

function SnapshotGrid({
  snapshot,
  onPickConcept,
}: {
  snapshot: MarketContextSnapshot;
  onPickConcept?: (key: string, sourceCn: string) => void,
}) {
  return (
    <div className="breadth-snapshot-grid">
      <div className="breadth-snapshot-header">
        <span
          className="metric-label"
          onClick={() => onPickConcept?.("market_id", "市场宽度 · 参考市场")}
        >
          参考市场
        </span>
        <strong>{snapshot.market_id}</strong>
        <span className="muted">共 {snapshot.constituent_count} 只成分股</span>
      </div>

      <div className="breadth-metric-row">
        <Metric
          label="Breadth20 (MA20 上方占比)"
          value={fmtPct(snapshot.breadth_20)}
          delta={fmtSigned(snapshot.breadth_20_delta_5)}
          coverage={fmtPct(snapshot.coverage_20 * 100, 0)}
          conceptKey="breadth_20"
          onPick={onPickConcept}
        />
        <Metric
          label="Breadth50 (MA50 上方占比)"
          value={fmtPct(snapshot.breadth_50)}
          delta={fmtSigned(snapshot.breadth_50_delta_5)}
          coverage={fmtPct(snapshot.coverage_50 * 100, 0)}
          conceptKey="breadth_50"
          onPick={onPickConcept}
        />
        <Metric
          label="Breadth200 (MA200 上方占比)"
          value={fmtPct(snapshot.breadth_200)}
          delta={fmtSigned(snapshot.breadth_200_delta_20, 1)}
          coverage={fmtPct(snapshot.coverage_200 * 100, 0)}
          conceptKey="breadth_200"
          onPick={onPickConcept}
        />
      </div>

      <div className="breadth-metric-row">
        <SmallMetric
          label="5日方向"
          value={DIRECTION_CN[snapshot.breadth_direction] ?? snapshot.breadth_direction}
          conceptKey="breadth_direction"
          onPick={onPickConcept}
        />
        <SmallMetric
          label="长期底色 (Breadth200)"
          value={REGIME_CN[snapshot.long_regime] ?? snapshot.long_regime}
          conceptKey="long_regime"
          onPick={onPickConcept}
        />
        <SmallMetric
          label="市场热度"
          value={HEAT_CN[snapshot.heat_state] ?? snapshot.heat_state}
          conceptKey="heat_state"
          onPick={onPickConcept}
        />
        <SmallMetric
          label="指数回撤 (ATH)"
          value={fmtDrawdown(snapshot.drawdown_from_ath)}
          conceptKey="drawdown_from_ath"
          onPick={onPickConcept}
        />
      </div>

      {snapshot.extreme_events.length > 0 && (
        <div className="breadth-events-row">
          <span className="muted">极端事件：</span>
          {snapshot.extreme_events.map((e) => (
            <span
              key={e.event_type}
              className={`event-chip ${
                e.event_type.includes("hot") ? "hot" : "cold"
              }`}
              onClick={() => onPickConcept?.(
                e.event_type,
                `市场宽度 · 极端事件 ${e.event_type}`,
              )}
            >
              {e.event_type}
              {e.threshold_origin === "lei_threshold_research" && (
                <span className="research-tag" title="A 股固定阈值为研究级，非正式验证阈值">
                  研究
                </span>
              )}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

function Metric({
  label,
  value,
  delta,
  coverage,
  conceptKey,
  onPick,
}: {
  label: string;
  value: string;
  delta: string;
  coverage: string;
  conceptKey: string;
  onPick?: (key: string, sourceCn: string) => void,
}) {
  return (
    <div className="breadth-metric-cell">
      <div
        className="metric-label"
        onClick={() => onPick?.(conceptKey, `市场宽度 · ${label}`)}
      >
        {label}
      </div>
      <div className="metric-value">{value}</div>
      <div className="metric-delta muted">
        5日变化 {delta} · 覆盖率 {coverage}
      </div>
    </div>
  );
}

function SmallMetric({
  label,
  value,
  conceptKey,
  onPick,
}: {
  label: string;
  value: string;
  conceptKey: string;
  onPick?: (key: string, sourceCn: string) => void,
}) {
  return (
    <div
      className="breadth-small-metric"
      onClick={() => onPick?.(conceptKey, `市场宽度 · ${label}`)}
    >
      <span className="muted">{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function BreadthTrendChart({ symbol }: { symbol: string }) {
  // Pick the first snapshot's market (primary).
  const { data: full } = useQuery({
    queryKey: ["marketContextFull", symbol],
    queryFn: () => api.marketContextFull(symbol),
    enabled: Boolean(symbol),
    staleTime: 60_000,
  });
  const primary = full?.snapshots?.[0];
  const marketId = primary?.market_id;

  const { data: historyResp, isLoading } = useQuery({
    queryKey: ["breadthHistory", symbol, marketId, 120],
    queryFn: () => api.marketBreadthHistory(symbol, marketId as string, 120),
    enabled: Boolean(marketId),
    staleTime: 60_000,
  });

  const points: BreadthHistoryPoint[] = historyResp?.history ?? [];

  return (
    <div className="breadth-trend">
      <div className="breadth-trend-header">
        <span>近 120 交易日 B20 / B50 趋势</span>
        <span className="muted">虚线：20 / 50 / 80 研究参考线</span>
      </div>
      {isLoading && <div className="loading">正在加载历史…</div>}
      {!isLoading && points.length === 0 && (
        <div className="muted">暂无历史（首次写入后才有数据）</div>
      )}
      {points.length >= 2 && (
        <BreadthTrendSvg points={points} />
      )}
    </div>
  );
}

function BreadthTrendSvg({ points }: { points: BreadthHistoryPoint[] }) {
  const w = 560;
  const h = 140;
  const padX = 36;
  const padY = 14;

  const xs = points.map((_, i) => i);
  const ys = points.flatMap((p) => [p.breadth_20 ?? 50, p.breadth_50 ?? 50]);
  const yMin = Math.min(0, ...ys);
  const yMax = Math.max(100, ...ys);
  const xRange = xs.length - 1 || 1;

  const xToPx = (i: number) => padX + (i / xRange) * (w - padX * 2);
  const yToPx = (v: number) =>
    h - padY - ((v - yMin) / (yMax - yMin)) * (h - padY * 2);

  const linePath = (key: "breadth_20" | "breadth_50") =>
    points
      .map((p, i) => {
        const v = p[key];
        if (v == null) return null;
        return `${i === 0 ? "M" : "L"}${xToPx(i).toFixed(1)},${yToPx(v).toFixed(1)}`;
      })
      .filter(Boolean)
      .join(" ");

  return (
    <svg width="100%" height={h} viewBox={`0 0 ${w} ${h}`} preserveAspectRatio="none">
      {RESEARCH_LINES.map((line) => (
        <g key={line}>
          <line
            x1={padX}
            x2={w - padX}
            y1={yToPx(line)}
            y2={yToPx(line)}
            stroke="var(--border, #d6dde6)"
            strokeDasharray="4 3"
            strokeWidth="0.8"
          />
          <text
            x={w - padX + 2}
            y={yToPx(line) + 3}
            fontSize="9"
            fill="var(--text-faint, #7b8494)"
          >
            {line}
          </text>
        </g>
      ))}
      <path d={linePath("breadth_50")} fill="none" stroke="#2563eb" strokeWidth="1.5" />
      <path d={linePath("breadth_20")} fill="none" stroke="#e36b1c" strokeWidth="1.5" />
      <text x={padX} y={padY + 10} fontSize="10" fill="#2563eb">B50</text>
      <text x={padX + 36} y={padY + 10} fontSize="10" fill="#e36b1c">B20</text>
    </svg>
  );
}
