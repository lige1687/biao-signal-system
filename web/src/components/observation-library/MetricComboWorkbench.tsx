import { useState } from "react";
import type { HorizonForwardStats, ScreenedEpisode } from "../market-style/breadthRegimeScreener";
import type { BarFrequency, MetricComboEvaluation, MetricComboRuleSpec } from "./metricCrossScreener";

const exists = (v: number | null | undefined): v is number => typeof v === "number" && Number.isFinite(v);
const fmtPct = (v: number | null | undefined, digits = 1) => (exists(v) ? `${v.toFixed(digits)}%` : "—");
const fmtSignedPct = (v: number | null | undefined, digits = 2, suffix = "%") =>
  exists(v) ? `${v >= 0 ? "+" : ""}${v.toFixed(digits)}${suffix}` : "—";

export default function MetricComboWorkbench({
  evaluation,
  priceName,
  frequency = "daily",
  latestDate,
  activeIds,
  selectedEpisodeId,
  onToggleRule,
  onClearRules,
  onSelectEpisode,
  onResetZoom,
}: {
  evaluation: MetricComboEvaluation;
  priceName: string;
  frequency?: BarFrequency;
  latestDate?: string | null;
  activeIds: ReadonlySet<string>;
  selectedEpisodeId: string;
  onToggleRule: (id: string) => void;
  onClearRules: () => void;
  onSelectEpisode: (ep: ScreenedEpisode) => void;
  onResetZoom: () => void;
}) {
  const [showBaseline, setShowBaseline] = useState(false);

  if (!evaluation.supported || !evaluation.rules.length) return null;

  const coreBull = evaluation.rules.filter((r) => r.tier === "core" && r.intent === "bull");
  const coreRisk = evaluation.rules.filter((r) => r.tier === "core" && r.intent !== "bull");
  const baselineRules = evaluation.rules.filter((r) => r.tier === "baseline");
  const activeRuleSpecs = evaluation.rules.filter((r) => activeIds.has(r.id));
  const baselineActiveCount = baselineRules.filter((r) => activeIds.has(r.id)).length;
  const screeningActive = activeRuleSpecs.length > 0;
  const unitText = frequency === "monthly" ? "月" : frequency === "weekly" ? "周" : "日";

  const renderPill = (rule: MetricComboRuleSpec) => {
    const count = evaluation.byRule[rule.id]?.episodeCount ?? 0;
    return (
      <button
        key={rule.id}
        type="button"
        aria-pressed={activeIds.has(rule.id)}
        title={`${rule.formula}｜${rule.basis}`}
        onClick={() => onToggleRule(rule.id)}
      >
        <span className="mcw-dot" style={{ background: rule.color }} aria-hidden="true" />
        <span>{rule.short}</span>
        <em className="mcw-count">{count}段</em>
      </button>
    );
  };

  const renderForwardCell = (label: string, stats: HorizonForwardStats) => {
    if (stats.sampleCount === 0) {
      return (
        <div className="mcw-score-cell">
          <span className="mcw-score-horizon">{label}</span>
          <span className="mcw-score-empty">样本未满{stats.horizonBars}{unitText}（待完整走完）</span>
        </div>
      );
    }
    const edgeTone = exists(stats.edgeMean) ? (stats.edgeMean >= 0 ? "pos" : "neg") : "flat";
    return (
      <div className="mcw-score-cell">
        <span className="mcw-score-horizon">{label} <em>({stats.sampleCount}次)</em></span>
        <span>胜率 <b>{fmtPct(stats.winRate)}</b></span>
        <span>均值 <b>{fmtSignedPct(stats.meanReturn)}</b></span>
        {exists(stats.edgeMean) && (
          <span className={`mcw-score-edge mcw-score-edge-${edgeTone}`}>
            较窗口基准 {fmtSignedPct(stats.edgeMean, 2, "pp")}
          </span>
        )}
        <span>中位 <b>{fmtSignedPct(stats.medianReturn)}</b></span>
        <span>均最大回撤 <b>{fmtSignedPct(stats.avgMaxDrawdown)}</b></span>
      </div>
    );
  };

  return (
    <div className="mcw-panel" aria-label="核心实战联动组合工作台">
      <div className="mcw-head">
        <strong>历史验证信号</strong>
        <span>
          只留长期真管用的 {coreBull.length + coreRisk.length} 个（买点 {coreBull.length} · 卖点 {coreRisk.length}）
        </span>
        <div className="mcw-actions">
          {baselineRules.length > 0 && (
            <button
              type="button"
              className="mcw-toggle"
              aria-expanded={showBaseline}
              onClick={() => setShowBaseline((prev) => !prev)}
            >
              {showBaseline
                ? `收起${evaluation.baselineLabel} ▴`
                : baselineActiveCount > 0
                  ? `${evaluation.baselineLabel} (已选${baselineActiveCount}) ▾`
                  : `${evaluation.baselineLabel} (${baselineRules.length}) ▾`}
            </button>
          )}
          {screeningActive && (
            <button type="button" className="mcw-clear" onClick={onClearRules}>
              清空
            </button>
          )}
        </div>
      </div>

      {evaluation.latestActiveRuleIds.length > 0 && (
        <div className="mcw-latest-hit" aria-label="最新一期已触发信号">
          <span className="mcw-latest-label">
            最新{frequency === "monthly" ? "月" : frequency === "weekly" ? "周" : "日"} ({latestDate ? (latestDate.length > 7 ? latestDate.slice(5) : latestDate) : "—"}) 命中
          </span>
          {evaluation.latestActiveRuleIds.map((rId) => {
            const rule = evaluation.rules.find((item) => item.id === rId);
            if (!rule) return null;
            return (
              <button
                key={rule.id}
                type="button"
                aria-pressed={activeIds.has(rule.id)}
                onClick={() => onToggleRule(rule.id)}
              >
                <span className="mcw-dot" style={{ background: rule.color }} aria-hidden="true" />
                {rule.short}
              </button>
            );
          })}
        </div>
      )}

      <div className="mcw-core-grid">
        {coreBull.length > 0 && (
          <div className="mcw-cluster" role="group" aria-label="联动买点参考">
            <span className="mcw-cluster-tag mcw-cluster-bull">买点</span>
            <div className="mcw-pills">{coreBull.map(renderPill)}</div>
          </div>
        )}
        {coreRisk.length > 0 && (
          <div className="mcw-cluster" role="group" aria-label="联动卖点与风险提醒">
            <span className="mcw-cluster-tag mcw-cluster-risk">卖点</span>
            <div className="mcw-pills">{coreRisk.map(renderPill)}</div>
          </div>
        )}
      </div>

      {showBaseline && baselineRules.length > 0 && (
        <div className="mcw-baseline-row" role="group" aria-label={evaluation.baselineLabel}>
          <span className="mcw-baseline-label">{evaluation.baselineLabel}</span>
          <div className="mcw-pills">{baselineRules.map(renderPill)}</div>
        </div>
      )}

      {screeningActive && (
        <div className="mcw-active">
          <div className="mcw-notes">
            {activeRuleSpecs.map((rule) => (
              <p key={rule.id}>
                <span className="mcw-dot" style={{ background: rule.color }} aria-hidden="true" />
                <b>{rule.short}</b>：{rule.formula} — <span>{rule.basis}</span>
              </p>
            ))}
          </div>
          <div className="mcw-scorecard" aria-label="当前组合历史触发后收益统计">
            <div className="mcw-score-head">
              <span className="mcw-score-badge">历史触发战绩 · {priceName}</span>
              <span>
                这段时间共出现 <b>{evaluation.outcome.dedupEpisodeCount}</b> 次（{evaluation.outcome.cooldownBars}{unitText}内重复算1次，共 {evaluation.outcome.rawEpisodeCount} 段 · 按每次刚出现那天收盘价往后算）
              </span>
            </div>
            <div className="mcw-score-grid">
              {renderForwardCell(evaluation.horizonLabels[0], evaluation.outcome.h1)}
              {renderForwardCell(evaluation.horizonLabels[1], evaluation.outcome.h2)}
            </div>
          </div>
          <div className="mcw-jump">
            <label>
              命中区间 ({evaluation.episodes.length}段)
              <select
                aria-label="查看组合命中区间"
                value={selectedEpisodeId}
                onChange={(event) => {
                  const epId = event.target.value;
                  if (!epId) {
                    onResetZoom();
                    return;
                  }
                  const ep = evaluation.episodes.find((item) => item.id === epId);
                  if (ep) onSelectEpisode(ep);
                }}
              >
                <option value="">选择区间并定位缩放…</option>
                {[...evaluation.episodes].reverse().map((ep) => (
                  <option key={ep.id} value={ep.id}>
                    {ep.startDate}{ep.endDate !== ep.startDate ? `—${ep.endDate}` : ""} · {ep.days}{unitText} · {ep.ruleLabel}
                  </option>
                ))}
              </select>
            </label>
            <button type="button" onClick={onResetZoom}>重置缩放</button>
          </div>
        </div>
      )}
    </div>
  );
}
