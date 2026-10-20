import { Link } from "react-router-dom";
import type { EvidenceCard, MatchedBacktestRun } from "../types";
import { subjectLabel, compatCn, expectancyCn, exitCn, moduleCn, noteCn, R_EXPLAIN_CN } from "../utils/agentUx";

/** 单条运行结果的统计短语（零交易如实说明，胜率/R 数值原样）。 */
function runStatsCn(r: MatchedBacktestRun): string {
  if (!r.summary) return "";
  if (r.summary.zero_trades) return "——这段历史里没有触发过买卖，胜率算不出来";
  return `——交易 ${r.summary.trade_count ?? "-"} 笔，胜率 ${
    r.summary.win_rate != null ? `${Math.round(r.summary.win_rate * 100)}%` : "-"
  }，${expectancyCn(r.summary.expectancy_r)}`;
}

/** 单条运行的附带说明（明细后置而非删除：U4 返修）。 */
function runNotesCn(r: MatchedBacktestRun): string[] {
  const notes: string[] = [];
  if (r.differences_cn?.length) notes.push(`差异：${r.differences_cn.join("；")}`);
  if (r.window_note_cn) notes.push(r.window_note_cn);
  return notes;
}

/** 03B-R2 契约3：四分区证据卡视图（UX 第一期 2026-09-13 中文化）。
 * 同一个服务端结构化产物（facts / history_and_scope / explanations /
 * pending_conditions）在工作台与侧边控制台渲染同一套卡——不依赖 LLM
 * 恰好把证据复述一遍；无模型时（模板直出）卡片照常显示事实与缺口。
 * 数值只来自服务端字段（matched_runs 直接读补测结果文件的总览），本组件
 * 不做任何计算。UX 第一期改动：
 * - 首层只放中文结论（适用于这次问题 / 暂不能确定是否适用），模块/退出
 *   用中文打法名，不出现英文枚举与代码；
 * - 运行编号、差异明细、兼容性代码收进"查看依据详情"折叠区；
 * - R 第一次出现附大白话解释；历史缺字段时朴素展示，不填造。
 * U4 返修（主控复核 2026-09-13）：
 * - forceDetailsOpen：动作条"查看依据详情"按钮可把本卡全部折叠区展开
 *   （两入口一致）；false/缺省时用户照常手动开合；
 * - 支持本问题的运行同样保留附带说明（window_note_cn / differences_cn），
 *   明细后置而非删除。 */
export default function EvidenceCardView({ card, forceDetailsOpen }: {
  card: EvidenceCard;
  /** true 时展开本卡全部"查看依据详情"折叠区（动作条按钮触发）。 */
  forceDetailsOpen?: boolean;
}) {
  if (!card || (!card.facts && !card.history_and_scope && !card.explanations)) {
    return null;
  }
  const facts = card.facts ?? {};
  const hs = card.history_and_scope ?? {};
  const matched = hs.matched_runs ?? [];
  const pending = (card.pending_conditions ?? []).filter(Boolean);
  const supporting = matched.filter(r => r.supports_question);
  const referencing = matched.filter(r => !r.supports_question);
  const detailsOpenProps = forceDetailsOpen ? { open: true } : {};
  return (
    <div className="evidence-card cp-card" style={{ marginTop: 6 }}>
      <div className="cp-label">依据卡（判定层事实 · 非预测）</div>
      <div style={{ fontSize: 12 }}>
        <span className="muted">对象：</span>
        {subjectLabel(facts.symbol, facts.display_name)}
        {facts.as_of ? ` · 数据日 ${facts.as_of}` : " · 数据日期未提供"}
        {facts.verdict_cn ? ` · ${facts.verdict_cn}` : ""}
        {typeof facts.buy_point_candidate_n === "number" &&
          ` · 买点候选 ${facts.buy_point_candidate_n} 个`}
      </div>
      {facts.sector_summary_cn && <div>{facts.sector_summary_cn}</div>}
      {facts.subject_kind === "sector" && <Link to="/sectors">查看行业板块资料</Link>}
      {(hs.note_cn || hs.winrate_evidence != null) && (
        <div style={{ fontSize: 12 }}>
          <span className="muted">历史依据：</span>
          {hs.winrate_evidence && (hs.winrate_evidence as Record<string, unknown>).compatibility
            ? compatCn(String((hs.winrate_evidence as Record<string, unknown>).compatibility))
            : ""}
          {hs.note_cn ? `——${noteCn(hs.note_cn)}` : "（见下方详情）"}
        </div>
      )}
      {matched.length > 0 && (
        <div className="evidence-card-runs" style={{ marginTop: 4 }}>
          <div className="muted" style={{ fontSize: 11.5 }}>
            本标的补测结果（只有与这次问题方法完全一致的才支持本问题）：
          </div>
          {supporting.map(r => (
            <div key={r.request_id} style={{ fontSize: 11.5, paddingLeft: 8 }}>
              · ✓ 适用于这次问题：{moduleCn(r.module)}配{exitCn(r.exit_variant)}{runStatsCn(r)}
              {r.summary?.expectancy_r != null && (
                <span className="muted">（{R_EXPLAIN_CN}）</span>
              )}
              {runNotesCn(r).length > 0 && (
                <details className="evidence-card-details" {...detailsOpenProps}>
                  <summary>查看依据详情（该次运行的附带说明）</summary>
                  {runNotesCn(r).map((note, i) => (
                    <div key={i} className="muted" style={{ paddingLeft: 12 }}>{note}</div>
                  ))}
                </details>
              )}
              <Link className="bsp-run-link" to={`/backtest?run=${encodeURIComponent(r.run_id)}`}>
                查看该次测试 ↗
              </Link>
            </div>
          ))}
          {referencing.length > 0 && (
            <details className="evidence-card-details" {...detailsOpenProps}>
              <summary>查看依据详情（{referencing.length} 次不匹配/待确认的旧测试）</summary>
              {referencing.map(r => (
                <div key={r.request_id} style={{ fontSize: 11.5, paddingLeft: 8 }}>
                  · {compatCn(r.compatibility)}：{moduleCn(r.module)}配{exitCn(r.exit_variant)}
                  {r.summary && !r.summary.zero_trades
                    ? runStatsCn(r)
                    : r.summary?.zero_trades
                      ? "——这段历史里没有触发过买卖"
                      : ""}
                  {r.differences_cn.length > 0 && (
                    <div className="muted" style={{ paddingLeft: 12 }}>
                      差异：{r.differences_cn.join("；")}
                    </div>
                  )}
                  {r.window_note_cn && (
                    <div className="muted" style={{ paddingLeft: 12 }}>{r.window_note_cn}</div>
                  )}
                  <Link className="bsp-run-link" to={`/backtest?run=${encodeURIComponent(r.run_id)}`}>
                    查看该次测试 ↗
                  </Link>
                </div>
              ))}
            </details>
          )}
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
