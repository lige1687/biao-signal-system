import { useQuery } from "@tanstack/react-query";

import { api } from "../api/client";
import type { ForwardStatBucket, GlobalPanel } from "../types";

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

const HORIZON_LABELS: Record<string, string> = {
  "5": "5 个交易日后",
  "20": "20 个交易日后 (≈1 月)",
  "60": "60 个交易日后 (≈1 季)",
};

/**
 * Modal opened by clicking a topbar strip panel.
 *
 * Layout:
 *   1. Alert banners (if B50/B200 triggered 85/15 extremes)
 *   2. Breadth grid (only cells with real data; null cells omitted)
 *   3. 牛/熊底色 (B200 > 50 = 牛, < 50 = 熊)
 *   4. 预警规则说明 (the 85/15 thresholds, always shown)
 *   5. Forward-return table (only when percentile is available)
 */
export default function MarketBreadthModal({ panel, onClose }: Props) {
  const percentile = panel.percentile_20;
  const { data: forward, isLoading: loadingForward } = useQuery({
    queryKey: ["forwardStats", panel.market_id, percentile],
    queryFn: () => api.marketContextForwardStats(panel.market_id, percentile ?? 50, 5),
    enabled: percentile != null,
    staleTime: 600_000,
  });

  const hasB200 = panel.breadth_200 != null;
  const isBull = hasB200 && panel.breadth_200! > 50;
  const isBear = hasB200 && panel.breadth_200! < 50;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-card breadth-modal" onClick={(e) => e.stopPropagation()}>
        <div className="modal-head">
          <h2>{panel.display_name} · 市场宽度</h2>
          <button className="btn small" onClick={onClose}>关闭</button>
        </div>

        {/* 1. 预警横幅 */}
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

        {/* 2. 宽度指标网格（只显示有数据的格子） */}
        <div className="breadth-modal-grid">
          <div className="modal-cell">
            <div className="muted">B20 (MA20 上方)</div>
            <div className="modal-value">{fmtPct(panel.breadth_20)}</div>
            <div className="modal-sub">5 日 {fmtSigned(panel.breadth_20_delta_5)}</div>
          </div>
          {panel.breadth_50 != null && (
            <div className="modal-cell">
              <div className="muted">B50 (MA50 上方)</div>
              <div className="modal-value">{fmtPct(panel.breadth_50)}</div>
              <div className="modal-sub">5 日 {fmtSigned(panel.breadth_50_delta_5)}</div>
            </div>
          )}
          {hasB200 && (
            <div className="modal-cell">
              <div className="muted">B200 (MA200 上方)</div>
              <div className="modal-value">{fmtPct(panel.breadth_200)}</div>
              <div className="modal-sub">
                {isBull ? "高于 50% → 牛市底色" : isBear ? "低于 50% → 熊市底色" : "恰在 50%" }
              </div>
            </div>
          )}
          {percentile != null && (
            <div className="modal-cell">
              <div className="muted">历史分位 (P20)</div>
              <div className="modal-value">P{percentile.toFixed(0)}</div>
              <div className="modal-sub">
                {percentile >= 85 ? "高位区域 ⚠" : percentile <= 15 ? "低位区域 ⚠" : "中性区间"}
              </div>
            </div>
          )}
        </div>

        {/* 3. 牛/熊底色 */}
        {hasB200 && (
          <div className={`breadth-regime-banner ${isBull ? "bull" : isBear ? "bear" : "neutral"}`}>
            {isBull ? "🐂 牛市底色" : isBear ? "🐻 熊市底色" : "中性"}
            <span className="muted">
              {" "}— B200 = {fmtPct(panel.breadth_200)}
              {isBull ? " > 50%" : isBear ? " < 50%" : " = 50%"}
            </span>
          </div>
        )}

        {/* 4. 预警规则说明 */}
        <div className="breadth-modal-section">
          <h3>宽度极端预警规则</h3>
          <div className="breadth-rules">
            <div className="breadth-rule">
              <span className="rule-tag tag-stage-top">B50 ≥ 85%</span>
              <span>阶段性顶部预警 — 大概率短期高点</span>
            </div>
            <div className="breadth-rule">
              <span className="rule-tag tag-stage-bottom">B50 ≤ 15%</span>
              <span>短期底部预警 — 大概率短期低点</span>
            </div>
            <div className="breadth-rule">
              <span className="rule-tag tag-reversal-top">B50 + B200 同时 ≥ 85%</span>
              <span>反转顶部信号 — 两个周期共振极热，大概率趋势反转</span>
            </div>
            <div className="breadth-rule">
              <span className="rule-tag tag-reversal-bottom">B50 + B200 同时 ≤ 15%</span>
              <span>反转底部信号 — 两个周期共振极冷，大概率趋势反转</span>
            </div>
            <div className="breadth-rule">
              <span className="rule-tag tag-bull">B200 &gt; 50%</span>
              <span>牛市底色 — 长期趋势偏多</span>
            </div>
            <div className="breadth-rule">
              <span className="rule-tag tag-bear">B200 &lt; 50%</span>
              <span>熊市底色 — 长期趋势偏空</span>
            </div>
          </div>
          {panel.breadth_50 == null && !hasB200 && (
            <p className="muted breadth-modal-hint">
              当前数据源只提供 B20（MA20 站上率），B50/B200 暂不可用。
              预警将在 B50/B200 数据就绪后自动触发。
            </p>
          )}
        </div>

        {/* 5. 历史分位前瞻收益（仅有分位时显示） */}
        {percentile != null && (
          <div className="breadth-modal-section">
            <h3>历史分位 → 同期指数收益</h3>
            <p className="muted breadth-modal-hint">
              把过去所有"B20 历史分位落在 ±5pp 桶内"的交易日挑出来，
              分别看其后 5 / 20 / 60 个交易日指数的真实涨跌分布。
              当前分位 = P{percentile.toFixed(1)}。
            </p>
            {loadingForward && <div className="loading">正在统计…</div>}
            {forward && (
              <>
                {forward.bucket_size !== undefined && (
                  <div className="muted breadth-modal-meta">
                    桶内样本：{forward.bucket_size} 个交易日
                    {forward.bucket_half_width !== undefined &&
                      ` (分位 P${percentile.toFixed(0)} ± ${forward.bucket_half_width})`}
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
                      if (!s || s.n === 0) {
                        return (
                          <tr key={h}>
                            <td>{HORIZON_LABELS[h]}</td>
                            <td colSpan={5} className="muted">样本不足</td>
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
                          <td className="muted">{fmtSigned(s.min)} / {fmtSigned(s.max)}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </>
            )}
          </div>
        )}

        <div className="breadth-modal-footer muted">
          数据来源：{panel.market_id} · 更新{" "}
          {new Date(panel.updated_at).toLocaleString("zh-CN", { hour12: false })}
        </div>
      </div>
    </div>
  );
}
