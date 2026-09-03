import { useMemo, useRef, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { newsApi } from "../api/client";
import type { NewsItem } from "../types";

/**
 * 资讯流：基本面消息检索与排序（宏观/系统性风险/政策/行业公司 + 博主观点）。
 *
 * 红线对齐（与后端 newsfeed 一致）：
 * - 参考层：LLM 打分是"重要性/类别/方向"的结构化工序，不是交易信号；
 * - 排序 = importance 降序（已评分在前），未评分条目垫底按时间倒序；
 * - 数据日更（launchd 20:30），「立即刷新」走后台管线。
 *
 * 页面结构（按信息优先级，2026-08-27 用户反馈调整）：
 *   1. 今日要点 = 最新简报的 top_events（当天最关键的几条，大卡）+ 分类归纳（折叠）
 *   2. 博主观点 = 按博主分组（谁说了啥），每人近 2 天最新观点
 *   3. 关键消息 = 默认只看近 1 天 importance≥5，「显示全部」放宽
 */

const CATEGORY_CN: Record<string, string> = {
  macro: "宏观",
  risk: "系统性风险",
  policy: "政策",
  industry: "行业与公司",
  blogger: "博主观点",
};

const CATEGORY_ORDER = ["macro", "risk", "policy", "industry", "blogger"];

const SOURCE_CN: Record<string, string> = {
  eastmoney: "东财快讯",
  sina: "新浪7x24",
  gnews: "Google News",
  rss: "RSS",
  wechat: "公众号",
  bilibili: "B站",
};

const DIRECTION_CN: Record<string, { label: string; cls: string }> = {
  bullish: { label: "利多 ↑", cls: "up" },
  bearish: { label: "利空 ↓", cls: "down" },
  neutral: { label: "中性 —", cls: "text-faint" },
};

type RangeKey = "1d" | "3d" | "7d" | "30d" | "all";

const RANGES: { key: RangeKey; label: string; days: number | null }[] = [
  { key: "1d", label: "近1天", days: 1 },
  { key: "3d", label: "近3天", days: 3 },
  { key: "7d", label: "近7天", days: 7 },
  { key: "30d", label: "近30天", days: 30 },
  { key: "all", label: "全部", days: null },
];

function dayLabel(publishedAt: string): string {
  const d = publishedAt.slice(5, 10).replace("-", "/");
  const today = new Date().toISOString().slice(0, 10);
  const yesterday = new Date(Date.now() - 86_400_000).toISOString().slice(0, 10);
  if (publishedAt.slice(0, 10) === today) return "今天";
  if (publishedAt.slice(0, 10) === yesterday) return "昨天";
  return d;
}

function Stars({ importance }: { importance: number | null }) {
  if (importance == null) {
    return <span className="nf-unscored" title="LLM 尚未评分（每日 20:30 批量整合）">未评分</span>;
  }
  const stars = Math.max(1, Math.round(importance / 2));
  return (
    <span className="nf-stars" title={`重要性 ${importance}/10`}>
      {"★".repeat(stars)}
      <span className="nf-stars-dim">{"★".repeat(5 - stars)}</span>
    </span>
  );
}

function DirectionTag({ direction }: { direction: string | null }) {
  if (!direction) return null;
  const d = DIRECTION_CN[direction];
  if (!d) return null;
  return <span className={d.cls}>{d.label}</span>;
}

function ItemCard({ item }: { item: NewsItem }) {
  return (
    <div className="nf-card">
      <div className="nf-card-head">
        <Stars importance={item.importance} />
        {item.category && (
          <span className={`nf-cat nf-cat-${item.category}`}>
            {CATEGORY_CN[item.category] ?? item.category}
          </span>
        )}
        <DirectionTag direction={item.direction} />
        {item.symbols.length > 0 && (
          <span className="nf-symbols">
            {item.symbols.map((s) => (
              <span key={s} className="stage-chip neutral-info">{s}</span>
            ))}
          </span>
        )}
      </div>
      <div className="nf-title">
        {item.url ? (
          <a href={item.url} target="_blank" rel="noreferrer">
            {item.title}
            <span className="nf-link-hint"> ↗</span>
          </a>
        ) : (
          item.title
        )}
      </div>
      {item.llm_note && <div className="nf-note">{item.llm_note}</div>}
      {!item.llm_note && item.summary && <div className="nf-summary">{item.summary}</div>}
      <div className="nf-meta">
        <span className="text-dim">
          {SOURCE_CN[item.source] ?? item.source}
          {item.source_name ? ` · ${item.source_name}` : ""}
        </span>
        <span className="text-faint">{item.published_at.slice(5, 16).replace("T", " ")}</span>
      </div>
    </div>
  );
}

/** 顶部：今日要点（top_events 大卡）+ 分类归纳（折叠）。 */
function DigestHeadline() {
  const { data } = useQuery({
    queryKey: ["newsDigests"],
    queryFn: () => newsApi.digests(3),
    staleTime: 5 * 60_000,
  });
  const digest = data?.digests?.[0];
  if (!digest) return null;
  const sections = [...(digest.payload.sections ?? [])].sort(
    (a, b) => CATEGORY_ORDER.indexOf(a.category) - CATEGORY_ORDER.indexOf(b.category),
  );
  const tops = digest.payload.top_events ?? [];
  return (
    <div className="nf-digest">
      <div className="nf-digest-head">
        <h2>今日要点</h2>
        <span className="text-faint">{digest.digest_date} · 整合简报</span>
      </div>
      {tops.length === 0 && sections.length === 0 && (
        <div className="text-faint">本日暂无整合内容。</div>
      )}
      {tops.length > 0 && (
        <div className="nf-tops">
          {tops.map((e, i) => (
            <div key={i} className="nf-top">
              <span className="nf-top-rank">{i + 1}</span>
              <div className="nf-top-body">
                <div className="nf-top-line">
                  <span className="nf-top-title">{e.title}</span>
                  <Stars importance={e.importance} />
                </div>
                <div className="nf-top-why">{e.why}</div>
              </div>
            </div>
          ))}
        </div>
      )}
      {sections.length > 0 && (
        <details className="nf-detail">
          <summary>分类归纳（宏观/风险/政策/行业）</summary>
          {sections.map((s) => (
            <div key={s.category} className="nf-digest-section">
              <div className="nf-digest-title">
                <span className={`nf-cat nf-cat-${s.category}`}>
                  {CATEGORY_CN[s.category] ?? s.category}
                </span>
                {s.headline}
              </div>
              <ul>
                {s.bullets.map((b, i) => (
                  <li key={i}>{b}</li>
                ))}
              </ul>
            </div>
          ))}
        </details>
      )}
    </div>
  );
}

/** 博主观点板：按博主分组——"谁、哪天、说了啥"。 */
function BloggerBoard() {
  const { data } = useQuery({
    queryKey: ["newsBloggerBoard"],
    queryFn: () =>
      newsApi.items({ category: "blogger", from: daysAgo(2), limit: 40, scored: "all" }),
    staleTime: 5 * 60_000,
  });
  const groups = useMemo(() => {
    const byName = new Map<string, NewsItem[]>();
    for (const it of data?.items ?? []) {
      const name = it.source_name || (SOURCE_CN[it.source] ?? it.source);
      if (!byName.has(name)) byName.set(name, []);
      byName.get(name)!.push(it);
    }
    // 每人最多展示 3 条（最新的在前——API 已按重要性排序，组内改按时间）
    const latestOf = (items: NewsItem[]) =>
      items.reduce((m, i) => (i.published_at > m ? i.published_at : m), "");
    return [...byName.entries()]
      .map(([name, items]) => [
        name,
        [...items].sort((a, b) => b.published_at.localeCompare(a.published_at)).slice(0, 3),
      ] as [string, NewsItem[]])
      .sort((a, b) => latestOf(b[1]).localeCompare(latestOf(a[1])));
  }, [data]);
  if (!groups.length) return null;
  const AVATAR_HUES = 5;
  return (
    <div className="nf-bloggers">
      <h2 className="nf-section-title">
        博主观点 <span className="fund-count">近2天 · {groups.length} 位</span>
      </h2>
      <div className="nf-blogger-grid">
        {groups.map(([name, items], gi) => (
          <div key={name} className="nf-blogger">
            <div className="nf-blogger-head">
              <span className={`nf-avatar hue-${gi % AVATAR_HUES}`}>
                {name.slice(0, 1)}
              </span>
              <span className="nf-blogger-name">{name}</span>
            </div>
            {items.map((it) => (
              <div key={it.id} className="nf-blogger-item">
                <div className="nf-blogger-item-row">
                  <span className="nf-blogger-day">{dayLabel(it.published_at)}</span>
                  {it.url ? (
                    <a href={it.url} target="_blank" rel="noreferrer" className="nf-blogger-title">
                      {it.title}
                    </a>
                  ) : (
                    <span className="nf-blogger-title">{it.title}</span>
                  )}
                </div>
                {it.llm_note && <div className="nf-blogger-note">{it.llm_note}</div>}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}

function daysAgo(n: number): string {
  return new Date(Date.now() - n * 86_400_000).toISOString().slice(0, 10);
}

export default function NewsPage() {
  const [focus, setFocus] = useState(true); // 聚焦模式：近1天 + importance≥5
  const [category, setCategory] = useState<string>("");
  const [source, setSource] = useState<string>("");
  const [range, setRange] = useState<RangeKey>("1d");
  const [search, setSearch] = useState("");
  const [queryText, setQueryText] = useState("");
  const debounceRef = useRef<number | null>(null);
  const queryClient = useQueryClient();
  const [running, setRunning] = useState(false);
  const pollRef = useRef<number | null>(null);

  const effectiveRange: RangeKey = focus ? "1d" : range;
  const from = useMemo(() => {
    const r = RANGES.find((x) => x.key === effectiveRange);
    if (!r?.days) return undefined;
    return new Date(Date.now() - r.days * 86_400_000).toISOString().slice(0, 10);
  }, [effectiveRange]);

  const { data, isLoading, error } = useQuery({
    queryKey: ["newsItems", category, source, effectiveRange, queryText, focus],
    queryFn: () =>
      newsApi.items({
        category: category || undefined,
        source: source || undefined,
        from,
        q: queryText || undefined,
        scored: focus ? "scored" : "all",
        min_importance: focus ? 6 : undefined,
        limit: focus ? 25 : 100,
      }),
    staleTime: 60_000,
  });

  const onSearchInput = (value: string) => {
    setSearch(value);
    if (debounceRef.current) window.clearTimeout(debounceRef.current);
    debounceRef.current = window.setTimeout(() => setQueryText(value.trim()), 400);
  };

  const onRefresh = async () => {
    if (running) return;
    setRunning(true);
    try {
      await newsApi.run();
      const started = Date.now();
      pollRef.current = window.setInterval(async () => {
        try {
          const st = await newsApi.status();
          const last = st.last_run;
          if ((last && last.finished_at) || Date.now() - started > 90_000) {
            if (pollRef.current) window.clearInterval(pollRef.current);
            setRunning(false);
            void queryClient.invalidateQueries({ queryKey: ["newsItems"] });
            void queryClient.invalidateQueries({ queryKey: ["newsDigests"] });
            void queryClient.invalidateQueries({ queryKey: ["newsBloggerBoard"] });
          }
        } catch {
          /* 轮询失败继续 */
        }
      }, 3000);
    } catch {
      setRunning(false);
    }
  };

  return (
    <div className="page">
      <div className="header">
        <h1>
          资讯流{" "}
          <span className="fund-count">
            {focus ? "今天重点" : data ? `${data.total} 条` : ""}
          </span>
        </h1>
        <span className="generated">每日 20:30 自动整合 · 参考层，非交易信号</span>
        <span className="spacer" />
        <button className="btn primary" onClick={onRefresh} disabled={running}>
          {running ? "抓取中…" : "立即刷新"}
        </button>
      </div>

      <DigestHeadline />
      <BloggerBoard />

      <div className="nf-toolbar">
        <button className={`nf-focus-btn ${focus ? "active" : ""}`} onClick={() => setFocus((f) => !f)}>
          {focus ? "★ 今天重点（近1天·重要性≥6·前25条）" : "显示今天重点"}
        </button>
        <div className="nf-tabs">
          <button className={!category ? "active" : ""} onClick={() => setCategory("")}>
            全部
          </button>
          {CATEGORY_ORDER.map((c) => (
            <button
              key={c}
              className={category === c ? "active" : ""}
              onClick={() => setCategory(category === c ? "" : c)}
            >
              {CATEGORY_CN[c]}
            </button>
          ))}
        </div>
        <select value={source} onChange={(e) => setSource(e.target.value)}>
          <option value="">全部来源</option>
          {Object.entries(SOURCE_CN).map(([k, v]) => (
            <option key={k} value={k}>{v}</option>
          ))}
        </select>
        {!focus && (
          <select value={range} onChange={(e) => setRange(e.target.value as RangeKey)}>
            {RANGES.map((r) => (
              <option key={r.key} value={r.key}>{r.label}</option>
            ))}
          </select>
        )}
        <input
          className="nf-search"
          placeholder="关键词搜索（标题/摘要/点评）"
          value={search}
          onChange={(e) => onSearchInput(e.target.value)}
        />
      </div>

      {isLoading && <div className="legend">加载中…</div>}
      {error != null && (
        <div className="fund-errors">
          <div className="fund-error">资讯流加载失败：{String(error)}</div>
          <div className="fund-hint">确认后端已升级（含 /api/news 路由）并执行 biao restart。</div>
        </div>
      )}
      {data && data.items.length === 0 && (
        <div className="legend">
          {focus ? "今天还没有高分条目——点上方按钮「显示全部」看全量。" : "没有符合条件的条目。"}
        </div>
      )}
      {data && data.items.length > 0 && (
        <div className="nf-list">
          {data.items.map((it) => (
            <ItemCard key={it.id} item={it} />
          ))}
        </div>
      )}
    </div>
  );
}
