import { useEffect, useMemo, useState } from "react";
import ObservationMetric from "./ObservationMetric";
import { GROUP_LABELS, OBSERVATION_BY_ID, OBSERVATION_CATALOG, OBSERVATION_SECTIONS, observationReadingRank, observationSection, type ObservationEntry, type ObservationMarket } from "./catalog";
import { useObservationPreferences } from "./usePreferences";
import "./observation-library.css";

type MarketFilter = "all" | "cn" | "us";
type StatusFilter = "all" | "readable" | "pending";

const MARKET_NAME: Record<ObservationMarket, string> = { cn: "A股", us: "美股", global: "跨市场" };
const MARKET_FILTERS: readonly MarketFilter[] = ["all", "cn", "us"];
const MARKET_FILTER_NAME: Record<MarketFilter, string> = { all: "全部市场", cn: "A股", us: "美股" };

function matchesMarket(item: ObservationEntry, market: MarketFilter) {
  return market === "all" || item.market === market || item.market === "global";
}

/** The catalogue is initially closed. Opening one row mounts one data adapter at most. */
export function ObservationLibrary({ market }: { market?: "cn" | "us" }) {
  const { pinnedIds, warning, setPinned } = useObservationPreferences();
  const [open, setOpen] = useState(false);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [search, setSearch] = useState("");
  const [marketFilter, setMarketFilter] = useState<MarketFilter>(market ?? "all");
  const [statusFilter, setStatusFilter] = useState<StatusFilter>("all");
  useEffect(() => { if (market) setMarketFilter(market); }, [market]);
  const matching = useMemo(() => {
    const term = search.trim().toLocaleLowerCase("zh-CN");
    return OBSERVATION_CATALOG.filter((item) =>
      matchesMarket(item, marketFilter)
      && (statusFilter === "all" || item.readable === (statusFilter === "readable"))
      && (!term || `${item.label} ${item.candidate} ${item.meaning} ${GROUP_LABELS[item.group]}`.toLocaleLowerCase("zh-CN").includes(term)))
      .sort((a, b) => observationReadingRank(a) - observationReadingRank(b));
  }, [marketFilter, search, statusFilter]);
  const availableCount = OBSERVATION_CATALOG.filter((item) => matchesMarket(item, marketFilter) && item.readable).length;

  const renderItem = (item: ObservationEntry) => {
    const active = activeId === item.id;
    const pinned = pinnedIds.includes(item.id);
    return <article className={`ol-item${active ? " is-open" : ""}`} key={item.id}>
      <div className="ol-row">
        <button type="button" className="ol-row-main" aria-expanded={active} aria-controls={`ol-detail-${item.id}`} onClick={() => setActiveId(active ? null : item.id)}>
          <span className="ol-row-text"><b>{item.label}</b><small>{item.meaning}</small></span>
          <span className="ol-market">{MARKET_NAME[item.market]}</span>
          <span className="ol-chevron" aria-hidden="true">{active ? "−" : "+"}</span>
        </button>
        <button type="button" className={`ol-pin${pinned ? " is-pinned" : ""}`} disabled={!item.readable}
          aria-label={`${pinned ? "从首页收回" : "放到首页"}：${item.label}`}
          title={item.readable ? undefined : item.limitation} onClick={() => setPinned(item.id, !pinned)}>
          {pinned ? "收回" : item.readable ? "放首页" : "待接入"}
        </button>
      </div>
      {active && <div className="ol-detail" id={`ol-detail-${item.id}`}>
        {item.readable ? <>
          {item.id !== "baker-wurgler" && <p className="ol-detail-limit">{item.limitation}</p>}
          <ObservationMetric id={item.id} />
        </> : <p className="ol-pending">{item.limitation}</p>}
      </div>}
    </article>;
  };

  return <section className="ol-library" aria-label="市场观察库">
    <button className="ol-trigger" type="button" aria-expanded={open} onClick={() => setOpen((value) => !value)}>
      <span><b>市场观察库</b><small>{availableCount} 项可查看 · 按观察用途排序</small></span>
      <span className="ol-trigger-right">已放首页 {pinnedIds.length} 项 <span aria-hidden="true">{open ? "收起 ↑" : "展开 ↓"}</span></span>
    </button>
    {open && <div className="ol-body">
      <p className="ol-note">按日常查看顺序排列，可自行放到首页。读数日期见展开项；排序不代表预测能力。</p>
      {warning && <p className="ol-warning" role="status">{warning}</p>}
      <div className="ol-controls">
        <label>查找观察项<input type="search" value={search} onChange={(event) => setSearch(event.target.value)} placeholder="搜索指标或想观察的问题" /></label>
        <label>市场<select value={marketFilter} onChange={(event) => setMarketFilter(event.target.value as MarketFilter)}>
          {MARKET_FILTERS.map((filter) => <option value={filter} key={filter}>{MARKET_FILTER_NAME[filter]}</option>)}
        </select></label>
        <label>资料状态<select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value as StatusFilter)}>
          <option value="all">全部状态</option><option value="readable">可查看</option><option value="pending">待接入</option>
        </select></label>
      </div>
      <p className="ol-count" role="status">{matching.filter((item) => item.readable).length} 项可查看，{matching.filter((item) => !item.readable).length} 项待接入</p>
      {OBSERVATION_SECTIONS.map((section) => {
        const items = matching.filter((item) => observationSection(item) === section.id);
        if (!items.length) return null;
        if (section.id === "pending") return <details className="ol-pending-group" key={`${section.id}-${Boolean(search.trim())}-${statusFilter}`} open={Boolean(search.trim()) || statusFilter === "pending"}>
          <summary>待接入 <span>{items.length}</span><small>含 ETF 规模与份额、盈利等候选</small></summary>
          <div className="ol-list">{items.map(renderItem)}</div>
        </details>;
        return <section className="ol-section" key={section.id} aria-label={section.label}>
          <header><h3>{section.label}<span>{items.length}</span></h3><p>{section.note}</p></header>
          <div className="ol-list">{items.map(renderItem)}</div>
        </section>;
      })}
      {!matching.length && <p className="ol-empty">没有符合筛选条件的观察项。</p>}
    </div>}
  </section>;
}

/** The home mounts data only for the user's chosen entries. */
export function ObservationHome() {
  const { pinnedIds, warning, setPinned } = useObservationPreferences();
  const orderedPins = pinnedIds.map((id) => OBSERVATION_BY_ID.get(id)).filter((item): item is ObservationEntry => !!item?.readable)
    .sort((a, b) => observationReadingRank(a) - observationReadingRank(b));
  return <section className="ol-home" aria-label="首页市场观察">
    <ObservationLibrary />
    {warning && <p className="ol-warning" role="status">{warning}</p>}
    {orderedPins.length > 0 && <div className="ol-home-list">{orderedPins.map((item) => {
      return <article className="ol-home-item" key={item.id}>
        <div className="ol-home-item-head"><strong>{item.label}</strong><button type="button" onClick={() => setPinned(item.id, false)} aria-label={`从首页收回：${item.label}`}>收回</button></div>
        <ObservationMetric id={item.id} compact />
      </article>;
    })}</div>}
  </section>;
}
