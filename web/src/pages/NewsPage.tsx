import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { api, newsApi } from "../api/client";
import type { NewsItem, NewsMood, NewsWatchEntry } from "../types";

/**
 * 资讯流：基本面消息检索与排序（宏观/系统性风险/政策/行业公司 + 博主观点）。
 *
 * 红线对齐（与后端 newsfeed 一致）：
 * - 参考层：LLM 打分是"重要性/类别/方向"的结构化工序，不是交易信号；
 * - 排序 = importance 降序（已评分在前），未评分条目垫底按时间倒序；
 * - 数据日更（launchd 20:30），「立即刷新」走后台管线。
 *
 * 页面结构（按信息优先级，2026-08-27 用户反馈调整 + 2026-09-03 交易联动）：
 *   1. 自选消息雷达 = 我的自选 × 近3天消息：多空温度计 + 每标的多空计数/最新一条，
 *      卡片叠加该标的当前交易信号徽标（买·行动/卖·硬…）——消息与技术面同屏对照；
 *      点击标的直达该标的消息流（自动放宽到近30天全量）——把消息对齐到自选视角
 *   2. 今日要点 = 最新简报的 top_events（当天最关键的几条，大卡）+ 分类归纳（折叠）
 *   3. 博主观点 = 按博主分组（谁说了啥），每人近 2 天最新观点
 *   4. 关键消息 = 默认只看近 1 天 importance≥6，「显示全部」放宽；支持方向过滤（利多/利空）
 *
 * 交易联动入口：/news?symbol=NVDA 从看盘页信号行跳入，直接过滤该标的消息。
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

function ItemCard({ item, onPickSymbol }: { item: NewsItem; onPickSymbol: (s: string) => void }) {
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
              <button
                key={s}
                className="stage-chip neutral-info nf-symbol-chip"
                title={`只看「${s}」相关消息`}
                onClick={() => onPickSymbol(s)}
              >
                {s}
              </button>
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

/** 顶部：今日要点（top_events 大卡）+ 分类归纳（折叠）。
 *  2026-09-04：大卡带事件整体方向与影响标的（chips 可点击直达该标的消息流）；
 *  旧简报无 symbols/direction 字段时自然降级为原样式。 */
function DigestHeadline({ onPickSymbol }: { onPickSymbol: (s: string) => void }) {
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
                  <DirectionTag direction={e.direction ?? null} />
                  {(e.symbols ?? []).length > 0 && (
                    <span className="nf-symbols">
                      {(e.symbols ?? []).map((s) => (
                        <button
                          key={s}
                          className="stage-chip neutral-info nf-symbol-chip"
                          title={`只看「${s}」相关消息`}
                          onClick={() => onPickSymbol(s)}
                        >
                          {s}
                        </button>
                      ))}
                    </span>
                  )}
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

/** 多空温度计：近 N 天已评分条目的方向分布，点击条段直达方向过滤。 */
function MoodBar({
  mood,
  days,
  direction,
  onPick,
}: {
  mood: NewsMood;
  days: number;
  direction: string;
  onPick: (d: string) => void;
}) {
  const total = mood.bullish + mood.bearish + mood.neutral;
  if (!total) return null;
  const pct = (n: number) => `${(n / total) * 100}%`;
  const bias =
    mood.bearish > mood.bullish * 1.5
      ? "消息面偏空"
      : mood.bullish > mood.bearish * 1.5
        ? "消息面偏多"
        : "多空大体均衡";
  const segs = [
    { key: "bullish", label: "利多", n: mood.bullish, cls: "up" },
    { key: "neutral", label: "中性", n: mood.neutral, cls: "mid" },
    { key: "bearish", label: "利空", n: mood.bearish, cls: "down" },
  ];
  const hint = (titles: { title: string; importance: number }[]) =>
    titles.map((t) => `★${t.importance} ${t.title}`).join("\n") || "无重点条目";
  return (
    <div className="nf-mood">
      <div className="nf-mood-head">
        <span className="nf-mood-bias">{bias}</span>
        <span className="text-faint">
          近{days}天 {total} 条已评分 · 点击色段只看对应方向
        </span>
      </div>
      <div className="nf-mood-bar">
        {segs.map(
          (s) =>
            s.n > 0 && (
              <button
                key={s.key}
                className={`nf-mood-seg nf-mood-${s.cls} ${direction === s.key ? "active" : ""}`}
                style={{ width: pct(s.n) }}
                title={hint(s.key === "bullish" ? mood.top_bullish : s.key === "bearish" ? mood.top_bearish : [])}
                onClick={() => onPick(direction === s.key ? "" : s.key)}
              >
                {s.n}
              </button>
            ),
        )}
      </div>
      <div className="nf-mood-legend">
        {segs.map((s) => (
          <span key={s.key} className={`nf-mood-dot-${s.cls}`}>
            {s.label} {s.n}
          </span>
        ))}
      </div>
    </div>
  );
}

/** 标的 → 当前交易信号徽标（与看盘信号横幅同一数据源，卖点优先于买点）。 */
function useSignalBadges(): Map<string, { label: string; cls: string }> {
  const { data } = useQuery({
    queryKey: ["signalsToday"],
    queryFn: () => api.signalsToday(),
    staleTime: 60_000,
    retry: false,
  });
  return useMemo(() => {
    const m = new Map<string, { label: string; cls: string }>();
    if (!data) return m;
    const put = (list: { symbol: string }[], label: string, cls: string) => {
      for (const s of list) if (!m.has(s.symbol)) m.set(s.symbol, { label, cls });
    };
    put(data.sell_hard ?? [], "卖·硬", "nf-sig-hard");
    put(data.actionable ?? [], "买·行动", "nf-sig-buy");
    put(data.sell_warn ?? [], "卖·预警", "nf-sig-warn");
    put(data.waiting ?? [], "买·等待", "nf-sig-wait");
    put(data.sell_soft ?? [], "卖·提醒", "nf-sig-soft");
    return m;
  }, [data]);
}

/** 自选消息雷达：我的自选 × 近 N 天消息——多空温度计 + 标的卡（点击直达筛选）。 */
function WatchlistRadar({
  selected,
  direction,
  onPickSymbol,
  onPickDirection,
}: {
  selected: string;
  direction: string;
  onPickSymbol: (s: string) => void;
  onPickDirection: (d: string) => void;
}) {
  const { data } = useQuery({
    queryKey: ["newsWatchlistBrief"],
    queryFn: () => newsApi.watchlistBrief(3),
    staleTime: 5 * 60_000,
  });
  const signals = useSignalBadges();
  if (!data || (data.items.length === 0 && data.mood.bullish + data.mood.bearish + data.mood.neutral === 0))
    return null;
  return (
    <div className="nf-radar">
      <div className="nf-digest-head">
        <h2>自选消息雷达</h2>
        <span className="text-faint">
          近{data.days}天 · {data.items.length} 个标的有消息 · 对齐看盘自选与信号
        </span>
      </div>
      <MoodBar mood={data.mood} days={data.days} direction={direction} onPick={onPickDirection} />
      {data.items.length > 0 && (
        <div className="nf-radar-grid">
          {data.items.map((e: NewsWatchEntry) => {
            const sig = signals.get(e.symbol);
            const heavy = (e.top?.importance ?? 0) >= 8;
            return (
              <div
                key={e.symbol}
                role="button"
                tabIndex={0}
                className={`nf-radar-card ${selected === e.symbol ? "active" : ""} ${
                  e.bearish > e.bullish ? "bearish" : e.bullish > e.bearish ? "bullish" : ""
                }`}
                title={`${e.symbol} · 共${e.count}条（利多${e.bullish}/中性${e.neutral}/利空${e.bearish}）`}
                onClick={() => onPickSymbol(e.symbol)}
                onKeyDown={(ev) => {
                  if (ev.key === "Enter" || ev.key === " ") onPickSymbol(e.symbol);
                }}
              >
                <span className="nf-radar-name-row">
                  <span className="nf-radar-name">{e.display_name ?? e.symbol}</span>
                  {sig && <span className={`nf-radar-signal ${sig.cls}`}>{sig.label}</span>}
                </span>
                <span className="nf-radar-counts">
                  {e.bullish > 0 && <span className="up">↑{e.bullish}</span>}
                  {e.bearish > 0 && <span className="down">↓{e.bearish}</span>}
                  {heavy && <span className="nf-radar-heavy" title="最高分消息 ≥8 分">重磅</span>}
                  {e.bullish === 0 && e.bearish === 0 && !heavy && (
                    <span className="text-faint">{e.count}条</span>
                  )}
                </span>
                {e.top && (
                  <span className="nf-radar-top" title={e.top.llm_note ?? e.top.title}>
                    {e.top.title}
                  </span>
                )}
                <span className="nf-radar-foot">
                  {e.latest_at && <span className="nf-radar-time">{dayLabel(e.latest_at)}</span>}
                  <Link
                    to={`/symbol/${encodeURIComponent(e.symbol)}`}
                    className="nf-radar-link"
                    onClick={(ev) => ev.stopPropagation()}
                  >
                    看盘 ↗
                  </Link>
                </span>
              </div>
            );
          })}
        </div>
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
  const [focus, setFocus] = useState(true); // 聚焦模式：近1天 + importance≥6
  const [category, setCategory] = useState<string>("");
  const [source, setSource] = useState<string>("");
  const [range, setRange] = useState<RangeKey>("1d");
  const [search, setSearch] = useState("");
  const [queryText, setQueryText] = useState("");
  const [directionFilter, setDirectionFilter] = useState(""); // 利多/利空专项排查
  const debounceRef = useRef<number | null>(null);
  const queryClient = useQueryClient();
  const [running, setRunning] = useState(false);
  const [runError, setRunError] = useState<string | null>(null);
  const pollRef = useRef<number | null>(null);

  // 标的筛选以 URL ?symbol= 为唯一事实来源：看盘信号行 /news?symbol=XXX 跳入即生效，
  // 刷新/分享链接保持状态；清除时清空查询串。
  const [searchParams, setSearchParams] = useSearchParams();
  const symbolFilter = searchParams.get("symbol") ?? "";
  useEffect(() => {
    if (symbolFilter) {
      setFocus(false);
      setRange("30d");
    }
  }, [symbolFilter]);
  const pickSymbol = (s: string) => {
    const next = symbolFilter === s ? "" : s;
    setSearchParams(next ? { symbol: next } : {}, { replace: true });
  };

  const effectiveRange: RangeKey = focus ? "1d" : range;
  const from = useMemo(() => {
    const r = RANGES.find((x) => x.key === effectiveRange);
    if (!r?.days) return undefined;
    return new Date(Date.now() - r.days * 86_400_000).toISOString().slice(0, 10);
  }, [effectiveRange]);

  const { data, isLoading, error } = useQuery({
    queryKey: ["newsItems", category, source, effectiveRange, queryText, focus, symbolFilter, directionFilter],
    queryFn: () =>
      newsApi.items({
        category: category || undefined,
        source: source || undefined,
        from,
        q: queryText || undefined,
        symbol: symbolFilter || undefined,
        direction: directionFilter || undefined,
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
    setRunError(null);
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
            void queryClient.invalidateQueries({ queryKey: ["newsWatchlistBrief"] });
          }
        } catch {
          /* 轮询失败继续 */
        }
      }, 3000);
    } catch (e) {
      setRunError(e instanceof Error ? e.message : String(e));
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

      {runError && (
        <div className="fund-errors">
          抓取启动失败：{runError}（通常是 LLM 配额或数据源限流，稍后再试）
          <button className="btn small" style={{ marginLeft: 8 }} onClick={() => setRunError(null)}>
            知道了
          </button>
        </div>
      )}

      <WatchlistRadar
        selected={symbolFilter}
        direction={directionFilter}
        onPickSymbol={pickSymbol}
        onPickDirection={(d) => setDirectionFilter(d)}
      />
      <DigestHeadline onPickSymbol={pickSymbol} />
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
        <div className="nf-tabs">
          <button
            className={!directionFilter ? "active" : ""}
            onClick={() => setDirectionFilter("")}
          >
            全方向
          </button>
          <button
            className={directionFilter === "bullish" ? "active up" : ""}
            onClick={() => setDirectionFilter(directionFilter === "bullish" ? "" : "bullish")}
          >
            利多 ↑
          </button>
          <button
            className={directionFilter === "bearish" ? "active down" : ""}
            onClick={() => setDirectionFilter(directionFilter === "bearish" ? "" : "bearish")}
          >
            利空 ↓
          </button>
        </div>
        {symbolFilter && (
          <button className="nf-filter-chip" onClick={() => pickSymbol(symbolFilter)}>
            标的：{symbolFilter} ✕
          </button>
        )}
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
          {symbolFilter
            ? `「${symbolFilter}」在当前范围内没有匹配消息——可放宽时间范围或清除标的筛选。`
            : focus
              ? "今天还没有高分条目——点上方按钮「显示全部」看全量。"
              : "没有符合条件的条目。"}
        </div>
      )}
      {data && data.items.length > 0 && (
        <div className="nf-list">
          {data.items.map((it) => (
            <ItemCard key={it.id} item={it} onPickSymbol={pickSymbol} />
          ))}
        </div>
      )}
    </div>
  );
}
