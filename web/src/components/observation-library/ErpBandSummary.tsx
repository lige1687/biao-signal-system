import { bandDistance, erpBandPosition, ERP_BAND_METHOD, type ErpBandPoint } from "./erpBands";
import "./erpBands.css";

const value = (n: number | null | undefined) => n == null ? "—" : n.toFixed(2);

export default function ErpBandSummary({ row, compact = false }: { row?: ErpBandPoint; compact?: boolean }) {
  return <div className={`erp-bands-summary${compact ? " compact" : ""}`}>
    <div className="erp-bands-position"><strong>{erpBandPosition(row)}</strong><span>{bandDistance(row, "upper")} · {bandDistance(row, "lower")}</span></div>
    <div className="erp-bands-values" aria-label="股债利差轨道数值">
      <span><i className="erp-upper" />上轨 <b>{value(row?.upper)}</b></span>
      <span><i className="erp-middle" />中轨 <b>{value(row?.middle)}</b></span>
      <span><i className="erp-lower" />下轨 <b>{value(row?.lower)}</b></span>
      <small>百分点</small>
    </div>
    {!compact && <p>{ERP_BAND_METHOD.label}。越靠上，股票盈利收益率相对国债越高；越靠下则越低。触轨不等于价格已经见底或见顶。</p>}
  </div>;
}
