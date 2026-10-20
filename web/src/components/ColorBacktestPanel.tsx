import { useState } from "react";
import type { ColorBacktest, ColorBacktestSide, ColorPerformance } from "../types";

interface Props {
  report: ColorBacktest;
}

const ROWS: Array<{
  key: keyof Pick<
    ColorPerformance,
    "sample_count" | "win_rate" | "mean_return" | "median_return" | "mean_mfe" | "mean_mae"
  >;
  label: string;
}> = [
  { key: "sample_count", label: "样本数" },
  { key: "win_rate", label: "胜率" },
  { key: "mean_return", label: "平均策略收益" },
  { key: "median_return", label: "收益中位数" },
  { key: "mean_mfe", label: "平均MFE" },
  { key: "mean_mae", label: "平均MAE" },
];

function fmt(value: number | null, key: string): string {
  if (value == null) return "—";
  if (key === "sample_count") return String(Math.round(value));
  if (key === "win_rate") return `${(value * 100).toFixed(1)}%`;
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function tone(value: number | null, key: string): string {
  if (value == null || key === "sample_count" || key === "win_rate") return "neutral";
  return value > 0 ? "positive" : value < 0 ? "negative" : "neutral";
}

function BacktestTable({ side }: { side: ColorBacktestSide }) {
  const signalExit = side.stats.find((stat) => stat.key === "signal_exit");
  return (
    <section className={`cb-side ${side.side}`}>
      <div className="cb-side-head">
        <div>
          <h4>{side.title_cn}</h4>
          <p>{side.entry_rule_cn}</p>
        </div>
        <div className="cb-sample">
          <strong>{side.total_signals}</strong>
          <span>次信号</span>
        </div>
      </div>
      <div className="cb-exit-rule">
        <span>信号退出</span>
        {side.exit_rule_cn}
        {signalExit && <b> · 已完成 {signalExit.sample_count} 笔</b>}
        {side.open_trades > 0 && <b> · {side.open_trades} 笔尚未退出</b>}
        {signalExit?.mean_holding_days != null && (
          <b> · 平均持有 {signalExit.mean_holding_days.toFixed(1)} 日</b>
        )}
      </div>
      {signalExit && (
        <div className="cb-exit-summary" aria-label={`${side.title_cn}信号退出汇总`}>
          <div>
            <span>完成交易</span>
            <strong>{signalExit.sample_count} 笔</strong>
          </div>
          <div>
            <span>平均盈利</span>
            <strong className={tone(signalExit.mean_return, "mean_return")}>
              {fmt(signalExit.mean_return, "mean_return")}
            </strong>
          </div>
          <div>
            <span>中位盈利</span>
            <strong className={tone(signalExit.median_return, "median_return")}>
              {fmt(signalExit.median_return, "median_return")}
            </strong>
          </div>
          <div>
            <span>胜率</span>
            <strong>{fmt(signalExit.win_rate, "win_rate")}</strong>
          </div>
        </div>
      )}
      <div className="cb-table-scroll">
        <table className="cb-table">
          <thead>
            <tr>
              <th>指标</th>
              {side.stats.map((stat) => (
                <th key={stat.key} className={stat.key === "signal_exit" ? "strategy-col" : ""}>
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
                        stat.key === "signal_exit" ? "strategy-col" : ""
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

/** 绿灰黑信号的固定周期与状态退出表现；仅用于历史研究，不是交易指令。 */
export default function ColorBacktestPanel({ report }: Props) {
  const [expanded, setExpanded] = useState(false);
  const longExit = report.long.stats.find((stat) => stat.key === "signal_exit");
  const shortExit = report.short.stats.find((stat) => stat.key === "signal_exit");

  return (
    <section className={`panel color-backtest ${expanded ? "expanded" : "collapsed"}`}>
      <button
        type="button"
        className="cb-toggle"
        aria-expanded={expanded}
        aria-controls="color-backtest-content"
        onClick={() => setExpanded((current) => !current)}
      >
        <span className="cb-toggle-icon" aria-hidden="true">
          {expanded ? "−" : "+"}
        </span>
        <span className="cb-toggle-copy">
          <strong>绿灰黑信号回测</strong>
          <small>
            {report.start_date}—{report.end_date} · {report.total_bars}根有效K线 · 点击
            {expanded ? "收起" : "展开"}
          </small>
        </span>
        <span className="cb-collapsed-stats" aria-label="信号退出交易摘要">
          <span>
            做多 <b>{longExit?.sample_count ?? 0}</b> 笔
          </span>
          <span>
            均值/中位 <b>{fmt(longExit?.mean_return ?? null, "mean_return")}</b> /{" "}
            <b>{fmt(longExit?.median_return ?? null, "median_return")}</b>
          </span>
          <span>
            做空 <b>{shortExit?.sample_count ?? 0}</b> 笔
          </span>
          <span>
            均值/中位 <b>{fmt(shortExit?.mean_return ?? null, "mean_return")}</b> /{" "}
            <b>{fmt(shortExit?.median_return ?? null, "median_return")}</b>
          </span>
        </span>
        <span className="cb-research-chip">历史研究</span>
      </button>

      {expanded && (
        <div id="color-backtest-content" className="cb-content">
          <div className="cb-method">
            <b>统计口径：</b>
            历史上每次符合翻色条件都记为一笔独立交易；“信号退出”汇总所有已完成交易的平均盈利、
            中位盈利、胜率与平均持有日数，不是只计算一笔交易。{report.methodology_cn}
          </div>

          <div className="cb-grid">
            <BacktestTable side={report.long} />
            <BacktestTable side={report.short} />
          </div>

          <div className="cb-footnote">
            胜率按策略方向调整：做多上涨为正，做空下跌为正。MFE/MAE 为持有期内平均最大有利/不利波动；
            固定周期样本随周期延长而减少，信号退出未完成交易不进入平均盈利与中位盈利统计。
          </div>
        </div>
      )}
    </section>
  );
}
