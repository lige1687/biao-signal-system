import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { api, dailyBriefApi, sectorsApi } from "../api/client";
import InfoTip from "../components/InfoTip";
import { fmt, fmtPrice } from "../utils/format";
import type { DailyBriefResponse } from "../types";

type DailyBriefResponseBrief = DailyBriefResponse["brief"];

/* ------------------------------------------------------------------ */
/*  术语解释（本页文案与 SectorsPage 同风格：贴近用户、不新造指标）      */
/* ------------------------------------------------------------------ */
const TIPS = {
  breadth: "宽度 = 全市场站上这条均线的股票占比。比如 43% 的股票站上 20 日线，宽度就是 43%：比例越高，上涨的参与面越广，行情越扎实。",
  pctile: "近一年位置（分位）= 当前数值在过去一年里排第几。第 97% 位表示过去一年 97% 的时间都比现在低。≥90% 或 ≤10% 视为「异常区间」，值得留意。",
  b20: "过去 20 个交易日的平均价，约一个月成本线。站上的股票多 = 短期行情偏强。",
  b50: "过去 50 个交易日的平均价，约一个季度成本线，看中期参与度。",
  b200: "过去 200 个交易日的平均价，约一年成本线（俗称「年线」）。站上的比例低，说明多数股票处于长期弱势。",
  margin: "两融余额 = 全市场融资买入的未偿还总额，反映借钱炒股的资金规模，是市场情绪的温度计。",
  marginPct: "两融余额占流通市值的比例，比绝对值更能反映杠杆水平，历史警戒区约 3.5%。",
  vix: "VIX = 美股「恐慌指数」，由期权价格反推的波动预期。低于 20 算平静，高于 30 说明市场恐慌。",
  spread: "中国 10 年期国债收益率减美国的差值。为负说明中国利率更低，通常对应资金更宽松。",
  streak: "连续在榜天数 = 该板块连续多少天出现在观察清单里。天数越长，热度越持续、越不是一日游。",
  rs: "强弱百分位 = 板块涨幅相对全市场所有板块的排名（0 最弱、100 最强），50 是分界线。",
  rsDelta: "近 20 日强弱百分位的变化：正数 = 相对全市场在走强，负数 = 在走弱。",
  flow: "近 20 日主力资金累计净流入（亿元）。「主力」按单笔成交金额大小推算（超大单+大单），是研究代理口径，非真实机构数据。",
  pe: "市盈率 TTM = 按最近四个季度利润计算的估值，负数代表亏损。",
  stage: "板块趋势阶段：筑底=跌完横盘中 / 上升=趋势向上 / 派发=高位转弱 / 下降=趋势向下。",
  color: "LEI 趋势颜色：绿 = 价格在 20 日线上方且高于 20 天前（向上）；灰 = 均线方向分歧（震荡）；黑 = 价格在 20 日线下方且低于 20 天前（向下）。",
  verdict: "机会档位来自「机会扫描」：可操作 = 满足条件可研究入场；等待 = 方向对但条件未齐；受阻 = 有明确阻力；当前无机会 = 条件不成立。",
  updown: "板块内当日上涨家数 / 下跌家数，反映板块内部共识：一边倒说明涨得齐、跌得也齐。",
  dist60: "现价相对 60 日线的位置：+2% = 高出 60 日线 2 个百分点，负数 = 还在 60 日线下方。",
  quote: "来自行情快照：收盘版为当日收盘涨跌幅，盘中版为最新价实时涨跌。",
};

const SLOT_CN: Record<string, string> = {
  "1445": "盘中预判 · 14:45（未收盘，结论以收盘版为准）",
  "1645": "收盘复核 · 16:45",
};

/** 宽度指标 → 人话标签 */
const METRIC_CN: Record<string, string> = {
  b20: "站上 20日线",
  b50: "站上 50日线",
  b200: "站上 200日线（年线）",
};
const METRIC_TIP: Record<string, string> = { b20: TIPS.b20, b50: TIPS.b50, b200: TIPS.b200 };

/** 板块阶段（与 SectorsPage 同口径） */
const STAGE_CN: Record<string, string> = {
  markup: "上升",
  accumulation: "筑底",
  distribution: "派发",
  decline: "下降",
};

/** LEI 三色兜底（旧简报落盘时 color_cn 为 null，仅有英文枚举） */
const COLOR_CN: Record<string, string> = {
  green: "绿",
  gray: "灰",
  black: "黑",
};

/** 维度取值 → 小格着色 */
function dimTone(v: string): string {
  if (v.includes("支持") || v.includes("通畅")) return "pos";
  if (v.includes("冲突") || v.includes("阻力")) return "neg";
  if (v.includes("改善")) return "imp";
  return "mid";
}

function verdictTone(verdict: string | null): string {
  switch (verdict) {
    case "actionable":
      return "opportunity";
    case "waiting":
      return "neutral";
    case "blocked":
      return "caution";
    default:
      return "muted-chip";
  }
}

function colorTone(color: string | null | undefined): string {
  switch (color) {
    case "green":
      return "pos";
    case "black":
      return "neg";
    default:
      return "mid";
  }
}

/** 较前日格式化：0 显示持平，正红负绿（中国惯例，与全站一致） */
function fmtDayChange(v: number | null | undefined): { text: string; cls: string } {
  if (v == null) return { text: "—", cls: "flat" };
  if (Math.abs(v) < 0.05) return { text: "持平", cls: "flat" };
  return { text: `${v > 0 ? "+" : ""}${v.toFixed(1)}`, cls: v > 0 ? "up" : "down" };
}

/** 涨跌幅单元格：正红负绿，null/不可用 → 灰 — */
function PctCell({ v, title }: { v: number | null | undefined; title?: string }) {
  if (v == null || Number.isNaN(v)) return <span className="flat">—</span>;
  const cls = v > 0 ? "up" : v < 0 ? "down" : "flat";
  return (
    <span className={cls} title={title}>
      {v > 0 ? "+" : ""}
      {v.toFixed(2)}%
    </span>
  );
}

/* ------------------------------------------------------------------ */

export default function DailyBriefPage() {
  const [slot, setSlot] = useState<string | null>(null);
  const { data, error } = useQuery({
    queryKey: ["dailyBriefLatest"],
    queryFn: () => dailyBriefApi.latest(),
    staleTime: 5 * 60_000,
  });

  if (error) {
    return (
      <div className="page">
        <div className="header">
          <h1>收盘简报</h1>
        </div>
        <div className="fund-errors">
          加载失败：{(error as Error).message}
          <div className="fund-hint">请先在本机跑 scripts/precompute_daily_brief.py 生成简报。</div>
        </div>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="page">
        <div className="header">
          <h1>收盘简报</h1>
        </div>
        <div className="muted">加载中…</div>
      </div>
    );
  }

  const activeSlot = slot && data.slots_available.includes(slot) ? slot : data.slot;

  return (
    <div className="page">
      <div className="header">
        <h1>收盘简报</h1>
        <span className="generated">
          {data.date} · {SLOT_CN[activeSlot] ?? activeSlot} · 生成于 {data.brief.generated_at}
        </span>
        <span className="spacer" />
        {data.slots_available.map((s) => (
          <button
            key={s}
            className={`btn ${s === activeSlot ? "primary" : ""}`}
            onClick={() => setSlot(s)}
          >
            {s === "1445" ? "14:45 预判" : "16:45 收盘"}
          </button>
        ))}
      </div>

      {activeSlot !== data.slot ? (
        <SlotView date={data.date} slot={activeSlot} />
      ) : (
        <BriefBody brief={data.brief} />
      )}
    </div>
  );
}

function SlotView({ date, slot }: { date: string; slot: string }) {
  const { data } = useQuery({
    queryKey: ["dailyBrief", date, slot],
    queryFn: () => dailyBriefApi.byDate(date),
    staleTime: 5 * 60_000,
  });
  if (!data || data.slot !== slot) return <div className="muted">加载中…</div>;
  return <BriefBody brief={data.brief} />;
}

/* ------------------------------------------------------------------ */
/*  文字要点（LLM/模板）：极简 markdown 渲染（双栏排版提密度）          */
/* ------------------------------------------------------------------ */

function renderInline(text: string, keyBase: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g);
  return parts.map((p, i) =>
    p.startsWith("**") && p.endsWith("**") ? (
      <strong key={`${keyBase}-${i}`}>{p.slice(2, -2)}</strong>
    ) : (
      <span key={`${keyBase}-${i}`}>{p}</span>
    ),
  );
}

function SummaryBlock({ brief }: { brief: DailyBriefResponseBrief }) {
  const byLlm = brief.summary.generated_by === "llm";
  const lines = brief.summary.text.split("\n");
  return (
    <section className="brief-summary">
      <div className="brief-summary-head">
        <span className="brief-summary-title">今日要点</span>
        <InfoTip tip="所有数字由本机规则引擎计算，这段文字只是把下面三节的数据串成人话；数据本身与文字无关（判定权在 Python 规则层）。">
          {byLlm ? "AI 组织文字" : "模板生成文字"}
        </InfoTip>
      </div>
      <div className="brief-summary-body">
        {lines.map((raw, i) => {
          const line = raw.trimEnd();
          if (!line.trim()) return null;
          if (/^#{1,3}\s/.test(line) || /^[①②③④]/.test(line.trim()))
            return (
              <div key={i} className="brief-sum-h">
                {renderInline(line.replace(/^#{1,3}\s*/, ""), `h${i}`)}
              </div>
            );
          if (/^[-•*]\s+/.test(line.trim()))
            return (
              <div key={i} className="brief-sum-li">
                <span className="brief-sum-dot">·</span>
                {renderInline(line.trim().replace(/^[-•*]\s+/, ""), `l${i}`)}
              </div>
            );
          return (
            <div key={i} className="brief-sum-p">
              {renderInline(line, `p${i}`)}
            </div>
          );
        })}
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  ① 市场环境                                                          */
/* ------------------------------------------------------------------ */

function EnvSection({ env }: { env: DailyBriefResponseBrief["env"] }) {
  // 转置：行 = 宽度指标，列 = A股/美股（每格塞现值+较前日+分位）
  const metrics = ["b20", "b50", "b200"];
  const byMarket = (mkt: string, metric: string) =>
    env.breadth_context.find((c) => c.market === mkt && c.metric === metric);
  const aDate = env.breadth_context.find((c) => c.market === "A股")?.date;
  const usDate = env.breadth_context.find((c) => c.market === "美股")?.date;

  const raw = env.macro.raw;
  const marginYi = raw?.margin?.rzrqye_yi ?? raw?.margin?.rzye_yi;

  return (
    <section className="brief-env brief-sec">
      <div className="brief-sec-head">
        <h2 className="fund-section-title">① 市场环境</h2>
        <span className="fund-hint">
          全市场参与面是否异常：
          <InfoTip tip={TIPS.breadth}>宽度</InfoTip> 与{" "}
          <InfoTip tip={TIPS.pctile}>近一年位置</InfoTip>
          {env.anomalies.length > 0 && (
            <span className="brief-anomaly-inline">
              ⚠{" "}
              {env.anomalies
                .map(
                  (a) =>
                    `${a.market}${METRIC_CN[a.metric] ?? a.metric} 第${Math.round(a.pctile_250d ?? 0)}%位`,
                )
                .join(" · ")}
            </span>
          )}
        </span>
      </div>

      <div className="brief-env-flex">
        <div className="fund-table-wrap brief-env-tablewrap">
          <table className="event-table fund-table brief-env-table">
            <thead>
              <tr>
                <th>
                  <InfoTip tip={TIPS.breadth}>宽度指标（占比）</InfoTip>
                </th>
                <th className="brief-env-mkt">A股（{aDate ?? "—"}）</th>
                <th className="brief-env-mkt">美股（{usDate ?? "—"}）</th>
              </tr>
            </thead>
            <tbody>
              {metrics.map((m) => (
                <tr key={m}>
                  <th className="brief-env-metric">
                    <InfoTip tip={METRIC_TIP[m] ?? TIPS.breadth}>{METRIC_CN[m] ?? m}</InfoTip>
                  </th>
                  {(["A股", "美股"] as const).map((mkt) => {
                    const c = byMarket(mkt, m);
                    const chg = fmtDayChange(c?.day_change);
                    const pct = c?.pctile_250d;
                    const extreme =
                      pct != null && (pct >= 90 || pct <= 10) ? (pct >= 90 ? "hi" : "lo") : "";
                    return (
                      <td key={`${mkt}-${m}`} className={`brief-env-cell ${extreme}`}>
                        <span className="brief-cell-main">{c ? `${fmt(c.value, 1)}%` : "—"}</span>
                        <span className={`brief-delta ${chg.cls}`}>{chg.text}</span>
                        {pct != null && (
                          <span className={`brief-pct ${extreme}`} title={TIPS.pctile}>
                            第 {Math.round(pct)}% 位{extreme ? (pct >= 90 ? "·偏高" : "·偏低") : ""}
                          </span>
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="brief-macro-col">
          <div className="brief-macro-label">背景参考（不参与判定）</div>
          {marginYi != null && (
            <div className="brief-macro-item">
              <InfoTip tip={TIPS.margin}>两融余额</InfoTip>
              <b>{(marginYi / 10000).toFixed(2)}万亿</b>
              {raw?.margin?.rzyezb_pct != null && (
                <span className="muted">
                  （<InfoTip tip={TIPS.marginPct}>占流通市值</InfoTip>{" "}
                  {raw.margin.rzyezb_pct.toFixed(2)}%）
                </span>
              )}
            </div>
          )}
          {raw?.vix?.value != null && (
            <div className="brief-macro-item">
              <InfoTip tip={TIPS.vix}>VIX 恐慌指数</InfoTip>
              <b>{raw.vix.value.toFixed(1)}</b>
              <span className="muted">
                {raw.vix.value < 20 ? "（平静）" : raw.vix.value >= 30 ? "（恐慌）" : ""}
              </span>
            </div>
          )}
          {raw?.cn_us_spread_10y != null && (
            <div className="brief-macro-item">
              <InfoTip tip={TIPS.spread}>中美 10Y 利差</InfoTip>
              <b>
                {raw.cn_us_spread_10y > 0 ? "+" : ""}
                {raw.cn_us_spread_10y.toFixed(2)}pct
              </b>
            </div>
          )}
          {marginYi == null && raw?.vix?.value == null && env.macro.line_cn && (
            <div className="muted">{env.macro.line_cn}</div>
          )}
        </div>
      </div>
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  ② 自选重点变化（联表行情卡片：现价 + 当日涨跌）                       */
/* ------------------------------------------------------------------ */

function WatchSection({ wl }: { wl: DailyBriefResponseBrief["watchlist"] }) {
  // 与看盘页共享同一 queryKey：进过看盘页这里秒开，反之并行取
  const { data: cardsData } = useQuery({
    queryKey: ["cards", "watchlist"],
    queryFn: () => api.dashboard("watchlist"),
    staleTime: 60_000,
  });
  const quoteBy = new Map((cardsData?.cards ?? []).map((c) => [c.symbol, c]));

  const items = wl.items;
  const changedCount = items.filter((it) => it.n_changes > 0 || it.is_new).length;
  return (
    <section className="brief-watch-sec brief-sec">
      <div className="brief-sec-head">
        <h2 className="fund-section-title">② 自选重点变化</h2>
        <span className="fund-hint">
          共 {items.length} 只 · {changedCount} 只今日有变化
          {wl.sector_watch_count > 0 && ` · 另有 ${wl.sector_watch_count} 项板块自选`}
          ：与上一份简报逐项对比，没写的就是和昨天一样
        </span>
      </div>
      {items.length === 0 ? (
        <div className="muted">自选为空</div>
      ) : (
        <div className="fund-table-wrap">
          <table className="event-table fund-table brief-watch-table">
            <thead>
              <tr>
                <th>标的</th>
                <th className="num">
                  <InfoTip tip={TIPS.quote}>现价</InfoTip>
                </th>
                <th className="num">
                  <InfoTip tip={TIPS.quote}>当日</InfoTip>
                </th>
                <th>
                  <InfoTip tip={TIPS.color}>趋势</InfoTip>
                  {" / "}
                  <InfoTip tip={TIPS.verdict}>档位</InfoTip>
                </th>
                <th>状态速览（六维）</th>
                <th>今日变化（与上一份简报对比）</th>
              </tr>
            </thead>
            <tbody>
              {items.map((it) => {
                const changed = it.n_changes > 0 || it.is_new;
                const q = quoteBy.get(it.symbol);
                const colorCn =
                  it.state?.color_cn ?? (it.state?.color ? COLOR_CN[it.state.color] : null);
                return (
                  <tr
                    key={it.symbol}
                    className={
                      it.verdict === "actionable" || it.verdict === "waiting"
                        ? "brief-row-hot"
                        : changed
                          ? ""
                          : "brief-row-unchanged"
                    }
                  >
                    <td>
                      <Link to={`/symbol/${encodeURIComponent(it.symbol)}`} className="brief-sym">
                        {it.display_name ?? it.symbol}
                        <span className="symbol"> {it.symbol}</span>
                      </Link>
                    </td>
                    <td className="num">{q?.price != null ? fmtPrice(q.price) : "—"}</td>
                    <td className="num">
                      <PctCell v={q?.change_pct} title={TIPS.quote} />
                    </td>
                    <td className="brief-status">
                      {colorCn && (
                        <span
                          className={`brief-color-dot ${colorTone(it.state?.color)}`}
                          title={TIPS.color}
                        >
                          {colorCn}
                        </span>
                      )}
                      {it.state?.stage_cn && (
                        <span className="brief-stage-cn" title="规则引擎判定的当前阶段">
                          {it.state.stage_cn}
                        </span>
                      )}
                      {it.verdict_cn && (
                        <span className={`macro-chip ${verdictTone(it.verdict)}`}>
                          {it.verdict_cn}
                        </span>
                      )}
                    </td>
                    <td className="brief-dims">
                      {it.state?.dimensions
                        ? Object.entries(it.state.dimensions).map(([k, v]) => (
                            <span key={k} className={`brief-dim ${dimTone(v)}`} title={`${k}：${v}`}>
                              {k} {v}
                            </span>
                          ))
                        : "—"}
                    </td>
                    <td className="brief-changes">
                      {it.is_new ? (
                        <span className="macro-chip neutral">首次纳入简报</span>
                      ) : changed ? (
                        it.changes.slice(0, 4).map((ch, i) => (
                          <div key={i} className="brief-change-line">
                            {ch}
                          </div>
                        ))
                      ) : (
                        <span className="muted">无变化</span>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/* ------------------------------------------------------------------ */
/*  ③ 板块观察池（联表 /sectors/trend：当日涨跌 + 涨跌家数 + 距60日线）  */
/* ------------------------------------------------------------------ */

function PoolSection({ pool }: { pool: DailyBriefResponseBrief["pool"] }) {
  // 与行业板块页共享同一 queryKey
  const { data: trendData } = useQuery({
    queryKey: ["sectorsTrend"],
    queryFn: () => sectorsApi.trend(false, "all"),
    staleTime: 5 * 60_000,
  });
  const rowBy = new Map((trendData?.boards ?? []).map((b) => [b.code, b]));

  return (
    <section className="brief-pool-sec brief-sec">
      <div className="brief-sec-head">
        <h2 className="fund-section-title">③ 板块观察池</h2>
        <span className="fund-hint">
          近几日持续登上观察清单的行业板块：
          <InfoTip tip={TIPS.streak}>连续天数</InfoTip> 越长热度越持续，入榜理由见「为什么在榜」
        </span>
      </div>
      {pool.items.length === 0 ? (
        <div className="muted">当前无持续上榜板块</div>
      ) : (
        <div className="fund-table-wrap">
          <table className="event-table fund-table brief-pool-table">
            <thead>
              <tr>
                <th>板块</th>
                <th className="num">当日涨跌</th>
                <th className="num">
                  <InfoTip tip={TIPS.updown}>涨/跌家数</InfoTip>
                </th>
                <th>
                  <InfoTip tip={TIPS.stage}>阶段</InfoTip>
                </th>
                <th className="num">
                  <InfoTip tip={TIPS.streak}>连续在榜</InfoTip>
                </th>
                <th>为什么在榜</th>
                <th className="num">
                  <InfoTip tip={TIPS.rs}>强弱百分位</InfoTip>
                </th>
                <th className="num">
                  <InfoTip tip={TIPS.rsDelta}>20日变化</InfoTip>
                </th>
                <th className="num">
                  <InfoTip tip={TIPS.dist60}>距60日线</InfoTip>
                </th>
                <th className="num">
                  <InfoTip tip={TIPS.flow}>主力资金20日</InfoTip>
                </th>
                <th className="num">
                  <InfoTip tip={TIPS.pe}>市盈率</InfoTip>
                </th>
                <th>下一观察点</th>
              </tr>
            </thead>
            <tbody>
              {pool.items.map((it) => {
                const row = rowBy.get(it.code);
                return (
                  <tr key={it.code}>
                    <td>
                      {it.name ?? it.code} <span className="symbol">{it.code}</span>
                    </td>
                    <td className="num">
                      <PctCell v={row?.pct_change} />
                    </td>
                    <td className="num brief-updn">
                      {row?.up_count != null || row?.down_count != null
                        ? `${row?.up_count ?? "-"} / ${row?.down_count ?? "-"}`
                        : "—"}
                    </td>
                    <td>
                      {it.stage ? (
                        <span className={`brief-stage s-${it.stage}`}>
                          {STAGE_CN[it.stage] ?? it.stage}
                        </span>
                      ) : (
                        <span className="muted">未定</span>
                      )}
                    </td>
                    <td className="num">{it.streak >= 3 ? `🔥${it.streak}天` : `${it.streak}天`}</td>
                    <td className="brief-tags">
                      {it.tags.map((t) => (
                        <span key={t} className="brief-tag">
                          {t}
                        </span>
                      ))}
                    </td>
                    <td className="num">{fmt(it.rs_pctile, 0)}</td>
                    <td className={`num ${(it.rs_pctile_delta_20 ?? 0) > 0 ? "up" : "down"}`}>
                      {it.rs_pctile_delta_20 != null
                        ? `${it.rs_pctile_delta_20 > 0 ? "+" : ""}${it.rs_pctile_delta_20.toFixed(0)}`
                        : "-"}
                    </td>
                    <td className={`num ${(row?.dist_to_sma60_pct ?? 0) >= 0 ? "up" : "down"}`}>
                      {row?.dist_to_sma60_pct != null
                        ? `${row.dist_to_sma60_pct > 0 ? "+" : ""}${row.dist_to_sma60_pct.toFixed(1)}%`
                        : "—"}
                    </td>
                    <td
                      className={`num ${it.flow_20d_main_yi != null && it.flow_20d_main_yi > 0 ? "up" : "down"}`}
                    >
                      {it.flow_20d_main_yi != null ? `${it.flow_20d_main_yi.toFixed(0)}亿` : "—"}
                    </td>
                    <td className="num">
                      {it.pe_ttm == null
                        ? "-"
                        : it.pe_ttm < 0
                          ? "亏损"
                          : it.pe_ttm > 500
                            ? ">500"
                            : it.pe_ttm.toFixed(0)}
                    </td>
                    <td className="brief-next">
                      {(it.next_watch ?? "-").replace(/SMA60/g, "60日线")}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}

/* ------------------------------------------------------------------ */

/* ------------------------------------------------------------------ */
/*  今日机会速览条：系统最关心的一问——有没有值得动手的标的               */
/* ------------------------------------------------------------------ */

function OpportunityStrip({
  wl,
  pool,
  env,
}: {
  wl: DailyBriefResponseBrief["watchlist"];
  pool: DailyBriefResponseBrief["pool"];
  env: DailyBriefResponseBrief["env"];
}) {
  const act = wl.items.filter((it) => it.verdict === "actionable");
  const wait = wl.items.filter((it) => it.verdict === "waiting");
  const nearUpgrade = pool.items.filter((it) => it.tags.includes("临近升级")).length;
  return (
    <div className={`brief-opp-strip${act.length > 0 ? " has-action" : ""}`}>
      <span className="brief-opp-label">
        <InfoTip tip={TIPS.verdict}>今日机会</InfoTip>
      </span>
      {act.length + wait.length === 0 ? (
        <span className="muted">无可操作 / 等待中的自选（今日全部为低档位）</span>
      ) : (
        <>
          {act.map((it) => (
            <Link
              key={it.symbol}
              to={`/symbol/${encodeURIComponent(it.symbol)}`}
              className="brief-opp-chip act"
              title="机会扫描判定：条件满足，可研究入场（非买卖建议）"
            >
              {it.display_name ?? it.symbol} · 可操作
            </Link>
          ))}
          {wait.map((it) => (
            <Link
              key={it.symbol}
              to={`/symbol/${encodeURIComponent(it.symbol)}`}
              className="brief-opp-chip wait"
              title="方向对但条件未齐，等回调/确认"
            >
              {it.display_name ?? it.symbol} · 等待条件
            </Link>
          ))}
        </>
      )}
      <span className="brief-opp-meta">
        自选 {wl.items.length} · 板块观察 {pool.items.length}
        {nearUpgrade > 0 && ` · 板块临近升级 ${nearUpgrade}`} · 环境异常 {env.anomalies.length} 项
      </span>
    </div>
  );
}

/* ------------------------------------------------------------------ */

function BriefBody({ brief }: { brief: DailyBriefResponseBrief }) {
  return (
    <>
      <OpportunityStrip wl={brief.watchlist} pool={brief.pool} env={brief.env} />
      <SummaryBlock brief={brief} />
      <EnvSection env={brief.env} />
      <WatchSection wl={brief.watchlist} />
      <PoolSection pool={brief.pool} />

      <details className="brief-raw">
        <summary>原始文字版（用于复制 / 与飞书推送对照）</summary>
        <pre className="brief-text">{brief.summary.text}</pre>
      </details>

      <div className="legend" style={{ marginTop: 10 }}>
        本页为个人研究参考（research_proxy），不构成买卖建议。所有「主力资金」按单笔成交金额规模推算，是研究代理口径而非真实机构数据；
        盘中版（14:45）生成时未收盘，结论以收盘版（16:45）为准。
      </div>
    </>
  );
}
