import type { Metric, TodayOverview } from "../types";

interface Props {
  today: TodayOverview;
  onPickConcept?: (conceptKey: string, sourceCn: string) => void;
}

function fmtValue(m: Metric): string {
  if (m.text) return m.text;
  if (m.value == null) return "—";
  const abs = Math.abs(m.value);
  // 成交量这类大数用万/亿收敛，避免一长串数字挤爆栅格
  if (m.unit === "" && abs >= 1e8) return `${(m.value / 1e8).toFixed(2)}亿`;
  if (m.unit === "" && abs >= 1e4) return `${(m.value / 1e4).toFixed(0)}万`;
  const digits = abs >= 1000 ? 2 : abs >= 1 ? 2 : 3;
  const sign = m.unit === "%" && m.value > 0 ? "+" : "";
  return `${sign}${m.value.toFixed(digits)}${m.unit}`;
}

function MetricCell({ m, onPick }: { m: Metric; onPick?: () => void }) {
  const clickable = Boolean(m.concept && onPick);
  return (
    <div
      className={`metric ${m.tone} ${clickable ? "clickable" : ""}`}
      title={m.hint_cn || undefined}
      onClick={clickable ? onPick : undefined}
    >
      <div className="m-label">
        {m.label_cn}
        {clickable && <span className="m-q">?</span>}
      </div>
      <div className="m-value">{fmtValue(m)}</div>
    </div>
  );
}

function Group({
  title,
  metrics,
  onPickConcept,
}: {
  title: string;
  metrics: Metric[];
  onPickConcept?: (key: string, src: string) => void;
}) {
  if (metrics.length === 0) return null;
  return (
    <div className="ov-group">
      <div className="ov-title">{title}</div>
      <div className="ov-grid">
        {metrics.map((m) => (
          <MetricCell
            key={m.key}
            m={m}
            onPick={
              m.concept && onPickConcept
                ? () => onPickConcept(m.concept!, `今日概述 · ${m.label_cn}`)
                : undefined
            }
          />
        ))}
      </div>
    </div>
  );
}

/** 中间栏「今日信息概述」：LEI、趋势波动、量能、价格与资金。 */
export default function TodayOverviewPanel({ today, onPickConcept }: Props) {
  return (
    <div className="panel overview">
      <div className="ov-head">
        <h3>今日概述</h3>
        <span className="muted">{today.as_of}</span>
        {!today.quote_available && (
          <span className="stale-chip" title={today.quote_note_cn}>
            无盘口数据
          </span>
        )}
      </div>
      <Group title="LEI 信号" metrics={today.signal} onPickConcept={onPickConcept} />
      <Group title="趋势与波动" metrics={today.technical ?? []} onPickConcept={onPickConcept} />
      <Group title="量能" metrics={today.volume} onPickConcept={onPickConcept} />
      <Group title="价格" metrics={today.price} onPickConcept={onPickConcept} />
      <Group title="资金与市值" metrics={today.capital} onPickConcept={onPickConcept} />
    </div>
  );
}
