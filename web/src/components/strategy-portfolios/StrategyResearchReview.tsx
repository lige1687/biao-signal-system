import "./strategyResearchReview.css";

type Candidate = {
  title: string;
  scope: string;
  lead: string;
  why: string;
  difference: string;
  opponent: string;
  costAndStop: string;
  data: string;
  source: { label: string; href: string };
};

const candidates: Candidate[] = [
  {
    title: "行业相对反转",
    scope: "A 股与美股分别研究 · 尚无本地收益",
    lead: "寻找相对同行异常下跌的股票，区分整行业走弱、公告消息与暂时的买卖压力。",
    why: "短期流动性压力可能使价格暂时偏离；低换手股票的反转可能持续更久。月度观察有文献理由，不能把本轮“近期偏冷＋低波动”的负结果直接说成反转逻辑错误。",
    difference: "现有方案按股票自身最近一月涨幅排序，还共同加入低波动。新问题要先区分同行共同下跌、公司公告和个股相对下跌，再在两市场分别评价。",
    opponent: "同范围原始反转、低波动、中期上涨，以及对应市场指数持有；逐项看收益、跌幅、错过的上涨与费用。行业处理和公告处理分别检验，不能一次混进去。",
    costAndStop: "周度可能增加交易与维护，先以月度作低频主用途。若扣费后的改善不稳、主要来自难交易股票，或错过大行情的代价过高，就不进入账户。",
    data: "尚缺可按历史日期使用的行业归属、首次公告时间与当时交易资格。本地尚未做此候选的完整账户检验，也没有可展示的收益。原论文的多空收益不能移植为个人只买入账户的收益。",
    source: { label: "Dai 等（2023）研究原文", href: "https://mysimon.rochester.edu/novy-marx/research/RRLP.pdf" },
  },
  {
    title: "价值与中期上涨分开组合",
    scope: "两种信息分别建账户 · 未进入前向",
    lead: "价格相对经营价值偏低，与价格上涨后信息逐步被市场消化，可能来自不同的金融原因。",
    why: "把来源不同的选择方法分别评估，再研究固定资金配比，才看得清每种方法帮了什么、组合是否减少共同下跌。",
    difference: "现有两套方案都含低波动，主要仍由价格加工信息决定。这个方向先让价值和中期上涨各自成为完整方法，不直接把未经核准的质量字段塞进同一分数。",
    opponent: "只用价值、只用中期上涨、固定平均分配与现有两套账户；比较同一合格股票和资金规则下的收益、风险、费用及共同下跌。",
    costAndStop: "价值可能多年落后，独立观察会占用资金和维护精力。若资料覆盖窄、价格与账面口径不可靠，或组合没有扣费后的实际增量，就停止资金用途。",
    data: "两市场历史逐股价值字段的披露日期、修订和可比性尚不合格。已有美股经营盈利研究覆盖有限且未证明相对动量的稳定增量，保留负结果；本候选没有本地账户成绩，也未进入前向。",
    source: { label: "AQR（2013）《Value and Momentum Everywhere》", href: "https://www.aqr.com/insights/research/journal-article/value-and-momentum-everywhere" },
  },
  {
    title: "公告后信息消化",
    scope: "复用现有盈利资料负责人 · 尚无本地效力",
    lead: "经营变化公告后，市场可能需要时间才能把新信息反映到价格中。",
    why: "公告带来的价格变化不应被当作纯粹的短期反转；先分清信息驱动和流动性驱动，才能判断是否有另一个可用来源。",
    difference: "现有组合只用价格序列选股，没有按当时已知的公告内容和首次披露时间单独提出问题。",
    opponent: "相同公告日期、行业和相近中期涨幅的股票，以及简单动量账户。与去年同季相比好转不等于超出市场预期，必须先固定一种准确含义。",
    costAndStop: "申报解析、公告时点核对和季度口径维护都要花成本。若无法确认当时何时可知，或新增信息不能改善实际决定，就不建前向账户。",
    data: "首次公告时间、同口径季度资料和历史成员还没齐。复用已有经营盈利研究及其负责人，不重复采集；目前没有本地策略收益或前向记录。",
    source: { label: "Dai 等（2023）§2.1 原型", href: "https://mysimon.rochester.edu/novy-marx/research/RRLP.pdf" },
  },
];

export default function StrategyResearchReview() {
  return <div className="srr-root">
    <header className="srr-head">
      <span className="srr-eyebrow">2026-10-20 · 证据审核</span>
      <h2>现有两套方案未达到资金采用条件</h2>
      <p>历史结果显示两方案经常一起涨跌，主要改善也没有同时在 A 股、美股成立。下面三项是下一批待核的研究问题，均没有本地策略收益，也没有进入真实交易。</p>
    </header>

    <section className="srr-panel" aria-labelledby="srr-result-title">
      <h3 id="srr-result-title">为什么继续找不同的来源</h3>
      <div className="srr-market-grid">
        <div><strong>A 股</strong><p>两方案每日收益同向程度 <b>0.851</b>。年化收益分别 <b>5.33%</b>、<b>2.46%</b>，历史最大跌幅分别 <b>54.89%</b>、<b>52.97%</b>。</p><small>2015—2025 年；固定的历史 300 只股票。</small></div>
        <div><strong>美股</strong><p>两方案每日收益同向程度 <b>0.802</b>。年化收益分别 <b>5.49%</b>、<b>0.69%</b>，历史最大跌幅分别 <b>16.43%</b>、<b>20.22%</b>。简单低波动为 <b>7.94%</b>、<b>16.09%</b>。</p><small>2021 年 2 月—2026 年 6 月；用当前 IVV 成分回看，504 只中 502 只有历史价格，存在成分幸存偏差。</small></div>
      </div>
      <p className="srr-note">顺序为“中期上涨＋低波动”“近期偏冷＋低波动”。相关程度越接近 1，越容易一起涨跌。以上都是已看过的历史，不能当独立验证；美股范围会遗漏后来退出的股票。冻结账户的采集和记录状态仍以“已冻结方案记录”为准。</p>
      <p className="srr-note">保存成交记录显示：A 股两方案平均每月约 31、35 笔，美股约 30、37 笔。月度选股仍伴随日常退出和调整，维护负担需要单独评价。</p>
    </section>

    <section aria-labelledby="srr-candidates-title">
      <div className="srr-section-head"><h3 id="srr-candidates-title">下一批候选</h3><p>先查能否拿到当时可用的资料，再决定是否值得做账户检验。</p></div>
      <div className="srr-candidates">{candidates.map((candidate, index) => <details className="srr-card" key={candidate.title}>
        <summary><span className="srr-number">0{index + 1}</span><span className="srr-card-title"><strong>{candidate.title}</strong><small>{candidate.scope}</small><span>{candidate.lead}</span></span><span className="srr-open">查看依据与缺口</span></summary>
        <div className="srr-card-body">
          <dl>
            <div><dt>金融理由</dt><dd>{candidate.why}</dd></div>
            <div><dt>如何与现有方案不同</dt><dd>{candidate.difference}</dd></div>
            <div><dt>要打败的简单方法</dt><dd>{candidate.opponent}</dd></div>
            <div><dt>代价与失败条件</dt><dd>{candidate.costAndStop}</dd></div>
            <div><dt>本地资料状态</dt><dd>{candidate.data}</dd></div>
          </dl>
          <a href={candidate.source.href} target="_blank" rel="noreferrer">{candidate.source.label}</a>
        </div>
      </details>)}</div>
    </section>

    <section className="srr-panel srr-choices" aria-labelledby="srr-choices-title"><h3 id="srr-choices-title">需要持续权衡的两件事</h3>
      <p><strong>反转看多频繁？</strong>周度观察可能抓到较快的变化，也会增加交易和维护。个人低频用途先以月度为主，只有额外帮助足以抵消代价才考虑周度。</p>
      <p><strong>价值可能多年落后怎么办？</strong>可以先作为小比例独立观察方向评估，但比例须由证据和个人承受能力另行决定；这里不承诺配比或自动采用。</p>
    </section>

    <details className="srr-sources"><summary>查看研究记录与原始依据</summary><ul>
      <li><a href="/library?report=docs%2Fexperiments%2Fmature-strategy-review-2026-10-20.md">本次成熟策略审核</a></li>
      <li><a href="/library?report=docs%2Fexperiments%2Ffactor-strategy-portfolios-2026-10-20.md">现有两套个股策略的历史与前向边界</a></li>
      <li><a href="/library?report=docs%2Fexperiments%2Fus-op-common-history-2026-10-20.md">美股经营盈利资料与有限负结果</a></li>
      <li><a href="/library?report=docs%2Fexperiments%2Fa-share-reversal-applicability-review-2026-10-20.md">另一负责人的 A 股反转适用范围审查</a></li>
    </ul></details>
  </div>;
}
