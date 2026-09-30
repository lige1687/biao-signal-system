import type { Snapshot } from "./model";
import { catalogCounts, categoryObjectCounts, kindLabels, reviewLabels, runLabels } from "./model";
import "./factor-overview.css";

const questions: Record<string, string> = {
  趋势: "价格处在怎样的趋势中",
  回调位置: "价格离已有参照位置有多远",
  相对强弱: "哪些产品相对更强",
  风险: "波动和下跌风险怎样",
  宽度: "走强是普遍现象还是少数股票",
};

export default function FactorResearchOverview({ snapshot, onCategory, onExperiment, onCatalog }: {
  snapshot: Snapshot; onCategory: (category: string) => void; onExperiment: (id: string) => void; onCatalog: () => void;
}) {
  const counts = catalogCounts(snapshot.items, snapshot.experiments);
  const categories = categoryObjectCounts(snapshot.items);
  return <div className="fr-research-overview">
    <p className="fr-overview-lead">因子，就是把一个观察写成可计算的指标。本页先帮助你看清已接入资料回答了什么、在哪些产品和日期检查，以及还有什么缺口。</p>
    <p className="fr-overview-counts">已接入 {counts.factor_objects} 个研究对象、{counts.definition_versions} 个定义版本、{counts.executed_experiments} 项已运行实验。候选登记与正式对象分开统计。</p>
    <section aria-labelledby="fr-overview-evidence"><h2 id="fr-overview-evidence">已接入实验怎么说</h2>
      {snapshot.experiments.length ? snapshot.experiments.map(experiment => <article className="fr-overview-study" key={experiment.id}>
        <div className="fr-overview-study-head"><h3>{experiment.title}</h3><button type="button" onClick={() => onExperiment(experiment.id)}>查看实验详情</button></div>
        <p>{experiment.conclusion || "这项实验尚未记录结论。"}</p>
        <p className="fr-overview-study-meta">{kindLabels[experiment.kind] ?? experiment.kind} · {experiment.products.length ? experiment.products.map(product => product.name || product.code).join("、") : "产品未记录"} · 观察期 {experiment.period.start?.slice(0, 10) ?? "未记录"} 至 {experiment.period.end?.slice(0, 10) ?? "未记录"} · {runLabels[experiment.run_status] ?? experiment.run_status} · {reviewLabels[experiment.review_status] ?? experiment.review_status}</p>
        <p className="fr-overview-study-limit"><strong>主要限制：</strong>{experiment.limitations[0] ?? "未记录，请查看实验详情核对适用范围。"}</p>
      </article>) : <p>当前快照没有已接入实验；这里不展示演示结论。</p>}
    </section>
    <section aria-labelledby="fr-overview-questions"><h2 id="fr-overview-questions">按问题找因子</h2><div className="fr-overview-categories">{Object.entries(categories).map(([category, count]) => <button type="button" key={category} onClick={() => onCategory(category)}><strong>{category}</strong><span>{questions[category] ?? "查看定义范围"}</span><small>{count} 个对象</small></button>)}</div><button type="button" className="fr-overview-all" onClick={onCatalog}>查看完整因子目录</button></section>
    <section aria-labelledby="fr-overview-materials"><h2 id="fr-overview-materials">继续查原始资料</h2><div className="fr-overview-links"><a href="/strategy?collection=factor-guide&doc=research-guide">研究指南</a><a href="/strategy?collection=factor-guide&doc=candidate-registry">候选注册表</a><a href="/library">全部实验报告</a></div><p>候选登记不等于正式定义，定义与实验也不等于获准交易。</p></section>
  </div>;
}
