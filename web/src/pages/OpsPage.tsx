import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { RecommendCardView } from "../components/copilot/CopilotCards";
import SymbolKlinePanel from "../components/SymbolKlinePanel";

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
  // K线联动选中态：必须位于所有 early-return 之前（React hook 规则）
  const [picked, setPicked] = useState<string | null>(null);
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
  const firstSym =
    ops.plan_todos[0]?.symbol ??
    ops.watch_triggers[0]?.symbol ??
    ops.holdings_actions.find((l) => l.symbol !== "-")?.symbol ??
    null;
  const active = picked ?? firstSym ?? null;
  const pick = (sym: string | null) => setPicked(sym);
  // 组体摘要：只做既有数据的计数汇总（不新增信息，明细仍在下方分区）
  const maxNag = ops.plan_todos.reduce((m, t) => Math.max(m, t.nag_count), 0);
  const hotBoards = ops.sentiment?.hot_boards ?? [];
  return (
    <div className="page ops-page">
      {/* S13 信号组层级：单一一级信号组（组头=标题+日期+主任务提示，
          组体=今日事项摘要+风险提醒，动作组=进入入口/查看详情） */}
      <div className="pg-firstlook-group ops-firstlook-group">
        <div className="pg-grp-head">
          <h1>今日操作</h1>
          <span className="pg-grp-meta">{ops.run_date}</span>
        </div>
        {ops.push_summary_cn && <p className="pg-grp-hint">{ops.push_summary_cn}</p>}
        <div className="pg-grp-body">
          <div className="ops-grp-sumline">
            <span>持仓待处理 <b>{ops.holdings_actions.filter((l) => l.symbol !== "-").length}</b> 项</span>
            <span>计划待办 <b>{ops.plan_todos.length}</b> 项{maxNag > 0 && `（已催最多 ${maxNag} 次）`}</span>
            <span>观察触发 <b>{ops.watch_triggers.length}</b> 项</span>
            {hotBoards.length > 0 && (
              <span className="ops-grp-risk">
                ⚠ 过热警示：{hotBoards.map((b) => `${b.name}（${b.heat_pctile}分位）`).join("、")}
              </span>
            )}
          </div>
        </div>
        <div className="pg-grp-actions">
          <a className="cp-link" href="#ops-sentiment">展开情绪面与事件详情</a>
          {ops.plan_todos.length > 0 && (
            <Link className="btn primary" to="/plans">去监督待办处理</Link>
          )}
        </div>
      </div>

      <div className="ops-with-kline">
      <div className="ops-main"> <div className="ops-grid">
        <section className="ops-section">
          <h3>① 持仓要处理的</h3>
          {ops.holdings_actions.length === 0 && <div className="ops-empty">暂无。</div>}
          {ops.holdings_actions.map((l, i) => (
            <div key={i} className="cp-row">
              {l.symbol !== "-" && (
                <button
                  className={`cp-sym ops-pick ${active === l.symbol ? "is-active" : ""}`}
                  onClick={() => pick(l.symbol)}
                  title="点我看K线"
                >
                  {l.display_name || l.symbol}
                </button>
              )}
              <span>{l.text_cn}</span>
            </div>
          ))}
        </section>

        <section className="ops-section">
          <h3>② 计划待办</h3>
          {ops.plan_todos.length === 0 && <div className="ops-empty">暂无待办。</div>}
          {ops.plan_todos.map((t) => (
            <div key={t.action_id} className="cp-row">
              <button
                className={`cp-sym ops-pick ${active === t.symbol ? "is-active" : ""}`}
                onClick={() => pick(t.symbol)}
                title="点我看K线"
              >
                {t.symbol}
              </button>
              <span className={t.kind === "EXIT" ? "cp-error" : ""}>
                {t.kind_cn}待办 · 已催 {t.nag_count} 次 · 可执行自 {t.due_from || "-"}
              </span>
              <Link to="/plans" className="cp-link">去监督待办处理</Link>
            </div>
          ))}
        </section>

        <section className="ops-section">
          <h3>③ 观察触发</h3>
          {ops.watch_triggers.length === 0 && <div className="ops-empty">暂无观察项。</div>}
          {ops.watch_triggers.map((l, i) => (
            <div key={i} className="cp-row">
              <button
                className={`cp-sym ops-pick ${active === l.symbol ? "is-active" : ""}`}
                onClick={() => pick(l.symbol)}
                title="点我看K线"
              >
                {l.display_name || l.symbol}
              </button>
              <span className="muted">{l.text_cn}</span>
            </div>
          ))}
        </section>

        <section className="ops-section span-all" id="ops-sentiment">
          <h3>④ 情绪面（叙事标注，不构成判定）</h3>
          {ops.sentiment?.margin_cn && (
            <div className="cp-row">
              <span className="cp-sym">融资环境</span>
              <span className="muted">{ops.sentiment.margin_cn}</span>
            </div>
          )}
          {ops.sentiment?.hot_boards?.length ? (
            <div className="cp-row">
              <span className="cp-sym">过热警示</span>
              <span className="muted">
                {ops.sentiment.hot_boards
                  .map((b) => `${b.name}（${b.heat_pctile}分位）`)
                  .join("、")}
              </span>
            </div>
          ) : null}
          {ops.sentiment?.holdings_states?.map((h) => (
            <div className="cp-row" key={h.group_cn}>
              <span className="cp-sym">{h.group_cn}</span>
              <span className="muted">{h.state_cn}</span>
            </div>
          ))}
          {ops.sentiment?.signal_lines?.map((l) => (
            <div className="cp-row" key={l.group_cn}>
              <span className="cp-sym">{l.group_cn}</span>
              <span className="muted">{l.state_cn}</span>
            </div>
          ))}
          {ops.sentiment && !ops.sentiment.available && (
            <div className="ops-empty" style={{ fontSize: 11 }}>
              {ops.sentiment.note_cn ||
                "情绪面：数据累积中（约需 20 个交易日资金流）"}
            </div>
          )}
        </section>

        {ops.major_events?.available && ops.major_events.items.length > 0 && (
          <section className="ops-section span-all">
            <h3>⑤ 近3日重大事件（客观参考，不构成判定）</h3>
            {ops.major_events.items.map((e, i) => (
              <div key={i} className="cp-row ops-major">
                <span className="ops-major-meta">
                  <b className="ops-major-imp">{e.importance}分</b>
                  <span className="ops-major-cat">{e.category_cn}</span>
                  <span
                    className={
                      e.direction_cn === "利多" ? "up" : e.direction_cn === "利空" ? "down" : "muted"
                    }
                  >
                    {e.direction_cn}
                  </span>
                  <span className="muted">{e.when_cn}</span>
                </span>
                <span className="ops-major-title">{e.title}</span>
              </div>
            ))}
          </section>
        )}

        <section className="ops-section span-all" id="ops-recommend">
          <h3>{ops.major_events?.available && ops.major_events.items.length > 0 ? "⑥" : "⑤"} 今日推荐</h3>
          {ops.recommendations ? (
            <RecommendCardView card={ops.recommendations} />
          ) : (
            <div className="ops-empty">今日尚未生成推荐（收盘后自动生成）。</div>
          )}
        </section>
      </div></div>
      <SymbolKlinePanel symbol={active} emptyHint="点左侧任意标的名，这里出它的K线" />
      </div>
    </div>
  );
}
