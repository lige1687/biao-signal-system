import { useQuery } from "@tanstack/react-query";
import { sentimentApi } from "../api/client";
import { etfsForSector } from "../data/sectorEtfMap";
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
  const { data, isLoading, error } = useQuery({
    queryKey: ["sentimentDashboard"],
    queryFn: () => sentimentApi.dashboard(),
    staleTime: 10 * 60_000,
  });

  if (isLoading) return <div className="page"><p className="muted">情绪仪表盘加载中…</p></div>;
  if (error || !data) return <div className="page"><p className="muted">加载失败：{(error as Error)?.message ?? "请先运行预计算"}</p></div>;

  const cn = data.cn_mood;
  const nPicks = data.action?.opportunity_cards?.length ?? 0;
  const nAlarms = data.action?.alarm_cards?.length ?? 0;
  const holdDanger = (data.action?.holding_risk ?? []).filter((h) => h.state === "danger");
  const holdWatch = (data.action?.holding_risk ?? []).filter((h) => h.state === "watch");

  return (
    <div className="page">
      <div className="sx-header">
        <div className="sx-title">
          <h1>情绪仪表盘</h1>
          <span className="sx-meta">· 环境标注层，只描述"现在市场冷热"，不构成买卖点</span>
        </div>
      </div>

      {/* ── 第一屏结论条：一句话回答"现在怎样、要不要行动" ── */}
      <VerdictBar data={data} />

      {/* ── 行动区：有信号时给操作卡 + 持仓风险 ── */}
      {data.action?.available && (nPicks > 0 || nAlarms > 0 || holdDanger.length > 0) && (
        <section className="mood-action">
          {(data.action.opportunity_cards ?? []).map((c) => (
            <div key={c.code} className="mood-card action pick">
              <div className="mood-card-head">
                <b>❄ 冰点机会 · {c.name}</b>
                {c.holding && <span className="mood-hold-tag">持仓相关</span>}
                <span className="spacer" />
                {(etfsForSector(c.name) ?? []).slice(0, 2).map((e) => (
                  <span key={e.symbol} className="mood-etf-badge">{e.name}</span>
                ))}
              </div>
              <div className="mood-card-facts">
                <span>散户涌入强度 <b>{c.z?.toFixed(2) ?? "-"}</b></span>
                <span>板块内走强股票占比 <b>{c.b50?.toFixed(0) ?? "-"}%</b></span>
                <span>阶段 <b>{c.stage ?? "-"}</b></span>
              </div>
              <div className="mood-card-body">{c.plan_cn}</div>
              <div className="mood-card-win">{c.win_rate_cn}</div>
            </div>
          ))}
          {(data.action.alarm_cards ?? []).map((c) => (
            <div key={c.code} className="mood-card action alarm">
              <div className="mood-card-head">
                <b>⚠ 强热警报 · {c.name}</b>
                {c.holding && <span className="mood-hold-tag danger">持仓相关</span>}
                <span className="spacer" />
                {(etfsForSector(c.name) ?? []).slice(0, 2).map((e) => (
                  <span key={e.symbol} className="mood-etf-badge">{e.name}</span>
                ))}
              </div>
              <div className="mood-card-facts">
                <span>散户涌入强度 <b>{c.z?.toFixed(2) ?? "-"}</b></span>
                <span>板块内走强股票占比 <b>{c.b50?.toFixed(0) ?? "-"}%</b></span>
              </div>
              <div className="mood-card-body">{c.plan_cn}</div>
              <div className="mood-card-win">{c.win_rate_cn}</div>
            </div>
          ))}
          {(holdDanger.length > 0 || holdWatch.length > 0) && (
            <div className="mood-holding">
              <div className="sx-rail-title" style={{ fontSize: 12 }}>持仓情绪风险</div>
              {holdDanger.map((h) => (
                <span key={h.code} className="mood-hold-chip danger" title={h.detail_cn}>{h.name} · 情绪危险</span>
              ))}
              {holdWatch.map((h) => (
                <span key={h.code} className="mood-hold-chip watch" title={h.detail_cn}>{h.name} · 需留意</span>
              ))}
              <span className="mood-hold-chip">其余 {(data.action.holding_risk ?? []).length - holdDanger.length - holdWatch.length} 个持仓情绪正常</span>
            </div>
          )}
        </section>
      )}

      <div className="mood-grid">
        <CnMoodCard cn={cn} />
        <MarketStructureCard data={data} />
        <UsMoodCard data={data} />
        <UsSurveyCard data={data} />
      </div>

      {/* ── 两个经过历史验证的情绪信号：结构化卡片，激活/未激活一眼可见 ── */}
      <SignalCards cn={cn} />

      {/* ── A股板块散户热度（仅一、二级行业） ── */}
      <section className="sx-rail-card" style={{ marginTop: 14 }}>
        <div className="sx-rail-head">
          <span className="sx-rail-title">A股板块散户热度</span>
          <span className="sx-rail-sub">
            {data.sector_heat.available
              ? `散户小单vs超大单 · 近${data.sector_heat.meta?.window_days}天 · 只看大板块（${data.sector_heat.boards.length}个有数据）`
              : "数据重建中"}
          </span>
        </div>
        {data.sector_heat.available ? (
          <div className="mood-sector-grid">
            {data.sector_heat.boards.slice(0, 40).map((b) => (
              <div key={b.code} className={`mood-sector-chip${b.sig_heat_alarm ? " warn" : b.sig_icepoint_pick ? " ice" : b.heat_warning ? " warn" : b.heat_hot ? " hot" : b.heat_cold ? " cold" : ""}`}
                   title={(b as { sig_note_cn?: string | null }).sig_note_cn ?? b.heat_note_cn ?? `散户热度分位 ${b.heat_pctile}`}>
                <span>{b.name}{b.sig_heat_alarm ? " ⚠强热" : b.sig_icepoint_pick ? " ❄冰点关注" : ""}</span>
                <b>{b.heat_pctile?.toFixed(0)}</b>
              </div>
            ))}
          </div>
        ) : (
          <div className="muted" style={{ padding: "10px 8px", lineHeight: 1.8 }}>
            板块资金流数据正在每日自动累积（需要连续 20 个交易日的数据才能算热度，约 9 月底恢复）。
            恢复后这里会显示：每个大板块的散户热度分位（0–100，越高表示散户相对大资金越活跃），
            红色=散户过热、蓝色=散户冰点。
          </div>
        )}
        <div className="muted mood-note">
          怎么看：数字=散户热度分位（近20天散户小单相对超大单的活跃程度，在所有大板块里排名）。
          高≠必跌、低≠必涨，只作参考背景；红/蓝标记含义同上。
        </div>
      </section>

      <div className="muted mood-note" style={{ marginTop: 10 }}>{data.disclaimer_cn}</div>
    </div>
  );
}

/* ══════════════ 第一屏结论条 ══════════════ */
function VerdictBar({ data }: { data: SentimentDashboard }) {
  const cn = data.cn_mood;
  const nPicks = data.action?.opportunity_cards?.length ?? 0;
  const nAlarms = data.action?.alarm_cards?.length ?? 0;
  const holdDanger = (data.action?.holding_risk ?? []).filter((h) => h.state === "danger");

  let tone: "danger" | "caution" | "info" | "neutral";
  let icon: string;
  let headline: string;
  if (nPicks > 0) {
    tone = "info"; icon = "❄";
    headline = `冰点机会窗口开启：${nPicks} 个板块命中（恐慌中散户逆势涌入的板块，历史上这种时候买入胜率高）`;
  } else if (nAlarms > 0 || holdDanger.length > 0) {
    tone = "danger"; icon = "⚠";
    headline = `有情绪警报：${nAlarms > 0 ? `${nAlarms} 个板块散户过热` : ""}${nAlarms > 0 && holdDanger.length > 0 ? "，" : ""}${holdDanger.length > 0 ? `${holdDanger.length} 个持仓情绪危险` : ""}（狂欢中散户涌入，历史上这种时候要小心）`;
  } else if (cn.state === "热") {
    tone = "caution"; icon = "🌡";
    headline = "情绪偏热但未触发信号：散户整体在涌入，暂无操作提示，持仓照常按规则管理";
  } else if (cn.state === "冷") {
    tone = "info"; icon = "❄";
    headline = "情绪偏冷：市场在冰点区附近，留意后续是否出现「冰点机会」（跌深的板块+散户仍涌入）";
  } else {
    tone = "neutral"; icon = "○";
    headline = "情绪平静：无信号、无警报，今天情绪面不需要做任何事";
  }

  return (
    <div className={`mood-verdictbar ${tone}`}>
      <span className="mood-verdictbar-icon">{icon}</span>
      <div>
        <div className="mood-verdictbar-main">{headline}</div>
        <div className="mood-verdictbar-sub">
          全A情绪 <b style={{ color: MOOD_TONE[cn.state ?? "中"] }}>{cn.state ?? "?"}</b>
          {" · "}美股宽度 {data.us_mood.breadth.ok ? `${data.us_mood.breadth.breadth_50}%（${data.us_mood.breadth.state === "宽" ? "偏强" : "偏弱"}）` : "不可用"}
          {data.market_structure?.available && data.market_structure.polar != null && (
            <>{" · "}A股 <b>{(data.market_structure.polar ?? 0) >= 50 ? "结构市（强弱分化）" : "整体市"}</b></>
          )}
        </div>
      </div>
    </div>
  );
}

/* ══════════════ 卡1：全A情绪（三票） ══════════════ */
const CN_COMP_EXPLAIN: Record<string, { name: string; hint: string }> = {
  margin20: { name: "借钱炒股的总量变化", hint: "融资余额=投资者向券商借钱买股票的总额。20日变化为正=加杠杆（通常代表情绪热）" },
  retail_small20: { name: "散户小单净流入", hint: "全市场小单买入减卖出，近20天合计。散户越买越猛=情绪越热（历史上散户狂欢常接近阶段顶）" },
  equal_mom20: { name: "全体股票20天涨跌", hint: "等权指数=每只股票权重相同，反映整体股票而非少数大权重股的走势。近20天上涨=情绪回暖" },
};

function CnMoodCard({ cn }: { cn: SentimentDashboard["cn_mood"] }) {
  const state = cn.state ?? "中";
  const tone = state === "热" ? "danger" : state === "冷" ? "info" : "neutral";
  const verdict = state === "热"
    ? "散户整体情绪偏热——多数指标向上，追高需谨慎"
    : state === "冷"
      ? "散户整体情绪偏冷——多数指标向下，留意思变的可能"
      : state === "中"
        ? "散户情绪中性——指标有涨有跌，方向不明"
        : "情绪数据不足，暂不判定";
  const hotVotes = Object.values(cn.components ?? {}).filter((c) => c.ok && (c.vote ?? 0) > 0).length;
  const coldVotes = Object.values(cn.components ?? {}).filter((c) => c.ok && (c.vote ?? 0) < 0).length;
  return (
    <section className="sx-rail-card mood-card">
      <CardHead
        title="全A情绪（散户视角）"
        badge={<Badge tone={tone}>{state === "热" ? "偏热" : state === "冷" ? "偏冷" : "中性"}</Badge>}
        verdict={verdict}
        verdictColor={MOOD_TONE[state]}
      />
      <div className="mood-comp" style={{ marginTop: 4 }}>
        <span>投票结果</span>
        <b><span className="up">{hotVotes} 票热</span> / <span className="down">{coldVotes} 票冷</span></b>
      </div>
      {Object.entries(cn.components ?? {}).map(([k, c]) => {
        const ex = CN_COMP_EXPLAIN[k] ?? { name: c.label_cn, hint: "" };
        // 金额类（亿）超过 1 万亿换算成「万亿」展示，避免一长串数字
        const fmtVal = () => {
          if (!c.ok || c.value == null) return <span className="muted">不可用</span>;
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
        怎么看：三个指标各投一票（向上=热票、向下=冷票），多数票决定冷热。
        这是"环境温度计"，热≠马上跌、冷≠马上涨，只提醒你现在站在什么环境里。
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
  const isStruct = (ms.polar ?? 0) >= 50;
  return (
    <section className="sx-rail-card mood-card">
      <CardHead
        title="A股市场结构"
        badge={<Badge tone={isStruct ? "caution" : "neutral"}>{isStruct ? "结构市" : "整体市"}</Badge>}
        verdict={isStruct
          ? "强弱板块同时大量存在——别用大盘一刀切，板块要单独看"
          : "板块涨跌比较同步，大盘环境可作整体参考"}
        verdictColor={isStruct ? "#b45309" : "#4b5563"}
      />
      <Row name="强弱分化度" strong
        hint="强势板块占比+弱势板块占比。大于50=结构市（一半以上板块处于明显强或明显弱），说明市场分化严重"
        value={<>{ms.polar?.toFixed(0)}<span className="muted">（≥50 即结构市）</span></>} />
      <Row name="强势板块占比 / 弱势板块占比"
        hint="板块内站上50日线的股票占比>70%算强势板块，<30%算弱势板块"
        value={`${ms.strong_pct?.toFixed(0)}% / ${ms.weak_pct?.toFixed(0)}%`} />
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
        怎么看：结构市里"指数没涨但某些板块很强"是常态，选对板块比猜大盘更重要；
        整体市里板块同涨同跌，大盘方向就是仓位方向。
      </div>
    </section>
  );
}

/* ══════════════ 卡3：美股情绪 ══════════════ */
function UsMoodCard({ data }: { data: SentimentDashboard }) {
  const b = data.us_mood.breadth;
  const v = data.us_mood.vix;
  const breadthHot = b.ok && (b.breadth_50 ?? 0) > 80;
  const breadthCold = b.ok && (b.breadth_50 ?? 0) < 20;
  const tone = breadthHot ? "danger" : breadthCold ? "opportunity" : "neutral";
  const verdict = !b.ok
    ? "美股宽度数据不可用"
    : breadthHot
      ? "美股过热：绝大多数成分股在上涨趋势中（历史上常接近阶段顶）"
      : breadthCold
        ? "美股过冷：绝大多数成分股在下跌趋势中（历史上常接近阶段底）"
        : `美股宽度正常偏${b.state === "宽" ? "强" : "弱"}，无极端`;
  return (
    <section className="sx-rail-card mood-card">
      <CardHead
        title="美股情绪"
        badge={<Badge tone={tone}>{b.ok ? (breadthHot ? "过热" : breadthCold ? "过冷" : "正常") : "不可用"}</Badge>}
        verdict={verdict}
        verdictColor={breadthHot ? "#d24a43" : breadthCold ? "#15803d" : "#4b5563"}
      />
      {b.ok && (
        <Row name="标普500 宽度" strong
          hint="500只成分股里，站上50日均线（近一年均价的中期趋势线）的比例。>80%=普涨过热，<20%=普跌过冷，历史极端后常有反转"
          value={<>{b.breadth_50}%{b.pctile_60d != null && <span className="muted">（近3个月排位第 {b.pctile_60d} 百分位）</span>}</>} />
      )}
      {v.ok && (
        <Row name="VIX 恐慌指数" strong
          hint="市场对未来30天波动的预期，俗称恐慌指数。<15=低位自满（大家都不怕），>30=恐慌（历史上常对应阶段性底部）"
          value={<>{v.value} · {v.state_cn}</>} />
      )}
      {data.us_mood.risk_appetite.ok && (
        <Row name="风险偏好"
          hint="对比「可选消费/必选消费」的相对强弱：大家愿意买餐厅汽车等非必需品=敢于冒险；只买食品药品=避险"
          value={data.us_mood.risk_appetite.state_cn} />
      )}
      <div className="muted mood-note">
        怎么看：美股影响全球风险偏好（含A股外资流向）。宽度+VIX 同看：
        宽度&gt;80% 且 VIX&lt;15 = 乐观末期的典型组合，宜谨慎不宜追高。
        宽度数据自 1986 年（本地全史）。
      </div>
    </section>
  );
}

/* ══════════════ 卡4：美国调查情绪 ══════════════ */
function UsSurveyCard({ data }: { data: SentimentDashboard }) {
  const s = data.us_survey;
  const naaim = s.naaim;
  const aaii = s.aaii;
  const extreme = (naaim?.state_cn.includes("极端乐观") || aaii?.state_cn.includes("贪婪") || aaii?.state_cn.includes("恐惧"));
  const tone = extreme ? "danger" : "neutral";
  return (
    <section className="sx-rail-card mood-card">
      <CardHead
        title="美国投资者/机构调查"
        badge={<Badge tone={tone}>{s.available ? (extreme ? "极端读数" : "正常区间") : "未接入"}</Badge>}
        verdict={s.available
          ? extreme ? "调查出现极端读数——逆向视角：当前方向盛极而衰的概率上升" : "调查读数在正常区间，无极端信号"
          : "调查数据未接入（AAII/NAAIM 周度问卷）"}
        verdictColor={extreme ? "#d24a43" : "#4b5563"}
      />
      {aaii?.available && (
        <Row name="AAII 散户问卷" strong
          hint="美国散户协会每周问卷：看多/看空人数占比。散户集体看多常接近顶、集体看空常接近底（逆向指标）"
          value={<>多 {aaii.bullish}% / 空 {aaii.bearish}% · {aaii.state_cn}<span className="muted">（{aaii.as_of}）</span></>} />
      )}
      {naaim?.available && (
        <Row name="NAAIM 机构仓位" strong
          hint="美国机构基金经理每周自报的股票仓位（0-200）。>100=加杠杆般乐观（自满风险），<40=极度悲观（机会区）"
          value={<>{naaim.exposure_index} · {naaim.state_cn}<span className="muted">（{naaim.as_of}）</span></>} />
      )}
      {!s.available && (
        <div className="muted" style={{ lineHeight: 1.7, padding: "4px 2px" }}>
          {s.hint_cn}。接入后阈值口径：{s.threshold_source_cn}。
        </div>
      )}
      <div className="muted mood-note">
        怎么看：问卷反映"嘴上说的情绪"。极端读数（散户/机构一边倒）才值得注意，
        且宜持续 2 周以上或配合价格拐点确认，单周噪声大。
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
        <span className="sx-rail-title">情绪信号（经历史数据验证）</span>
        <span className="sx-rail-sub">两个信号 · 只提示不构成买卖点</span>
      </div>
      <div className="mood-signal-grid">
        <div className={`mood-signal-card${cold ? " on-blue" : ""}`}>
          <div className="mood-signal-head">
            <b>❄ 信号一：冰点机会</b>
            {cold
              ? <Badge tone="info">环境就绪，等板块命中</Badge>
              : <Badge tone="neutral">未激活</Badge>}
          </div>
          <div className="mood-signal-body">
            <p><b>是什么：</b>全市场恐慌、板块已跌 10% 以上、但散户仍在逆势买入、板块内大部分股票已深度走弱——这种"越跌散户越买"的板块，历史上反弹概率高。</p>
            <p><b>历史成绩：</b>2022 上海疫情期、2022 十月、2026 四月、2026 七月四次验证全部盈利，平均涨幅 0.6%~12.9%，2026 七月那次 88 个命中板块平均 +12.9%。</p>
            <p><b>现在：</b>{cold ? "全A情绪已进入冰点区，命中板块会出现在页面顶部操作卡里。" : "全A情绪未到冰点，信号未激活。冰点的特征是散户集体撤退、借钱炒股的总量收缩。"}</p>
          </div>
        </div>
        <div className="mood-signal-card">
          <div className="mood-signal-head">
            <b>⚠ 信号二：强热警报</b>
            <Badge tone="neutral">未激活</Badge>
          </div>
          <div className="mood-signal-body">
            <p><b>是什么：</b>板块全面走强（大部分股票在强势区）的同时散户大量涌入——"狂欢中的散户"历史上往往接近阶段顶部。</p>
            <p><b>历史成绩（已降级）：</b>2022 下半年市场转弱期，命中板块 10 天平均 -3.58%（可信）；但 2026 上半年结构牛市中反而 +7.62%（失效）。<b>只在市场转弱期可信</b>，整体牛市里会误报。</p>
            <p><b>现在：</b>无板块命中。命中时顶部操作卡会出现红色警示，持仓相关板块会标注"情绪危险"。</p>
          </div>
        </div>
      </div>
      <div className="muted mood-note">
        两个信号都来自散户资金流研究（2026-09 归档，实验报告库「retail-sentiment-ts」），
        样本为近一年+A股大板块，历史上有效但样本有限，只能当"参考提示"不能当买卖指令。
      </div>
    </section>
  );
}
