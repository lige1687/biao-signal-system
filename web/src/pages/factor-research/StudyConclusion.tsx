import type { Experiment } from "./model";
import { kindLabels, reviewLabels, runLabels, safeReportHref } from "./model";

/** Keep each conclusion, scope and caveat attached to the same experiment. */
export default function StudyConclusion({ experiment, onOpen }: { experiment: Experiment; onOpen?: () => void }) {
  const Heading = onOpen ? "h3" : "h2";
  const reports = experiment.sources.flatMap(source => {
    const href = safeReportHref(source.path);
    return href ? [{ ...source, href }] : [];
  });
  return <article className="fr-study-reading" aria-label={experiment.title} data-experiment-id={experiment.id}>
    <div className="fr-study-reading-head"><Heading>{experiment.title}</Heading>{onOpen && <button type="button" onClick={onOpen}>查看实验详情</button>}</div>
    <p className="fr-study-conclusion"><strong>{experiment.conclusion || "尚未记录结论"}</strong></p>
    <dl className="fr-study-scope">
      <div><dt>检查对象</dt><dd>{experiment.products.map(product => product.name || product.code).join("、") || "未记录"} · {kindLabels[experiment.kind] ?? experiment.kind}</dd></div>
      <div><dt>观察期</dt><dd>{experiment.period.start?.slice(0, 10) ?? "未记录"} 至 {experiment.period.end?.slice(0, 10) ?? "未记录"}</dd></div>
      <div><dt>后续期限</dt><dd>{experiment.target_horizon || "原接入资料未单列，请核对实验协议"}</dd></div>
      {experiment.evaluation_period && <div><dt>效果检查期</dt><dd>{experiment.evaluation_period}</dd></div>}
      <div><dt>资料截至</dt><dd>{experiment.data_cutoff?.slice(0, 10) ?? "未核实"}</dd></div>
    </dl>
    <p className="fr-study-limit"><strong>主要限制：</strong>{experiment.limitations[0] || "未记录，请核对原报告"}</p>
    {experiment.limitations.length > 1 && <details className="fr-study-more"><summary>全部限制（{experiment.limitations.length}项）</summary><ul>{experiment.limitations.map((text, index) => <li key={index}>{text}</li>)}</ul></details>}
    <p className="fr-study-review">{runLabels[experiment.run_status] ?? experiment.run_status} · {reviewLabels[experiment.review_status] ?? experiment.review_status} · 复核日期 {experiment.reviewed_at?.slice(0, 10) ?? "未记录"}</p>
    <details className="fr-study-more"><summary>复核说明、来源与更正</summary><p>{experiment.review_summary || "复核说明未记录"}</p>
      {experiment.source_note && <p><strong>来源记录：</strong>{experiment.source_note}</p>}
      {experiment.correction && <div className="fr-study-correction"><p><strong>{experiment.correction.status === "superseded" ? "原结果已被更正替代" : "已有更正说明"}：</strong>{experiment.correction.note}</p>{experiment.correction.sources.map(source => <p key={source.path}>{safeReportHref(source.path) ? <a href={safeReportHref(source.path)!}>阅读更正说明</a> : source.path}</p>)}</div>}
      <small>实验身份：{experiment.id}</small>
    </details>
    {experiment.correction && <p className="fr-study-limit"><strong>更正状态：</strong>{experiment.correction.note}；请连同原结果阅读。</p>}
    {reports.length > 0 && <div className="fr-study-report-links">{reports.map(source => <a key={source.path} href={source.href}>{source.role === "family_report" ? "阅读家族结案报告" : source.role === "controller" ? "阅读主控复核" : "阅读实验原报告"}</a>)}</div>}
  </article>;
}
