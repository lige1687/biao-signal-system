import { useState } from "react";
import type { PullbackPerformance, ScenarioBacktest, ScenarioBacktestSide } from "../types";

interface Props {
  report: ScenarioBacktest;
}

const ROWS: Array<{
  key: keyof Pick<
    PullbackPerformance,
    | "sample_count"
    | "incomplete_count"
    | "win_rate"
    | "mean_return"
    | "median_return"
    | "mean_mfe"
    | "mean_mae"
    | "mean_holding_days"
  >;
  label: string;
}> = [
  { key: "sample_count", label: "完成样本" },
  { key: "incomplete_count", label: "未完成" },
  { key: "win_rate", label: "胜率" },
  { key: "mean_return", label: "平均收益" },
  { key: "median_return", label: "收益中位数" },
  { key: "mean_mfe", label: "平均MFE" },
  { key: "mean_mae", label: "平均MAE" },
  { key: "mean_holding_days", label: "平均持有日" },
];

function fmt(value: number | null, key: string): string {
  if (value == null) return "—";
  if (key === "sample_count" || key === "incomplete_count") return String(Math.round(value));
  if (key === "win_rate") return `${(value * 100).toFixed(1)}%`;
  if (key === "mean_holding_days") return value.toFixed(1);
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function tone(value: number | null, key: string): string {
  if (
    value == null ||
    key === "sample_count" ||
    key === "incomplete_count" ||
    key === "win_rate" ||
    key === "mean_holding_days"
  ) {
    return "neutral";
  }
  return value > 0 ? "positive" : value < 0 ? "negative" : "neutral";
}

function SideTable({ side }: { side: ScenarioBacktestSide }) {
  const ruleExit = side.stats.find((stat) => stat.key === "rule_exit");
  return (
    <section className="pb-side">
      <div className="pb-side-head">
        <div>
          <h4>{side.title_cn}</h4>
          <p>{side.entry_rule_cn}</p>
        </div>
        <div className="pb-sample">
          <strong>{side.total_signals}</strong>
          <span>次确认</span>
        </div>
      </div>
      <div className="pb-exit-rule">
        <span>规则退出</span>
        {side.exit_rule_cn}
        {ruleExit && <b> · 已完成 {ruleExit.sample_count} 笔</b>}
        {side.open_trades > 0 && <b> · {side.open_trades} 笔未退出</b>}
      </div>
      <div className="pb-table-scroll">
        <table className="pb-table">
          <thead>
            <tr>
              <th>指标</th>
              {side.stats.map((stat) => (
                <th key={stat.key} className={stat.key === "rule_exit" ? "strategy-col" : ""}>
                  {stat.label_cn}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {ROWS.map((row) => (
              <tr key={row.key}>
                <th>{row.label}</th>
                {side.stats.map((stat) => {
                  const value = stat[row.key] as number | null;
                  return (
                    <td
                      key={stat.key}
                      className={`${tone(value, row.key)} ${
                        stat.key === "rule_exit" ? "strategy-col" : ""
                      }`}
                    >
                      {fmt(value, row.key)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function ScenarioBacktestPanel({ report }: Props) {
  const [expanded, setExpanded] = useState(false);
  const summaries = report.sides.map((side) => ({
    side,
    exit: side.stats.find((stat) => stat.key === "rule_exit"),
  }));

  return (
    <section className={`panel scenario-backtest ${expanded ? "expanded" : "collapsed"}`}>
      <button
        type="button"
        className="pb-toggle"
        aria-expanded={expanded}
        aria-controls={`scenario-backtest-${report.scenario_id}`}
        onClick={() => setExpanded((current) => !current)}
      >
        <span className="pb-toggle-icon" aria-hidden="true">
          {expanded ? "−" : "+"}
        </span>
        <span className="pb-toggle-copy">
          <strong>{report.scenario_cn}</strong>
          <small>
            {report.start_date}—{report.end_date} · 研究代理 · 点击{expanded ? "收起" : "展开"}
          </small>
        </span>
        <span className="pb-collapsed-stats" aria-label={`${report.scenario_cn} 规则退出摘要`}>
          {summaries.map(({ side, exit }) => (
            <span key={side.key}>
              {side.title_cn} <b>{side.total_signals}</b>次 · 均值
              <b>{fmt(exit?.mean_return ?? null, "mean_return")}</b>
            </span>
          ))}
        </span>
        <span className="pb-research-chip">研究代理</span>
      </button>

      {expanded && (
        <div id={`scenario-backtest-${report.scenario_id}`} className="pb-content">
          <div className="pb-method">
            <b>规则口径：</b>
            {report.research_disclaimer_cn}
          </div>
          <div className="pb-grid">
            {report.sides.map((side) => (
              <SideTable key={side.key} side={side} />
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
