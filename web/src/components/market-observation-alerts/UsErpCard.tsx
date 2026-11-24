import { useEffect, useMemo, useState } from "react";
import { useProjectionSource } from "../observation-library/projectionSources";
import { usErpBands } from "../observation-library/usErpBands";
import { bandDistance } from "../observation-library/erpBands";
import { withErpSigma, type ErpSigma } from "../observation-library/erpSensitivity";
import ObservationDetailDialog from "../observation-library/ObservationDetailDialog";
import { OBSERVATION_BY_ID } from "../observation-library/catalog";
import MiniTrend from "./MiniTrend";
import ChartLegend, { CHART_COLORS } from "./ChartLegend";
import type { CandidateSummary } from "./CandidateShelf";
import "./us-erp-card.css";

const fmt = (value: number | null | undefined) => value == null ? "—" : value.toFixed(2);
const lowerColor = "#986737", upperColor = "#327c72";

export default function UsErpCard({ collapsed, onCollapse, onSummary }: {
  collapsed?: boolean; onCollapse: () => void; onSummary: (summary: CandidateSummary) => void;
}) {
  const source = useProjectionSource("erp-us");
  const rows = useMemo(() => usErpBands(source.points), [source.points]);
  const [sigmas, setSigmas] = useState<readonly ErpSigma[]>([1.5, 2]);
  const [expanded, setExpanded] = useState(false);
  const latest = rows[rows.length - 1];
  const ready = !source.error && !source.isPending && latest?.value != null;
  const z = latest?.z;
  const historical = !!latest && Date.now() - Date.parse(`${latest.date}T00:00:00Z`) > 7 * 86_400_000;
  const crossed = ready && z != null && Math.abs(z) > 2;
  const position = z == null ? "参考历史不足" : crossed
    ? `${z > 0 ? "高于2σ上" : "低于2σ下"}轨 · 相对${z > 0 ? "便宜" : "偏贵"}`
    : "位于2σ参考区间内";
  const dataState = source.error ? "历史资料暂不可用" : source.isPending ? "读取历史资料…" : "最新股债读数缺失";
  const conclusion = !ready ? dataState : `${historical ? "历史读数 · " : ""}${position}`;
  const allRails = useMemo(() => ([1.5, 2] as const).map(sigma => ({ sigma, rows: withErpSigma(rows, sigma) })), [rows]);
  const inner = allRails[0].rows[rows.length - 1];
  const nearest = ready && inner?.value != null && inner.lower != null && inner.upper != null
    ? bandDistance(inner, Math.abs(inner.value - inner.lower) <= Math.abs(inner.value - inner.upper) ? "lower" : "upper") : null;
  const visible = rows.slice(-1260);
  const prior = rows.length > 20 ? rows[rows.length - 21] : undefined;
  const change = ready && prior?.value != null ? latest!.value! - prior.value : null;
  useEffect(() => { onSummary({ value: ready ? `${fmt(latest?.value)} 个百分点` : "读数待补", meaning: conclusion, date: latest?.date }); },
    [ready, latest?.value, latest?.date, conclusion, onSummary]);
  if (collapsed) return null;
  const toggle = (sigma: ErpSigma) => {
    if (sigmas.length === 1 && sigmas.includes(sigma)) return;
    setSigmas(sigmas.includes(sigma) ? sigmas.filter(value => value !== sigma) : [...sigmas, sigma].sort());
  };
  return <article className="moa-item us-erp-card" data-tone={!historical && crossed ? z! < 0 ? "caution" : "supportive" : "neutral"} aria-label="标普500 · 股债利差" data-overview-card="erp-us">
    <div className="moa-item-head"><h3>标普500 · 股债利差</h3><button type="button" onClick={onCollapse}>收起</button></div>
    <h4 className="moa-conclusion">{conclusion}</h4>
    <div className="moa-erp-value"><strong>{ready ? fmt(latest?.value) : "—"}</strong><span>个百分点</span><time dateTime={latest?.date}>{latest?.date ?? "日期待补"}</time></div>
    <div className="us-erp-thresholds" role="group" aria-label="美股股债小图参考线显示">
      {allRails.map(({ sigma, rows: values }) => { const last = values[values.length - 1]; return <button type="button" key={sigma}
        aria-pressed={sigmas.includes(sigma)} disabled={sigmas.length === 1 && sigmas.includes(sigma)} onClick={() => toggle(sigma)}>
        <span>{sigma === 1.5 ? "○ 1.5σ · 内轨" : "◆ 2σ · 外轨"}</span>
        <span><b style={{ color: lowerColor }}>下 {fmt(last?.lower)}</b><b style={{ color: upperColor }}>上 {fmt(last?.upper)}</b></span>
      </button>; })}
    </div>
    <ChartLegend items={[{ label: "股债利差", color: CHART_COLORS.primary }, { label: "上轨 · 相对便宜", color: upperColor, dashed: true }, { label: "下轨 · 相对偏贵", color: lowerColor, dashed: true }]} />
    {ready ? <MiniTrend dates={visible.map(row => row.date)} lines={[{ name: "美股股债利差", color: CHART_COLORS.primary, values: visible.map(row => row.value) }]}
      references={allRails.filter(({ sigma }) => sigmas.includes(sigma)).flatMap(({ sigma, rows: values }) => [
        { name: `${sigma}σ上轨`, color: sigma === 2 ? upperColor : "#73a89f", values: values.slice(-1260).map(row => row.upper) },
        { name: `${sigma}σ下轨`, color: sigma === 2 ? lowerColor : "#bc9974", values: values.slice(-1260).map(row => row.lower) },
      ])} label={`标普500股债利差近五年，显示${sigmas.join("及")}倍标准差；青绿上轨看相对便宜，棕色下轨看相对偏贵`} />
      : <p role="status">{dataState}<button type="button" onClick={source.retry}>重试</button></p>}
    <p className="moa-reference-caption">滚动3年 · 日频观测，不含当期 · 单位：百分点</p>
    {change !== null && <p className="moa-card-change">较{prior!.date} <b>{change > 0 ? "+" : ""}{change.toFixed(2)} 个百分点</b></p>}
    <p className="moa-use">{nearest ? `1.5σ内轨：${nearest}` : "参考轨道待补齐"}</p>
    <p className="moa-card-meta">盈利端月频 · 尚不足以支持择时{historical ? " · 更新待补" : ""}</p>
    <footer><button type="button" onClick={() => setExpanded(true)}>看大图 · 轨道与价格 ↗</button><details><summary>参考依据</summary>
      <p>两档轨道均按此前3个自然年的均值和标准差计算，不含当期。标题按2σ，按钮只控制参考线显示；图示年限不改变计算窗口。</p>
      <p>数据：{source.sourceName}。负值表示盈利收益率低于国债收益率。</p>
      <p><a href="https://www.ssga.com/nz/en_gb/institutional/insights/mind-on-the-market-01-june-2026" target="_blank" rel="noreferrer">道富：股债相对估值</a>；1.5σ/2σ为本地观察参考。</p>
      <p>上轨每档仅3次可比事件；1.5σ下轨风险线索不稳，2σ未见增量。<a href="/library?report=docs%2Fexperiments%2Fbreadth-erp-ma200-increment-review-2026-11-02.md">查看检验</a></p>
    </details></footer>
    {expanded && <ObservationDetailDialog item={OBSERVATION_BY_ID.get("erp-us")!} onClose={() => setExpanded(false)} />}
  </article>;
}
