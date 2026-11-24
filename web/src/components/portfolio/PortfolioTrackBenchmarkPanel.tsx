import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../../api/client";
import type { Card, PortfolioGroup } from "../../types";
import { TRACK_BENCHMARKS } from "../../utils/portfolioTrackBenchmarks";
import ColorBadge from "../ColorBadge";

interface Props {
  groups: PortfolioGroup[];
  activeGroupKey?: string;
  onSelectGroup?: (groupKey: string) => void;
}

const money = (v: number) =>
  `¥${v.toLocaleString("zh-CN", { minimumFractionDigits: 0, maximumFractionDigits: 0 })}`;

function fmtSigned(v: number | null | undefined): string {
  if (v == null || !Number.isFinite(v)) return "—";
  return `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;
}

export default function PortfolioTrackBenchmarkPanel({ groups, activeGroupKey, onSelectGroup }: Props) {
  const { data: dashboard } = useQuery({
    queryKey: ["cards"],
    queryFn: () => api.dashboard(),
    staleTime: 60_000,
  });

  const cardMap = useMemo(() => {
    const m = new Map<string, Card>();
    for (const c of dashboard?.cards ?? []) {
      if (!c.error) m.set(c.symbol, c);
    }
    return m;
  }, [dashboard]);

  const sortedGroups = useMemo(
    () => [...groups].sort((a, b) => b.amount - a.amount),
    [groups],
  );

  if (sortedGroups.length === 0) return null;

  return (
    <details className="ptb-panel" open>
      <summary className="ptb-summary">
        <div className="ptb-summary-left">
          <strong>赛道仓位 × 外部大势</strong>
          <span
            className="ctl-help-btn"
            tabIndex={0}
            onClick={(e) => e.preventDefault()}
            title="场外主动/联接基金按赛道对照同方向公开市场指数或 ETF 顺逆风（非单只基金实时净值）；点击任意赛道行可联动筛选下方基金明细"
          >
            ?
          </span>
          <span>点击赛道筛选下方基金 · 点参考标的看 K 线</span>
        </div>
        <Link
          to="/?view=compare&scope=portfolio"
          className="ptb-jump-link"
          onClick={(e) => e.stopPropagation()}
        >
          在横向比强弱中展开 →
        </Link>
      </summary>

      <div className="ptb-table-wrap">
        <table className="ptb-table">
          <thead>
            <tr>
              <th>我的持仓方向</th>
              <th className="ptb-num">仓位占比 / 金额</th>
              <th>同方向公开市场参考</th>
              <th>参考标的状态与周/日趋势</th>
              <th className="ptb-num">距 20日 / 60日均线</th>
            </tr>
          </thead>
          <tbody>
            {sortedGroups.map((g) => {
              const spec = TRACK_BENCHMARKS[g.group_key];
              const refs = (spec?.referenceSymbols ?? [])
                .map((sym) => cardMap.get(sym))
                .filter((c): c is Card => Boolean(c));
              const primary = refs[0] ?? null;
              const isSelected = activeGroupKey === g.group_key;

              return (
                <tr
                  key={g.group_key}
                  className={isSelected ? "ptb-row-active" : undefined}
                  style={onSelectGroup ? { cursor: "pointer" } : undefined}
                  onClick={onSelectGroup ? () => onSelectGroup(isSelected ? "all" : g.group_key) : undefined}
                >
                  <td>
                    {onSelectGroup ? (
                      <button
                        type="button"
                        className="ptb-group-btn"
                        aria-pressed={isSelected}
                        onClick={(e) => {
                          e.stopPropagation();
                          onSelectGroup(isSelected ? "all" : g.group_key);
                        }}
                        title={isSelected ? "再次点击取消赛道筛选" : "筛选查看该方向下的基金明细"}
                      >
                        <strong>{g.name}</strong>
                        <small>{g.holdings.length} 只{isSelected ? " · 已筛" : ""}</small>
                      </button>
                    ) : (
                      <div className="ptb-group-static">
                        <strong>{g.name}</strong>
                        <small>{g.holdings.length} 只基金</small>
                      </div>
                    )}
                  </td>

                  <td className="ptb-num">
                    <div className="ptb-weight-cell">
                      <strong>{g.pct.toFixed(1)}%</strong>
                      <small>{money(g.amount)}</small>
                    </div>
                    <div className="ptb-mini-bar" aria-hidden="true">
                      <i style={{ width: `${Math.max(2, Math.min(100, g.pct))}%` }} />
                    </div>
                  </td>

                  <td>
                    {refs.length > 0 ? (
                      <div className="ptb-ref-chips">
                        {refs.slice(0, 2).map((rc) => (
                          <Link
                            key={rc.symbol}
                            to={`/?symbol=${encodeURIComponent(rc.symbol)}`}
                            className="ptb-ref-chip"
                            onClick={(e) => e.stopPropagation()}
                            title={`点击查看 ${rc.display_name} (${rc.symbol}) K 线`}
                          >
                            {rc.display_name}
                          </Link>
                        ))}
                      </div>
                    ) : (
                      <span className="ptb-muted">
                        {spec?.noteCn ?? (dashboard ? "暂无已缓存参考标的" : "读取参考行情中…")}
                      </span>
                    )}
                  </td>

                  <td>
                    {primary ? (
                      <div className="ptb-state-cell">
                        <ColorBadge
                          color={primary.color}
                          colorCn={primary.color_cn}
                          days={primary.color_days}
                        />
                        <span className="ptb-trend-text">
                          {primary.weekly_long_trend_cn && primary.weekly_long_trend_cn !== "数据不足"
                            ? `周·${primary.weekly_long_trend_cn} / `
                            : ""}
                          日·{primary.daily_long_trend_cn || "—"}
                        </span>
                      </div>
                    ) : (
                      <span className="ptb-muted">—</span>
                    )}
                  </td>

                  <td className="ptb-num ptb-mono">
                    {primary ? (
                      <>
                        <div>20日 {fmtSigned(primary.dist_ema20_pct)}</div>
                        <small className="ptb-muted">60日 {fmtSigned(primary.dist_ema60_pct)}</small>
                      </>
                    ) : (
                      <span className="ptb-muted">—</span>
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </details>
  );
}
