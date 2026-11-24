import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import MiniTrend from "../market-observation-alerts/MiniTrend";
import ChartLegend, { CHART_COLORS } from "../market-observation-alerts/ChartLegend";
import type { CandidateSummary } from "../market-observation-alerts/CandidateShelf";
import { priorReferenceBands } from "../market-observation-alerts/referenceBands";
import { historicalPosition, recentDelta } from "../market-style/indicatorReading";
import ObservationDetailDialog from "../observation-library/ObservationDetailDialog";
import { OBSERVATION_BY_ID } from "../observation-library/catalog";
import { useRecentFocusMomentum } from "./recent";
import { FocusMomentumPriceProjection } from "./price-projection";
import "./overview.css";

/** Parent dashboards may own the dialog; existing callers keep the local dialog. */
export function FocusMomentumOverview({ onOpen, collapsed = false, onCollapse, onSummary }: {
  onOpen?: () => void; collapsed?: boolean; onCollapse?: () => void; onSummary?: (summary: CandidateSummary) => void;
} = {}) {
  const query = useRecentFocusMomentum();
  const [expanded, setExpanded] = useState(false);
  const open = () => { if (onOpen) onOpen(); else setExpanded(true); };
  const data = query.isError ? undefined : query.data;
  const point = data?.latest;
  const rows = data?.series.slice(-90) ?? [];
  const focusHistory = data?.series.map((entry) => ({ date: entry.date, value: entry.focus * 100 })) ?? [];
  const bands = priorReferenceBands(focusHistory, 756, 756, 90);
  const position = historicalPosition(focusHistory, 756);
  const change = recentDelta(focusHistory, 20);
  const focusLevel = point ? point.focus * 100 : null;
  const relative = focusLevel !== null && bands.latest.low !== null && bands.latest.high !== null
    ? focusLevel < bands.latest.low ? "近期表现处于历史偏弱区" : focusLevel > bands.latest.high ? "近期表现处于历史偏强区" : "近期表现处于历史常见区间" : "历史资料不足，暂不判断高低";
  useEffect(() => {
    onSummary?.({ value: query.isError ? "读取失败" : !point ? "读取中" : `${point.focus > 0 ? "+" : ""}${(point.focus * 100).toFixed(2)}% · 20日`,
      meaning: !query.isError && point ? `活跃股过去20日平均${point.focus < 0 ? "下跌" : point.focus > 0 ? "上涨" : "持平"}；${relative}` : "活跃股读数待补齐",
      date: point ? data?.asOf : undefined });
  }, [onSummary, query.isError, point?.focus, data?.asOf, relative]);
  if (collapsed) return null;
  return <article className="moa-item moa-focus" aria-label="A股焦点动量" data-overview-card="focus-momentum">
    <div className="moa-item-head"><h3>A股 · 焦点动量</h3><div className="moa-item-actions"><span className="moa-quality">历史观察</span>{onCollapse && <button type="button" onClick={onCollapse}>收起</button>}</div></div>
    <h4 className="moa-conclusion">{query.isError ? "资料暂不可用" : !point ? "读取中…" : point.focus < 0 ? "活跃股近20日平均下跌" : point.focus > 0 ? "活跃股近20日平均上涨" : "活跃股近20日平均持平"}</h4>
    <div className="fmo-preview">
    <div className="moa-erp-value"><strong>{point ? `${point.focus > 0 ? "+" : ""}${(point.focus * 100).toFixed(2)}` : "—"}</strong><span>% · 20日</span></div>
    <ChartLegend items={[
      { label: "焦点动量", color: CHART_COLORS.secondary },
      { label: "涨跌分界", value: "0%", color: CHART_COLORS.zero, dashed: true },
      ...(bands.latest.low !== null && bands.latest.high !== null ? [
        { label: "历史15%分位", value: `${bands.latest.low.toFixed(2)}%`, color: CHART_COLORS.low, dashed: true },
        { label: "历史85%分位", value: `${bands.latest.high.toFixed(2)}%`, color: CHART_COLORS.high, dashed: true },
      ] : []),
    ]} />
    <MiniTrend dates={rows.map(p => p.date)} lines={[
      { name: "焦点动量", color: CHART_COLORS.secondary, values: rows.map(p => p.focus * 100) },
    ]} references={[
      { name: "涨跌分界", color: CHART_COLORS.zero, values: rows.map(() => 0) },
      ...(bands.latest.low !== null && bands.latest.high !== null ? [
        { name: "历史偏低", color: CHART_COLORS.low, values: bands.low.slice(-90), endLabel: `偏低 ${bands.latest.low.toFixed(1)}%` },
        { name: "历史偏高", color: CHART_COLORS.high, values: bands.high.slice(-90), endLabel: `偏高 ${bands.latest.high.toFixed(1)}%` },
      ] : []),
    ]} label="焦点动量：紫色为活跃股过去20日平均涨跌，灰色为零线，青绿虚线为历史偏低参考，橙色虚线为历史偏高参考" />
    <button type="button" className="fmo-preview-open" onClick={open}
      aria-label="打开焦点动量大图，查看价格、穿零点与日期" aria-haspopup="dialog"
      aria-expanded={onOpen ? undefined : expanded}><span aria-hidden="true">看大图 ↗</span></button>
    </div>
    <p className="moa-card-reading">{relative}。0%区分过去20日平均涨跌；低位回升看活跃股修复，高位回落看表现降温，再与市场宽度一起观察扩散。</p>
    <p className="moa-card-change">{change ? <>较{change.previous.date} <b>{change.difference >= 0 ? "+" : ""}{change.difference.toFixed(2)}个百分点</b></> : "前期读数待补齐，当前先看已有水平。"}</p>
    {position !== null && <p className="moa-card-meta">高于历史 {position.toFixed(1)}% 的时期</p>}
    <p className="moa-card-meta">截至 {data?.asOf ?? "—"}{point ? ` · 固定300股样本中选出${point.focusCount}只活跃股` : ""}</p>
    <p className="moa-card-limit">高低线比较此前756日的位置；15%／85%是观察分位，买卖效果未确立。</p>
    <footer><button type="button" onClick={open} aria-haspopup="dialog">看大图 · 价格与穿零点 ↗</button><Link to="/factors?wb=observation">研究依据</Link></footer>
    {expanded && <FocusMomentumDetailDialog onClose={() => setExpanded(false)} />}
  </article>;
}

export function FocusMomentumDetailDialog({ onClose }: { onClose: () => void }) {
  return <ObservationDetailDialog item={OBSERVATION_BY_ID.get("focus-momentum")!} onClose={onClose} />;
}

export function RecentFocusProjection() {
  const query = useRecentFocusMomentum();
  if (query.isPending) return <p role="status">焦点动量读取中…</p>;
  if (query.isError || !query.data) return <p role="alert">焦点动量资料暂不可用。<button type="button" onClick={() => void query.refetch()}>重试</button></p>;
  return <><p className="fmp-note">0%表示当天选出的活跃股过去20日平均持平。上方是平均上涨，下方是平均下跌；用来观察活跃股表现，再结合宽度看强弱是否扩散到更广市场。</p><FocusMomentumPriceProjection data={query.data} />
    <details className="fmp-source"><summary>阈值依据与历史效果</summary>
      <p><strong>0%：过去涨跌分界。</strong><a href="https://www.fidelity.com/learning-center/trading-investing/technical-analysis/technical-indicator-guide/roc" target="_blank" rel="noreferrer">富达的ROC说明</a>用零线区分正负涨跌，并提醒超卖可以持续。这里的负值说明活跃股近期平均下跌，不能直接推导接下来见底。</p>
      <p><strong>极端位置：结合自身历史和趋势。</strong><a href="https://scs.fidelity.com/webcontent/ap010098-etf-content/16.11/help/research/learn_er_glossary_3.shtml" target="_blank" rel="noreferrer">富达旧版ROC指引</a>举过约5%时间落入极端区的做法，区分震荡与趋势环境；未规定适用于本模型的数值或回看窗口。小卡仍用此前756个观察日的15%／85%分位描述相对高低，这是本地显示规则，未经买卖效果验证。</p>
      <p><strong>上穿零：有趋势研究背景，效果要单独看。</strong><a href="https://www.aqr.com/Insights/Research/Journal-Article/Time-Series-Momentum" target="_blank" rel="noreferrer">Moskowitz等人的时间序列动量研究</a>考察58种期货和远期的12个月超额收益方向，不能直接套到这张20日活跃股均值图。</p>
      <p><strong>本图对应的固定300股检验：</strong>2015—2025年114次上穿后，沪深300全收益指数后20日平均+0.49%，上涨50.0%；全部共同日期为+0.59%、53.6%。相似背景内差值−0.06个百分点，95%区间[−0.84, +0.78]，预测增量尚不确定。收益从下一交易日收盘算起，窗口可重叠；图中指数价格不含分红。<a href="/library?report=docs%2Fexperiments%2Ffocus-momentum-threshold-review-2026-11-05.md">查看出处、检验与反例 →</a></p>
    </details>
  </>;
}
