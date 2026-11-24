import type { ValuationReference } from "./marketReferenceBands";

const pe = (value: number) => `${value.toFixed(2)}倍`;
const rank = (value: number) => `P${value.toFixed(1).replace(/\.0$/, "")}`;

export default function ValuationReferenceReading({ reference, compact = false }: {
  reference: ValuationReference;
  compact?: boolean;
}) {
  const { latest, position, sensitivity, longHistory } = reference;
  if (latest?.percentile == null || latest.lower == null || latest.upper == null) {
    return <p>同口径月度历史不足，暂不计算近10年分位。</p>;
  }
  return <>
    <p><strong>近10年 {rank(latest.percentile)} · {position}</strong> · P20 {pe(latest.lower)} ／ P80 {pe(latest.upper)}</p>
    {!compact && <>
      <small>参照窗口：{reference.coverage}</small>
      {latest.lowExtreme != null && latest.highExtreme != null && <p>更极端位置：P10 {pe(latest.lowExtreme)} ／ P90 {pe(latest.highExtreme)}</p>}
      {sensitivity?.percentile != null && sensitivity.lower != null && sensitivity.upper != null &&
        <p>近15年复核：{rank(sensitivity.percentile)} · P20 {pe(sensitivity.lower)} ／ P80 {pe(sensitivity.upper)}（{sensitivity.n}/180个有效月）</p>}
      {longHistory && <p>{longHistory.full ? "完整来源历史" : "现有长历史"}极端高位 P95：{pe(longHistory.upper)}（{longHistory.start}—{longHistory.end}）</p>}
    </>}
  </>;
}
