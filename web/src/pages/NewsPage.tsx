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
 * - 数据日更（launchd 20:30），“立即刷新”走后台管线。
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

function ItemCard({ item }: { item: NewsItem }) {
  const dir = item.direction ? DIRECTION_CN[item.direction] : null;
  return (
    <div className="nf-card">
      <div className="nf-card-head">
        <Stars importance={item.importance} />
        {item.category && (
          <span className={`stage-chip nf-cat-${item.category}`}>
            {CATEGORY_CN[item.category] ?? item.category}
          </span>
        )}
        {dir && <span className={dir.cls}>{dir.label}</span>}
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
          {item.source_name && item.source !== "bilibili" ? ` · ${item.source_name}` : ""}
          {item.source === "bilibili" && item.source_name ? ` · ${item.source_name}` : ""}
        </span>
        <span className="text-faint">{item.published_at.slice(5, 16).replace("T", " ")}</span>
      </div>
    </div>
  );
}

function DigestCard() {
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
  return (
    <div className="nf-digest">
      <div className="nf-digest-head">
        <h2>今日整合简报</h2>
        <span className="text-faint">{digest.digest_date}</span>
      </div>
      {sections.length === 0 && <div className="text-faint">本日暂无整合内容。</div>}
      {sections.map((s) => (
        <div key={s.category} className="nf-digest-section">
          <div className="nf-digest-title">
            <span className={`stage-chip nf-cat-${s.category}`}>
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
      {(digest.payload.top_events ?? []).length > 0 && (
        <div className="nf-digest-section">
          <div className="nf-digest-title">要点</div>
          <ul>
            {digest.payload.top_events.map((e, i) => (
              <li key={i}>
                <b>{e.title}</b>
                <span className="text-dim">（{e.importance}/10 · {e.why}）</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function NewsPage() {
  const [category, setCategory] = useState<string>("");
  const [source, setSource] = useState<string>("");
  const [range, setRange] = useState<RangeKey>("7d");
  const [search, setSearch] = useState("");
  const [queryText, setQueryText] = useState("");
  const debounceRef = useRef<number | null>(null);
  const queryClient = useQueryClient();
  const [running, setRunning] = useState(false);
  const pollRef = useRef<number | null>(null);

  const from = useMemo(() => {
    const r = RANGES.find((x) => x.key === range);
    if (!r?.days) return undefined;
    const d = new Date(Date.now() - r.days * 86_400_000);
    return d.toISOString().slice(0, 10);
  }, [range]);

  const { data, isLoading, error } = useQuery({
    queryKey: ["newsItems", category, source, range, queryText],
    queryFn: () =>
      newsApi.items({
        category: category || undefined,
        source: source || undefined,
        from,
        q: queryText || undefined,
        limit: 100,
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
      // 轮询状态直到 run 结束（status 出现 finished 或 90s 超时）
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
            {data ? `${data.total} 条` : ""}
          </span>
        </h1>
        <span className="generated">每日 20:30 自动整合 · 参考层，非交易信号</span>
        <span className="spacer" />
        <button className="btn primary" onClick={onRefresh} disabled={running}>
          {running ? "抓取中…" : "立即刷新"}
        </button>
      </div>

      <DigestCard />

      <div className="nf-toolbar">
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
        <select value={range} onChange={(e) => setRange(e.target.value as RangeKey)}>
          {RANGES.map((r) => (
            <option key={r.key} value={r.key}>{r.label}</option>
          ))}
        </select>
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
        <div className="legend">没有符合条件的条目。首次使用请点「立即刷新」抓取。</div>
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
