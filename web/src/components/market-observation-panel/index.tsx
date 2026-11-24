import { useEffect, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import TrendChart from "./TrendChart";
import { buildReminders } from "./diagnostics";
import { INDICATOR_META_CONFIG, PANEL_QUERY_KEY, PANEL_URL, finite, formatNumber, formatValue, isFresh, latest, validPacket, type ObservationCardData, type ObservationPanelData } from "./model";
import "./style.css";

export { INDICATOR_META_CONFIG, PANEL_QUERY_KEY } from "./model";
export type { ObservationCardData, ObservationPanelData, Point } from "./model";

class PanelFetchError extends Error { constructor(readonly status: number) { super(`HTTP ${status}`); } }
async function fetchPanel(): Promise<ObservationPanelData> {
  const response = await fetch(PANEL_URL, { cache: "no-cache" });
  if (!response.ok) throw new PanelFetchError(response.status);
  const packet: unknown = await response.json();
  if (!validPacket(packet)) throw new Error("invalid panel data");
  return packet;
}
function usePanelData() {
  return useQuery({ queryKey: PANEL_QUERY_KEY, queryFn: fetchPanel, staleTime: 5 * 60_000, retry: (attempts, error) => !(error instanceof PanelFetchError && error.status === 404) && attempts < 2 });
}
const FREQ = { daily: "日频", weekly: "周频", monthly: "月频" } as const;
const GROUPS = [
  { id: "pressure", title: "① 波动与系统防线", label: "波动与系统防线" },
  { id: "breadth", title: "② 筹码结构与赚钱效应", label: "筹码结构与赚钱效应" },
  { id: "positioning", title: "③ 资金杠杆与逆向情绪", label: "资金杠杆与逆向情绪" },
] as const;
const statusMessage = (error: Error | null, missing = false) => missing ? "这项资料尚未接入；接通后可查看当前水平与趋势。" : error instanceof PanelFetchError && error.status === 404 ? "市场观察资料尚未发布。" : error ? "市场观察资料暂时无法读取，请稍后重试。" : "正在读取市场观察资料…";
const MA = { daily: "20日均值", weekly: "4周均值", monthly: "月频位置" } as const;
const windowLabel = (data: ObservationCardData) => data.frequency === "daily" ? "252日"
  : data.frequency === "weekly" ? "156周" : "60月";
const signed = (value: number, digits: number) => `${value > 0 ? "+" : value < 0 ? "−" : ""}${Math.abs(value).toFixed(digits)}`;
const zLabel = (value?: number | null) => finite(value) ? `${signed(value, 1)}σ` : "—";
const latestLine = (data: ObservationCardData, id: string) => {
  const points = data.lines?.find(line => line.id === id)?.points;
  return points?.[points.length - 1];
};
function ratio(data: ObservationCardData) {
  const short = latest(data), long = latestLine(data, "hv60");
  return finite(short?.value) && finite(long?.value) && long.value > 0 && short.date === long.date
    ? short.value / long.value : null;
}
function statusFor(data: ObservationCardData, id: string) {
  const point = latest(data), meta = INDICATOR_META_CONFIG[id];
  if (!finite(point?.value)) return { label: "读数缺失", tone: "muted" };
  if (id === "baker-wurgler") return { label: "作者历史", tone: "muted" };
  if (!isFresh(point.date, data.frequency)) return { label: "往期资料", tone: "muted" };
  if (finite(meta.ratioAlert) && (ratio(data) ?? 0) > meta.ratioAlert)
    return { label: "短期波动放大", tone: "watch" };
  const rail = [...meta.hard_thresholds].reverse().find(item =>
    (item.tone === "high" || item.tone === "watch") && point.value! > item.value)
    ?? meta.hard_thresholds.find(item => item.tone === "low" && point.value! < item.value);
  if (rail) return { label: rail.label, tone: rail.tone };
  const z = data.current_zscore_raw ?? data.current_zscore;
  if (!finite(z)) return { label: "历史不足", tone: "muted" };
  if (z >= 1.5) return { label: meta.direction === "higher_sentiment" ? "情绪偏热" : "历史偏高", tone: "watch" };
  if (z <= -1.5) return { label: "历史偏低", tone: "low" };
  return { label: "常态区间", tone: "normal" };
}
function percentileLabel(data: ObservationCardData) {
  return finite(data.current_percentile)
    ? `${formatNumber(data.current_percentile, 0)}%分位 · ${windowLabel(data)}`
    : data.observations < data.window ? `有效 ${data.observations}/${data.window} 期` : "当前分位不可算";
}
function compactValue(value: number | null | undefined, unit: string, precision?: number) {
  if (unit === "百万美元") return formatValue(finite(value) ? value / 100 : value, "亿美元", precision);
  return formatValue(value, unit === "指数点" || unit === "指数值" ? "点" : unit, precision);
}
function maDeviation(data: ObservationCardData) {
  const point = latest(data);
  if (!finite(point?.ma20) || !finite(point.value)) return null;
  const unit = data.unit === "%" ? "百分点" : ["指数点", "指数值"].includes(data.unit) ? "点" : data.unit;
  return `偏离 ${signed(point.value - point.ma20, 2)} ${unit}`;
}
function dynamicInterpret(data: ObservationCardData, id: string): string {
  const meta = INDICATOR_META_CONFIG[id], point = latest(data);
  if (!point || !finite(point.value)) return "当前读数缺失。";
  if (id === "baker-wurgler") return meta.reading;
  const period = data.frequency === "weekly" ? "4周均值" : "20日均值";
  const delta = finite(point.ma20) ? point.value - point.ma20 : null;
  const comparison = delta === null ? "" : delta > 0 ? `高于${period}，` : delta < 0 ? `低于${period}，` : `与${period}持平，`;
  const { label, tone } = statusFor(data, id);
  const level = tone === "high" ? "破观察线" : tone === "watch" ? "偏高"
    : tone === "low" ? "偏低" : label === "往期资料" ? "往期" : label;
  return `${level}，${comparison}${meta.reading}`;
}
function source(data: ObservationCardData) { return data.sourceUrl && /^https?:\/\//.test(data.sourceUrl) ? <a href={data.sourceUrl} target="_blank" rel="noreferrer">{data.sourceName}</a> : data.sourceName; }
function DetailDialog({ id, data, close }: { id: string; data: ObservationCardData; close: () => void }) {
  const dialog = useRef<HTMLDialogElement>(null), meta = INDICATOR_META_CONFIG[id];
  const [fullHistory, setFullHistory] = useState(false);
  useEffect(() => {
    const node = dialog.current;
    const trigger = document.activeElement;
    node?.showModal();
    return () => {
      node?.close();
      if (trigger instanceof HTMLElement && trigger.isConnected) trigger.focus({ preventScroll: true });
    };
  }, []);
  if (!meta) return null;
  const point = latest(data);
  return <dialog ref={dialog} className="mop-dialog" aria-label={`${meta.label}详情`}
    onCancel={event => { event.preventDefault(); close(); }}
    onClick={event => { if (event.target === event.currentTarget) close(); }}>
    <div className="mop-dialog-head"><div><h2>{meta.label}</h2><p>{meta.meaning}</p></div><button type="button" onClick={close} aria-label="关闭详情">关闭</button></div>
    <div className="mop-detail-value"><strong>{formatValue(point?.value, data.unit, meta.precision)}</strong><span>{point?.date ?? "暂无日期"} · {FREQ[data.frequency]}</span></div>
    {id === "baker-wurgler" && <button type="button" aria-pressed={fullHistory} onClick={() => setFullHistory(value => !value)}>
      {fullHistory ? "回到近60月" : "查看完整作者历史"}
    </button>}
    <TrendChart data={id === "baker-wurgler" && !fullHistory ? { ...data, points: data.points.slice(-60) } : data}
      rails={meta.hard_thresholds} label={`${meta.label}历史曲线与观察线`} large />
    <p className="mop-reading">{meta.reading}</p>
    <div className="mop-detail-grid"><div><b>历史位置</b><span>{percentileLabel(data)}</span></div><div><b>比较窗口</b><span>{data.window > 0 ? `${data.window}期` : "暂无"} · {data.observations}个有效点</span></div><div><b>资料日期</b><span>{point?.date ?? "暂无"}</span></div><div><b>来源</b><span>{source(data)}</span></div></div>
    {data.auxiliary?.length ? <div className="mop-aux">{data.auxiliary.map(item => <div key={`${item.label}-${item.date}`}><span>{item.label}</span><strong>{formatValue(item.value, item.unit)}</strong><small>{item.date}</small></div>)}</div> : null}
    {data.note && <p className="mop-note">{data.note}</p>}
  </dialog>;
}
export function ObservationPanelCard({ id, onCollapse }: { id: string; onCollapse?: () => void }) {
  const query = usePanelData(), [open, setOpen] = useState(false), meta = INDICATOR_META_CONFIG[id];
  if (!meta) return null;
  const data = query.data?.cards[id], point = latest(data), fresh = data && isFresh(point?.date, data.frequency);
  const capsule = data ? statusFor(data, id) : { label: "待资料", tone: "muted" };
  const comparison = data ? ratio(data) : null;
  const proxy = data ? latestLine(data, "nowcast") : undefined;
  const layer = GROUPS.find(group => group.id === meta.group)?.label;
  const status = !query.data ? statusMessage(query.error) : !data ? statusMessage(null, true) : null;
  return <article data-overview-card={id} className={`mop-card ${fresh ? "" : "mop-stale"}`} aria-label={meta.label}>
    <div className="mop-top-row"><span>{meta.market === "cn" ? "A股" : meta.market === "us" ? "美股" : "跨市场"} · {layer}</span>
      <span className={`mop-capsule mop-capsule-${capsule.tone}`}>{data && finite(data.current_zscore) && `${zLabel(data.current_zscore)} · `}{capsule.label}</span>
    </div>
    <div className="mop-card-head"><div><h3>{meta.label}</h3><p>{meta.human_reminder}</p></div>
      {onCollapse && <button type="button" className="mop-collapse" onClick={onCollapse} aria-label={`收起${meta.label}`}>×</button>}
    </div>
    {status ? <p className="mop-status">{status}{query.isError && <button type="button" onClick={() => query.refetch()}>重试</button>}</p> : <>
      <div className="mop-readouts">
        <div><small>{data!.mainLabel ?? "当前读数"}</small><strong>{compactValue(point?.value, data!.unit, meta.precision)}</strong>
          <time dateTime={point?.date}>{point?.date ?? "暂无日期"}</time>
          {data!.latestQualifier && <em>{data!.latestQualifier}</em>}
          {comparison !== null && <em className={meta.ratioAlert && comparison > meta.ratioAlert ? "mop-ratio-watch" : ""}>20D/60D {formatNumber(comparison)} 倍</em>}
        </div>
        <div><small>{MA[data!.frequency]}</small>
          {data!.frequency === "monthly" ? <><strong>{compactValue(point?.mean, data!.unit)}</strong><small>近60月均值</small></>
            : <><strong>{compactValue(point?.ma20, data!.unit, meta.precision)}</strong><small>{maDeviation(data!) ?? "均值资料不足"}</small></>}
        </div>
        <div><small>历史位置</small><strong>{zLabel(data!.current_zscore)}</strong><small>{percentileLabel(data!)}</small></div>
      </div>
      {data!.auxiliary?.map(item => <div className="mop-inline-aux" key={item.label}>{item.label} <b>{formatValue(item.value, item.unit)}</b> · {item.date}</div>)}
      {finite(proxy?.value) && <div className="mop-inline-aux mop-nowcast">实时代理延伸 <b>{signed(proxy.value, 2)}</b> · {proxy.date}</div>}
      <TrendChart data={data!} rails={meta.hard_thresholds} label={`${meta.label}历史曲线`} />
      <div className="mop-card-actions"><button type="button" onClick={() => setOpen(true)}>展开图表与口径</button></div>
      <div className="mop-card-foot">
        <p className="mop-card-reading" title={dynamicInterpret(data!, id)}>{dynamicInterpret(data!, id)}</p>
      </div>
      {open && <DetailDialog id={id} data={data!} close={() => setOpen(false)} />}
    </>}
  </article>;
}
export function ObservationPanelThumbnail({ id }: { id: string }) {
  const query = usePanelData(), meta = INDICATOR_META_CONFIG[id];
  if (!meta) return null;
  const data = query.data?.cards[id], point = latest(data);
  if (!data) return <div className="mop-thumbnail mop-status">{statusMessage(query.error, !!query.data)}</div>;
  return <div className="mop-thumbnail" aria-label={`${meta.label}概览`}><div><strong>{formatValue(point?.value, data.unit, meta.precision)}</strong><span>{point?.date ?? "暂无日期"} · {FREQ[data.frequency]}{isFresh(point?.date, data.frequency) ? "" : " · 往期资料"}</span></div><TrendChart data={data} rails={meta.hard_thresholds} label={`${meta.label}历史与观察线`} /><small>{percentileLabel(data)}</small></div>;
}
export function ObservationPanel() {
  const query = usePanelData();
  const reminders = query.data ? buildReminders(query.data) : [];
  return <section className="mop-panel" aria-label="市场观察"><header className="mop-panel-head"><div><h2>市场观察</h2><p>对照波动、参与和融资状态；按各资料日期判断。</p></div>{query.data && <small>资料包生成 {query.data.generatedAt.slice(0, 10)}{query.data.partialUpdate?.message && <> · {query.data.partialUpdate.message}</>}</small>}</header>
    {GROUPS.map((group, index) => <details key={group.id} className="mop-group" open><summary>{group.title}</summary>{reminders[index] && <div className={`mop-reminder mop-reminder-${reminders[index].state}`}><strong>{reminders[index].title}</strong><span>{reminders[index].detail}</span></div>}<div className="mop-grid">{Object.values(INDICATOR_META_CONFIG).filter(meta => meta.group === group.id).map(meta => <ObservationPanelCard key={meta.id} id={meta.id} />)}</div></details>)}
  </section>;
}
export default ObservationPanel;
