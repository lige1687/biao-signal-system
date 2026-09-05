import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { RecommendCardView } from "../components/copilot/CopilotCards";

/** 每日操作清单页（/ops）：确定性组装的四段，收盘后自动生成。
 *  短清单段并排成网格提高密度；推荐卡跨整行。 */
export default function OpsPage() {
  const q = useQuery({
    queryKey: ["opsToday"],
    queryFn: () => api.opsToday(),
    refetchInterval: 60_000,
    retry: 2,
    retryDelay: 4000,
  });
  const [slow, setSlow] = useState(false);
  useEffect(() => {
    if (!q.isLoading && !q.isFetching) return undefined;
    setSlow(false);
    const t = window.setTimeout(() => setSlow(true), 10_000);
    return () => window.clearTimeout(t);
  }, [q.isLoading, q.isFetching]);
  if (q.isLoading)
    return (
      <div className="page" style={{ padding: "40px 18px", textAlign: "center" }}>
        <div style={{ display: "flex", gap: 4, justifyContent: "center" }} aria-hidden>
          <i className="ws-dot" /><i className="ws-dot" /><i className="ws-dot" />
        </div>
        <div style={{ marginTop: 10 }}>清单加载中…</div>
        {slow && (
          <div className="muted" style={{ marginTop: 6, fontSize: 12 }}>
            等得有点久——后端可能在启动预热（约 1–3 分钟），页面会自动重试；也可稍后刷新。
          </div>
        )}
      </div>
    );
  if (q.isError || !q.data)
    return (
      <div className="page" style={{ padding: "40px 18px", textAlign: "center" }}>
        <div className="cp-error">清单加载失败。</div>
        <button className="btn small" style={{ marginTop: 10 }} onClick={() => q.refetch()}>
          重试
        </button>
      </div>
    );
  const ops = q.data;
  return (
    <div className="page ops-page">
      <div className="page-head">
        <h1>今日操作 · {ops.run_date}</h1>
        <span className="ph-meta">{ops.push_summary_cn}</span>
      </div>

      <div className="ops-grid">
        <section className="ops-section">
          <h3>① 持仓要处理的</h3>
          {ops.holdings_actions.length === 0 && <div className="ops-empty">暂无。</div>}
          {ops.holdings_actions.map((l, i) => (
            <div key={i} className="cp-row">
              {l.symbol !== "-" && (
                <Link to={`/symbol/${l.symbol}`} className="cp-sym">
                  {l.display_name || l.symbol}
                </Link>
              )}
              <span>{l.text_cn}</span>
            </div>
          ))}
        </section>

        <section className="ops-section">
          <h3>③ 计划待办</h3>
          {ops.plan_todos.length === 0 && <div className="ops-empty">暂无待办。</div>}
          {ops.plan_todos.map((t) => (
            <div key={t.action_id} className="cp-row">
              <Link to={`/symbol/${t.symbol}`} className="cp-sym">{t.symbol}</Link>
              <span className={t.kind === "EXIT" ? "cp-error" : ""}>
                {t.kind_cn}待办 · 已催 {t.nag_count} 次 · 可执行自 {t.due_from || "-"}
              </span>
              <Link to="/plans" className="cp-link">去监督待办处理</Link>
            </div>
          ))}
        </section>

        <section className="ops-section">
          <h3>④ 观察触发</h3>
          {ops.watch_triggers.length === 0 && <div className="ops-empty">暂无观察项。</div>}
          {ops.watch_triggers.map((l, i) => (
            <div key={i} className="cp-row">
              <Link to={`/symbol/${l.symbol}`} className="cp-sym">
                {l.display_name || l.symbol}
              </Link>
              <span className="muted">{l.text_cn}</span>
            </div>
          ))}
        </section>

        <section className="ops-section span-all">
          <h3>② 今日推荐</h3>
          {ops.recommendations ? (
            <RecommendCardView card={ops.recommendations} />
          ) : (
            <div className="ops-empty">今日尚未生成推荐（收盘后自动生成）。</div>
          )}
        </section>
      </div>
    </div>
  );
}
