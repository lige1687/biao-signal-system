import type { CurveDataset, CurveSelection } from "../factor-research/factorCurvesModel";
import { metric, pct, type ICRecord } from "./metrics";
import "./metric-reference.css";
import traceability from "./traceability.json";

interface ResearchIdentityProps {
  dataset: CurveDataset;
  selection: CurveSelection;
  record?: ICRecord;
}

export function ResearchIdentity({ dataset, selection, record }: ResearchIdentityProps) {
  const factor = dataset.factors.find(item => item.id === selection.curveFactor);
  const pool = dataset.pools.find(item => item.id === selection.pool);
  const definition = dataset.id === traceability.datasetId ? traceability.factors.find(item => item.factorId === selection.curveFactor)?.reference : undefined;
  const ic = record && record.datasetId === dataset.id && record.factorId === selection.curveFactor
    && record.poolId === selection.pool && record.periodId === selection.period ? record : undefined;
  const interval = ic?.uncertainty && typeof ic.uncertainty === "object" ? ic.uncertainty : undefined;
  const hasInterval = interval && interval.lower != null && interval.upper != null;

  return <section className="fw-research-identity fw-block" aria-labelledby="fw-research-identity-title">
    <div className="fw-block-head"><h3 id="fw-research-identity-title">这组数字研究的是谁</h3><span>身份来自当前研究目录和所选指标记录</span></div>
    <dl className="fw-identity-grid">
      <div><dt>市场与研究样本</dt><dd><strong>{dataset.market}</strong><span>{dataset.universeLabel || "样本说明未接入"}</span></dd></div>
      <div><dt>当前候选池</dt><dd>{pool?.label || "候选池未接入"}</dd></div>
      <div><dt>所选因子与公式</dt><dd><strong>{factor?.name || "因子未接入"}</strong><span>{factor?.formula || "公式未接入"}</span></dd></div>
      <div><dt>未来结果期限</dt><dd>{ic?.horizon || "未评价"}</dd></div>
      <div><dt>有效观察</dt><dd>{ic ? `${ic.range[0]} 至 ${ic.range[1]} · ${ic.nPeriods} 个月度观察期 · 覆盖 ${pct(ic.coverage, 1)}` : "当前选择未评价"}</dd></div>
      <div><dt>平均 Rank IC 与均值区间</dt><dd>{ic ? <>{metric(ic.mean)}<span>{hasInterval ? `${metric(interval.lower)} 至 ${metric(interval.upper)}（均值的历史区间）` : "均值区间未提供"}</span></> : "未评价"}</dd></div>
    </dl>
    <p className="fw-identity-note">公式中的 20 日等窗口指观察日前的回看；未来结果按“{ic?.horizon || "未评价"}”另行定义。这里的均值区间只对应 Rank IC 均值，不是 ICIR 的区间。</p>
    <details className="fw-identity-detail"><summary>查看未来结果定义与区间方法</summary>
      <p>研究批次：{dataset.name}（{dataset.id}）；候选池：{selection.pool}；定义：{definition || "当前批次未接入版本绑定"}。</p>
      <p>未来结果标签：{ic?.labelDefinition || "当前选择未评价"}</p>
      <p>均值区间方法：{interval?.method || "未提供"}。按月形成的后续持有月标签，不能读成每天重复预测未来 20 日。</p>
    </details>
  </section>;
}

export function MetricReference() {
  return <section className="fw-metric-reference fw-block" aria-labelledby="fw-metric-reference-title">
    <div className="fw-block-head"><h3 id="fw-metric-reference-title">Rank IC / ICIR 怎么读</h3><span>数值是读数参考，不能套用通用及格线</span></div>
    <p className="fw-reference-lead">Rank IC 使用 Spearman 排名相关，比较每期股票因子排序与后续结果排序；ICIR 看逐期 Rank IC 均值相对其波动的大小。本页 ICIR 用逐月样本标准差、不年化，并保留正负号。</p>
    <div className="fw-reference-scroll" role="region" aria-label="Rank IC 与 ICIR 数值参考" tabIndex={0}>
      <table><thead><tr><th scope="col">指标</th><th scope="col">数值参考</th><th scope="col">含义</th></tr></thead><tbody>
        <tr><th scope="row">平均 Rank IC</th><td>0；约 +0.05 / −0.05</td><td>0 表示平均没有单调排序方向；±0.05 仅示例弱的同向／反向排序相关，不是 5% 收益或胜率。</td></tr>
        <tr><th scope="row">ICIR（不年化）</th><td>+0.5 / +1；负值保留</td><td>0.5 或 1 只表示均值分别是逐期标准差的 0.5 或 1 倍，不是合格线；负值也不能自动翻成有效反转策略。</td></tr>
        <tr><th scope="row">账户 IR（年化）</th><td>另看账户记录</td><td>衡量账户超额收益相对其波动的稳定性，与这里的股票排序 ICIR 是不同指标。</td></tr>
      </tbody></table>
    </div>
    <details className="fw-reference-detail"><summary>判断证据与方法出处</summary>
      <p>先比同池、同期限的简单对手，再看 Rank IC 均值区间是否跨 0、跨年份是否稳定，以及未参与调规则的新资料和交易成本。区间未跨 0 也不能单独证明可交易或有效；ICIR 数值不是均值区间。</p>
      <p>本页按月形成、后续一个持有月的标签，不是每天生成未来 20 日的重叠标签。其他研究若使用重叠标签，区间需处理时间依赖。</p>
      <p>方法与警示：<a href="https://github.com/quantopian/alphalens/blob/master/alphalens/performance.py" target="_blank" rel="noopener noreferrer">Alphalens performance.py（IC 计算）</a>、<a href="https://github.com/quantopian/alphalens/blob/master/alphalens/plotting.py" target="_blank" rel="noopener noreferrer">Alphalens plotting.py（IC 展示）</a>、<a href="https://academic.oup.com/rfs/article-abstract/29/1/5/1843824" target="_blank" rel="noopener noreferrer">Harvey 等：反复检验需更强证据</a>。这些来源不提供本页统一及格线，论文中的 t 值门槛也不能直接移植到本页。</p>
    </details>
  </section>;
}
