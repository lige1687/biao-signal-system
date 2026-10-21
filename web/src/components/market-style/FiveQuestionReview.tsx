import type { ComponentProps } from "react";
import type ObservationConditions from "./ObservationConditions";
import type { PortfolioReview } from "./PortfolioRiskReview";
import "./five-question-review.css";

export type ReviewQuestion = {
  id: string; title: string; fact: string; reading: string; watch: string;
  short_answer: string; coverage: string; source_ids: string[]; data_date: string | null;
};
type Conditions = ComponentProps<typeof ObservationConditions>;
export type MarketReview = {
  asof: string; market: string; completion: string; questions: ReviewQuestion[];
  style_daily_date?: string | null;
  portfolio: PortfolioReview;
  volatility: NonNullable<Conditions["volatility"]>;
  nfci: NonNullable<Conditions["nfci"]>;
  sources: { id: string; name: string; url: string }[];
  missing: string[];
};

export default function FiveQuestionReview({ data, loading, error }: {
  data?: MarketReview; loading: boolean; error: boolean;
}) {
  return <section className="mq-review" aria-label="五问当前答案">
    <header><h2>五问当前答案</h2>
      <p>{data?.style_daily_date ? `收益与相对表现：近1年日线至${data.style_daily_date}；行业与估值：2026-09-30。` : "全球风格月末资料：2026-09-30。"}第五问：{data?.market === "us" ? "美股" : "A股"}策略记录。每行展开看证据。</p>
    </header>
    {loading && <p role="status">正在核对五问的已有资料…</p>}
    {error && <p role="alert" className="ms-error">五问资料读取失败，暂不能显示最新核对结果。</p>}
    {data && <div className="mq-questions">{data.questions.map((question, i) =>
      <details key={question.id}>
        <summary><span className="mq-number">{i + 1}</span><span className="mq-question-copy">
          <strong>{question.title}</strong><span>{question.short_answer}</span>
        </span><span className="mq-coverage">{question.coverage}</span></summary>
        <div className="mq-answer">
          <p><b>证据</b>{question.fact}</p>
          <p><b>怎么理解</b>{question.reading}</p>
          <p className="mq-gap"><b>{question.id === "q2" ? "适用边界" : "仍未回答"}</b>{question.watch}</p>
          <div className="mq-sources">{data.sources.filter(s => question.source_ids.includes(s.id)).map(source =>
            <a key={source.id} href={source.url} target="_blank" rel="noreferrer">{source.name} ↗</a>)}</div>
        </div>
      </details>
    )}</div>}
    <p className="mq-boundary">五问整体尚未全部答完。收益贡献、历史估值位置与实际资金持仓风险有核心资料缺口；下方曲线和已核数字不替代这些答案。</p>
  </section>;
}
