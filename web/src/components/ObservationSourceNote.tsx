import type { MarketObservation } from "../types";

const ACCESS: Record<string, string> = {
  public_web: "公开网页", public_with_source_terms: "公开资料，使用受来源条款约束",
  local_source_claim_unverified: "本地资料，来源声明未逐期核实",
  unverified: "来源未核实", unknown: "来源状态未核实",
};

export default function ObservationSourceNote({ item }: { item: MarketObservation }) {
  return (
    <details className="observation-source">
      <summary>来源、参考值与限制</summary>
      {item.quality_reason && <p>{item.quality_reason}</p>}
      {item.reference_note && <p>{item.reference_note}</p>}
      {(item.metric_id === "aaii" || item.metric_id === "naaim") && <p>
        QQQ 收盘价历史检验：{item.metric_id === "aaii"
          ? "考虑当时价格走势后，尚未确认情绪有稳定的额外帮助。"
          : "原参考值对应的极端周太少，目前无法确认稳定关联。"}
        这是事后对照，不能据此提前预警。
        <a href="/library?report=docs%2Fexperiments%2Fnasdaq-sentiment-retrospective-2026-10-02.md">查看研究与反例</a>
      </p>}
      <dl>
        <div><dt>范围</dt><dd>{item.universe}</dd></div>
        <div><dt>资料所属期</dt><dd>{item.observation_date ?? "未核实"}</dd></div>
        <div><dt>来源发布时间</dt><dd>{item.publication_precision === "unknown" ? "未核实" : `${item.published_at ?? "未记录"}${item.published_at ? (item.publication_precision === "date" ? "（仅确认日期）" : "（记录到时刻）") : ""}`}</dd></div>
        <div><dt>抓取时间</dt><dd>{item.fetched_at ?? "未记录"}</dd></div>
        <div><dt>来源</dt><dd>{item.source_url ? <a href={item.source_url} target="_blank" rel="noreferrer">{item.source_name}</a> : item.source_name}（{ACCESS[item.source_access] ?? item.source_access}）</dd></div>
        <div><dt>历史范围</dt><dd>{item.history_start && item.history_end ? `${item.history_start} 至 ${item.history_end}` : "未确认"}</dd></div>
        <div><dt>样本</dt><dd>观察 {item.observation_count ?? "—"}，有效 {item.valid_count ?? "—"}，可对齐 {item.eligible_count ?? "—"}</dd></div>
        <div><dt>定义版本</dt><dd>{item.definition_version}</dd></div>
      </dl>
      {item.limitations.length > 0 && <p>{item.limitations.join("；")}</p>}
      {item.evidence_refs.length > 0 && <p>证据：{item.evidence_refs.map((ref, index) => <span key={`${ref}-${index}`}>{index > 0 ? "；" : ""}{/^https?:\/\//.test(ref) ? <a href={ref} target="_blank" rel="noreferrer">{ref}</a> : ref}</span>)}</p>}
    </details>
  );
}
