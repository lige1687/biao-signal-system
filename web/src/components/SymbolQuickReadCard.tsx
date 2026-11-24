import type { Assessment, ChartPayload, Metric, TodayOverview } from "../types";
import type { Selection } from "./ExplanationPanel";
import { computeTrendChecklist } from "./TrendChecklist";

interface Props {
  assessment: Assessment;
  today: TodayOverview | null;
  chart: ChartPayload;
  onPickConcept: (conceptKey: string, sourceCn: string) => void;
  onSelect: (selection: Selection) => void;
}

function findMetric(list: Metric[] | undefined, key: string): Metric | undefined {
  return list?.find((m) => m.key === key);
}

function fmtMetric(m: Metric | undefined): string {
  if (!m) return "—";
  if (m.text) return m.text;
  if (m.value == null || !Number.isFinite(m.value)) return "—";
  const sign = m.unit === "%" && m.value > 0 ? "+" : "";
  return `${sign}${m.value.toFixed(2)}${m.unit}`;
}

function lastNonNull(arr: (number | null)[] | undefined): number | null {
  if (!arr) return null;
  for (let i = arr.length - 1; i >= 0; i--) {
    const v = arr[i];
    if (v != null && Number.isFinite(v)) return v;
  }
  return null;
}

function fmtDist(target: number | null, current: number | null): string {
  if (target == null || current == null || current <= 0) return "—";
  const pct = ((target / current) - 1) * 100;
  return `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`;
}

type LevelAnchor = {
  key: string;
  label: string;
  price: number;
  tone: "support" | "cost" | "threshold" | "resistance" | "current";
  conceptKey?: string;
  conceptTitle?: string;
  hint: string;
};

/**
 * K 线下方决策速览卡（重构版）：
 * 去掉与顶栏/K线重复的基础数抄写，聚焦看盘人最关心的 3 个问题：
 * 1) 一句话行动结论（退出提醒 > 买点机会 > 当前局面与等待条件）
 * 2) 可视化关键价位标尺（前低底线 / 现价 / 20日成本 / 抵扣门槛 / 前高阻力，一眼看空间赔率）
 * 3) 五步转折进度灯（前2步系统判定 + 后3步MACD强度参考）
 */
export default function SymbolQuickReadCard({
  assessment: a,
  today,
  chart,
  onPickConcept,
  onSelect,
}: Props) {
  const conds = computeTrendChecklist(chart, a);
  const weeklyTrend = findMetric(today?.technical, "weekly_long_trend");
  const dailyTrend = findMetric(today?.technical, "daily_long_trend");
  const distEma60 = findMetric(today?.technical, "dist_ema60");
  const atrPct = findMetric(today?.technical, "atr14_pct");
  const volRatio = findMetric(today?.volume, "vol_ratio20");
  const distC = findMetric(today?.signal, "dist_c");
  const distB1 = findMetric(today?.signal, "dist_b1");

  const activeExits = a.exit_signals.filter((e) => e.state === "active");
  const activeOpps = a.trade_opportunities.slice(0, 2);
  const activePullbacks = a.pullback_opportunities.slice(0, 2);
  const hasConfirmedOpp = activeOpps.some((o) => o.current_conditions_confirmed) || activePullbacks.length > 0;

  // ── 1) 一句话行动结论 ──
  const verdictTone: "danger" | "opportunity" | "warn" | "neutral" =
    activeExits.length > 0
      ? "danger"
      : hasConfirmedOpp
        ? "opportunity"
        : a.tradability && !a.tradability.tradable
          ? "warn"
          : "neutral";

  const verdictHeadline =
    activeExits.length > 0
      ? `触发退出提醒：${activeExits[0].rule_cn}`
      : hasConfirmedOpp
        ? `观察机会成立：${activeOpps[0]?.structure.structure_type_cn ?? `首次回撤 ${activePullbacks[0]?.ma_name}`}`
        : a.tradability && !a.tradability.tradable
          ? `暂不宜追 · ${a.tradability.trend_type_cn || a.opportunity_stage_cn}`
          : a.tradability?.trend_type_cn ?? a.opportunity_stage_cn;

  const verdictSub =
    activeExits.length > 0
      ? activeExits[0].reason_cn || "收盘跌破 20 日均线与抵扣价"
      : a.tradability && !a.tradability.tradable && a.tradability.blocking_reasons[0]
        ? a.tradability.blocking_reasons[0]
        : a.stage_change_reason_cn || "当前无成立买点，等待趋势走顺或新底部确认";

  // ── 2) 可视化关键价位标尺（只取后端既有价格，不新算规则） ──
  const currentPrice = chart.lastClose ?? (chart.ohlc.length ? chart.ohlc[chart.ohlc.length - 1][1] : null);
  const ema20Price = lastNonNull(chart.ema20);
  const ref20Price = lastNonNull(chart.ref20);
  const cLinePrice = chart.bottomLines.length ? chart.bottomLines[chart.bottomLines.length - 1].yAxis : null;
  const b1LinePrice = chart.b1Line?.yAxis ?? null;

  const anchors: LevelAnchor[] = [];
  if (cLinePrice != null && Number.isFinite(cLinePrice)) {
    anchors.push({
      key: "c",
      label: "前低底线",
      price: cLinePrice,
      tone: "support",
      conceptKey: "c_point",
      conceptTitle: "速览 · 阶段前低跌破位",
      hint: distC?.hint_cn || "跌破该前低支撑位，原底部结构失效",
    });
  }
  if (ema20Price != null) {
    anchors.push({
      key: "ema20",
      label: "20日线",
      price: ema20Price,
      tone: "cost",
      conceptKey: "bias",
      conceptTitle: "速览 · 20日均线位置",
      hint: "20 日指数均线（短期趋势与成本分界）",
    });
  }
  if (ref20Price != null) {
    anchors.push({
      key: "ref20",
      label: "20日抵扣",
      price: ref20Price,
      tone: "threshold",
      conceptKey: "ref20",
      conceptTitle: "速览 · 20日抵扣价",
      hint: "收盘高于该价位时，20 日均线方向继续向上；低于则承压",
    });
  }
  if (b1LinePrice != null && Number.isFinite(b1LinePrice)) {
    anchors.push({
      key: "b1",
      label: "前高阻力",
      price: b1LinePrice,
      tone: "resistance",
      conceptKey: "b1",
      conceptTitle: "速览 · 上方前高阻力",
      hint: distB1?.hint_cn || "上方近期前高阻力位",
    });
  }
  if (currentPrice != null && Number.isFinite(currentPrice)) {
    anchors.push({
      key: "now",
      label: "现价",
      price: currentPrice,
      tone: "current",
      hint: `最新收盘价 ${currentPrice.toFixed(2)}`,
    });
  }

  const sortedAnchors = [...anchors].sort((x, y) => x.price - y.price);
  const minP = sortedAnchors.length ? sortedAnchors[0].price : 0;
  const maxP = sortedAnchors.length ? sortedAnchors[sortedAnchors.length - 1].price : 1;
  const spanP = maxP - minP;
  const posPct = (p: number) =>
    spanP > 1e-6 ? 4 + ((p - minP) / spanP) * 92 : 50;

  return (
    <section className="panel sqr-card sqr-v2" aria-label="当前标的决策速览">
      <div className="sqr-head">
        <div className="sqr-head-left">
          <h3>决策速览</h3>
          <span className="sqr-date">判定日 {a.as_of}</span>
          <div className="sqr-context-chips">
            {weeklyTrend && weeklyTrend.text !== "数据不足" && (
              <button
                type="button"
                className={`sqr-meta-chip tone-${weeklyTrend.tone ?? "neutral"}`}
                onClick={() => onPickConcept("long_trend", "速览 · 周线大方向")}
                title={weeklyTrend.hint_cn || "点击查看周线趋势说明"}
              >
                周线 {fmtMetric(weeklyTrend)}
              </button>
            )}
            {dailyTrend && (
              <button
                type="button"
                className={`sqr-meta-chip tone-${dailyTrend.tone ?? "neutral"}`}
                onClick={() => onPickConcept("long_trend", "速览 · 日线中长趋势")}
                title={dailyTrend.hint_cn || "点击查看日线趋势说明"}
              >
                日线 {fmtMetric(dailyTrend)}
              </button>
            )}
            <span className="sqr-meta-chip" title="相对 60 日均线偏离">
              60日线 {fmtMetric(distEma60)}
            </span>
            <span className="sqr-meta-chip" title="日均真实波幅占比">
              日均波动 {fmtMetric(atrPct)}
            </span>
            <span className="sqr-meta-chip" title="相对 20 日均量倍数">
              量能 {fmtMetric(volRatio)}
            </span>
            <span className="sqr-meta-chip" title="EMA20 与 SMA20 是否协同向上">
              双20同向：{a.joint_confirmed_now ? "是" : "否"}
            </span>
          </div>
        </div>
      </div>

      {/* ① 一句话行动结论 + 可点击触发项 */}
      <div className={`sqr-verdict is-${verdictTone}`}>
        <div className="sqr-verdict-main">
          <strong>{verdictHeadline}</strong>
          <span>{verdictSub}</span>
        </div>
        {(activeExits.length > 0 || activeOpps.length > 0 || activePullbacks.length > 0) && (
          <div className="sqr-verdict-actions">
            {activeExits.map((ex) => (
              <button
                key={ex.rule_id}
                type="button"
                className="sqr-opp-btn exit-active"
                onClick={() =>
                  onSelect({
                    source: "速览 · 持仓退出",
                    date: ex.last_trigger_date ?? undefined,
                    explanation: ex.explanation,
                    events: ex.supporting_event ? [ex.supporting_event] : [],
                    eventsLoading: false,
                  })
                }
              >
                查看退出依据：{ex.rule_cn} →
              </button>
            ))}
            {activeOpps.map((o) => (
              <button
                key={o.lifecycle_id}
                type="button"
                className="sqr-opp-btn"
                onClick={() =>
                  onSelect({
                    source: "速览 · 买点提醒",
                    date: o.last_upgraded_on,
                    price: o.structure.c_price ?? undefined,
                    explanation: o.explanation,
                    structure: o.structure,
                    events: o.supporting_event ? [o.supporting_event] : [],
                    eventsLoading: false,
                  })
                }
              >
                <b>{o.structure.structure_type_cn}</b> · {o.state_cn}（
                {o.current_conditions_confirmed ? "条件成立" : o.missing_conditions[0] ?? "待补齐"}）
              </button>
            ))}
            {activePullbacks.map((p) => (
              <button
                key={p.lifecycle_id}
                type="button"
                className="sqr-opp-btn"
                onClick={() =>
                  onSelect({
                    source: "速览 · 首次回撤",
                    date: p.latest_date,
                    price: p.ma_value,
                    explanation: p.explanation,
                    events: p.supporting_event ? [p.supporting_event] : [],
                    eventsLoading: false,
                  })
                }
              >
                <b>首次回撤 {p.ma_name}</b> · {p.state_cn}（{p.next_step_cn}）
              </button>
            ))}
          </div>
        )}
      </div>

      <div className="sqr-lower-grid">
        {/* ② 可视化关键价位标尺（向下防守 vs 向上空间） */}
        <div className="sqr-block">
          <div className="sqr-block-head">
            <span className="sqr-block-title">关键价位标尺</span>
            <span className="sqr-block-hint">向下防守位 · 均线/抵扣门槛 · 上方阻力</span>
          </div>
          {sortedAnchors.length >= 2 && (
            <div className="sqr-ruler" aria-label="关键价位空间标尺">
              <div className="sqr-ruler-track">
                {sortedAnchors.map((anc) => (
                  <span
                    key={anc.key}
                    className={`sqr-ruler-dot is-${anc.tone}`}
                    style={{ left: `${posPct(anc.price).toFixed(1)}%` }}
                    title={`${anc.label} ${anc.price.toFixed(2)}（${anc.key === "now" ? "最新收盘" : `距现价 ${fmtDist(anc.price, currentPrice)}`}）\n${anc.hint}`}
                  />
                ))}
              </div>
              <div className="sqr-level-cards">
                {[
                  {
                    key: "c",
                    label: "前低底线",
                    price: cLinePrice,
                    tone: "support",
                    conceptKey: "c_point",
                    conceptTitle: "速览 · 阶段前低跌破位",
                    empty: "看均线",
                    hint: distC?.hint_cn || "跌破前低则原底部形态失效",
                  },
                  {
                    key: "ema20",
                    label: "20日成本线",
                    price: ema20Price,
                    tone: "cost",
                    conceptKey: "bias",
                    conceptTitle: "速览 · 均线偏离",
                    empty: "—",
                    hint: "短期趋势与平均成本分界",
                  },
                  {
                    key: "ref20",
                    label: "20日抵扣门槛",
                    price: ref20Price,
                    tone: "threshold",
                    conceptKey: "ref20",
                    conceptTitle: "速览 · 20日抵扣价",
                    empty: "—",
                    hint: "站上该价位，20 日均线方向向上",
                  },
                  {
                    key: "b1",
                    label: "前高阻力",
                    price: b1LinePrice,
                    tone: "resistance",
                    conceptKey: "b1",
                    conceptTitle: "速览 · 上方前高阻力",
                    empty: "无邻近",
                    hint: distB1?.hint_cn || "上方近期前高阻力位",
                  },
                ].map((lv) => (
                  <button
                    key={lv.key}
                    type="button"
                    className={`sqr-level-card is-${lv.tone}${lv.price == null ? " is-empty" : ""}`}
                    onClick={() => onPickConcept(lv.conceptKey, lv.conceptTitle)}
                    title={lv.hint}
                  >
                    <span className="sqr-lv-k">{lv.label}</span>
                    <b className="sqr-lv-p">{lv.price != null ? lv.price.toFixed(2) : lv.empty}</b>
                    <small className="sqr-lv-d">
                      {lv.price != null ? fmtDist(lv.price, currentPrice) : "—"}
                    </small>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ③ 五步转折进度灯 */}
        <div className="sqr-block">
          <div className="sqr-block-head">
            <span className="sqr-block-title">五步转折进度</span>
            <span className="sqr-block-hint">①② 系统破线拐头 · ③④⑤ MACD 强度佐证</span>
          </div>
          <div className="sqr-five-grid" aria-label="趋势五步进度">
            {conds.map((c, idx) => (
              <div
                key={c.key}
                className={`sqr-five-step is-${c.stance}`}
                title={`${c.name}：${c.status}${c.detail ? `（${c.detail}）` : ""}${c.proxy ? " · 研究代理，仅看强弱" : ""}`}
              >
                <div className="sqr-five-top">
                  <i>{idx + 1}</i>
                  <span>{c.name}</span>
                </div>
                <b className="sqr-five-status">{c.status}</b>
              </div>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
}
