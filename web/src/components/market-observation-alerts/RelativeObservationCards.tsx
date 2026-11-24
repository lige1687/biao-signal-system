import { useEffect, useMemo, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useQuery } from "@tanstack/react-query";
import MarketTrendChart from "../market-style/MarketTrendChart";
import type { CandidateSummary } from "./CandidateShelf";
import ChartLegend from "./ChartLegend";
import MiniTrend from "./MiniTrend";
import {
  parseRelativeObservationSnapshot, relativeObservationReading, RELATIVE_OBSERVATION_CARDS,
  type RelativeObservationCard, type RelativeObservationPoint,
} from "./relativeObservationData";
import "./increment-observation.css";
import "./relative-observation.css";

const SOURCE = "/research/relative-market-observations-20261108/data.json";
const PERIODS = [120, 252, "all"] as const;
const SNAPSHOT_NOTE = "未自动按日更新";

function chartSeries(points: RelativeObservationPoint[], term: boolean) {
  return [
    { name: "实际比值", color: "#28629e", values: points.map((point) => point.ratio) },
    { name: term ? "1倍 · 两者相同" : "60日均线", color: "#67747e", dashed: true,
      values: points.map((point) => term ? 1 : point.ma60) },
  ];
}

function interpretation(card: RelativeObservationCard) {
  return card.kind === "term"
    ? "1倍表示两者相同。比值越高，短期隐含波动率相对3个月越高。"
    : "比值上升表示前者相对更强，下降表示前者相对更弱。";
}

function RelativeObservationDetail({ card, onClose, trigger }: {
  card: RelativeObservationCard; onClose: () => void; trigger: HTMLButtonElement | null;
}) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [ready, setReady] = useState(false);
  const [period, setPeriod] = useState<typeof PERIODS[number]>(120);
  const term = card.kind === "term";
  const { latest, prior, headline, comparison, value } = relativeObservationReading(card);
  const points = useMemo(() => period === "all" ? card.points : card.points.slice(-period), [card.points, period]);
  const series = useMemo(() => chartSeries(points, term), [points, term]);
  const dates = useMemo(() => points.map(({ date }) => date), [points]);

  useEffect(() => {
    const node = dialog.current;
    if (!node) return;
    node.showModal();
    setReady(true);
    return () => {
      node.close();
      if (trigger?.isConnected) trigger.focus({ preventScroll: true });
    };
  }, [trigger]);

  return createPortal(<dialog ref={dialog} className="io-dialog ro-dialog" aria-label={card.title}
    onCancel={(event) => { event.preventDefault(); onClose(); }}
    onClick={(event) => { if (event.target === event.currentTarget) onClose(); }}>
    <div className="io-dialog-surface">
      <header><h2>{card.title}</h2><button type="button" onClick={onClose}>关闭 ×</button></header>
      <p className="io-detail-lead">截至 {latest.date} · {value}{term && ` · ${headline}`}</p>
      <p className="io-range">较 {prior.date}（20个共同交易日前），比值{comparison}。</p>
      {term && <p className="io-range">VIX {latest.numerator.toFixed(2)}% · VIX3M {latest.denominator.toFixed(2)}%</p>}
      <div className="io-period" role="group" aria-label="图表时间范围">
        {PERIODS.map((range) => <button key={range} type="button" aria-pressed={period === range}
          onClick={() => setPeriod(range)}>{range === "all" ? "全部" : `近${range}日`}</button>)}
      </div>
      <p className="io-range">{dates[0]} 至 {dates[dates.length - 1]} · 拖动滑块或滚轮缩放</p>
      {ready && <MarketTrendChart dates={dates} series={series} unit="倍" height={360} precision={term ? 3 : 4} />}
      <p className="io-explain">{interpretation(card)}{!term && "虚线是最近60个共同交易日的平均比值。"}</p>
      <p className="io-explain">比值为 {card.numerator.label} ÷ {card.denominator.label}，取两者都有读数的日期。{card.price_note}</p>
      <p className="io-source">历史快照 · {SNAPSHOT_NOTE}。{card.sources.map(({ name, url }) =>
        <a key={`${name}-${url}`} href={url} target="_blank" rel="noreferrer">{name}</a>)}</p>
    </div>
  </dialog>, document.body);
}

function ObservationCard({ card, onCollapse }: { card: RelativeObservationCard; onCollapse: () => void }) {
  const [open, setOpen] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null);
  const term = card.kind === "term";
  const { latest, prior, headline, comparison, value } = relativeObservationReading(card);
  const points = card.points.slice(-120);
  const [line, reference] = chartSeries(points, term);

  return <article className="moa-item io-card ro-card" data-overview-card={card.id} data-tone="neutral" aria-label={card.title}>
    <div className="moa-item-head"><h3>{card.title}</h3></div>
    <p className="ro-asof">截至 {latest.date} · 历史快照</p>
    <p className="ro-current"><strong>{value}</strong><span>{headline}</span></p>
    <p className="io-comparison">
      {term ? <>较 {prior.date}（20个共同交易日前），比值{comparison}。</> : <>与 {prior.date} 比较</>}
    </p>
    {term && <p className="ro-levels"><span>VIX <b>{latest.numerator.toFixed(2)}%</b></span>
      <span>VIX3M <b>{latest.denominator.toFixed(2)}%</b></span></p>}
    <ChartLegend items={[
      { label: line.name, color: line.color },
      { label: reference.name, color: reference.color, dashed: true },
    ]} />
    <MiniTrend dates={points.map(({ date }) => date)} lines={[line]} references={[reference]}
      label={`${card.title}近120个共同交易日的比值，单位为倍。实线为实际比值，虚线为${reference.name}。`} />
    <p className="io-scope-note">{interpretation(card)}</p>
    <p className="ro-asof">{SNAPSHOT_NOTE}</p>
    <footer>
      <button ref={trigger} type="button" aria-haspopup="dialog" onClick={() => setOpen(true)}>看历史与口径</button>
      <button type="button" onClick={onCollapse}>收起</button>
    </footer>
    {open && <RelativeObservationDetail card={card} onClose={() => setOpen(false)} trigger={trigger.current} />}
  </article>;
}

export default function RelativeObservationCards({ market, selectedIds, collapsedIds, onCollapse, onSummary }: {
  market: "cn" | "us"; selectedIds: readonly string[]; collapsedIds: readonly string[];
  onCollapse: (id: string) => void; onSummary: (id: string, summary: CandidateSummary) => void;
}) {
  const selected = useMemo(() => RELATIVE_OBSERVATION_CARDS.filter((card) => card.market === market && selectedIds.includes(card.id)),
    [market, selectedIds]);
  const visible = selected.filter(({ id }) => !collapsedIds.includes(id));
  const query = useQuery({
    queryKey: ["relativeObservationSnapshotV1"], enabled: selected.length > 0,
    queryFn: async ({ signal }) => {
      const response = await fetch(SOURCE, { signal, cache: "no-cache" });
      if (!response.ok) throw new Error("Observation snapshot unavailable");
      return parseRelativeObservationSnapshot(await response.json());
    },
    staleTime: 5 * 60_000, retry: false,
  });
  const { data, isError, isFetching } = query;

  useEffect(() => {
    selected.forEach(({ id }) => {
      const card = data?.cards.find((entry) => entry.id === id);
      if (card) {
        const { latest, value, headline } = relativeObservationReading(card);
        onSummary(id, { value, date: latest.date, meaning: `${headline} · 历史快照 · ${SNAPSHOT_NOTE}` });
      } else {
        const failed = isError && !isFetching;
        onSummary(id, { value: failed ? "读取失败" : "读取中",
          meaning: failed ? "历史快照暂不可用，可恢复卡片后重试" : "历史快照读取中" });
      }
    });
  }, [selected, data, isError, isFetching, onSummary]);

  return <>{visible.map(({ id, title }) => {
    const card = data?.cards.find((entry) => entry.id === id);
    if (card) return <ObservationCard key={id} card={card} onCollapse={() => onCollapse(id)} />;
    const failed = isError && !isFetching;
    return <article className="moa-item io-card ro-card" data-overview-card={id} key={id} aria-label={title}>
      <div className="moa-item-head"><h3>{title}</h3></div>
      <p className="io-scope-note" role={failed ? "alert" : "status"}>
        {failed ? "历史快照暂不可用。" : "历史快照读取中…"}
      </p>
      <footer>
        {failed && <button type="button" onClick={() => void query.refetch()}>重试</button>}
        <button type="button" onClick={() => onCollapse(id)}>收起</button>
      </footer>
    </article>;
  })}</>;
}
