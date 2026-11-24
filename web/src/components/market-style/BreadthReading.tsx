import type { BreadthHistoryPoint } from "../../types";
import { BREADTH_HORIZONS, type BreadthHorizon, type BreadthReadingPoint } from "./breadthReadingTypes";
import { breadthInterpretation } from "./breadthInterpretation";

const eventNames = {
  enter_low: "进入历史低位", exit_low: "退出历史低位", enter_high: "进入历史高位", exit_high: "退出历史高位",
  stay_low: "仍在历史低位", stay_high: "仍在历史高位", none: "轨道内", unknown: "越轨状态未知",
};
const positionNames = { low: "历史低位", middle: "历史中段", high: "历史高位", flat: "轨道重合", unknown: "位置未知" };
const horizonNames = { "20": "短期参与", "50": "中期参与", "200": "长期基础" };
const number = (value: number | null | undefined, suffix = "") =>
  typeof value === "number" && Number.isFinite(value) ? `${value.toFixed(1)}${suffix}` : "—";

/** Only renders server observations. No classification or threshold calculation lives here. */
export default function BreadthReading({ date, point, reading, horizon, onHorizonChange, error }: {
  date?: string;
  point?: BreadthHistoryPoint;
  reading?: BreadthReadingPoint;
  horizon: BreadthHorizon;
  onHorizonChange: (horizon: BreadthHorizon) => void;
  error?: string;
}) {
  const selected = reading?.horizons[horizon];
  const interpretation = breadthInterpretation(point ? reading : null);
  const headline = !point ? "当日宽度缺失" : !reading ? "判读暂未提供" : interpretation.headline;
  const meaning = !point ? "这一天没有宽度记录，不能沿用此前读数判断当前状态。"
    : !reading ? error ? "历史日期或输入需要核验，暂不生成判读。" : "原始曲线仍可查看，判读资料尚未加载。"
    : interpretation.meaning;
  return <div className="bc-reading" data-tone={interpretation.tone} aria-label="所选日期宽度判读">
    <div className="bc-reading-head">
      <div><span className="bc-eyebrow">{date ?? "日期未提供"} · 参与状态</span>
        <h3>{headline}</h3></div>
      <span className="bc-reading-tag" title="宽度变化与价格可不同步；只描述当前资料，不确认顶底">观察</span>
    </div>
    <p className="bc-reading-summary">{meaning}</p>
    <div className="bc-reading-metrics" role="group" aria-label="选择宽度周期">
      {BREADTH_HORIZONS.map((period) => {
        const stats = reading?.horizons[period];
        const delta = stats?.delta_5;
        return <button key={period} type="button" aria-pressed={horizon === period} onClick={() => onHorizonChange(period)}>
          <span className="bc-metric-label">{period}日 <span>{horizonNames[period]}</span></span>
          <strong>{number(point?.[`breadth_${period}`], "%")}</strong>
          <span className="bc-metric-change" title="与5条宽度记录前相比，不保证等于5个交易日">较5条前 <b>{delta == null ? "—" : `${delta > 0 ? "+" : ""}${delta.toFixed(1)}`}</b> 点</span>
        </button>;
      })}
    </div>
    <p className="bc-reading-watch">{point && reading ? interpretation.watch : "资料不足，暂不作参与判断。"}</p>
    <details className="bc-reading-detail"><summary>历史位置与判读依据</summary>
      <p>{reading?.state.summary ?? meaning}</p>
      <div className="bc-track-reading">
      <div><b>{horizon}日 · {selected ? positionNames[selected.position] : "位置未知"}</b>
        <span>{selected?.status === "ready" ? `${eventNames[selected.event]} · 历史百分位 ${number(selected.percentile)}`
          : selected?.status === "insufficient" ? `历史不足 ${selected.sample_count}/252 条，轨道暂缺`
          : "当日轨道暂无有效读数"}</span></div>
      {selected?.status === "ready" && <div className="bc-track-values"><span>下轨 <b>{number(selected.lower, "%")}</b></span><span>中位 <b>{number(selected.median, "%")}</b></span><span>上轨 <b>{number(selected.upper, "%")}</b></span></div>}
      </div>
      <p className="bc-reading-footnote">高位回落、低位修复只是参与变化观察，未确认价格顶底。</p>
    </details>
  </div>;
}
