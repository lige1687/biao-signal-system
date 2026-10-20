import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { RecommendCardView } from "../components/copilot/CopilotCards";
import SymbolKlinePanel from "../components/SymbolKlinePanel";
import type { ObservationBucket } from "../types";

/** 前向存证账本小卡：agent 说过的可检验判断，到期对账（分桶，不合并总胜率）。
 *  只读展示——全部数字来自后端账本；文案用中文状态词（已记录/待到期/缺数据），
 *  不直接显示 pending/桶等内部词。展示记录数与研究样本数分列。 */
function ObservationLedgerCard() {
  const q = useQuery({
    queryKey: ["observationLedger"],
    queryFn: () => api.observationLedger(),
    refetchInterval: 300_000,
    retry: 1,
  });
  if (q.isLoading) return <div className="ops-empty">前向存证账本加载中…</div>;
  if (q.isError || !q.data)
    return <div className="ops-empty">前向存证账本暂不可用。</div>;
  const { buckets, zero_trigger_days, n_superseded_batches, note_cn,
          independent_event_count, independent_event_note } = q.data.summary;
  const srcCn: Record<string, string> = {
    recommendation: "推荐观察", sentiment_day: "情绪信号",
  };
  const qualCn: Record<string, string> = {
    ok: "", legacy: "（历史迁入）", unknown: "（来源不明）",
    available_rows: "（按行参考）",
  };
  const label = (b: ObservationBucket): string => {
    const src = srcCn[b.source_type] ?? b.source_type;
    const dir = b.direction === "up" ? "（期待上涨）"
      : b.direction === "down" ? "（期待下跌）" : "";
    const ref = b.is_reference_version ? "·参考口径" : "";
    return `${src}·${b.horizon_days}日${dir}${ref}${qualCn[b.legacy_quality] ?? ""}`;
  };
  const recents = q.data.recent.filter((r) => r.record_type === "claim").slice(0, 8);
  return (
    <>
      {buckets.length === 0 && (
        <div className="ops-empty">
          账本已就绪，等待首批到期样本（观察发出后按 1/5/20、10/20 个交易日补齐）。
        </div>
      )}
      {buckets.map((b, i) => (
        <div key={i} className="cp-row">
          <span className="cp-sym">{label(b)}</span>
          <span>
            已记录{b.n_observations}条/研究样本{b.n_samples}个 · 已评价{b.n_ready_samples}
            {" / "}待到期{b.n_pending}
            {b.n_missing > 0 && ` / 缺数据${b.n_missing}`}
            {b.n_conflict_samples > 0 && ` / 数据冲突${b.n_conflict_samples}（不计入比例）`}
            {b.hit_rate_pct !== undefined && ` · 方向命中${b.hit_rate_pct}%`}
            {b.avg_change_pct !== null &&
              ` · 平均涨跌${b.avg_change_pct > 0 ? "+" : ""}${b.avg_change_pct}%`}
            {!b.has_baseline && " ·（绝对涨跌，无基准不算超额）"}
          </span>
        </div>
      ))}
      {Object.entries(zero_trigger_days).map(([src, n]) => (
        <div key={src} className="cp-row">
          <span className="cp-sym">零触发日</span>
          <span className="muted">{srcCn[src] ?? src}：{n} 天无信号（不计任何胜率）</span>
        </div>
      ))}
      {independent_event_count === null && (
        <div className="cp-row">
          <span className="cp-sym">独立事件数</span>
          <span className="muted">未知——{independent_event_note}</span>
        </div>
      )}
      {n_superseded_batches > 0 && (
        <div className="cp-row">
          <span className="cp-sym">修订留痕</span>
          <span className="muted">
            {n_superseded_batches} 次展示内容被后来版本取代（原话与成绩均留档可查）
          </span>
        </div>
      )}
      {recents.length > 0 && (
        <details style={{ marginTop: 6 }}>
          <summary className="muted" style={{ fontSize: 11, cursor: "pointer" }}>
            最近记录的原话（{recents.length} 条）
          </summary>
          {recents.map((r) => (
            <div key={r.observation_id} className="cp-row" style={{ fontSize: 11 }}>
              <span className="muted">{r.observed_at}</span>
              <span>
                {r.claim || "(展示批次)"}
                {r.superseded && "（已被修订）"}
                {r.legacy_quality === "legacy" && "（历史迁入）"}
                {r.legacy_quality === "unknown" && "（来源不明）"}
                {r.display_status === "not_shown" && "（未展示，不计成绩）"}
                {r.outcomes.length > 0 &&
                  ` · ${r.outcomes
                      .map((o) => {
                        const scope = o.is_reference_version ? "参考" : "严格";
                        const val = o.change_pct !== null
                          ? `${o.change_pct > 0 ? "+" : ""}${o.change_pct}%`
                          : "";
                        return `${scope}${o.horizon}日:${o.status_cn}${val ? ` ${val}` : ""}`;
                      })
                      .join("，")}`}
              </span>
            </div>
          ))}
        </details>
      )}
      <div className="muted" style={{ fontSize: 10, marginTop: 4 }}>{note_cn}</div>
    </>
  );
}

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
  return (
    <div className="page ops-page">
      <div className="page-head">
        <h1>今日操作 · {ops.run_date}</h1>
        <span className="ph-meta">{ops.push_summary_cn}</span>
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
          <h3>③ 计划待办</h3>
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
          <h3>④ 观察触发</h3>
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

        <section className="ops-section span-all">
          <h3>⑤ 情绪面（叙事标注，不构成判定）</h3>
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
            <h3>⑥ 近3日重大事件（客观参考，不构成判定）</h3>
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

        <section className="ops-section span-all">
          <h3>② 今日推荐</h3>
          {ops.recommendations ? (
            <RecommendCardView card={ops.recommendations} />
          ) : (
            <div className="ops-empty">今日尚未生成推荐（收盘后自动生成）。</div>
          )}
        </section>

        <section className="ops-section span-all">
          <h3>⑦ 前向存证账本（agent 说过的话 · 到期对账）</h3>
          <ObservationLedgerCard />
        </section>
      </div></div>
      <SymbolKlinePanel symbol={active} emptyHint="点左侧任意标的名，这里出它的K线" />
      </div>
    </div>
  );
}
