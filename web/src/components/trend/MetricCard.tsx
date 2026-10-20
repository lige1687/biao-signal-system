import Sparkline from "./Sparkline";

/** 通用指标卡：当前值 + 区间标签 + 小图，点开看大图（抽自 FundamentalsPage，纯重构）。 */
export default function MetricCard({
  label,
  value,
  sub,
  zoneLabel,
  zoneTone,
  sparkValues,
  markY,
  onOpen,
  loading,
}: {
  label: string;
  value: string;
  sub?: string;
  zoneLabel?: string;
  zoneTone?: string;
  sparkValues?: number[];
  markY?: number | null;
  onOpen?: () => void;
  loading?: boolean;
}) {
  return (
    <div
      className={`macro-card metric-card${onOpen ? " clickable" : ""}`}
      onClick={onOpen}
    >
      <div className="macro-head">
        <span className="macro-name">{label}</span>
        {zoneLabel && (
          <span className={`macro-chip ${zoneTone ?? ""}`}>{zoneLabel}</span>
        )}
      </div>
      <div className="macro-value">{value}</div>
      {sub && <div className="macro-note">{sub}</div>}
      {sparkValues && sparkValues.length >= 2 ? (
        <Sparkline values={sparkValues} markY={markY ?? null} height={48} />
      ) : (
        <div className="sparkline-muted">
          {loading ? "加载历史…" : "暂无历史"}
        </div>
      )}
    </div>
  );
}
