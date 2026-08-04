import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { api } from "../api/client";
import AddSymbolDialog from "../components/AddSymbolDialog";
import MarketBreadthStrip from "../components/MarketBreadthStrip";
import MarketCard from "../components/MarketCard";

export default function DashboardPage() {
  const queryClient = useQueryClient();
  const [showAdd, setShowAdd] = useState(false);

  const { data, isLoading, error } = useQuery({
    queryKey: ["cards"],
    queryFn: () => api.dashboard(),
  });

  const refreshMutation = useMutation({
    mutationFn: (symbols?: string[]) => api.refresh(symbols),
    onSuccess: (fresh) => queryClient.setQueryData(["cards"], fresh),
  });

  const removeMutation = useMutation({
    mutationFn: (symbol: string) => api.removeWatchlist(symbol),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["cards"] });
      queryClient.invalidateQueries({ queryKey: ["watchlist"] });
    },
  });

  const indexCards = data?.cards.filter((c) => c.group === "index") ?? [];
  const watchCards = data?.cards.filter((c) => c.group === "watchlist") ?? [];

  return (
    <div className="page">
      <div className="header">
        <h1>LEI 看盘系统</h1>
        {data && (
          <span className="generated">
            更新于 {new Date(data.generated_at).toLocaleString("zh-CN", { hour12: false })}
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

      {error && <div className="error-banner">加载失败：{String(error)}</div>}
      {isLoading && <div className="loading">正在加载行情与信号（首次需逐只分析，请稍候）…</div>}

      {data && (
        <>
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
            <div className="add-card" onClick={() => setShowAdd(true)}>
              ＋ 添加自选
            </div>
          </div>

          <div className="disclaimer">{data.disclaimer_cn}</div>
        </>
      )}

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
