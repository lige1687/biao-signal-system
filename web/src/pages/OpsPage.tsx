import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { RecommendCardView } from "../components/copilot/CopilotCards";

/** 每日操作清单页（/ops）：确定性组装的四段，收盘后自动生成。 */
export default function OpsPage() {
  const q = useQuery({
    queryKey: ["opsToday"],
    queryFn: () => api.opsToday(),
    refetchInterval: 60_000,
  });
  if (q.isLoading) return <div className="muted page">清单加载中…</div>;
  if (q.isError || !q.data)
    return <div className="cp-error page">清单加载失败，稍后重试。</div>;
  const ops = q.data;
  return (
    <div className="page" style={{ padding: "14px 18px", maxWidth: 860 }}>
      <h2>今日操作 · {ops.run_date}</h2>
      <div className="muted">{ops.push_summary_cn}</div>

      <section style={{ marginTop: 16 }}>
        <h3>① 持仓要处理的</h3>
        {ops.holdings_actions.length === 0 && <div className="muted">暂无。</div>}
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

      <section style={{ marginTop: 16 }}>
        <h3>② 今日推荐</h3>
        {ops.recommendations ? (
          <RecommendCardView card={ops.recommendations} />
        ) : (
          <div className="muted">今日尚未生成推荐（收盘后自动生成）。</div>
        )}
      </section>

      <section style={{ marginTop: 16 }}>
        <h3>③ 计划待办</h3>
        {ops.plan_todos.length === 0 && <div className="muted">暂无待办。</div>}
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

      <section style={{ marginTop: 16 }}>
        <h3>④ 观察触发</h3>
        {ops.watch_triggers.length === 0 && <div className="muted">暂无观察项。</div>}
        {ops.watch_triggers.map((l, i) => (
          <div key={i} className="cp-row">
            <Link to={`/symbol/${l.symbol}`} className="cp-sym">
              {l.display_name || l.symbol}
            </Link>
            <span className="muted">{l.text_cn}</span>
          </div>
        ))}
      </section>
    </div>
  );
}
