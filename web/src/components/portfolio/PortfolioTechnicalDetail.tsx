import { useQuery } from "@tanstack/react-query";
import { api } from "../../api/client";
import type { PortfolioHolding } from "../../types";
import type { HoldingSymbolMap } from "../../utils/portfolioSymbols";

interface Props { holding: PortfolioHolding; map: HoldingSymbolMap | undefined }

const price = (value: number) => Number.isFinite(value) ? value.toLocaleString("zh-CN", { maximumFractionDigits: 3 }) : "—";
const distance = (value: number) => Number.isFinite(value) ? `${value.toFixed(2)}%` : "—";
function referenceText(values: Record<string, number>) {
  return Object.entries(values).flatMap(([key, value]) => {
    if (key === "ema20") return [`20日指数均线 ${price(value)}`];
    if (/^close_lag\d+$/.test(key)) return [`${key.slice("close_lag".length)}日抵扣价 ${price(value)}`];
    if (key === "distance_to_ema20_pct") return [`距20日指数均线 ${distance(value)}`];
    if (key === "distance_to_costbasis_pct") return [`距抵扣价 ${distance(value)}`];
    return [];
  }).join("、");
}

export default function PortfolioTechnicalDetail({ holding, map }: Props) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["detail", map?.symbol],
    queryFn: () => api.detail(map!.symbol),
    enabled: Boolean(map),
    staleTime: 60_000,
  });
  if (!map) return <section className="pl-technical">
    <h3>技术状态与退出条件</h3>
    <p className="pl-technical-gap">尚未关联自身行情，阶段、触发条件和退出参考暂缺。对应指数或板块只能作背景参考，不能替代基金自身的判断。</p>
    <dl className="pl-missing"><div><dt>原入场依据</dt><dd>本页持仓记录未提供</dd></div><div><dt>原交易失效位</dt><dd>本页持仓记录未提供</dd></div></dl>
  </section>;
  if (isLoading) return <section className="pl-technical"><h3>技术状态与退出条件</h3><p>正在读取自身行情…</p></section>;
  if (error || !data) return <section className="pl-technical"><h3>技术状态与退出条件</h3><p>自身行情已关联，但技术资料暂时无法读取：{(error as Error | null)?.message ?? "请稍后重试"}。</p><p>原入场依据和失效位在本页持仓记录中未提供。</p></section>;
  const a = data.assessment;
  const conditions = a.conditional_scenarios ?? [];
  const exits = a.exit_signals ?? [];
  return <section className="pl-technical">
    <h3>技术状态与退出条件</h3>
    <p className="pl-technical-source">同一产品：{map.displayName}（{map.symbol}）<br />
      行情日 {data.meta.last_bar_date ?? a.as_of ?? "未提供"} · 来源 {data.meta.provider ?? "未提供"}
      {data.meta.is_intraday_forming ? " · 盘中形成中" : ""}
      {data.meta.cache_fallback_used ? " · 使用缓存" : ""}
    </p>
    <dl className="pl-tech-facts">
      <div><dt>阶段</dt><dd>{a.stage_cn || "未提供"}</dd></div>
      <div><dt>价格与20日均线/抵扣价</dt><dd>{a.color_cn || "未提供"}</dd></div>
      <div><dt>长周期背景</dt><dd>{a.dimensions["长周期"] || "未提供"}</dd></div>
      <div><dt>阶段依据</dt><dd>{a.stage_change_reason_cn || "当前资料未给出明确描述"}</dd></div>
    </dl>
    {(a.supports.length > 0 || a.conflicts.length > 0) && <div className="pl-tech-evidence">
      <h4>已给出的技术依据</h4>
      {a.supports.slice(0, 2).map(f => <p key={f.rule_id}><strong>{f.label_cn}</strong>：{f.detail_cn}</p>)}
      {a.conflicts.slice(0, 2).map(f => <p key={f.rule_id}><strong>{f.label_cn}</strong>：{f.detail_cn}</p>)}
    </div>}
    <div className="pl-tech-evidence"><h4>触发条件与退出提示</h4>
      <p>标为“研究代理”的内容，是将策略原则转换为程序条件的研究参考。</p>
      {conditions.length ? conditions.slice(0, 3).map(s => <p key={s.scenario_id}><strong>{s.scenario_cn} · {s.state_cn}</strong>（截至 {s.latest_date}）<br />
        关键价 {price(s.key_price)}；{s.next_step_cn}
        {s.missing_conditions.length > 0 && <>；尚缺：{s.missing_conditions.join("、")}</>}
        {s.invalidation_cn && <>；场景失效：{s.invalidation_cn}</>}
        {s.research_proxy ? " · 研究代理，不能直接作为交易指令" : ""}</p>) : <p>当前详情没有条件场景记录。</p>}
      {exits.length ? exits.slice(0, 3).map(e => <p key={e.rule_id}><strong>{e.rule_cn} · {e.state_cn}</strong>{e.last_trigger_date ? `（最近触发日 ${e.last_trigger_date}）` : ""}<br />
        {e.reason_cn}
        {e.close != null && <>；对应收盘价 {price(e.close)}</>}
        {referenceText(e.reference_values) && <>；参考值 {referenceText(e.reference_values)}</>}
        {e.research_proxy ? " · 研究代理" : ""}</p>) : <p>当前详情没有退出信号记录；这不表示没有风险。</p>}
    </div>
    <dl className="pl-missing"><div><dt>原入场依据</dt><dd>本页持仓记录未提供</dd></div><div><dt>原交易失效位</dt><dd>本页持仓记录未提供；上方场景及退出字段不自动替代个人原计划</dd></div></dl>
    {data.meta.data_warnings.length > 0 && <p className="pl-technical-warning">{data.meta.data_warnings.join("；")}</p>}
    <p className="pl-technical-foot">以上技术状态来自该产品的行情记录。持仓金额与收益属于另一份记录；尚未核对 {holding.name} 的原交易计划。</p>
  </section>;
}
