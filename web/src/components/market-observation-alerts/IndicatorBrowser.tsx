import { useEffect, useId, useRef, useState, type ReactNode } from "react";
import type { CandidateSummary } from "./CandidateShelf";
import { MemberDispersionDetail, MemberDispersionSummary } from "./MemberDispersion";
import { isMemberDispersion, useMemberDispersion } from "./memberDispersionData";
import {
  filterIndicators, INDICATOR_CATALOG, INDICATOR_CATEGORIES, type CategoryId, type IndicatorEntry,
} from "./indicatorCatalog";
import "./indicator-browser.css";

interface IndicatorBrowserProps {
  entries?: readonly IndicatorEntry[];
  selectedIds: readonly string[];
  summaries: Readonly<Record<string, CandidateSummary>>;
  onSetPinned: (id: string, pinned: boolean) => void;
  onPreview: (id: string) => void;
  previewId: string | null;
  preview: ReactNode;
  onClosePreview: () => void;
  renderThumbnail?: (id: string) => ReactNode;
}

const MARKET_LABELS: Record<IndicatorEntry["market"], string> = {
  cn: "A股",
  us: "美股",
  global: "跨市场",
};

function PinButton({ item, pinned, onSetPinned }: {
  item: IndicatorEntry;
  pinned: boolean;
  onSetPinned: IndicatorBrowserProps["onSetPinned"];
}) {
  return <button type="button" className="mib-button mib-pin" disabled={!item.readable && !pinned}
    onClick={() => onSetPinned(item.id, !pinned)}>
    {pinned ? "移出首页" : "加入首页"}
  </button>;
}

function LazyThumbnail({ id, children }: { id: string; children: ReactNode }) {
  const container = useRef<HTMLDivElement>(null);
  const [visible, setVisible] = useState(false);
  useEffect(() => {
    if (!container.current || typeof IntersectionObserver === "undefined") { setVisible(true); return; }
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { setVisible(true); observer.disconnect(); }
    }, { rootMargin: "240px" });
    observer.observe(container.current);
    return () => observer.disconnect();
  }, []);
  return <div ref={container} className="mib-thumbnail" data-indicator-thumbnail={id}>
    {visible ? children : <p className="mib-thumbnail-loading">正在准备趋势小图…</p>}
  </div>;
}

function DispersionBrowserContent({ id, detail = false, fallback }: {
  id: string; detail?: boolean; fallback: ReactNode;
}) {
  const card = useMemberDispersion(id);
  if (!card) return fallback;
  return detail ? <MemberDispersionDetail card={card} /> : <MemberDispersionSummary card={card} />;
}

export default function IndicatorBrowser({
  entries = INDICATOR_CATALOG, selectedIds, summaries, onSetPinned, onPreview, previewId, preview, onClosePreview, renderThumbnail,
}: IndicatorBrowserProps) {
  const [category, setCategory] = useState<CategoryId | "all">("all");
  const [market, setMarket] = useState<IndicatorEntry["market"] | "all">("all");
  const [query, setQuery] = useState("");
  const [includePending, setIncludePending] = useState(false);
  const headingId = useId();
  const previewRegionId = useId();
  const previewHeading = useRef<HTMLHeadingElement>(null);
  const searchInput = useRef<HTMLInputElement>(null);
  const opener = useRef<HTMLButtonElement | null>(null);

  const results = filterIndicators({ category, market, query, includePending }, entries);
  const groups = INDICATOR_CATEGORIES.map((group) => ({
    ...group,
    items: results.filter((item) => item.category === group.id),
  })).filter((group) => group.items.length > 0);
  const pinned = new Set(selectedIds);
  const previewItem = entries.find((item) => item.id === previewId);
  const activePreviewId = previewItem?.id;

  useEffect(() => {
    const title = previewHeading.current;
    if (activePreviewId && title) {
      title.focus({ preventScroll: true });
      title.scrollIntoView({ block: "nearest" });
    } else if (opener.current) {
      const target = opener.current.isConnected ? opener.current : searchInput.current;
      target?.focus({ preventScroll: true });
      target?.scrollIntoView({ block: "nearest" });
      opener.current = null;
    }
  }, [activePreviewId]);

  return <section className="mib-browser" aria-labelledby={headingId}>
    <header className="mib-header">
      <h2 id={headingId}>指标库</h2>
    </header>
    <div className="mib-categories" role="group" aria-label="指标分类">
      <button type="button" className="mib-button" aria-pressed={category === "all"}
        onClick={() => setCategory("all")}>全部</button>
      {INDICATOR_CATEGORIES.map(({ id, label }) => <button key={id} type="button" className="mib-button"
        aria-pressed={category === id} onClick={() => setCategory(id)}>{label}</button>)}
    </div>
    <div className="mib-filters">
      <label className="mib-search">
        <span>搜索指标</span>
        <input ref={searchInput} type="search" value={query} placeholder="名称或 ETF 代码"
          onChange={(event) => setQuery(event.currentTarget.value)} />
      </label>
      <label>
        <span>市场</span>
        <select value={market} onChange={(event) => setMarket(event.currentTarget.value as typeof market)}>
          <option value="all">全部市场</option>
          {Object.entries(MARKET_LABELS).map(([id, label]) => <option key={id} value={id}>{label}</option>)}
        </select>
      </label>
      <label className="mib-status-filter">
        <input type="checkbox" checked={includePending}
          onChange={(event) => setIncludePending(event.currentTarget.checked)} />
        显示待接入指标
      </label>
    </div>
    {previewItem && <section className="mib-preview" id={previewRegionId} aria-label={`${previewItem.label}预览`}>
      <div className="mib-preview-header">
        <div>
          <h3 ref={previewHeading} tabIndex={-1}>{previewItem.label}</h3>
          {!isMemberDispersion(previewItem.id) && <p>{previewItem.meaning}</p>}
        </div>
        <div className="mib-actions">
          <PinButton item={previewItem} pinned={pinned.has(previewItem.id)} onSetPinned={onSetPinned} />
          <button type="button" className="mib-button" onClick={onClosePreview}>关闭预览</button>
        </div>
      </div>
      {previewItem.readable
        ? isMemberDispersion(previewItem.id)
          ? <DispersionBrowserContent key={previewItem.id} id={previewItem.id} detail fallback={preview} />
          : preview
        : <p className="mib-limitation">{previewItem.limitation}</p>}
    </section>}
    <p className="mib-count" role="status">{results.length} 项指标</p>
    {groups.length === 0 && <p className="mib-empty">没有符合当前筛选条件的指标。</p>}
    {groups.map(({ id, label, items }) => <section key={id} className="mib-group"
      aria-labelledby={`${headingId}-${id}`}>
      <h3 id={`${headingId}-${id}`}>{label}</h3>
      <ul className="mib-grid">
        {items.map((item) => {
          const isPinned = pinned.has(item.id);
          const summary = summaries[`${item.market}:${item.id}`] ?? summaries[item.id];
          const itemHeadingId = `${headingId}-${item.id}`;
          const dispersion = isMemberDispersion(item.id);
          return <li key={item.id}>
            <article className="mib-item" aria-labelledby={itemHeadingId}>
              <div className="mib-tags">
                <span>{MARKET_LABELS[item.market]}</span>
                {isPinned && <span className="mib-pinned">已在首页</span>}
                {!item.readable && <span className="mib-pending">待接入</span>}
              </div>
              <h4 id={itemHeadingId}>{item.label}</h4>
              {!dispersion && <p>{item.meaning}</p>}
              {item.readable && !renderThumbnail && summary && <p className="mib-reading">
                <strong>{summary.value}</strong>{summary.date && <time>{summary.date}</time>}
              </p>}
              {item.readable && renderThumbnail && <LazyThumbnail id={item.id}>
                {dispersion
                  ? <DispersionBrowserContent id={item.id} fallback={renderThumbnail(item.id)} />
                  : renderThumbnail(item.id)}
              </LazyThumbnail>}
              {!item.readable && <p className="mib-limitation">{item.limitation}</p>}
              <div className="mib-actions">
                <button type="button" className="mib-button mib-view" aria-label={`查看${item.label}`}
                  aria-expanded={previewItem?.id === item.id}
                  aria-controls={previewItem?.id === item.id ? previewRegionId : undefined}
                  onClick={(event) => {
                    opener.current = event.currentTarget;
                    if (previewItem?.id === item.id) {
                      previewHeading.current?.focus({ preventScroll: true });
                      previewHeading.current?.scrollIntoView({ block: "nearest" });
                    } else {
                      onPreview(item.id);
                    }
                  }}>{item.readable ? "展开图表与口径" : "查看缺项"}</button>
                <PinButton item={item} pinned={isPinned} onSetPinned={onSetPinned} />
              </div>
            </article>
          </li>;
        })}
      </ul>
    </section>)}
  </section>;
}
