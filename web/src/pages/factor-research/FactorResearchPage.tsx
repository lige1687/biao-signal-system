import { useEffect, useState, type ReactNode } from "react";
import { useSearchParams } from "react-router-dom";
import type { AssessmentFramework, AssessmentTopic, DossierSection, Experiment, FactorItem, Filters, GuideLookup, MetricsGuidance, Project, ReadingGuidance, Snapshot, Source } from "./model";
import { accountMetricRows, calculationLabels, cardMetricEvidence, categoryObjectCounts, categoryTone, checkEvidence, displayFactorName, dossierFacts, dossierSection, emptyFilters, emptyGuides, factorOutcome, formatGeneratedAt, formatValue, groupCatalog, indexGuides, kindLabels, limitationText, linkedExperiments, metricProfileFor, nextSearchParams, paginateCatalog, projectStageLabels, purposeText, resultLabels, resultTone, reviewLabels, reviewTone, runLabels, safeReportHref, sortCatalog, stageLabels, statusText, typeLabels, type CatalogSort, type DisplayTone } from "./model";
import readingGuidance from "./reading-guidance.json";
import metricsGuidance from "./metrics-guidance.json";
import assessmentFramework from "./assessment-framework.json";
import FactorResearchOverview from "./FactorResearchOverview";
import StudyConclusion from "./StudyConclusion";
import { catalogAction, factorView } from "./overviewModel";
import "./factor-research.css";

const TAB_LABELS: Record<string, string> = { overview: "研究概览", catalog: "因子目录", experiments: "实验与组合", legacy: "旧行情快照" };
const display = (value: string | null | undefined) => value?.trim() || "未记录";
const date = (value: string | null | undefined) => value ? value.slice(0, 10) : "未记录";
const reading = (() => {
  try { return { guides: indexGuides(readingGuidance as ReadingGuidance), error: null as string | null, note: readingGuidance.note }; }
  catch (error) { return { guides: emptyGuides, error: error instanceof Error ? error.message : String(error), note: "阅读说明暂时不可用。" }; }
})();
const metricGuide = metricsGuidance as MetricsGuidance;
const assessment = assessmentFramework as AssessmentFramework;
const observationPeriod = (experiment: Experiment) => `${date(experiment.period.start)} 至 ${date(experiment.period.end)}`;
const priceStudyCaution = (experiment: Experiment) => experiment.measure === "prediction_error" ? "预测误差减少表示预测更接近实际；负值表示误差增加。这些比例不是胜率或投资收益。" : experiment.kind === "predictive_study" ? "排名关系不是胜率；后续价格差不是账户收益。" : experiment.kind === "price_description" ? "后续价格均值不是完整账户收益。" : null;

function StatusBadge({ children, tone }: { children: ReactNode; tone: DisplayTone }) {
  return <span className="fr-status-badge" data-tone={tone}><span aria-hidden="true" className="fr-badge-mark" />{children}</span>;
}

function SourceList({ sources }: { sources: Source[] }) {
  if (!sources.length) return <p className="fr-dim">本项未记录可打开的来源。</p>;
  return <ul className="fr-sources">{sources.map((source, i) => {
    const href = safeReportHref(source.path);
    return <li key={`${source.path}-${i}`}>
      {href ? <a href={href}>{source.path}</a> : <code>{source.path}</code>}
      <small>{source.role ? `${source.role} · ` : ""}SHA-256 {source.sha256 ? source.sha256.slice(0, 12) : "未记录"}</small>
    </li>;
  })}</ul>;
}

function Notes({ title, values }: { title: string; values: string[] }) {
  return <section className="fr-notes"><h3>{title}</h3>{values.length ? <ul>{values.map((v, i) => <li key={i}>{limitationText(v)}</li>)}</ul> : <p className="fr-dim">未记录</p>}</section>;
}

function PeriodDifferenceChart({ table }: { table: Experiment["result_tables"][number] }) {
  const periodKey = table.columns.find(c => c.key === "period" || c.key === "year")?.key;
  const difference = table.columns.find(c => c.unit === "fraction");
  if (!periodKey || !difference) return null;
  const points = table.rows.map(row => ({ label: row[periodKey], value: row[difference.key] })).filter((p): p is { label: string | number; value: number } => (typeof p.label === "string" || typeof p.label === "number") && typeof p.value === "number" && Number.isFinite(p.value));
  if (points.length < 2) return null;
  const max = Math.max(...points.map(p => Math.abs(p.value)));
  if (max === 0) return null;
  return <figure className="fr-period-chart" aria-label={`${table.title}：${difference.label}，单位百分点`}><figcaption>{difference.label}（百分点，零线左右分别表示负值和正值）</figcaption>{points.map((p, i) => <div className="fr-period-row" key={`${p.label}-${i}`}><span>{p.label}</span><div className="fr-period-track"><div className={`fr-period-bar${p.value < 0 ? " negative" : ""}`} style={{ width: `${Math.abs(p.value) / max * 50}%`, left: p.value < 0 ? `${50 - Math.abs(p.value) / max * 50}%` : "50%" }} /></div><strong>{formatValue(p.value, "fraction")}</strong></div>)}</figure>;
}

function ResultTable({ table }: { table: Experiment["result_tables"][number] }) {
  const periodKey = table.columns.find(column => column.key === "period" || column.key === "year")?.key;
  const differenceKey = table.columns.find(column => column.unit === "fraction")?.key;
  const chartValues = periodKey && differenceKey ? table.rows.filter(row => (typeof row[periodKey] === "string" || typeof row[periodKey] === "number") && typeof row[differenceKey] === "number" && Number.isFinite(row[differenceKey])).map(row => row[differenceKey] as number) : [];
  const hasChart = chartValues.length >= 2 && chartValues.some(value => value !== 0);
  return <section className="fr-section fr-result-table"><h3>{table.title}</h3><PeriodDifferenceChart table={table} />{table.note && <p className="fr-table-note">{table.note}</p>}<details open={!hasChart} className="fr-raw-table"><summary>{hasChart ? "查看精确数值表" : "原结果表"} · {table.rows.length} 行</summary><div className="fr-table-scroll"><table><thead><tr>{table.columns.map(column => <th key={column.key} scope="col">{column.label}</th>)}</tr></thead><tbody>{table.rows.map((row, rowIndex) => <tr key={rowIndex}>{table.columns.map(column => <td key={column.key}>{formatValue(row[column.key] ?? null, column.unit)}</td>)}</tr>)}</tbody></table></div></details></section>;
}

function AccountMetrics({ experiment, reference }: { experiment: Experiment | null; reference?: string }) {
  const rows = accountMetricRows(metricGuide.account_metrics, experiment, reference);
  const noCompletedAccount = !experiment || experiment.kind !== "strategy_backtest" && experiment.kind !== "portfolio_comparison" || experiment.run_status !== "completed";
  const keyLabels = rows.filter(row => ["net_annualized_return", "max_drawdown", "costs"].includes(row.spec.id)).map(row => row.spec.label);
  return <section className="fr-section fr-account-section"><h3>完整账户的收益、风险与代价</h3>
    {!noCompletedAccount && <p className="fr-account-intro">这些数值只读取同一版本、已运行完整策略或组合实验的原指标；需连同费用与固定对照口径阅读。</p>}
    {experiment && <p className="fr-metric-provenance">{experiment.title} · {observationPeriod(experiment)} · {runLabels[experiment.run_status] ?? experiment.run_status} · {reviewLabels[experiment.review_status] ?? experiment.review_status}</p>}
    {noCompletedAccount ? <><p className="fr-account-empty">{!experiment ? "尚无此版本已接入的完整策略或组合回测；价格变化不能当账户收益。" : experiment.kind !== "strategy_backtest" && experiment.kind !== "portfolio_comparison" ? "本实验未计算完整账户指标；价格变化不能当账户收益。" : `对应回测${runLabels[experiment.run_status] ?? "尚未完成"}，暂无可展示的账户数值。`}</p><p className="fr-account-key-labels">待核账户项：{keyLabels.join(" · ")}{rows.length > keyLabels.length ? " 等" : ""}</p><details className="fr-account-guide"><summary>查看全部 {rows.length} 项账户指标及解释</summary><div className="fr-table-scroll"><table className="fr-account-table"><thead><tr><th scope="col">账户关注项</th><th scope="col">为什么要看</th></tr></thead><tbody>{rows.map(row => <tr key={row.spec.id}><th scope="row">{row.spec.label}</th><td>{row.spec.meaning}</td></tr>)}</tbody></table></div></details></> : <div className="fr-account-grid">{rows.map(row => <div key={row.spec.id}><strong>{row.spec.label}</strong><span className={row.status === "available" ? "fr-account-value" : "fr-account-gap"}>{row.metric ? formatValue(row.metric.value, row.metric.unit) : "未报告"}</span><small>{row.spec.meaning}</small></div>)}</div>}
  </section>;
}

function ExperimentEvidence({ experiment, onOpen }: { experiment: Experiment; onOpen: () => void }) {
  return <div className="fr-experiment-evidence"><div className="fr-experiment-evidence-head"><strong>{experiment.title}</strong><div>{experiment.result && <StatusBadge tone={resultTone(experiment.result)}>{resultLabels[experiment.result as keyof typeof resultLabels] ?? experiment.result}</StatusBadge>}<button type="button" onClick={onOpen}>查看实验</button></div></div>
    <p className="fr-metric-provenance">{kindLabels[experiment.kind] ?? experiment.kind} · {observationPeriod(experiment)} · {runLabels[experiment.run_status] ?? experiment.run_status} · {reviewLabels[experiment.review_status] ?? experiment.review_status}</p>
    {experiment.metrics.length > 0 ? <div className="fr-metric-list">{experiment.metrics.map((metric, index) => <div key={index}><span>{metric.label}</span><strong>{formatValue(metric.value, metric.unit)}</strong>{metric.meaning && <details className="fr-metric-meaning"><summary>口径</summary><small>{metric.meaning}</small></details>}</div>)}</div> : <p className="fr-dim">本实验暂无已接入数值。</p>}
    {priceStudyCaution(experiment) && <p className="fr-price-caution">{priceStudyCaution(experiment)}</p>}
    <details className="fr-experiment-method"><summary>样本、产品范围与固定对照</summary><p>产品：{experiment.products.length ? experiment.products.map(product => product.name && product.name !== product.code ? `${product.name}（${product.code}）` : product.code).join("、") : "未记录"}；固定对照：{display(experiment.baseline)}</p>{experiment.sample.length > 0 && <div className="fr-evidence-samples"><strong>样本</strong>{experiment.sample.map((sample, index) => <span key={index}>{sample.label} {formatValue(sample.value, sample.unit)}</span>)}</div>}</details>
  </div>;
}

function ExperimentDetail({ experiment }: { experiment: Experiment }) {
  return <article className="fr-detail" aria-label="实验详情">
    <StudyConclusion experiment={experiment} />
    <section className="fr-section fr-experiment-key-results"><h3>本实验已报告的指标</h3>{experiment.metrics.length ? <div className="fr-metric-list">{experiment.metrics.map((m, i) => <div key={i}><span>{m.label}</span><strong>{formatValue(m.value, m.unit)}</strong>{m.meaning && <details className="fr-metric-meaning"><summary>口径</summary><small>{m.meaning}</small></details>}</div>)}</div> : <p className="fr-dim">本实验暂无已接入数值。</p>}</section>
    {priceStudyCaution(experiment) && <p className="fr-price-caution">{priceStudyCaution(experiment)}</p>}
    {experiment.result_tables.map((table, i) => <ResultTable table={table} key={i} />)}
    <AccountMetrics experiment={experiment} />
    <details className="fr-experiment-method"><summary>复核、样本与实验口径</summary><div className="fr-callout fr-review-callout" data-tone={reviewTone(experiment.review_status)}><strong>复核到哪一步</strong><p>{display(experiment.review_summary)}</p></div><dl className="fr-facts">
      <div><dt>研究对象版本</dt><dd>{experiment.references.length ? experiment.references.join("、") : "未绑定正式定义"}</dd></div>
      <div><dt>产品</dt><dd>{experiment.products.length ? experiment.products.map(p => p.name && p.name !== p.code ? `${p.name}（${p.code}）` : p.code).join("、") : "未记录"}</dd></div>
      <div><dt>观察期</dt><dd>{date(experiment.period.start)} 至 {date(experiment.period.end)}</dd></div>
      <div><dt>数据截至</dt><dd>{date(experiment.data_cutoff)}</dd></div>
      <div><dt>运行时间</dt><dd>{date(experiment.run_at)}</dd></div>
      <div><dt>复核时间</dt><dd>{date(experiment.reviewed_at)}</dd></div>
      <div><dt>对照方法</dt><dd>{display(experiment.baseline)}</dd></div>
      <div><dt>费用与成交</dt><dd>{display(experiment.costs)}</dd></div>
    </dl>{experiment.result && <p>结果登记：{resultLabels[experiment.result as keyof typeof resultLabels] ?? experiment.result}</p>}{experiment.sample.length > 0 && <section className="fr-section"><h3>样本范围</h3><div className="fr-metric-list">{experiment.sample.map((m, i) => <div key={i}><span>{m.label}</span><strong>{formatValue(m.value, m.unit)}</strong></div>)}</div></section>}<Notes title="适用限制" values={experiment.limitations} /><Notes title="后续工作" values={experiment.next_steps} /></details>
    <details className="fr-sources-fold"><summary>来源与文件指纹</summary><SourceList sources={experiment.sources} /></details>
  </article>;
}

const dossierTabs: { id: DossierSection; label: string }[] = [{ id: "overview", label: "总览" }, { id: "evidence", label: "研究证据" }, { id: "strategy", label: "策略与组合" }, { id: "definition", label: "定义与数据" }];

function AssessmentChecks({ topic, item, experiments, initialOpen = false }: { topic: AssessmentTopic; item: FactorItem; experiments: Experiment[]; initialOpen?: boolean }) {
  const states = topic.checks.map(check => ({ check, evidence: checkEvidence(item, experiments, check) }));
  const matched = states.filter(state => state.evidence.length > 0).length;
  return <details className="fr-assessment-checks" open={initialOpen}><summary><strong>{topic.title}</strong><span>{matched ? `可展开查看 ${matched} 项相关资料` : "暂无单列资料"}；有材料不代表检查通过</span></summary><div className="fr-assessment-list">{states.map(({ check, evidence }) => <div key={check.id} className="fr-assessment-row"><div><strong>{check.label}</strong><p>{check.why}</p></div><span className={evidence.length ? "has-source" : "no-source"}>{evidence.length ? "有对应资料，仍需核对" : "本页未单列资料"}</span>{evidence.length > 0 && <details><summary>查看对应资料（{evidence.length}）</summary><ul>{evidence.map((entry, index) => <li key={`${entry.kind}-${entry.label}-${index}`}>{entry.label}</li>)}</ul></details>}</div>)}</div></details>;
}

function FactorDetail({ item, versions, experiments, guides, section, onSectionChange, onOpenExperiment, onVersionChange }: { item: FactorItem; versions: FactorItem[]; experiments: Experiment[]; guides: GuideLookup; section: DossierSection; onSectionChange: (section: DossierSection) => void; onOpenExperiment: (id: string) => void; onVersionChange: (reference: string) => void }) {
  const linked = linkedExperiments(item, experiments);
  const guide = guides.get(item.reference);
  const metricProfile = metricProfileFor(item, metricGuide);
  const facts = dossierFacts(item, experiments, Boolean(guide));
  const accountExperiments = linked.filter(experiment => experiment.kind === "strategy_backtest" || experiment.kind === "portfolio_comparison");
  const comparisons = linked.filter(experiment => experiment.kind === "portfolio_comparison");
  const topic = (id: string) => assessment.topics.find(value => value.id === id);
  const originalLimits = linked.flatMap(experiment => experiment.limitations.map(text => ({ title: experiment.title, text })));
  const leadMetrics = cardMetricEvidence(item, experiments);
  const outcome = factorOutcome(item);
  const completedAccounts = accountExperiments.filter(experiment => experiment.run_status === "completed");
  const hasAccountValue = completedAccounts.some(experiment => accountMetricRows(metricGuide.account_metrics, experiment, item.reference).some(row => row.status === "available"));
  return <article className="fr-detail fr-factor-detail fr-dossier" aria-label="因子研究档案" data-category={categoryTone(item.category)}>
    <div className="fr-dossier-heading"><h2>{displayFactorName(item, guides)}</h2><div className="fr-meta-line"><span className="fr-category-tag" data-category={categoryTone(item.category)}>{item.category}</span><span>{typeLabels[item.object_type] ?? item.object_type}</span><span>v{item.version}</span></div></div>
    <p className="fr-detail-question"><strong>观察什么：</strong>{guide?.watch || purposeText(item.purpose)}</p>
    <p className="fr-detail-answer"><strong>已接入资料：</strong>{linked.length ? `本精确版本有${linked.length}项实验。每项结论只适用于下列对应范围，不合并成一个买卖判断。` : `${outcome.headline}。${outcome.explanation}`}</p>
    {linked.map(experiment => <StudyConclusion key={experiment.id} experiment={experiment} onOpen={() => onOpenExperiment(experiment.id)} />)}
    {!linked.length && item.limitations[0] && <p className="fr-detail-limit"><strong>定义限制：</strong>{limitationText(item.limitations[0])}</p>}
    {versions.length > 1 && <div className="fr-version-choice"><label htmlFor="fr-version">定义版本</label><select id="fr-version" value={item.reference} onChange={e => onVersionChange(e.target.value)}>{versions.map(version => <option key={version.reference} value={version.reference}>v{version.version}{version.reference === item.reference ? "（当前）" : ""}</option>)}</select><span>各版研究证据独立展示。</span></div>}
    <nav className="fr-dossier-tabs" aria-label="档案内部页面">{dossierTabs.map(tab => <button key={tab.id} type="button" aria-current={section === tab.id ? "page" : undefined} className={section === tab.id ? "active" : ""} onClick={() => onSectionChange(tab.id)}>{tab.label}</button>)}</nav>
    {section === "overview" && <div className="fr-dossier-panel" aria-label="总览">
      <section className="fr-user-outcome" data-tone={outcome.tone}><span>有没有帮助</span><h3>{outcome.headline}</h3><p>{outcome.explanation}</p><details><summary>查看登记原结论与状态</summary><p>{display(item.research.summary)}</p><small>{stageLabels[item.research.stage] ?? "阶段未核明"} · {resultLabels[item.research.result] ?? "结论未核明"} · 证据日期 {date(item.research.evidence_date)}</small></details></section>
      <div className="fr-user-answers"><section><h3>策略能否增加收益？</h3><p>{hasAccountValue ? "已有完整账户指标；是否改善收益仍须看原实验固定对照。" : completedAccounts.length ? "已有完整回测记录，但本页未报告可核的账户指标，暂不能判断。" : "尚不能判断：暂无可展示的同版本扣费后账户结果。"}</p><small>短期价格变化、预测误差与排名关系不是账户利润。</small></section></div>
      {leadMetrics.length > 0 && <details className="fr-user-numbers"><summary>查看本次研究的原数值与单位</summary><div>{leadMetrics.map(({ experiment, metric }, index) => <p key={`${experiment.id}-${index}`}><strong>{metric.label}：{formatValue(metric.value, metric.unit)}</strong><span> · {observationPeriod(experiment)} · {reviewLabels[experiment.review_status] ?? experiment.review_status}</span></p>)}</div></details>}
      <div className="fr-overview-purpose"><strong>它关注什么</strong><span>{guide?.watch || purposeText(display(item.purpose))}</span>{guide && <details><summary>完整读法与误读</summary><div><p><strong>重点看：</strong>{guide.watch}</p><p><strong>怎么看：</strong>{guide.read}</p><p><strong>还需一起看：</strong>{guide.context.join("；")}</p><p><strong>容易误读：</strong>{guide.pitfall}</p><small>{guide.verification_scope}</small></div></details>}</div>
      <details className="fr-overview-limits"><summary>查看全部局限与下一步（{item.limitations.length + originalLimits.length} 项局限）</summary><div className="fr-dossier-limit-columns"><div><strong>本版本限制</strong>{item.limitations.length ? <ul>{item.limitations.map((text, index) => <li key={index}>{limitationText(text)}</li>)}</ul> : <p>未记录</p>}</div><div><strong>关联实验原限制</strong>{originalLimits.length ? <ul>{originalLimits.map((limit, index) => <li key={index}>{limit.text}<small>— {limit.title}</small></li>)}</ul> : <p>暂无关联实验原限制；不表示不存在其他限制。</p>}</div></div><Notes title="本版本后续工作" values={item.next_steps} /></details>
      <details className="fr-deep-material"><summary>深入了解：定义范围与八方面核对资料</summary><div className="fr-dossier-scope"><div><strong>定义适用</strong><p>{display(item.scope)} · {item.asset_classes.join("、") || "资产未记录"}</p></div><div><strong>本版已接入研究</strong><p>{linked.length ? linked.map(experiment => `${experiment.title}：${observationPeriod(experiment)}；${experiment.products.map(product => product.name || product.code).join("、") || "产品未记录"}`).join("；") : "暂无关联实验；定义范围不等于验证范围。"}</p></div></div><p className="fr-dossier-note">资料可见不等于核查通过或投资有效。</p><div className="fr-dense-topic-grid">{assessment.topics.map(topicItem => { const fact = facts.find(value => value.id === topicItem.id); const missing = topicItem.checks.filter(check => checkEvidence(item, experiments, check).length === 0); return <button className="fr-dense-topic" type="button" key={topicItem.id} onClick={() => onSectionChange(topicItem.section === "overview" ? "definition" : topicItem.section)}><strong>{topicItem.title}</strong><span>{fact?.label ?? "资料未核明"}</span><small>{missing.length ? `待查：${missing[0].label}${missing.length > 1 ? `等${missing.length}项` : ""}` : "相关资料已列，仍需核对"}</small></button>; })}</div></details>
    </div>}
    {section === "evidence" && <div className="fr-dossier-panel" aria-label="研究证据">
      <section className="fr-section fr-evidence-first"><h3>此版本的真实实验结果</h3>{linked.length ? linked.map(experiment => <div className="fr-dossier-experiment" key={experiment.id}><ExperimentEvidence experiment={experiment} onOpen={() => onOpenExperiment(experiment.id)} />{experiment.result_tables.map((table, index) => <ResultTable key={index} table={table} />)}<details className="fr-experiment-review"><summary>原结论、复核说明、日期与实验限制</summary><p>实验原结论：{display(experiment.conclusion)}</p><p>复核说明：{display(experiment.review_summary)}；数据截至 {date(experiment.data_cutoff)}；运行 {date(experiment.run_at)}；复核 {date(experiment.reviewed_at)}</p><Notes title="本实验限制" values={experiment.limitations} /></details></div>) : <p className="fr-dim">本精确版本暂无已接入实验数值或逐期表。不能据此断言全仓从未研究。</p>}</section>
      <details className="fr-method-fold"><summary>按用途理解评价指标</summary><div className="fr-metric-checks">{metricProfile ? <><p>{metricProfile.title}</p><ul>{metricProfile.checks.map(check => <li key={check.label}><strong>{check.label}</strong><span>{check.why}</span></li>)}</ul></> : <p>当前类别暂无专门检查项，请按上方实验的用途和原结论阅读。</p>}<small>检查项不是新计算或有效性判定。</small></div></details>
      <details className="fr-method-fold"><summary>逐项核对资料与稳健性</summary><p className="fr-dossier-note">有对应资料不等于检查通过。逐期表不凭年份正负数量判稳定。</p>{["effect", "stability", "robustness"].map(id => topic(id) && <AssessmentChecks key={id} topic={topic(id)!} item={item} experiments={experiments} />)}</details>
    </div>}
    {section === "strategy" && <div className="fr-dossier-panel" aria-label="策略与组合">
      {accountExperiments.length > 0 && <section className="fr-dossier-strategy-lead"><h3>完整账户结果</h3><p>此版本关联 {accountExperiments.length} 项策略或组合实验，以下按每项原实验分别呈现。</p></section>}
      {accountExperiments.length ? accountExperiments.map(experiment => <AccountMetrics key={experiment.id} experiment={experiment} reference={item.reference} />) : <AccountMetrics experiment={null} reference={item.reference} />}
      <section className="fr-section fr-dossier-combination"><h3>加入组合后，需核新增价值</h3><p>{comparisons.length ? `已关联 ${comparisons.length} 项组合对照实验；实验类型不代表各项增量证据均已报告。` : "本版本未关联组合对照实验；不能推定分散或净收益改善。"}</p>{comparisons.map(experiment => <ExperimentEvidence key={experiment.id} experiment={experiment} onOpen={() => onOpenExperiment(experiment.id)} />)}{["implementation", "incremental"].map(id => topic(id) && <AssessmentChecks key={id} topic={topic(id)!} item={item} experiments={experiments} />)}</section>
    </div>}
    {section === "definition" && <div className="fr-dossier-panel" aria-label="定义与数据">
      <section className="fr-section"><h3>正式定义与计算口径</h3><dl className="fr-facts"><div><dt>正式定义名称</dt><dd>{item.name}</dd></div><div><dt>精确身份</dt><dd><code>{item.reference}</code></dd></div><div><dt>计算核对</dt><dd>{statusText(item.calculation.status, calculationLabels)}；{display(item.calculation.scope)}</dd></div><div><dt>公式</dt><dd><code>{display(item.formula)}</code></dd></div><div><dt>单位</dt><dd>{display(item.unit)}</dd></div><div><dt>输入</dt><dd>{display(item.input)}</dd></div><div><dt>何时可用</dt><dd>{display(item.time)}</dd></div><div><dt>定义适用范围</dt><dd>{display(item.scope)}；{item.asset_classes.join("、") || "资产未记录"}</dd></div></dl><p className="fr-dim">定义写有时间与输入要求，不等于每次历史实验已验证资料当时可得。</p></section>
      <section className="fr-section"><h3>资料问题与来源范围</h3><p className="fr-dim">已有实验的产品、观察期和样本读数列在研究证据页；它们不等于缺失率、覆盖率或独立样本数。</p>{["purpose", "data", "governance"].map(id => topic(id) && <AssessmentChecks key={id} topic={topic(id)!} item={item} experiments={experiments} />)}</section>
      <section className="fr-section"><h3>版本、实验日期与复核</h3><div className="fr-table-scroll"><table className="fr-governance-table"><thead><tr><th scope="col">精确关联实验</th><th scope="col">观察期</th><th scope="col">资料截至</th><th scope="col">运行</th><th scope="col">复核</th></tr></thead><tbody>{linked.map(experiment => <tr key={experiment.id}><th scope="row">{experiment.title}<small>{experiment.id}</small></th><td>{observationPeriod(experiment)}</td><td>{date(experiment.data_cutoff)}</td><td>{runLabels[experiment.run_status] ?? experiment.run_status} · {date(experiment.run_at)}</td><td>{reviewLabels[experiment.review_status] ?? experiment.review_status} · {date(experiment.reviewed_at)}</td></tr>)}{!linked.length && <tr><td colSpan={5}>本版本暂无关联实验；生成日期不能代替实验与复核日期。</td></tr>}</tbody></table></div></section>
      <Notes title="定义限制" values={item.limitations} /><Notes title="后续工作" values={item.next_steps} />
      <details className="fr-sources-fold"><summary>来源与文件指纹</summary><SourceList sources={item.sources} />{guide && <p className="fr-guidance-sources">阅读说明依据：{guide.source_refs.join("、")}</p>}<p className="fr-guidance-sources">评价框架依据：{assessment.source_refs.join("、")}。{assessment.note}</p><p className="fr-guidance-sources">指标检查说明：{metricGuide.note} 依据：{metricGuide.source_refs?.join("、") || "未记录"}</p></details>
    </div>}
  </article>;
}

function ProjectDetail({ project }: { project: Project }) {
  return <article className="fr-detail"><div className="fr-meta-line"><span>研究项目</span><StatusBadge tone={project.stage === "in_progress" || project.stage === "insufficient" ? "attention" : "quiet"}>{statusText(project.stage, projectStageLabels)}</StatusBadge><StatusBadge tone={reviewTone(project.review_status)}>{reviewLabels[project.review_status] ?? project.review_status}</StatusBadge></div><h2>{project.title}</h2><p className="fr-lead">{project.summary}</p><p className="fr-dim">证据日期 {date(project.evidence_date)}。这项计划不计入正式研究对象或已运行实验；尚无可据此判断的历史效果。</p><Notes title="限制" values={project.limitations} /><Notes title="下一步" values={project.next_steps} /><details className="fr-sources-fold"><summary>来源与文件指纹</summary><SourceList sources={project.sources} /></details></article>;
}


function CatalogCard({ group, guides, experiments, onOpen, onOpenExperiment, compact = false }: {
  group: ReturnType<typeof groupCatalog>[number]; guides: GuideLookup; experiments: Experiment[];
  onOpen: () => void; onOpenExperiment: (id: string) => void; compact?: boolean;
}) {
  const { item, versions } = group;
  const guide = guides.get(item.reference);
  const linked = linkedExperiments(item, experiments);
  const study = linked.find(experiment => experiment.run_status === "completed");
  const outcome = factorOutcome(item);
  const purpose = guide?.watch || purposeText(item.purpose);
  if (compact) return <article className="fr-object-row" data-category={categoryTone(item.category)}>
    <div className="fr-row-identity"><span className="fr-mobile-label">观察什么</span><span className="fr-category-tag" data-category={categoryTone(item.category)}>{item.category}</span><h3>{displayFactorName(item, guides)}</h3><p>{purpose}</p><small>v{item.version}{versions.length > 1 ? ` · 共${versions.length}版` : ""}</small></div>
    <div className="fr-row-outcome" data-tone={outcome.tone}><span className="fr-mobile-label">已记录结论</span><strong>{outcome.headline}</strong></div>
    <div className="fr-row-scope"><span className="fr-mobile-label">证据范围</span>{linked.length > 1 ? <><span>{linked.length}项实验，分别记录范围</span><small>打开后逐项看结论、日期和限制</small></> : study ? <><span>{study.products.length ? `${study.products.length} 个产品` : "产品未记录"}</span><small>{observationPeriod(study)} · {reviewLabels[study.review_status] ?? study.review_status}</small></> : <span>本页未接入该版本实验</span>}</div>
    <button type="button" className="fr-main-action fr-row-open" onClick={onOpen}>{catalogAction(item, experiments)}</button>
  </article>;
  return <article className="fr-object-card" data-category={categoryTone(item.category)}>
    <div className="fr-card-top"><span className="fr-category-tag" data-category={categoryTone(item.category)}><span className="fr-category-mark" aria-hidden="true" />{item.category}</span><span className="fr-card-assets">v{item.version}{versions.length > 1 ? ` · 共${versions.length}版` : ""}</span></div>
    <h3>{displayFactorName(item, guides)}</h3>
    <p className="fr-grid-purpose">{purpose}</p><div className="fr-grid-outcome" data-tone={outcome.tone}><strong>{outcome.headline}</strong></div>
    <div className="fr-grid-scope">{linked.length > 1 ? <><span>{linked.length}项实验，分别记录范围</span><small>打开后逐项看结论、日期和限制</small></> : study ? <><span>{study.products.length ? `${study.products.length} 个产品` : "产品未记录"}</span><small>{observationPeriod(study)} · {reviewLabels[study.review_status] ?? study.review_status}</small></> : <span>本页未接入该版本实验</span>}</div>
    <div className="fr-card-actions"><button type="button" className="fr-main-action" onClick={onOpen}>{catalogAction(item, experiments)}</button>{linked.length === 1 && <button type="button" className="fr-text-action" onClick={() => onOpenExperiment(linked[0].id)}>看原实验</button>}</div>
  </article>;
}

export default function FactorResearchPage({ legacy }: { legacy: ReactNode }) {
  const [snapshot, setSnapshot] = useState<Snapshot | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);
  const [params, setParams] = useSearchParams();
  const tab = factorView(params);
  const factor = params.get("factor");
  const section = dossierSection(params.get("section"));
  const experiment = params.get("experiment");
  const project = params.get("project");
  const filters: Filters = { query: params.get("q") ?? "", asset: params.get("asset") ?? "", category: params.get("category") ?? "", stage: params.get("stage") ?? "", result: params.get("result") ?? "" };
  const sort: CatalogSort = params.get("sort") === "date" || params.get("sort") === "name" ? params.get("sort") as CatalogSort : "evidence";
  const view = params.get("view") === "grid" ? "grid" : "list";
  const requestedPage = Number(params.get("page") || "1");
  const update = (changes: Record<string, string | null>) => setParams(nextSearchParams(params, changes));
  const changeFilter = (changes: Record<string, string | null>) => update({ ...changes, factor: null, section: null, page: null });
  const scrollTop = () => window.scrollTo({ top: 0, behavior: "auto" });
  const openFactor = (reference: string) => { update({ tab: "catalog", factor: reference, section: null, experiment: null, project: null }); scrollTop(); };
  const changeSection = (next: DossierSection) => { update({ section: next === "overview" ? null : next }); scrollTop(); };
  const openExperiment = (id: string) => { update({ tab: "experiments", factor: null, section: null, experiment: id, project: null }); scrollTop(); };
  const openProject = (id: string) => { update({ tab: "experiments", factor: null, section: null, experiment: null, project: id }); scrollTop(); };
  const openCategory = (category: string) => { update({ tab: "catalog", category, q: null, asset: null, stage: null, result: null, page: null, factor: null, section: null, experiment: null, project: null }); scrollTop(); };

  useEffect(() => {
    let active = true;
    fetch(new URL("./catalog.generated.json", import.meta.url)).then(async response => {
      if (!response.ok) throw new Error(`HTTP ${response.status}`);
      return response.json() as Promise<Snapshot>;
    }).then(data => {
      if (!active) return;
      if (data.schema_version !== "factor-research/1" || !Array.isArray(data.items) || !Array.isArray(data.experiments) || !Array.isArray(data.projects)) throw new Error("快照格式与当前页面不兼容");
      setSnapshot(data);
    }).catch((error: unknown) => active && setLoadError(error instanceof Error ? error.message : String(error)));
    return () => { active = false; };
  }, []);

  const allVersions = snapshot?.items ?? [];
  const groups = sortCatalog(groupCatalog(allVersions, filters, reading.guides), sort, reading.guides);
  const pageData = paginateCatalog(groups, requestedPage);
  const categoryCounts = categoryObjectCounts(allVersions);
  const selectedFactor = allVersions.find(item => item.reference === factor);
  const selectedVersions = factor ? groupCatalog(allVersions, emptyFilters).find(group => group.id === selectedFactor?.id)?.versions ?? [] : [];
  const selectedExperiment = snapshot?.experiments.find(e => e.id === experiment);
  const selectedProject = snapshot?.projects.find(p => p.id === project);
  const assets = [...new Set(allVersions.flatMap(item => item.asset_classes))].sort();
  const hasStrategyComparison = snapshot?.experiments.some(e => e.kind === "strategy_backtest" || e.kind === "portfolio_comparison") ?? false;

  return <main className="factor-research fr-redesign">
    <header className="fr-header"><div><h1>因子研究</h1><p>先看已接入资料回答的问题、研究范围和缺口，再查精确版本与原始报告。</p><p className="fr-header-scope">本页材料整理于 {snapshot ? formatGeneratedAt(snapshot.generated_at) : "读取中"}，只覆盖已接入材料；未接入不等于未研究。生成日期、实验观察期和数据截止日各有不同含义。</p></div>{snapshot && <p className="fr-header-counts">已接入 {snapshot.counts.factor_objects} 个对象 · {snapshot.counts.definition_versions} 个定义版本 · {snapshot.counts.executed_experiments} 项已运行实验</p>}</header>
    <nav className="fr-tabs" aria-label="因子研究视图">{Object.entries(TAB_LABELS).map(([key, label]) => <button type="button" key={key} className={tab === key ? "active" : ""} aria-current={tab === key ? "page" : undefined} onClick={() => { update({ tab: key, factor: null, section: null, experiment: null, project: null }); scrollTop(); }}>{label}</button>)}</nav>
    {tab === "legacy" ? <><div className="fr-legacy-banner"><strong>旧行情快照</strong><span>下方沿用原接口的标的读数与历史评级；这些评级不代表新研究目录的结论。</span></div>{legacy}</> : loadError ? <div className="fr-load-state" role="alert"><h2>研究快照暂时不可用</h2><p>{loadError}</p><p>需重新生成并核对来源文件；页面不会显示演示数据。</p></div> : !snapshot ? <div className="fr-load-state" role="status">正在载入研究材料…</div> : tab === "overview" ? <FactorResearchOverview snapshot={snapshot} onCategory={openCategory} onExperiment={openExperiment} onCatalog={() => { update({ tab: "catalog", factor: null, experiment: null, project: null }); scrollTop(); }} /> : tab === "catalog" ? factor ? <div className="fr-full-detail">
      <button type="button" className="fr-back" onClick={() => { update({ factor: null, section: null }); scrollTop(); }}>← 返回因子库</button>
      {selectedFactor ? <FactorDetail item={selectedFactor} versions={selectedVersions} guides={reading.guides} experiments={snapshot.experiments} section={section} onSectionChange={changeSection} onOpenExperiment={openExperiment} onVersionChange={openFactor} /> : <div className="fr-empty" role="alert"><h2>没有找到这个精确版本</h2><code>{factor}</code><p>不会自动改选其他版本。请返回目录重新选择。</p></div>}
    </div> : <>
      <section className="fr-catalog-tools" aria-label="查找研究对象">
        <div className="fr-category-pills" aria-label="用途类别"><button type="button" className={!filters.category ? "active" : ""} aria-pressed={!filters.category} onClick={() => changeFilter({ category: null })}>全部 <span>{snapshot.counts.factor_objects}</span></button>{Object.entries(categoryCounts).sort((a, b) => a[0].localeCompare(b[0], "zh-CN")).map(([category, count]) => <button type="button" key={category} className={filters.category === category ? "active" : ""} aria-pressed={filters.category === category} onClick={() => changeFilter({ category })}>{category} <span>{count}</span></button>)}</div>
        <div className="fr-search-row"><label htmlFor="fr-search">搜索名称、阅读说明或精确版本</label><input id="fr-search" type="search" value={filters.query} onChange={e => changeFilter({ q: e.target.value })} placeholder="搜索名称、关注点或 id@版本" /></div>
        <div className="fr-outcome-shortcuts" aria-label="快速查看研究结论">{[["", "全部阶段"], ["historical", "有历史结果"], ["calculation_only", "仅验证计算"], ["unbound", "结论待补"]].map(([value, label]) => <button type="button" key={label} className={filters.stage === value ? "active" : ""} aria-pressed={filters.stage === value} onClick={() => changeFilter({ stage: value || null })}>{label}</button>)}</div>
        <div className="fr-control-row"><details className="fr-more-filters"><summary>更多筛选{filters.asset || filters.stage || filters.result ? "（已选）" : ""}</summary><div className="fr-filter-grid"><label>资产类别<select value={filters.asset} onChange={e => changeFilter({ asset: e.target.value })}><option value="">全部</option>{assets.map(asset => <option key={asset} value={asset}>{asset}</option>)}</select></label><label>证据阶段<select value={filters.stage} onChange={e => changeFilter({ stage: e.target.value })}><option value="">全部</option>{Object.entries(stageLabels).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label><label>研究结果<select value={filters.result} onChange={e => changeFilter({ result: e.target.value })}><option value="">全部</option>{Object.entries(resultLabels).map(([key, value]) => <option key={key} value={key}>{value}</option>)}</select></label></div></details>
          <span className="fr-result-count">找到 {pageData.total} 个对象，涉及 {groups.reduce((count, group) => count + group.matchingVersions.length, 0)} 个匹配版本</span>
          <label className="fr-sort">排序<select value={sort} onChange={e => update({ sort: e.target.value, page: null })}><option value="evidence">已有历史证据优先</option><option value="date">证据日期</option><option value="name">名称</option></select></label>
          <div className="fr-view-buttons" aria-label="显示方式"><button type="button" aria-pressed={view === "grid"} className={view === "grid" ? "active" : ""} onClick={() => update({ view: "grid" })}>卡片</button><button type="button" aria-pressed={view === "list"} className={view === "list" ? "active" : ""} onClick={() => update({ view: "list" })}>列表</button></div>
        </div>
        {filters.category === "宽度" && <p className="fr-category-explain">宽度：一批股票中，有多少站在各自均线上方。具体分母和均线周期以所选定义版本为准。</p>}
        {(filters.query || filters.asset || filters.category || filters.stage || filters.result) && <button type="button" className="fr-clear" onClick={() => changeFilter({ q: null, asset: null, category: null, stage: null, result: null })}>清除全部筛选</button>}
      </section>
      {groups.length ? <>{view === "list" && <div className="fr-list-columns" aria-hidden="true"><span>观察什么</span><span>已记录结论</span><span>证据范围</span><span>详情</span></div>}<section className={`fr-object-grid${view === "list" ? " is-list" : ""}`} aria-label="因子库对象">{pageData.rows.map(group => <CatalogCard key={group.id} group={group} guides={reading.guides} experiments={snapshot.experiments} compact={view === "list"} onOpen={() => openFactor(group.item.reference)} onOpenExperiment={openExperiment} />)}</section><nav className="fr-pagination" aria-label="目录分页"><button type="button" disabled={pageData.page <= 1} onClick={() => { update({ page: String(pageData.page - 1) }); scrollTop(); }}>上一页</button><span>第 {pageData.page} / {pageData.pages} 页</span><button type="button" disabled={pageData.page >= pageData.pages} onClick={() => { update({ page: String(pageData.page + 1) }); scrollTop(); }}>下一页</button></nav></> : <div className="fr-catalog-empty"><h2>没有符合条件的对象</h2><p>调整搜索或筛选条件后再看。</p><button type="button" onClick={() => changeFilter({ q: null, asset: null, category: null, stage: null, result: null })}>清除筛选</button></div>}
      {snapshot.projects.length > 0 && <section className="fr-project-strip"><div><h2>材料快照中的研究项目</h2><p>这些项目与正式定义、已运行实验分别记录；状态来自本次材料快照。</p></div><div className="fr-project-links">{snapshot.projects.map(item => <button type="button" key={item.id} onClick={() => openProject(item.id)}><strong>{item.title}</strong><span>{statusText(item.stage, projectStageLabels)} · 证据日期 {date(item.evidence_date)} · {item.summary}</span></button>)}</div></section>}
      <details className="fr-material-scope"><summary>材料范围与生成时间</summary><p>{reading.note}{reading.error && ` ${reading.error}`}</p><p>{metricGuide.note} 指标说明依据：{metricGuide.source_refs?.join("、") || "未记录"}。</p><p>生成于 {formatGeneratedAt(snapshot.generated_at)}；正式登记版本 {snapshot.registry_version}。生成时间不是实验日期或数据截止日。</p><p>目录计数只含已接入的数值描述、状态条件、风险指标与收益序列，不含策略或基准。</p><Notes title="材料限制" values={snapshot.limitations} /><SourceList sources={snapshot.sources} /></details>
    </> : experiment || project ? <div className="fr-full-detail"><button type="button" className="fr-back" onClick={() => { update({ experiment: null, project: null }); scrollTop(); }}>← 返回实验与项目</button>{selectedExperiment ? <ExperimentDetail experiment={selectedExperiment} /> : selectedProject ? <ProjectDetail project={selectedProject} /> : <div className="fr-empty" role="alert"><h2>未找到这条研究记录</h2><p>请返回列表选择。</p></div>}</div> : <div className="fr-experiment-catalog"><div className="fr-section-heading"><h2>已接入的实验</h2><p>复核进度与研究结果分开显示。{!hasStrategyComparison && "当前尚无相应的含成本策略回测或组合对照。"}</p></div><div className="fr-experiment-grid">{snapshot.experiments.length ? snapshot.experiments.map(item => <article className="fr-experiment-card" key={item.id}><div className="fr-meta-line"><span>{kindLabels[item.kind] ?? item.kind}</span><span>{runLabels[item.run_status] ?? item.run_status}</span><StatusBadge tone={reviewTone(item.review_status)}>{reviewLabels[item.review_status] ?? item.review_status}</StatusBadge></div><h3>{item.title}</h3><p>{item.conclusion}</p><small>观察期 {date(item.period.start)} 至 {date(item.period.end)}</small><button type="button" className="fr-main-action" onClick={() => openExperiment(item.id)}>查看实验详情</button></article>) : <div className="fr-empty">尚无已接入实验。</div>}</div><div className="fr-section-heading fr-project-heading"><h2>研究项目</h2><p>项目计划不计入已运行实验。</p></div><div className="fr-experiment-grid">{snapshot.projects.map(item => <article className="fr-experiment-card" key={item.id}><div className="fr-meta-line"><span>研究项目</span><StatusBadge tone={item.stage === "in_progress" || item.stage === "insufficient" ? "attention" : "quiet"}>{statusText(item.stage, projectStageLabels)}</StatusBadge></div><h3>{item.title}</h3><p>{item.summary}</p><small>证据日期 {date(item.evidence_date)}</small><button type="button" className="fr-main-action" onClick={() => openProject(item.id)}>查看项目详情</button></article>)}</div></div>}
  </main>;
}
