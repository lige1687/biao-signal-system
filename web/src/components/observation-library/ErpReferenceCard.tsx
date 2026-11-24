import { Fragment, useState } from "react";
import MiniTrend from "../market-observation-alerts/MiniTrend";
import { OBSERVATION_BY_ID } from "./catalog";
import ObservationDetailDialog from "./ObservationDetailDialog";
import { useProjectionSource } from "./projectionSources";
import "../market-observation-alerts/style.css";

/** The rates page uses the same dated ERP observation as the home and detail view. */
export default function ErpReferenceCard({ market }: { market: "cn" | "us" }) {
  const id = market === "cn" ? "erp-cn" : "erp-us";
  const source = useProjectionSource(id);
  const [open, setOpen] = useState(false);
  const last = source.points[source.points.length - 1];
  const ready = !source.isPending && !source.error && last?.value != null;
  const visible = source.points.slice(market === "cn" ? -104 : -504);
  const item = OBSERVATION_BY_ID.get(id);
  return <Fragment><div className="macro-card metric-card clickable" role="button" tabIndex={0}
    onClick={() => setOpen(true)}
    onKeyDown={event => { if (event.key === "Enter" || event.key === " ") { event.preventDefault(); setOpen(true); } }}>
    <div className="macro-head"><span className="macro-name">{market === "cn" ? "沪深300" : "标普500"}股债利差（E/P − 10Y）</span></div>
    <div className="macro-value">{ready ? `${last.value! >= 0 ? "+" : ""}${last.value!.toFixed(2)} 个百分点` : "暂不可用"}</div>
    <div className="macro-note">{source.isPending ? "正在读取股债利差…" : source.error ? "股债利差来源读取失败" : last?.value == null ? `截至 ${last?.date ?? "—"} · 最新读数缺失` : `截至 ${last.date} · ${source.frequency === "weekly" ? "周频历史参照" : "日线含月频盈利输入"}`}</div>
    <div className="macro-note">来源：{source.sourceName}</div>
    {ready && visible.length >= 2 && <MiniTrend dates={visible.map(p => p.date)} lines={[{ name: "股债利差", color: "#0891b2", values: visible.map(p => p.value) }]} label={`${market === "cn" ? "沪深300周频" : "标普500"}股债利差，单位百分点；缺值断线`} />}
    {!ready && <button type="button" onClick={event => { event.stopPropagation(); source.retry(); }}
      onKeyDown={event => event.stopPropagation()}>重试</button>}
    {item && <div className="macro-note">点开查看同源历史与参考轨道</div>}
  </div>
  {open && item && <ObservationDetailDialog item={item} onClose={() => setOpen(false)} />}
  </Fragment>;
}
