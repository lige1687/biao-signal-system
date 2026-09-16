import type { EvidenceCard } from "../types";

/** 03B-R2 契约3：四分区证据卡视图。
 * 同一个服务端结构化产物（facts / history_and_scope / explanations /
 * pending_conditions）在工作台与侧边控制台渲染同一套卡——不依赖 LLM
 * 恰好把证据复述一遍；无模型时（模板直出）卡片照常显示事实与缺口。
 * 数值只来自服务端字段（matched_runs 直接读补测结果文件的总览），本组件
 * 不做任何计算。 */
export default function EvidenceCardView({ card }: { card: EvidenceCard }) {
  if (!card || (!card.facts && !card.history_and_scope && !card.explanations)) {
    return null;
  }
  const facts = card.facts ?? {};
  const hs = card.history_and_scope ?? {};
  const matched = hs.matched_runs ?? [];
  const pending = (card.pending_conditions ?? []).filter(Boolean);
  return (
    <div className="evidence-card cp-card" style={{ marginTop: 6 }}>
      <div className="cp-label">依据卡（判定层事实 · 非预测）</div>
      <div style={{ fontSize: 12 }}>
        <span className="muted">对象：</span>
        {facts.symbol ?? "-"}
        {facts.as_of ? ` · 数据日 ${facts.as_of}` : ""}
        {facts.verdict_cn ? ` · ${facts.verdict_cn}` : ""}
        {typeof facts.buy_point_candidate_n === "number" &&
          ` · 买点候选 ${facts.buy_point_candidate_n} 个`}
      </div>
      {(hs.note_cn || hs.winrate_evidence != null) && (
        <div style={{ fontSize: 12 }}>
          <span className="muted">历史结果及适用范围：</span>
          {hs.note_cn || "（见引用卡）"}
        </div>
      )}
      {matched.length > 0 && (
        <div className="evidence-card-runs" style={{ marginTop: 4 }}>
          <div className="muted" style={{ fontSize: 11.5 }}>
            本标的补测结果（按完整方法比较，exact 才支持本问题）：
          </div>
          {matched.map((r) => (
            <div key={r.request_id} style={{ fontSize: 11.5, paddingLeft: 8 }}>
              · {r.supports_question ? "✓ 支持本问题" : "✗ 不支持本问题"}
              {" "}（模块{r.module} · 退出 {r.exit_variant} · 运行 {r.run_id}
              {r.compatibility ? ` · ${r.compatibility}` : ""}）
              {r.summary &&
                (r.summary.zero_trades
                  ? "：无可统计交易（胜率未知）"
                  : `：交易 ${r.summary.trade_count ?? "-"} 笔，胜率 ${
                      r.summary.win_rate != null
                        ? `${Math.round(r.summary.win_rate * 100)}%`
                        : "-"
                    }，每笔平均 ${
                      r.summary.expectancy_r != null
                        ? `${r.summary.expectancy_r.toFixed(2)}R`
                        : "-"
                    }`)}
              {r.differences_cn.length > 0 && (
                <div className="muted" style={{ paddingLeft: 12 }}>
                  差异：{r.differences_cn.join("；")}
                </div>
              )}
              {r.window_note_cn && (
                <div className="muted" style={{ paddingLeft: 12 }}>{r.window_note_cn}</div>
              )}
            </div>
          ))}
        </div>
      )}
      <div style={{ fontSize: 12 }}>
        <span className="muted">解释与假设：</span>
        {card.explanations?.note_cn ?? "消息面/情绪/经验为解释性材料，不参与技术判定"}
      </div>
      {pending.length > 0 && (
        <div style={{ fontSize: 12 }}>
          <span className="muted">尚待满足：</span>
          {pending.slice(0, 3).join("；")}
        </div>
      )}
    </div>
  );
}
