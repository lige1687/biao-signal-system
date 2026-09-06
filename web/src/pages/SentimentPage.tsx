import { useQuery } from "@tanstack/react-query";
import { sentimentApi } from "../api/client";
import { etfsForSector } from "../data/sectorEtfMap";

/* ── 情绪仪表盘页：全A / 美股 / 美国调查情绪 / A股板块散户热度 ───────────
 * 一切为叙事标注（research_proxy）：只描述环境与状态，不参与技术判定、
 * 不构成买卖点。阈值来源在卡片内标注（本系统回测 / 外部实证引用）。 */

const MOOD_TONE: Record<string, string> = { 热: "#d24a43", 冷: "#4d7fc4", 中: "#9aa4b2" };

export default function SentimentPage() {
  const { data, isLoading, error } = useQuery({
    queryKey: ["sentimentDashboard"],
    queryFn: () => sentimentApi.dashboard(),
    staleTime: 10 * 60_000,
  });

  if (isLoading) return <div className="page"><p className="muted">情绪仪表盘加载中…</p></div>;
  if (error || !data) return <div className="page"><p className="muted">加载失败：{(error as Error)?.message ?? "请先运行预计算"}</p></div>;

  return (
    <div className="page">
      <div className="sx-header">
        <div className="sx-title">
          <h1>情绪仪表盘</h1>
          {data.cn_mood.components && (
            <span className="sx-meta">
              · 叙事标注层 research_proxy · 只描述环境不构成买卖点
            </span>
          )}
        </div>
      </div>

            {/* ── 行动区：状态灯/操作卡/持仓风险（第一屏只回答"今天要不要行动"） ── */}
      {data.action?.available && (
        <section className="mood-action">
          {data.action.light === "gray" && (
            <div className="mood-light gray">
              <span className="mood-light-dot" style={{ background: "#9aa4b2" }} />
              当前无情绪信号触发（安静期）
              {data.cn_mood.state && data.cn_mood.state !== "冷" && (
                <span className="muted"> · 冰点窗口未开启（全A情绪{data.cn_mood.state}）</span>
              )}
            </div>
          )}
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
                <span>散户热度 z <b>{c.z?.toFixed(2) ?? "-"}</b></span>
                <span>宽度 b50 <b>{c.b50?.toFixed(0) ?? "-"}</b></span>
                <span>阶段 <b>{c.stage ?? "-"}</b></span>
              </div>
              <div className="mood-card-body">{c.plan_cn}</div>
              <div className="mood-card-win">{c.win_rate_cn}</div>
            </div>
          ))}
          {(data.action.alarm_cards ?? []).map((c) => (
            <div key={c.code} className="mood-card action alarm">
              <div className="mood-card-head">
                <b>⚠ 强势散户热警报 · {c.name}</b>
                {c.holding && <span className="mood-hold-tag danger">持仓相关</span>}
                <span className="spacer" />
                {(etfsForSector(c.name) ?? []).slice(0, 2).map((e) => (
                  <span key={e.symbol} className="mood-etf-badge">{e.name}</span>
                ))}
              </div>
              <div className="mood-card-facts">
                <span>散户热度 z <b>{c.z?.toFixed(2) ?? "-"}</b></span>
                <span>宽度 b50 <b>{c.b50?.toFixed(0) ?? "-"}</b></span>
              </div>
              <div className="mood-card-body">{c.plan_cn}</div>
              <div className="mood-card-win">{c.win_rate_cn}</div>
            </div>
          ))}
          <div className="mood-holding">
            <div className="sx-rail-title" style={{ fontSize: 12 }}>持仓风险</div>
            {(data.action.holding_risk ?? []).map((h) => (
              <span key={h.code} className={`mood-hold-chip ${h.state}`}
                    title={h.detail_cn}>{h.name}</span>
            ))}
          </div>
          <div className="muted mood-note">{data.action.note_cn}</div>
        </section>
      )}

      <div className="mood-grid">
        {/* ── 全A情绪 ── */}
        <section className="sx-rail-card mood-card">
          <div className="sx-rail-head"><span className="sx-rail-title">全A情绪</span>
            <span className="sx-rail-sub">两融+散户资金流+动能 三票</span></div>
          <MoodBig state={data.cn_mood.state} stateCn={data.cn_mood.state_cn} tone={MOOD_TONE[data.cn_mood.state ?? "中"]} />
          {Object.entries(data.cn_mood.components).map(([k, c]) => (
            <div key={k} className="mood-comp">
              <span>{c.label_cn}</span>
              <span>
                {c.ok && c.value != null ? (
                  <b className={(c.vote ?? 0) > 0 ? "up" : (c.vote ?? 0) < 0 ? "down" : ""}>
                    {c.value > 0 ? "+" : ""}{c.value}{c.unit ?? ""}
                  </b>
                ) : <span className="muted">不可用</span>}
              </span>
            </div>
          ))}
          <div className="muted mood-note">{data.cn_mood.note_cn}</div>
        </section>

        {/* ── 市场结构分化 ── */}
      <section className="sx-rail-card mood-card">
        <div className="sx-rail-head"><span className="sx-rail-title">市场结构</span>
          <span className="sx-rail-sub">板块强弱分化（结构市识别）</span></div>
        {data.market_structure?.available ? (
          <>
            <div className="mood-comp big">
              <span>结构状态</span>
              <b>{data.market_structure.state_cn}</b>
            </div>
            <div className="mood-comp">
              <span>极化指数（强占比+弱占比）</span>
              <b>{data.market_structure.polar?.toFixed(0)}</b>
            </div>
            <div className="mood-comp">
              <span>强势板块占比 / 弱势占比 / 中位b50</span>
              <b>{data.market_structure.strong_pct?.toFixed(0)}% / {data.market_structure.weak_pct?.toFixed(0)}% / {data.market_structure.median_b50?.toFixed(0)}</b>
            </div>
            <div className="mood-comp">
              <span>最强群（b50&gt;70 前5）</span>
              <b>{(data.market_structure.strong_boards ?? []).slice(0, 5).map(b => b.name).join("、")}</b>
            </div>
            <div className="mood-comp">
              <span>最弱群（b50&lt;30 前5）</span>
              <b>{(data.market_structure.weak_boards ?? []).slice(0, 5).map(b => b.name).join("、")}</b>
            </div>
            <div className="muted mood-note">{data.market_structure.note_cn}</div>
          </>
        ) : <div className="muted">结构数据不可用</div>}
      </section>

      {/* ── 美股情绪 ── */}
        <section className="sx-rail-card mood-card">
          <div className="sx-rail-head"><span className="sx-rail-title">美股情绪</span>
            <span className="sx-rail-sub">宽度 + VIX + 风险偏好</span></div>
          {data.us_mood.breadth.ok ? (
            <div className="mood-comp big">
              <span>SP500 宽度（站上50日线占比）</span>
              <b>{data.us_mood.breadth.breadth_50}% · {data.us_mood.breadth.state}
                {data.us_mood.breadth.pctile_60d != null && <span className="muted">（60日分位 {data.us_mood.breadth.pctile_60d}）</span>}
              </b>
            </div>
          ) : <div className="muted">宽度数据不可用</div>}
          {data.us_mood.vix.ok ? (
            <div className="mood-comp big">
              <span>VIX 恐慌指数</span>
              <b>{data.us_mood.vix.value} · {data.us_mood.vix.state_cn}</b>
            </div>
          ) : <div className="muted">VIX 不可用</div>}
          {data.us_mood.risk_appetite.ok ? (
            <div className="mood-comp big">
              <span>风险偏好（可选/必选消费）</span>
              <b>{data.us_mood.risk_appetite.state_cn}</b>
            </div>
          ) : <div className="muted">XLY/XLP 不可用</div>}
          <div className="muted mood-note">VIX 分档为市场通用惯例；宽度 1986 年以来全史（本地）。</div>
        </section>

        {/* ── 美国调查情绪 ── */}
        <section className="sx-rail-card mood-card">
          <div className="sx-rail-head"><span className="sx-rail-title">美国投资者/机构调查</span>
            <span className="sx-rail-sub">AAII 散户 · NAAIM 机构</span></div>
          {data.us_survey.available ? (
            <>
              {data.us_survey.aaii?.available && (
                <div className="mood-comp big">
                  <span>AAII（{data.us_survey.aaii.as_of}）</span>
                  <b>多 {data.us_survey.aaii.bullish}% / 空 {data.us_survey.aaii.bearish}% · {data.us_survey.aaii.state_cn}</b>
                </div>
              )}
              {data.us_survey.naaim?.available && (
                <div className="mood-comp big">
                  <span>NAAIM（{data.us_survey.naaim.as_of}）</span>
                  <b>{data.us_survey.naaim.exposure_index} · {data.us_survey.naaim.state_cn}</b>
                </div>
              )}
            </>
          ) : (
            <div className="muted" style={{ lineHeight: 1.7 }}>
              {data.us_survey.hint_cn}<br />
              阈值参考（{data.us_survey.threshold_source_cn}）：<br />
              牛熊价差 &gt;{data.us_survey.thresholds?.spread_greed}pp=过度乐观、
              &lt;{data.us_survey.thresholds?.spread_fear}pp=极度恐惧；
              看多&gt;{data.us_survey.thresholds?.bullish_greed}% 或看空&gt;{data.us_survey.thresholds?.bearish_fear}% 为极端。
              极端读数宜持续 2 周以上或配合价格确认再解读。
            </div>
          )}
        </section>
      </div>

      {/* ── 终版情绪信号（实验验证，触发板块清单） ── */}
      <section className="sx-rail-card" style={{ marginTop: 14 }}>
        <div className="sx-rail-head">
          <span className="sx-rail-title">情绪信号</span>
          <span className="sx-rail-sub">
            冰点机会 / 强势散户热警报（research_proxy · 实验验证 · 非买卖点）
          </span>
        </div>
        <div className="mood-comp big">
          <span>全A情绪环境</span>
          <b>{data.cn_mood.state === "冷" ? "冰点（信号1激活窗口）" : `${data.cn_mood.state ?? "?"}（信号1需冰点环境）`}</b>
        </div>
        <div className="muted mood-note">
          信号1「冰点机会」：全A情绪冰点时，已跌10%+且散户仍在逆势涌入、宽度深的板块（回测 10 日超额 +6.5~7.8%、79% 板块同向）→ 下方网格中标记「冰点关注」；
          信号2「强势散户热警报」：全面强势板块（b50/b200 &gt; 70）的散户涌入（回测 10 日 -9.3%、无一板块幸免）→ 标记「强热」。
          单年双事件样本，多年复验待做；只提示不构成买卖点（实验归档：实验报告库 retail-sentiment-ts）。
        </div>
      </section>

      {/* ── A股板块散户热度（仅一、二级行业） ── */}
      <section className="sx-rail-card" style={{ marginTop: 14 }}>
        <div className="sx-rail-head">
          <span className="sx-rail-title">A股板块散户热度</span>
          <span className="sx-rail-sub">
            {data.sector_heat.available
              ? `小单−超大单分化 · ${data.sector_heat.meta?.window_days}日 · 一二级行业（${data.sector_heat.boards.length}个有数据）`
              : "数据累积中"}
          </span>
        </div>
        {data.sector_heat.available ? (
          <div className="mood-sector-grid">
            {data.sector_heat.boards.slice(0, 40).map((b) => (
              <div key={b.code} className={`mood-sector-chip${b.sig_heat_alarm ? " warn" : b.sig_icepoint_pick ? " ice" : b.heat_warning ? " warn" : b.heat_hot ? " hot" : b.heat_cold ? " cold" : ""}`}
                   title={(b as { sig_note_cn?: string | null }).sig_note_cn ?? b.heat_note_cn ?? `散户热度分位 ${b.heat_pctile}（research_proxy）`}>
                <span>{b.name}{b.sig_heat_alarm ? " ⚠强热" : b.sig_icepoint_pick ? " ❄冰点关注" : ""}</span>
                <b>{b.heat_pctile?.toFixed(0)}</b>
              </div>
            ))}
          </div>
        ) : (
          <div className="muted" style={{ padding: "6px 8px" }}>
            板块资金流历史重建中（热度需连续 20 个交易日资金流；每日自动累积）。
          </div>
        )}
        <div className="muted mood-note">
          红色=过热警示（过热×上升/派发阶段）、橙=过热区、蓝=冰点区；阈值为回测校准前的占位刻度（rules.v2.yaml retail_heat）。
        </div>
      </section>

      <div className="muted mood-note" style={{ marginTop: 10 }}>{data.disclaimer_cn}</div>
    </div>
  );
}

function MoodBig({ state, stateCn, tone }: { state: string | null; stateCn: string; tone: string }) {
  return (
    <div className="mood-big" style={{ borderColor: tone, color: tone }}>
      <span className="mood-big-state">{state ?? "?"}</span>
      <span className="mood-big-cn">{stateCn}</span>
    </div>
  );
}
