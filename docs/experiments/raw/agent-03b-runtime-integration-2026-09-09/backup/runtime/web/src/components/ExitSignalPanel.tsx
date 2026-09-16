import type { ExitSignal } from "../types";
import type { Selection } from "./ExplanationPanel";

interface Props {
  exitSignals: ExitSignal[];
  onSelect: (selection: Selection) => void;
}

function fmtPct(value: number | undefined | null): string {
  if (value == null || !Number.isFinite(value)) return "-";
  return `${value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

/** 持仓退出层：展示退出条件当前是否触发、最近触发日与客观失效条件。 */
export default function ExitSignalPanel({ exitSignals, onSelect }: Props) {
  if (exitSignals.length === 0) return null;

  return (
    <section className="panel exit-signal-panel" aria-label="持仓退出">
      <div className="exit-signal-head">
        <div>
          <div className="trade-eyebrow">持仓退出参考 · 非交易指令 · 研究代理</div>
          <h3>持仓退出</h3>
        </div>
      </div>
      <div className="exit-signal-list">
        {exitSignals.map((item) => {
          const active = item.state === "active";
          const pick = () =>
            onSelect({
              source: "持仓退出 · 退出条件",
              date: item.last_trigger_date ?? undefined,
              explanation: item.explanation,
              events: item.supporting_event ? [item.supporting_event] : [],
              eventsLoading: false,
            });
          const ref = item.reference_values ?? {};
          return (
            <button
              key={item.rule_id}
              type="button"
              className={`exit-signal-row ${active ? "active" : "inactive"}`}
              onClick={pick}
              title="点击查看解释"
            >
              <span className={`trade-state ${active ? "weakened" : "watch"}`}>
                {item.state_cn}
              </span>
              <span className="trade-tier">
                <b>{item.rule_cn}</b>
                <small>{item.sub_rule_cn ?? "退出规则"}</small>
              </span>
              <span className="trade-current">
                {active
                  ? `收盘 ${item.close?.toFixed(2) ?? "-"} · 跌破 EMA20 ${fmtPct(ref.distance_to_ema20_pct)} · 跌破抵扣价 ${fmtPct(ref.distance_to_costbasis_pct)}`
                  : item.last_trigger_date
                    ? `最近触发 ${item.last_trigger_date}`
                    : "历史无触发"}
              </span>
              <span className="trade-open">查看解释</span>
            </button>
          );
        })}
      </div>
      <div className="trade-method">
        <span>A6① 抵扣价：收盘跌破 EMA20 + 20日抵扣价</span>
        <span>收盘后触发，下一交易日开盘退出</span>
      </div>
    </section>
  );
}
