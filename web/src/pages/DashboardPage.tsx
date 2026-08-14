import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import AddSymbolDialog from "../components/AddSymbolDialog";
import MarketBreadthStrip from "../components/MarketBreadthStrip";
import MarketCard from "../components/MarketCard";
import TodayOpportunityPanel from "../components/TodayOpportunityPanel";
import WatchSubscriptionsPanel from "../components/WatchSubscriptionsPanel";

/** 加载占位卡片：渐入的 shimmer 比纯文字 loading 更能表达"正在填充"。 */
function CardSkeletons({ n }: { n: number }) {
  return (
    <>
      {Array.from({ length: n }).map((_, i) => (
        <div key={`sk-${i}`} className="card-skeleton" />
      ))}
    </>
  );
}

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);

  // 拆成指数 / 自选两个请求：指数通常先回先渲染，自选后台填充。
  // react-query 缓存让二次进入两组卡片都秒开，后台静默刷新。
  const { data: indexData, isLoading: indexLoading, error: indexError } = useQuery({
    queryKey: ["cards", "index"],
    queryFn: () => api.dashboard("index"),
  });
  const { data: watchData, isLoading: watchLoading, error: watchError } = useQuery({
    queryKey: ["cards", "watchlist"],
    queryFn: () => api.dashboard("watchlist"),
  });

  const refreshMutation = useMutation({
    mutationFn: (symbols?: string[]) => api.refresh(symbols),
    onSuccess: (fresh) => {
      // refresh 返回全量，按 group 拆回两个缓存键
      const idx = fresh.cards.filter((c) => c.group === "index");
      const wch = fresh.cards.filter((c) => c.group === "watchlist");
      queryClient.setQueryData(["cards", "index"], { ...fresh, cards: idx });
      queryClient.setQueryData(["cards", "watchlist"], { ...fresh, cards: wch });
    },
  });

  const removeMutation = useMutation({
    mutationFn: (symbol: string) => api.removeWatchlist(symbol),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cards"] });
      queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });

  const indexCards = indexData?.cards ?? [];
  const watchCards = watchData?.cards ?? [];
  const generatedAt = indexData?.generated_at ?? watchData?.generated_at;
  const disclaimer = indexData?.disclaimer_cn ?? watchData?.disclaimer_cn;
  const error = indexError || watchError;

  return (
    <div className="page">
      <div className="header">
        <h1>LEI 看盘系统</h1>
        {generatedAt && (
          <span className="generated">
            更新于 {new Date(generatedAt).toLocaleString("zh-CN", { hour12: false })}
          </span>
        )}
        <span className="spacer" />
        <button
          className="btn primary"
          disabled={refreshMutation.isPending}
          onClick={() => refreshMutation.mutate(undefined)}
        >
          {refreshMutation.isPending ? "刷新中…" : "刷新行情"}
        </button>
      </div>

      <div className="legend">
        <span>
          <span className="dot" style={{ background: "var(--lei-green)" }} />
          绿=多头观察
        </span>
        <span>
          <span className="dot" style={{ background: "var(--lei-gray)" }} />
          灰=中性
        </span>
        <span>
          <span className="dot" style={{ background: "var(--lei-black)", border: "1.5px solid var(--border)" }} />
          黑=空头规避
        </span>
        <span style={{ color: "var(--text-faint)" }}>
          LEI 信号颜色与涨跌红绿（<span className="up">红涨</span>/
          <span className="down">绿跌</span>）无关 · 所有信号仅为观察记录，不构成买卖建议
        </span>
      </div>

      <MarketBreadthStrip />

      <TodayOpportunityPanel />

      <WatchSubscriptionsPanel />

      {error && <div className="error-banner">加载失败：{String(error)}</div>}

      <div className="section-title">
        指数总览 <span className="count">{indexCards.length}</span>
      </div>
      <div className="card-grid">
        {indexCards.map((card) => (
          <MarketCard
            key={card.symbol}
            card={card}
            onRetry={(s) => refreshMutation.mutate([s])}
          />
        ))}
        {indexLoading && !indexData && <CardSkeletons n={6} />}
      </div>

      <div className="section-title">
        我的自选 <span className="count">{watchCards.length}</span>
      </div>
      <div className="card-grid">
        {watchCards.map((card) => (
          <MarketCard
            key={card.symbol}
            card={card}
            onRemove={(s) => removeMutation.mutate(s)}
            onRetry={(s) => refreshMutation.mutate([s])}
          />
        ))}
        {watchLoading && !watchData && <CardSkeletons n={4} />}
        <div className="add-card" onClick={() => setShowAdd(true)}>
          ＋ 添加自选
        </div>
      </div>

      {disclaimer && <div className="disclaimer">{disclaimer}</div>}

      {showAdd && (
        <AddSymbolDialog
          onClose={() => setShowAdd(false)}
          onAdded={() => {
            queryClient.invalidateQueries({ queryKey: ["cards"] });
            queryClient.invalidateQueries({ queryKey: ["watchlist"] });
          }}
        />
      )}
    </div>
  );
}
