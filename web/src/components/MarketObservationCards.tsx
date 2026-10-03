import type { MarketObservationsResponse, MarketObservation } from "../types";
import ObservationSourceNote from "./ObservationSourceNote";
import "./market-observations.css";

const STATUS: Record<MarketObservation["quality_status"], string> = {
  current: "已核对", delayed: "延迟发布", stale: "已过期",
  time_unverified: "可用时间未核实", missing: "数据缺失", insufficient_history: "历史不足",
};

function readable(value: number, unit: string) {
  return `${new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 2 }).format(value)}${unit}`;
}

export default function MarketObservationCards({ response, title, limit, metricIds }: {
  response?: MarketObservationsResponse; title: string; limit?: number; metricIds?: string[];
}) {
  const filtered = metricIds ? response?.items.filter((item) => metricIds.includes(item.metric_id)) : response?.items;
  const items = limit ? filtered?.slice(0, limit) : filtered;
  return <section className="observation-section" aria-label={title}>
    <div className="observation-section-head"><h2>{title}</h2><span>{response ? `本页整理于 ${response.generated_at}；各项资料日期见卡片` : "资料加载中"}</span></div>
    {response?.errors.length ? <p className="observation-error">以下资料读取异常：{Array.from(new Set(response.errors.map((error) => response.items.find((item) => item.metric_id === error.split(":")[0])?.label ?? "部分来源"))).join("；")}</p> : null}
    {!items?.length && <p className="observation-empty">{response ? "所选范围暂无可展示的观察项。" : "正在加载市场观察资料…"}</p>}
    <div className="observation-grid">{items?.map((item) => {
      const showValue = item.value != null && !!item.observation_date && item.quality_status !== "missing";
      const current = item.quality_status === "current" || item.quality_status === "delayed";
      const fixedTurnover = item.metric_id === "stock_turnover" && item.observation_date === "2026-09-29";
      const changeUnit = item.change_unit ?? (item.unit === "%" ? "百分点" : item.unit);
      return <article className="observation-card" key={item.metric_id}>
        <div className="observation-card-top"><h3>{item.label}</h3><span className={`observation-status ${item.quality_status}`}>{STATUS[item.quality_status]}</span></div>
        {fixedTurnover && <p className="observation-reading">固定历史样本 · 截至 2026-09-29；刷新不会增加新交易日。</p>}
        <div className="observation-value">{showValue ? readable(item.value!, item.unit) : "—"}</div>
        {showValue && <p className="observation-change">{showValue && item.change != null ? `${item.comparison_period ?? "较上期"} ${item.change > 0 ? "+" : ""}${readable(item.change, changeUnit)}` : "暂无可比较的上期读数"}</p>}
        <p className="observation-reading">{showValue ? `${current || fixedTurnover ? "" : "最新情况未核实。"}${item.reading}` : item.quality_reason ?? "当前读数不可用于观察"}</p>
        {showValue && item.components && <p className="observation-change">看涨 {readable(item.components.bullish_pct, "%")} · 中性 {readable(item.components.neutral_pct, "%")} · 看跌 {readable(item.components.bearish_pct, "%")}</p>}
        <p className="observation-date">资料所属期：{item.observation_date ?? "未核实"}；{item.publication_precision === "unknown" ? "来源发布时间未核实" : `来源发布：${item.published_at ?? "未记录"}${item.published_at ? (item.publication_precision === "date" ? "（仅确认日期）" : "（记录到时刻）") : ""}`}</p>
        <ObservationSourceNote item={item} />
      </article>;
    })}</div>
  </section>;
}
