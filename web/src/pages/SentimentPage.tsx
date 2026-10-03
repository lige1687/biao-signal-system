import { useQuery } from "@tanstack/react-query";
import { fundamentalsApi, sentimentApi } from "../api/client";
import { useState } from "react";
import MarketObservationCards from "../components/MarketObservationCards";
import { etfsForSector } from "../data/sectorEtfMap";
import SentimentSectorBlock, { UsSectorBlock } from "../components/SentimentSectorBlock";
import "./reference-reading.css";
import "./sentiment.css"; // S14 页面级样式：趋势图视觉中心（禁写共享 styles.css）
import type { SentimentDashboard } from "../types";

/* ── 情绪仪表盘页：全A / 美股 / 美国调查情绪 / A股板块散户热度 ───────────
 * 设计原则（2026-09-07 可读性重做，用户反馈"看不出信息、没有重点"）：
 * 1. 结论先行——页面第一屏一句话回答"现在情绪怎样、有没有要行动的信号"；
 * 2. 每张卡顶部一个彩色状态徽章 + 一句话结论，先看颜色再看数字；
 * 3. 变量名全部大白话，每个指标跟一句"怎么看"的读法说明；
 * 4. 一切为叙事标注（research_proxy）：只描述环境与状态，不参与技术判定、
 *    不构成买卖点。阈值来源在卡片内标注（本系统回测 / 外部实证引用）。 */

const MOOD_TONE: Record<string, string> = { 热: "#d24a43", 冷: "#4d7fc4", 中: "#9aa4b2" };

/** 统一状态徽章：tone 决定颜色语义。 */
function Badge({ tone, children }: { tone: "danger" | "caution" | "opportunity" | "info" | "neutral"; children: React.ReactNode }) {
  return <span className={`macro-chip ${tone}`}>{children}</span>;
}

/** 指标行：左边白话名（带解释 tooltip），右边数值（涨红跌绿）。 */
function Row({ name, hint, value, tone, strong }: {
  name: string; hint?: string; value: React.ReactNode; tone?: "up" | "down" | ""; strong?: boolean;
}) {
  return (
    <div className={`mood-comp${strong ? " big" : ""}`}>
      <span title={hint}>{name}{hint && <span className="mood-q">?</span>}</span>
      <b className={tone ?? ""}>{value}</b>
    </div>
  );
}

/** 卡片通用头部：标题 + 状态徽章 + 一句话结论。 */
function CardHead({ title, badge, verdict, verdictColor }: {
  title: string; badge: React.ReactNode; verdict: string; verdictColor: string;
}) {
  return (
    <div className="mood-head2">
      <div className="mood-head2-top">
        <span className="sx-rail-title">{title}</span>
        {badge}
      </div>
      <div className="mood-verdict" style={{ color: verdictColor }}>{verdict}</div>
    </div>
  );
}

export default function SentimentPage() {
  const [market, setMarket] = useState<"cn" | "us">("cn");
  const { data: observations, isLoading: observationsLoading, error: observationsError } = useQuery({
    queryKey: ["fundamentalsObservations", market],
    queryFn: () => fundamentalsApi.observations(market),
    staleTime: 5 * 60_000,
  });
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["sentimentDashboard"],
    queryFn: () => sentimentApi.dashboard(),
    staleTime: 10 * 60_000,
  });

  /* 页头在加载/失败态也渲染：键值缺失显示"未知/不可用"，失败给重试（范式红线：不伪造状态） */
  const head = (d: SentimentDashboard | undefined) => (
    <div className="pg-head">
      <div className="pg-head-title">
        <h1>市场参与与情绪</h1>
        <span className="pg-head-sub">观察交易参与和调查读数；交易仍看阶段、路牌与触发条件</span>
      </div>
      <div className="pg-head-kv">
        <span className="pg-kv"><span className="k">A股快照生成于</span><b>{d?.sector_boards?.as_of ?? "未记录"}</b></span>
        <span className="pg-kv"><span className="k">美股板块日期</span><b>{d?.us_sector_boards?.as_of ?? "未记录"}</b></span>
      </div>
      <div className="pg-head-actions">
        {error && (
          <button className="btn small" onClick={() => refetch()}>重试</button>
        )}
      </div>
    </div>
  );

  const primary = <>
    <div className="observation-market-switch" role="group" aria-label="观察市场">
      <button type="button" className={market === "cn" ? "on" : ""} onClick={() => setMarket("cn")} aria-pressed={market === "cn"}>A股</button>
      <button type="button" className={market === "us" ? "on" : ""} onClick={() => setMarket("us")} aria-pressed={market === "us"}>美股</button>
    </div>
    {observationsLoading && <p className="muted">观察资料加载中…</p>}
    {observationsError && <p className="fund-errors">观察资料暂不可用：{(observationsError as Error).message}</p>}
    {(observations || (!observationsLoading && !observationsError)) &&
      <MarketObservationCards response={observations} title={`${market === "cn" ? "A股" : "美股"}核心观察`} limit={4}
        metricIds={market === "cn" ? ["margin_balance", "margin_buy", "stock_turnover"] : ["vix", "vxn", "aaii", "naaim"]} />}
    {market === "cn" && <p className="muted">A股目前没有可核对的机构调查时，不显示机构情绪读数。</p>}
    <p className="sent-sector-link">查看板块阶段、相对大盘强弱和下一观察条件：<a href="/sectors">进入行业板块页</a></p>
  </>;

  if (isLoading) return <div className="page sent-page">{head(undefined)}{primary}<p className="muted">原有板块资料加载中…</p></div>;
  if (error || !data) return <div className="page sent-page">{head(undefined)}{primary}<p className="muted">原有板块资料不可用：{(error as Error)?.message ?? "请先运行预计算"}</p></div>;

  const cn = data.cn_mood;
  const nPicks = data.action?.opportunity_cards?.length ?? 0;
  const nAlarms = data.action?.alarm_cards?.length ?? 0;
  const holdDanger = (data.action?.holding_risk ?? []).filter((h) => h.state === "danger");
  const holdWatch = (data.action?.holding_risk ?? []).filter((h) => h.state === "watch");

  return (
    <div className="page sent-page">
      {head(data)}

      {primary}

      {/* 旧面板缺少跨来源的统一可用时点，只保留背景查看。 */}
      <details className="sent-legacy"><summary>查看原有市场读数与历史研究</summary>
      <div id="sent-overall" className="reference-reading-anchor"><h2>原有市场读数</h2></div>
      <VerdictBar data={data} />

      {/* ── 板块情绪主区块（用户重点：图表化、持仓优先、推荐观察） ── */}
      <div id="sent-sectors" className="reference-reading-anchor"><h2>行业板块</h2><p>以下为所属日期的板块快照，进入行业页核对最新阶段、路牌和下一观察条件。</p><a href="/sectors">打开行业板块页</a></div>
      <details className="sent-sector-details"><summary>展开板块排行和图表</summary>
      {data.sector_boards?.available && (
        <SentimentSectorBlock
          view={data.sector_boards}
          heatAvailable={data.sector_heat.available}
          heatHint="订单规模差额排名暂不可用，恢复后显示"
        />
      )}
      {!data.sector_boards?.available && <p className="muted">板块情绪数据暂不可用；当前不展示板块结论。</p>}

      {/* ── 美股板块情绪（11 GICS 行业，对标 A股） ── */}
      {data.us_sector_boards?.available && <UsSectorBlock view={data.us_sector_boards} />}
      </details>

      {/* ── 行动区：有信号时给操作卡 + 持仓风险 ── */}
      <div id="sent-prompts" className="reference-reading-anchor"><h2>原有提示记录</h2><p>这些提示依据各自来源日期保存；资料未核实为及时前，不作为当前推荐。</p></div>
      {data.action?.available && (nPicks > 0 || nAlarms > 0 || holdDanger.length > 0) && (
        <section className="mood-action">
          {(data.action.opportunity_cards ?? []).map((c) => (
            <div key={c.code} className="mood-card action pick">
              <div className="mood-card-head">
                <b>❄ 旧冰点提示记录 · {c.name}（当前未核）</b>
                {c.holding && <span className="mood-hold-tag">持仓相关</span>}
                <span className="spacer" />
                {(etfsForSector(c.name) ?? []).slice(0, 2).map((e) => (
                  <span key={e.symbol} className="mood-etf-badge">{e.name}</span>
                ))}
              </div>
              <div className="mood-card-facts">
                <span>旧小单净流入强度 <b>{c.z?.toFixed(2) ?? "-"}</b></span>
                <span>板块内走强股票占比 <b>{c.b50?.toFixed(0) ?? "-"}%</b></span>
                <span>阶段 <b>{c.stage ?? "-"}</b></span>
              </div>
        <div className="mood-card-body">旧研究只复现四个指定区间的简化条件，未验证完整条件或交易规则。</div>
        <div className="mood-card-win"><a href="/library?report=docs%2Fexperiments%2Ficepoint-legacy-replay-2026-09-08.md">查看旧研究复核与适用限制</a></div>
            </div>
          ))}
          {(data.action.alarm_cards ?? []).map((c) => (
            <div key={c.code} className="mood-card action alarm">
              <div className="mood-card-head">
                <b>⚠ 旧偏热提示记录 · {c.name}（当前未核）</b>
                {c.holding && <span className="mood-hold-tag danger">持仓相关</span>}
                <span className="spacer" />
                {(etfsForSector(c.name) ?? []).slice(0, 2).map((e) => (
                  <span key={e.symbol} className="mood-etf-badge">{e.name}</span>
                ))}
              </div>
              <div className="mood-card-facts">
                <span>旧小单净流入强度 <b>{c.z?.toFixed(2) ?? "-"}</b></span>
                <span>板块内走强股票占比 <b>{c.b50?.toFixed(0) ?? "-"}%</b></span>
              </div>
              <div className="mood-card-body">旧研究的结果随时期改变，不能一概当作顶部警报。</div>
              <div className="mood-card-win"><a href="/library?report=docs%2Fexperiments%2Fretail-sentiment-ts-2026-09-05.md">查看历史研究和相反案例</a></div>
            </div>
          ))}
          {(holdDanger.length > 0 || holdWatch.length > 0) && (
            <div className="mood-holding">
              <div className="sx-rail-title" style={{ fontSize: 12 }}>旧持仓情绪标签（当前未核）</div>
              {holdDanger.map((h) => (
                <span key={h.code} className="mood-hold-chip danger" title={h.detail_cn}>{h.name} · 旧风险标签（当前未核）</span>
              ))}
              {holdWatch.map((h) => (
                <span key={h.code} className="mood-hold-chip watch" title={h.detail_cn}>{h.name} · 旧留意标签</span>
              ))}
              <span className="mood-hold-chip">其余 {(data.action.holding_risk ?? []).length - holdDanger.length - holdWatch.length} 个持仓未列入旧风险提示；当前状态未核实</span>
            </div>
          )}
        </section>
      )}

      <div id="sent-indicators" className="reference-reading-anchor"><h2>指标说明</h2></div>
      <div className="mood-grid">
        <CnMoodCard cn={cn} />
        <MarketStructureCard data={data} />
        <UsMoodCard data={data} />
        <UsSurveyCard data={data} />
      </div>

      {/* ── 两个经过历史验证的情绪信号：结构化卡片，激活/未激活一眼可见 ── */}
      <div id="sent-history" className="reference-reading-anchor"><h2>历史信号</h2></div>
      <SignalCards cn={cn} />

      <div className="muted mood-note" style={{ marginTop: 10 }}>{data.disclaimer_cn}</div>
      </details>
    </div>
  );
}

/* ══════════════ 第一屏结论条 ══════════════ */
function VerdictBar({ data }: { data: SentimentDashboard }) {
  const cn = data.cn_mood;
  return (
    <div className="mood-verdictbar neutral">
      <span className="mood-verdictbar-icon">○</span>
      <div>
        <div className="mood-verdictbar-main">各来源资料日期可能不同。下方保留原始读数，当前观察以顶部注明时点和质量的卡片为准。</div>
        <div className="mood-verdictbar-sub">
          原有A股投票：{cn.state ?? "未知"}；标普500宽度：{data.us_mood.breadth.ok ? `${data.us_mood.breadth.breadth_50}%（${data.us_mood.breadth.as_of ?? "日期未记录"}）` : "不可用"}
        </div>
      </div>
    </div>
  );
}

/* ══════════════ 卡1：全A情绪（三票） ══════════════ */
const CN_COMP_EXPLAIN: Record<string, { name: string; hint: string }> = {
  margin20: { name: "借钱炒股的总量变化", hint: "融资余额=投资者向券商借钱买股票的总额。20日变化为正=加杠杆（通常代表情绪热）" },
  retail_small20: { name: "板块汇总的小单净流入", hint: "近20天板块资金流汇总；板块成员可能重叠，不能当作不重叠的全A股票资金总额。" },
  equal_mom20: { name: "板块平均20天涨跌", hint: "来自板块收益平均，不等于每只股票各算一次的全A等权指数。" },
};

function CnMoodCard({ cn }: { cn: SentimentDashboard["cn_mood"] }) {
  const state = cn.state ?? "未知";
  const tone = state === "热" ? "danger" : state === "冷" ? "info" : "neutral";
  const verdict = "三个来源日期和股票范围可能不同；旧投票结果仅供追溯，不能据此认定当前冰点或交易方向。";
  const hotVotes = Object.values(cn.components ?? {}).filter((c) => c.ok && (c.vote ?? 0) > 0).length;
  const coldVotes = Object.values(cn.components ?? {}).filter((c) => c.ok && (c.vote ?? 0) < 0).length;
  const components = cn.components ?? {};
  const componentKeys = [...Object.keys(CN_COMP_EXPLAIN), ...Object.keys(components).filter(key => !(key in CN_COMP_EXPLAIN))];
  const hasValues = Object.values(components).some(c => c.ok && c.value != null);
  return (
    <section className="sx-rail-card mood-card">
      <CardHead
        title="全A情绪（旧来源投票）"
        badge={<Badge tone={tone}>{state === "热" ? "偏热" : state === "冷" ? "偏冷" : state === "中" ? "中性" : "数据不足"}</Badge>}
        verdict={verdict}
        verdictColor={MOOD_TONE[state]}
      />
      <div className="mood-comp" style={{ marginTop: 4 }}>
        <span>投票结果</span>
        <b>{hasValues ? <><span className="up">{hotVotes} 票热</span> / <span className="down">{coldVotes} 票冷</span></> : "未取得数据"}</b>
      </div>
      <p className="reference-vote-note">三个现有指标各投一票；缺失数据不作零票或正常值显示。</p>
      {componentKeys.map(k => {
        const c = components[k];
        if (!c) return <Row key={k} name={CN_COMP_EXPLAIN[k].name} hint={CN_COMP_EXPLAIN[k].hint} value={<span className="muted">未取得数据（日期未记录）</span>} />;
        const ex = CN_COMP_EXPLAIN[k] ?? { name: c.label_cn, hint: "" };
        // 金额类（亿）超过 1 万亿换算成「万亿」展示，避免一长串数字
        const fmtVal = () => {
          if (!c.ok || c.value == null) return <span className="muted">未取得数据{c.as_of ? `（${c.as_of}）` : "（日期未记录）"}</span>;
          const v = c.value;
          const shown = c.unit === "亿" && Math.abs(v) >= 10000
            ? `${v > 0 ? "+" : ""}${(v / 10000).toFixed(2)}万亿`
            : `${v > 0 ? "+" : ""}${v.toLocaleString("zh-CN")}${c.unit ?? ""}`;
          return <>{shown}{c.as_of ? <span className="muted">（{c.as_of}）</span> : null}</>;
        };
        return (
          <Row
            key={k}
            name={ex.name}
            hint={ex.hint}
            tone={(c.vote ?? 0) > 0 ? "up" : (c.vote ?? 0) < 0 ? "down" : ""}
            value={fmtVal()}
          />
        );
      })}
      <div className="muted mood-note">
        原组件采用三项投票。顶部观察卡优先显示原值、变化、来源日期与资料质量。
      </div>
    </section>
  );
}

/* ══════════════ 卡2：市场结构 ══════════════ */
function MarketStructureCard({ data }: { data: SentimentDashboard }) {
  const ms = data.market_structure;
  if (!ms?.available) {
    return (
      <section className="sx-rail-card mood-card">
        <CardHead title="A股市场结构" badge={<Badge tone="neutral">数据不可用</Badge>}
          verdict="板块结构数据暂不可用" verdictColor="#9aa4b2" />
      </section>
    );
  }
  const middle = ms.strong_pct != null && ms.weak_pct != null ? Math.max(0, 100 - ms.strong_pct - ms.weak_pct) : null;
  return (
    <section className="sx-rail-card mood-card">
      <CardHead
        title="A股市场结构"
        badge={<Badge tone="neutral">{ms.as_of ?? "日期未记录"}</Badge>}
        verdict="分别看强、居中、弱板块的占比；旧的合成分数不能说明强弱两群并存。"
        verdictColor="#4b5563"
      />
      <Row name="强势 / 居中 / 弱势板块占比" strong
        hint="板块内站上50日线的股票占比>70%算强势板块，<30%算弱势板块"
        value={[ms.strong_pct, middle, ms.weak_pct].map((v) => v == null ? "—" : `${v.toFixed(0)}%`).join(" / ")} />
      <Row name="板块强弱中位数"
        hint="所有板块「站上50日线股票占比」的中位数，代表典型板块的健康度"
        value={`${ms.median_b50?.toFixed(0)}%`} />
      <Row name="最强板块（前5）"
        hint="板块内走强股票占比最高的5个板块"
        value={(ms.strong_boards ?? []).slice(0, 5).map((b) => b.name).join("、")} />
      <Row name="最弱板块（前5）"
        hint="板块内走强股票占比最低的5个板块"
        value={(ms.weak_boards ?? []).slice(0, 5).map((b) => b.name).join("、")} />
      <div className="muted mood-note">
        这是板块价格状态的分布，不单独决定仓位。查看板块及对应ETF的阶段和下一观察条件。
      </div>
    </section>
  );
}

/* ══════════════ 卡3：美股情绪 ══════════════ */
function UsMoodCard({ data }: { data: SentimentDashboard }) {
  const b = data.us_mood.breadth;
  const v = data.us_mood.vix;
  const verdict = !b.ok
    ? "美股宽度数据不可用"
    : `标普500成分股中，${b.breadth_50 ?? "—"}%站上各自50个交易日均线。`;
  return (
    <section className="sx-rail-card mood-card">
      <CardHead
        title="美股情绪"
        badge={<Badge tone="neutral">{b.as_of ?? "日期未记录"}</Badge>}
        verdict={verdict}
        verdictColor="#4b5563"
      />
      {b.ok && (
        <Row name="标普500 宽度" strong
          hint="标普500成分股里，站上各自50个交易日均线的比例。观察参与范围，不是短期顶底线。"
          value={<>{b.breadth_50}%{b.pctile_60d != null && <span className="muted">（近3个月排位第 {b.pctile_60d} 百分位）</span>}</>} />
      )}
      {v.ok && (
        <Row name="VIX 恐慌指数" strong
          hint="标普500期权市场对未来约30天波动幅度的预期，不表示涨跌方向。"
          value={<>{v.value} · {v.state_cn}</>} />
      )}
      {data.us_mood.risk_appetite.ok && (
        <Row name="风险偏好"
          hint="对比「可选消费/必选消费」的相对强弱：大家愿意买餐厅汽车等非必需品=敢于冒险；只买食品药品=避险"
          value={data.us_mood.risk_appetite.state_cn} />
      )}
      <div className="muted mood-note">
        宽度是价格参与范围，VIX是标普500期权预期波动；不同日期或覆盖范围的读数不能合成即时结论。
      </div>
    </section>
  );
}

/* ══════════════ 卡4：美国调查情绪 ══════════════ */
function UsSurveyCard({ data }: { data: SentimentDashboard }) {
  const s = data.us_survey;
  const naaim = s.naaim;
  const aaii = s.aaii;
  return (
    <section className="sx-rail-card mood-card">
      <CardHead
        title="美国方向调查与自报敞口"
        badge={<Badge tone="neutral">{s.available ? "原始读数" : "未接入"}</Badge>}
        verdict={s.available ? "AAII是个人投资者看法问卷；NAAIM是基金经理自报股票敞口。两者不能共用20/80顶底线。" : "调查资料未接入"}
        verdictColor="#4b5563"
      />
      {aaii?.available && (
        <Row name="AAII 会员方向调查" strong
          hint="美国个人投资者协会会员对未来六个月股市方向的每周问卷，不代表实际持仓。"
          value={<>多 {aaii.bullish}% / 空 {aaii.bearish}% · {aaii.state_cn}<span className="muted">（{aaii.as_of}）</span></>} />
      )}
      {naaim?.available && (
        <Row name="NAAIM 自报股票敞口" strong
          hint="NAAIM主动投资管理人每周自报股票敞口，个别答复可为负值或超过100；公开资料可能延迟。"
          value={<>{naaim.exposure_index} · {naaim.state_cn}<span className="muted">（{naaim.as_of}）</span></>} />
      )}
      {!s.available && (
        <div className="muted" style={{ lineHeight: 1.7, padding: "4px 2px" }}>
          {s.hint_cn}。
        </div>
      )}
      <div className="muted mood-note">
        日期、来源和可用时间以顶部观察卡为准；单次调查不能证明标普500或纳斯达克短期拐点。
      </div>
    </section>
  );
}

/* ══════════════ 情绪信号（历史验证） ══════════════ */
function SignalCards({ cn }: { cn: SentimentDashboard["cn_mood"] }) {
  const cold = cn.state === "冷";
  return (
    <section className="sx-rail-card" style={{ marginTop: 14 }}>
      <div className="sx-rail-head">
        <span className="sx-rail-title">旧研究的适用边界</span>
        <span className="sx-rail-sub">完整条件尚未验证，保留历史证据入口</span>
      </div>
      <div className="mood-signal-grid">
        <div className={`mood-signal-card${cold ? " on-blue" : ""}`}>
          <div className="mood-signal-head">
            <b>❄ 旧冰点提示记录（当前未核）</b>
            {cold
              ? <Badge tone="info">旧分类显示偏冷</Badge>
              : <Badge tone="neutral">旧分类非偏冷</Badge>}
          </div>
          <div className="mood-signal-body">
            <p><b>是什么：</b>旧研究观察恐慌、板块下跌与小单资金流的组合。</p>
            <p><b>证据：</b>历史四个指定区间仅复现了简化条件；未重建完整四条件，也不是完整交易成绩。见实验报告库「icepoint-legacy-replay」。</p>
            <p><b>现在：</b>旧分类为{cold ? "偏冷" : "非偏冷"}；核对资料日期及ETF技术条件后再判断。</p>
          </div>
        </div>
        <div className="mood-signal-card">
          <div className="mood-signal-head">
            <b>⚠ 旧偏热提示记录（当前未核）</b>
            <Badge tone="neutral">当前未核</Badge>
          </div>
          <div className="mood-signal-body">
            <p><b>是什么：</b>旧研究观察板块走强时小单资金流增加的现象。</p>
            <p><b>反例：</b>2022下半年指定样本随后10天平均下跌3.58%，2026上半年指定样本随后反而上涨7.62%；不能一概称为顶部警报。</p>
            <p><b>现在：</b>若旧提示出现，仍须核对资料日期和ETF本身的技术路牌。</p>
          </div>
        </div>
      </div>
      <div className="muted mood-note">
        两个旧提示来自按订单规模分类的资金流研究（2026-09 归档，实验报告库「retail-sentiment-ts」），
        样本范围有限，完整条件的交易效果尚未验证。这些历史记录不构成买卖指令。
      </div>
    </section>
  );
}
