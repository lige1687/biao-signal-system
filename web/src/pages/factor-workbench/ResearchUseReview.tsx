import { useQuery } from "@tanstack/react-query";
import { sourceHref } from "./metrics";

const REPORT = "docs/experiments/existing-factor-strategy-expansion-2026-10-24.md";
const REPORT_SHA256 = "b5451fe30295ab1d7b3a67922eb686d86056baddfc4ff024f3657e1c6355a819";

// These are excerpts of one frozen comparison, independent of the page filters.
// Fail closed when its source changes, instead of retaining unbound numbers.
export async function verifyCombinationEvidence(signal?: AbortSignal): Promise<true> {
  const response = await fetch(`/api/experiments/${REPORT}`, { signal, cache: "no-cache" });
  if (!response.ok) throw new Error(`原报告暂不可读（HTTP ${response.status}），比较数值暂不展示。`);
  const data: unknown = await response.json();
  if (!data || typeof data !== "object" || !("name" in data) || data.name !== REPORT || !("markdown" in data) || typeof data.markdown !== "string") {
    throw new Error("返回内容不是这项研究的原报告，比较数值暂不展示。");
  }
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(data.markdown));
  const actual = Array.from(new Uint8Array(digest), n => n.toString(16).padStart(2, "0")).join("");
  if (actual !== REPORT_SHA256) throw new Error("原报告已变化，需重新核对摘录；比较数值暂不展示。");
  return true;
}

export default function ResearchUseReview() {
  const evidence = useQuery({ queryKey: ["price-operating-evidence", REPORT_SHA256], queryFn: ({ signal }) => verifyCombinationEvidence(signal), staleTime: 0 });
  return <section className="fw-block" aria-labelledby="research-use-title">
    <div className="fw-block-head"><h3 id="research-use-title">价格与经营信息一起看，实际多了什么？</h3><span>独立比较 · 2026-10-24 已见历史 · 不随上方筛选改变</span></div>
    <p>先看关键结果，再决定是否值得开发策略。这里是股票组合的研究，不限定于 ETF；估值观察与经营指标也分别保留各自含义。</p>
    {evidence.isLoading || evidence.isFetching ? <p role="status">正在核对原报告…</p> : evidence.error ? <p className="fw-alert" role="alert">{evidence.error instanceof Error ? evidence.error.message : "原报告核对失败，比较数值暂不展示。"} <button type="button" onClick={() => void evidence.refetch()}>重试</button></p> : evidence.data && <>
      <p><strong>A 股：动量＋毛利润＋经营现金流。</strong>固定 2014 年抽样框架的财务共同池累计 562 只股票，2015—2025 年的 127 个报价完整月份；不代表历史全 A 股。</p>
      <div className="fw-table-wrap"><table><caption>A 股历史表现与强简单对照；未扣个人交易费用</caption><thead><tr><th scope="col">办法</th><th scope="col">月平均报价收益</th><th scope="col">最差单月</th></tr></thead><tbody>
        <tr><th scope="row">只看动量</th><td>1.200%</td><td>−21.10%</td></tr>
        <tr><th scope="row">两套旧方法各用一半资金</th><td>1.293%</td><td>−20.41%</td></tr>
        <tr><th scope="row">三项一起评分选股</th><td>1.343%</td><td>−21.41%</td></tr>
      </tbody></table></div>
      <p className="fw-uncertainty">新评分比单动量多 0.142 个百分点/月；比两套旧方法简单混合仅多 0.049 个百分点/月，历史描述范围为 −0.035 至 +0.181 个百分点，跨过零。最差月反而多亏约 1 个百分点。</p>
      <p className="fw-note">简单混合指“动量＋毛利润”和“动量＋经营现金流”各一半；最差单月不等于账户最大回撤。2021—2025 年，新评分还落后于低波动对照，不能据此称为防守策略。</p>
      <p><strong>美股反例：</strong>2015—2024 年大盘盈利低扩张组与动量各用一半资金，年化 15.26%；比原盈利＋动量高 1.56 个百分点，但比盈利低扩张单项低 2.00 个百分点。来源为 French 动态股票分组，不是标普500，也未扣个人费用。</p>
      <p><strong>目前的判断：</strong>保留互补线索，尚未证明增加复杂度值得采用。母指数净优势、连续可执行账户及未看过的新数据效果均未评价。</p>
    </>}
    <div className="fw-actions" style={{ flexWrap: "wrap" }}><a href={sourceHref(REPORT)!}>查看完整性能、增量与反例</a><a href="/fundamentals?observation=hs300-pe#fund-sec-market">沪深300价格与PE</a><a href="/fundamentals?observation=sp500-cape#fund-sec-market">标普500价格与CAPE</a></div>
    <details className="fw-limits"><summary>这项比较能怎样用于后续研究</summary><p>观察层：同一指数价格和估值一起读，保留日期与频率。研究层：比较经营信息加入价格规则后的新增持股、放弃机会和费用。交易层：仍需完整规则与合格账户输入；本页不把财务指标加进现有 LEI 技术判定。</p><p>原报告 SHA-256：<code>{REPORT_SHA256}</code>。页面每次读取都核对原文；这一核对只保证摘录对应资料，不证明策略有效。</p></details>
  </section>;
}
