import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import KlineChart, { DEFAULT_DISPLAY } from "./KlineChart";

/**
 * 标的 K 线侧栏（公共组件）：OpsPage / AgentWorkspace 共用。
 * 选中标的 → 拉详情 → K 线（默认展示口径）+ 大图链接。
 */
export default function SymbolKlinePanel({
  symbol,
  emptyHint = "点左侧任意标的，这里出它的K线",
}: {
  symbol: string | null;
  emptyHint?: string;
}) {
  const detail = useQuery({
    queryKey: ["symbolDetail", symbol],
    queryFn: () => api.detail(symbol!),
    enabled: !!symbol,
    staleTime: 60_000,
  });
  return (
    <aside className="ops-kline-side">
      {symbol ? (
        <>
          <header className="ops-kline-head">
            <div className="ops-kline-title">
              <strong>{detail.data?.display_name || symbol}</strong>
              <span className="muted">{symbol}</span>
            </div>
            <Link to={`/symbol/${symbol}`} className="cp-link">大图 →</Link>
          </header>
          {detail.data ? (
            <div className="ops-kline-box">
              <KlineChart
                payload={detail.data.chart}
                display={DEFAULT_DISPLAY}
                onPick={() => undefined}
                onDownload={() => undefined}
              />
            </div>
          ) : (
            <div className="ops-kline-skeleton" aria-label="K线加载中">
              <div /><div /><div />
            </div>
          )}
        </>
      ) : (
        <div className="ops-kline-empty">
          <p>{emptyHint}</p>
        </div>
      )}
    </aside>
  );
}
