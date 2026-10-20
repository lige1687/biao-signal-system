/** 详情页「近期消息」：该标的近14天资讯流条目（参考层，非交易信号）。
 *
 *  匹配口径与资讯流 /news 一致：symbols 数组 / 标题 / 摘要命中；
 *  板块代码（TH…SECTOR）不会出现在标题里，调用方传「代码,展示名」双匹配。
 *  零消息不渲染（零噪音）；消息与信号同屏互查，互不改写。
 */
import { useQuery } from "@tanstack/react-query";
import { newsApi } from "../api/client";
import type { NewsItem } from "../types";
import CollapsiblePanel from "./CollapsiblePanel";

const DIRECTION_CN: Record<string, { label: string; cls: string }> = {
  bullish: { label: "利多 ↑", cls: "up" },
  bearish: { label: "利空 ↓", cls: "down" },
  neutral: { label: "中性 —", cls: "text-faint" },
};

function daysAgoIso(n: number): string {
  return new Date(Date.now() - n * 86_400_000).toISOString().slice(0, 10);
}

function Row({ it }: { it: NewsItem }) {
  const d = it.direction ? DIRECTION_CN[it.direction] : null;
  return (
    <div className="rn-row">
      <div className="rn-row-head">
        {d && <span className={d.cls}>{d.label}</span>}
        {it.importance != null && (
          <span className="rn-stars" title={`重要性 ${it.importance}/10`}>
            {"★".repeat(Math.max(1, Math.round(it.importance / 2)))}
          </span>
        )}
        {it.importance == null && <span className="text-faint">未评分</span>}
        <span className="rn-meta">
          {(it.source_name || it.source) + " · " + it.published_at.slice(5, 16).replace("T", " ")}
        </span>
      </div>
      <div className="rn-title">
        {it.url ? (
          <a href={it.url} target="_blank" rel="noreferrer">
            {it.title} <span className="text-faint">↗</span>
          </a>
        ) : (
          it.title
        )}
      </div>
      {it.llm_note && <div className="rn-note">{it.llm_note}</div>}
    </div>
  );
}

export default function RecentNewsPanel({
  symbol,
  displayName,
}: {
  symbol: string;
  displayName?: string | null;
}) {
  // 板块代码配展示名双匹配；美股代码单独即可（标题/摘要常直接出现）
  const match = displayName ? `${symbol},${displayName}` : symbol;
  const { data } = useQuery({
    queryKey: ["recentNews", match],
    queryFn: () =>
      newsApi.items({ symbol: match, from: daysAgoIso(14), scored: "all", limit: 15 }),
    staleTime: 5 * 60_000,
    retry: false,
  });
  const items = data?.items ?? [];
  if (items.length === 0) return null;
  return (
    <CollapsiblePanel
      title={`近期消息（${items.length}${data && data.total > items.length ? `/${data.total}` : ""}）`}
      summary="近14天 · 资讯流 · 参考层"
      storageKey="detail.card.news"
      defaultCollapsed={true}
    >
      {items.map((it) => (
        <Row key={it.id} it={it} />
      ))}
    </CollapsiblePanel>
  );
}
