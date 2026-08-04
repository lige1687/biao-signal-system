import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type { GlobalPanel, ForwardStatBucket } from "../types";

interface Props {
  panel: GlobalPanel;
  onClose: () => void;
}

function fmtPct(v: number | null | undefined, digits = 2): string {
  if (v == null) return "--";
  return `${v.toFixed(digits)}%`;
}

function fmtSigned(v: number | null | undefined, digits = 2): string {
  if (v == null) return "--";
  const sign = v > 0 ? "+" : "";
  return `${sign}${v.toFixed(digits)}%`;
}

const REGIME_CN: Record<string, string> = {
  bull: "偏多", bear: "偏空", unknown: "未知",
};
const HEAT_CN: Record<string, string> = {
  extreme_cold: "极冷", cold: "偏冷", neutral: "中性",
  hot: "偏热", extreme_hot: "过热", unknown: "未知",
};

const HORIZON_LABELS: Record<string, string> = {
  "5": "5 个交易日后",
  "20": "20 个交易日后 (≈1 月)",
  "60": "60 个交易日后 (≈1 季)",
};

const BUCKETS = [10, 30, 50, 70, 90];

/**
 * Modal opened by clicking a topbar strip panel. Shows the full snapshot
 * (B20/B50/B200 + 5/20-day changes + heat + drawdown) plus a forward-return
 * table: for the *current* Breadth20 percentile, what did the index do
 * over the next 5 / 20 / 60 trading days on average in past similar regimes.
 */
export default function MarketBreadthModal({ panel, onClose }: Props) {
  const percentile = panel.percentile_20;
  const { data: forward, isLoading: loadingForward } = useQuery({
    queryKey: ["forwardStats", panel.market_id, percentile],
    queryFn: () => api.marketContextForwardStats(panel.market_id, percentile ?? 50, 5),
    enabled: percentile != null,
    staleTime: 600_000,
  });

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card breadth-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>{panel.display_name} · 市场宽度</h2>
          <button className="btn small" onClick={onClose}>关闭</button>
        </div>

        {panel.alerts && panel.alerts.length > 0 && (
          <div className="breadth-alert-section">
            {panel.alerts.map((a) => (
              <div key={a.type} className={`breadth-alert-banner ${a.type}`}>
                <strong>{a.title}</strong>
                <div>{a.desc}</div>
              </div>
            ))}
          </div>
        )}

        <div className="breadth-modal-grid">
          <div className="modal-cell">
            <div className="muted">B20 (MA20 上方)</div>
            <div className="modal-value">{fmtPct(panel.breadth_20)}</div>
            <div className="modal-sub">5 日 {fmtSigned(panel.breadth_20_delta_5)}</div>
          </div>
          <div className="modal-cell">
            <div className="muted">B50 (MA50 上方)</div>
            <div className="modal-value">{fmtPct(panel.breadth_50)}</div>
            <div className="modal-sub">5 日 {fmtSigned(panel.breadth_50_delta_5)}</div>
          </div>
          <div className="modal-cell">
            <div className="muted">分位 (P20 / P50)</div>
            <div className="modal-value">
              {panel.percentile_20 == null ? "--" : `P${panel.percentile_20.toFixed(0)}`}
              {panel.percentile_50 == null ? "" : ` / P${panel.percentile_50.toFixed(0)}`}
            </div>
            <div className="modal-sub">
              长期 {REGIME_CN[panel.long_regime] ?? panel.long_regime} · 热度{" "}
              {HEAT_CN[panel.heat_state] ?? panel.heat_state}
            </div>
          </div>
          <div className="modal-cell">
            <div className="muted">指数回撤 (ATH)</div>
            <div className="modal-value">
              {panel.drawdown_from_ath == null
                ? "--"
                : `${(panel.drawdown_from_ath * 100).toFixed(2)}%`}
            </div>
            <div className="modal-sub">
              总结 {panel.summary_cn} · 状态 {panel.data_status}
            </div>
          </div>
        </div>

        <div className="breadth-modal-section">
          <h3>历史分位 → 同期指数收益</h3>
          <p className="muted breadth-modal-hint">
            把过去所有"B20 历史分位落在 ±5pp 桶内"的交易日挑出来，
            分别看其后 5 / 20 / 60 个交易日指数的真实涨跌分布。
            当前分位 = {percentile == null ? "--" : `P${percentile.toFixed(1)}`}。
            「命中率」= 桶内样本中指数上涨的比例。
          </p>
          {loadingForward && <div className="loading">正在统计历史分位收益…</div>}
          {forward && (
            <>
              {forward.bucket_size !== undefined && (
                <div className="muted breadth-modal-meta">
                  桶内样本：{forward.bucket_size} 个交易日
                  {forward.bucket_half_width !== undefined &&
                    ` (分位 ${percentile == null ? "?" : percentile.toFixed(0)} ± ${forward.bucket_half_width})`}
                </div>
              )}
              <table className="forward-stats-table">
                <thead>
                  <tr>
                    <th>持有期</th>
                    <th>样本数</th>
                    <th>中位收益</th>
                    <th>平均收益</th>
                    <th>命中率</th>
                    <th>最差 / 最佳</th>
                  </tr>
                </thead>
                <tbody>
                  {["5", "20", "60"].map((h) => {
                    const s: ForwardStatBucket | undefined = forward.stats?.[h];
                    if (!s) {
                      return (
                        <tr key={h}>
                          <td>{HORIZON_LABELS[h]}</td>
                          <td colSpan={5} className="muted">
                            样本不足 ({"<"} {forward.min_samples ?? 5})
                          </td>
                        </tr>
                      );
                    }
                    return (
                      <tr key={h}>
                        <td>{HORIZON_LABELS[h]}</td>
                        <td>{s.n}</td>
                        <td className={(s.median ?? 0) > 0 ? "up" : (s.median ?? 0) < 0 ? "down" : ""}>
                          {fmtSigned(s.median)}
                        </td>
                        <td className={(s.mean ?? 0) > 0 ? "up" : (s.mean ?? 0) < 0 ? "down" : ""}>
                          {fmtSigned(s.mean)}
                        </td>
                        <td>{s.hit_rate == null ? "--" : `${(s.hit_rate * 100).toFixed(0)}%`}</td>
                        <td className="muted">
                          {fmtSigned(s.min)} / {fmtSigned(s.max)}
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </>
          )}
        </div>

        <div className="breadth-modal-section">
          <h3>其它分位桶对照</h3>
          <p className="muted">
            想看其它分位档的对应收益？把鼠标停在数字上，
            表格里每行的样本桶都可以独立查询。
          </p>
          <div className="bucket-row">
            {BUCKETS.map((b) => (
              <span
                key={b}
                className={`bucket-chip ${Math.abs((percentile ?? 0) - b) < 5 ? "active" : ""}`}
                title={`分位 P${b} ± 5 桶的平均收益`}
              >
                P{b}
              </span>
            ))}
          </div>
        </div>

        <div className="breadth-modal-footer muted">
          数据来源：{panel.market_id} · 更新 {new Date(panel.updated_at).toLocaleString("zh-CN", { hour12: false })}
        </div>
      </div>
    </div>
  );
}
