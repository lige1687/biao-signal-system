import { useEffect, useState } from "react";
import { OBSERVATION_BY_ID } from "../observation-library/catalog";
import ObservationDetailDialog from "../observation-library/ObservationDetailDialog";
import { PROJECTION_METRICS, useProjectionSource } from "../observation-library/projectionSources";
import { marketReferenceBands } from "../observation-library/marketReferenceBands";
import ValuationReferenceReading from "../observation-library/ValuationReferenceReading";
import MiniTrend from "./MiniTrend";
import ChartLegend, { CHART_COLORS } from "./ChartLegend";
import type { CandidateSummary } from "./CandidateShelf";

export default function ExtraCandidateCard({ id, collapsed = false, onCollapse, onSummary }: {
  id: string; collapsed?: boolean; onCollapse?: () => void; onSummary?: (summary: CandidateSummary) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const item = OBSERVATION_BY_ID.get(id);
  const projection = PROJECTION_METRICS.find((metric) => metric.id === id);
  // A neutral source is still called unconditionally; its adapter has no enabled request.
  const source = useProjectionSource(projection?.id ?? "unknown");
  const last = source.points[source.points.length - 1];
  const rows = source.points.slice(-90);
  const reference = marketReferenceBands(id, source.points, source.valuationFull);
  const level = reference?.latest;
  const offset = source.points.length - rows.length;
  const usable = !!projection && !source.error && !source.isPending && last?.value !== null && last?.value !== undefined;
  useEffect(() => {
    if (!item || !onSummary) return;
    onSummary({ value: source.error ? "读取失败" : source.isPending ? "读取中" : usable ? `${last.value!.toFixed(2)} ${source.unit}` : "读数待补",
      meaning: usable ? item.meaning : "当前资料不足，暂不能判断", date: usable ? last.date : undefined });
  }, [item, onSummary, source.error, source.isPending, source.unit, usable, last?.value, last?.date]);
  if (!item || collapsed) return null;
  return <article className="moa-item" data-tone="neutral" aria-label={item.label} data-overview-card={id}>
    <div className="moa-item-head"><h3>{item.label}</h3><div className="moa-item-actions"><span className="moa-quality">{!item.readable ? "待接入" : source.error ? "读取失败" : source.isPending ? "读取中" : usable ? id === "turnover-concentration" ? "历史完整月" : "资料可查看" : "历史待核"}</span>{onCollapse && <button type="button" onClick={onCollapse}>收起</button>}</div></div>
    <h4 className="moa-conclusion">{reference?.kind === "valuation" && usable ? "与自身近10年估值比较" : usable && level?.lower != null && level.upper != null ? last.value! <= level.lower ? reference!.lowerLabel : last.value! >= level.upper ? reference!.upperLabel : "位于高低参照之间" : usable ? "观察当前水平与变化" : "当前读数待补"}</h4>
    <div className="moa-erp-value"><strong style={{ color: CHART_COLORS.primary }}>{usable ? last.value!.toFixed(2) : "未知"}</strong><span>{source.unit}</span></div>
    {reference?.kind === "valuation" && usable && <div className="moa-card-reading"><ValuationReferenceReading reference={reference} compact /></div>}
    {reference?.kind === "concentration" && level?.lower != null && level.upper != null && <p className="moa-card-reading"><b style={{color:"#3c867a"}}>{reference.lowerLabel} {level.lower.toFixed(2)}{reference.unit}</b> ／ <b style={{color:"#ac7032"}}>{reference.upperLabel} {level.upper.toFixed(2)}{reference.unit}</b></p>}
    <ChartLegend items={[{ label: item.label, color: CHART_COLORS.primary, value: usable ? `${last.value!.toFixed(2)}${source.unit}` : undefined }]} />
    <MiniTrend dates={rows.map((point) => point.date)} lines={[{ name: item.label, color: CHART_COLORS.primary, values: rows.map((point) => point.value) }]} references={reference ? [
      { name: reference.lowerLabel, color: "#3c867a", values: reference.rows.slice(offset).map(row => row.lower), endLabel: reference.lowerShort },
      { name: reference.upperLabel, color: "#ac7032", values: reference.rows.slice(offset).map(row => row.upper), endLabel: reference.upperShort },
    ] : []} label={`${item.label}历史曲线，缺值断线；高低线为本地历史参照`} />
    {reference?.kind !== "valuation" && <p className="moa-card-reading">{reference?.meaning ?? item.meaning}</p>}
    {source.status && <p className="moa-card-limit">{source.status}</p>}
    {reference && level?.lower != null && <p className="moa-card-meta"><a href={reference.source.url} target="_blank" rel="noreferrer">{reference.source.source} ↗</a><br />{reference.coverage}</p>}
    {!usable && <p className="moa-card-limit">还没有可比较的当前读数。</p>}
    <p className="moa-card-meta">资料截至 {last?.date ?? "未提供"} · {id === "hs300-pe" ? "月度历史附最新读数" : source.frequency === "monthly" ? "月频" : source.frequency === "weekly" ? "周频" : projection?.frequency === "monthly" ? "月频" : projection?.frequency === "weekly" ? "周频" : "日频"}</p>
    <footer><button type="button" onClick={() => setExpanded(true)}>看大图 ↗</button><details><summary>来源</summary><p>{source.sourceUrl ? <a href={source.sourceUrl} target="_blank" rel="noreferrer">{source.sourceName}</a> : source.sourceName}</p></details></footer>
    {expanded && <ObservationDetailDialog item={item} onClose={() => setExpanded(false)} />}
  </article>;
}
