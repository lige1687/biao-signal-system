import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import DailyStyleChart from "./DailyStyleChart";
import { buildStyleWealthHistory, STYLE_HISTORY_BASE_DATE, STYLE_HISTORY_SOURCE_DATE, STYLE_HISTORY_SOURCES, STYLE_HISTORY_IDS, type HistoryStyleId } from "./styleHistory";
import {
  SECTOR_ORDER, STYLE_RISK_BASIS, STYLE_SNAPSHOT_DATE,
  STYLE_SNAPSHOTS, WORLD_PARENT,
  type StylePeriod, type StyleSnapshot,
} from "./styleSnapshot";
import "./style-comparison.css";

const PERIODS: { id: StylePeriod; label: string }[] = [
  { id: "oneMonth", label: "1个月" },
  { id: "threeMonths", label: "3个月" },
  { id: "ytd", label: "年初至今" },
  { id: "oneYear", label: "1年" },
];

type ChartMode = "wealth" | "relative";
const CHART_STYLES: Record<HistoryStyleId, { name: string; color: string }> = {
  momentum: { name: "动量", color: "#dc6f36" },
  quality: { name: "质量", color: "#286db5" },
  value: { name: "价值", color: "#8c5ba8" },
  minimumVolatility: { name: "最小波动", color: "#369781" },
  world: { name: "MSCI World", color: "#657383" },
};

function StyleHistoryChart({ mode }: { mode: ChartMode }) {
  const ref = useRef<HTMLDivElement>(null);
  const points = useMemo(buildStyleWealthHistory, []);

  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current, undefined, { renderer: "svg" });
    const resize = new ResizeObserver(() => chart.resize());
    resize.observe(ref.current);
    return () => { resize.disconnect(); chart.dispose(); };
  }, []);

  useEffect(() => {
    const element = ref.current;
    if (!element) return;
    const chart = echarts.getInstanceByDom(element);
    if (!chart) return;
    const series: echarts.LineSeriesOption[] = STYLE_HISTORY_IDS.map((id) => ({
      name: CHART_STYLES[id].name,
      type: "line",
      data: points.map((point) => mode === "wealth" ? point[id] : point[id] / point.world * 100),
      showSymbol: true,
      symbol: "circle",
      symbolSize: id === "world" ? 5 : 6,
      smooth: false,
      connectNulls: false,
      lineStyle: { width: id === "world" ? 1.5 : 2.2, color: CHART_STYLES[id].color, type: id === "world" && mode === "relative" ? "dashed" : "solid" },
      itemStyle: { color: CHART_STYLES[id].color },
      emphasis: { focus: "series" },
    }));
    chart.setOption({
      animation: false,
      color: STYLE_HISTORY_IDS.map((id) => CHART_STYLES[id].color),
      tooltip: {
        trigger: "axis",
        confine: true,
        valueFormatter: (value: unknown) => value == null ? "—" : `${Number(value).toFixed(1)}（${mode === "wealth" ? "起点100" : "相对价值比"}）`,
      },
      legend: { top: 0, type: "plain", textStyle: { fontSize: 12, color: "#344256" }, data: STYLE_HISTORY_IDS.map((id) => CHART_STYLES[id].name) },
      grid: { left: 40, right: 42, top: 66, bottom: 36, containLabel: true },
      xAxis: {
        type: "category",
        data: points.map((point) => point.date),
        boundaryGap: false,
        axisLabel: { color: "#344256", fontSize: 12, hideOverlap: true, showMinLabel: true, showMaxLabel: true, formatter: (date: string) => date === "2026-09-30" ? "2026·9月" : date.slice(0, 4) },
      },
      yAxis: { type: "value", scale: true, name: mode === "wealth" ? "累计价值（起点=100）" : "相对价值比（起点=100）", nameTextStyle: { color: "#344256", fontSize: 12, align: "left" }, axisLabel: { color: "#344256", fontSize: 12 }, splitLine: { lineStyle: { color: "#e2e8f0", width: 1 } } },
      series,
    }, true);
  }, [mode, points]);

  return <div ref={ref} className="style-history-chart" role="img" aria-label={mode === "wealth" ? "四类风格与 MSCI World 的年度累计价值曲线" : "四类风格相对 MSCI World 的年度价值比曲线"} />;
}

const HOLDING_NAMES: Record<string, string> = {
  "Micron Technology": "美光", "Advanced Micro Devices": "AMD", "Intel Corp": "英特尔",
  "ASML Hldg": "阿斯麦", "Alphabet A": "Alphabet A（谷歌母公司）",
  "Alphabet C": "Alphabet C（谷歌母公司）", "Johnson & Johnson": "强生",
  "ExxonMobil Holdings": "埃克森美孚", "Lam Research Corp": "拉姆研究",
  "Applied Materials": "应用材料", "Microsoft Corp": "微软", "Meta Platforms A": "Meta",
  "Apple": "苹果", "Nvidia": "英伟达", "Broadcom": "博通", "Lilly (Eli) & Company": "礼来",
  "Visa A": "Visa", "JPMorgan Chase & Co": "摩根大通", "Berkshire Hathaway B": "伯克希尔 B",
  "AbbVie": "艾伯维", "Cisco Systems": "思科", "Duke Energy Corp": "杜克能源",
  "Motorola Solutions": "摩托罗拉解决方案", "Southern Company (The)": "南方电力", "AT&T": "AT&T",
};

function pct(value: number, signed = false) {
  return `${signed && value > 0 ? "+" : ""}${value.toFixed(2)}%`;
}

function signedPoints(value: number) {
  return `${value > 0 ? "+" : ""}${value.toFixed(2)} 个百分点`;
}

function directionClass(value: number) {
  return value > 0 ? "is-positive" : value < 0 ? "is-negative" : "is-zero";
}

function DifferenceBar({ difference, scale }: { difference: number; scale: number }) {
  const width = scale > 0 ? Math.min(50, Math.abs(difference) / scale * 50) : 0;
  return <span className={`style-difference ${directionClass(difference)}`}>
    <span className="style-difference-track" aria-hidden="true">
      <span className="style-difference-zero" />
      <span className="style-difference-fill" style={{ width: `${width}%`, left: difference < 0 ? `${50 - width}%` : "50%" }} />
    </span>
    <span className="style-difference-number">{signedPoints(difference)}</span>
  </span>;
}

function ComparisonDetail({ style, period }: { style: StyleSnapshot; period: StylePeriod }) {
  const parent = WORLD_PARENT;
  return <div className="style-detail" id={`style-detail-${style.id}`}>
    <div className="style-detail-head">
      <div><strong>{style.name}</strong><span>{style.officialName}</span></div>
      <a href={style.sourceUrl} target="_blank" rel="noopener noreferrer">查看 MSCI 官方事实表 ↗</a>
    </div>
    <div className="style-detail-figures">
      <span>所选期间收益 <b className={directionClass(style.returnsPct[period])}>{pct(style.returnsPct[period], true)}</b> <small>母指数 {pct(parent.returnsPct[period], true)}</small></span>
      <span>近3年年化波动 <b>{pct(style.threeYearAnnualizedVolPct)}</b> <small>母指数 {pct(parent.threeYearAnnualizedVolPct)}</small></span>
      <span>近期离高点跌幅 <b>见日线五问</b> <small>上方按近1年内高点计算；这里保留月末事实表口径</small></span>
      <span>历史最深下跌 <b>−{pct(style.historicalMaximumDrawdown.lossPct)}</b> <small>{style.historicalMaximumDrawdown.peakDate} 至 {style.historicalMaximumDrawdown.troughDate}；官方统计范围 {style.historicalMaximumDrawdown.observationStartDate} 至 {style.historicalMaximumDrawdown.observationEndDate}</small></span>
    </div>
    <div className="style-detail-valuation" aria-label="月末估值与股息率">
      <span>市盈率 <b>{style.pe.toFixed(2)}</b> <small>母指数 {parent.pe.toFixed(2)}</small></span>
      <span>市净率 <b>{style.pb.toFixed(2)}</b> <small>母指数 {parent.pb.toFixed(2)}</small></span>
      <span>股息率 <b>{pct(style.dividendYieldPct)}</b> <small>母指数 {pct(parent.dividendYieldPct)}</small></span>
    </div>
    <p className="style-detail-context">{STYLE_RISK_BASIS}，数值越大表示涨跌起伏越大。历史最深下跌来自官方事实表，各指数统计起点不同，部分跌幅发生在指数正式发布前；它不代表当前跌幅。估值是当期数据，不能据此说历史上处于便宜位置。{style.note ? ` ${style.note}` : ""}</p>
    <div className="style-detail-groups">
      <details>
        <summary>行业权重 · {STYLE_SNAPSHOT_DATE}</summary>
        <div className="style-detail-list">
          {SECTOR_ORDER.map((sector) => <div key={sector}><span>{sector}</span><b>{style.sectorWeightsPct[sector] == null ? "未列示" : pct(style.sectorWeightsPct[sector])}</b></div>)}
        </div>
        <p>这是当前配置权重，不能用来解释过去的收益贡献。</p>
      </details>
      <details>
        <summary>前十大持仓 · 合计 {pct(style.topTenTotalPct)}</summary>
        <div className="style-detail-list">
          {style.topTen.map((holding) => <div key={holding.name}><span title={holding.name}>{HOLDING_NAMES[holding.name] ?? holding.name}</span><b>{pct(holding.weightPct)}</b></div>)}
        </div>
        <p>这是当前持仓快照，不代表过去各股票带来的收益。合计沿用官方值，单项四舍五入后可能略有差异。</p>
      </details>
    </div>
    <p className="style-detail-source">收益以美元计算，含股息再投资，未扣预提税和实际投资费用。指数发布于 {style.launchDate}；发布前历史为事后计算。以上为月末阅读样例，持续取数与展示许可尚未核实。</p>
  </div>;
}

export default function StyleComparison({ onBasisChange }: { onBasisChange?: (basis: string) => void }) {
  const [period, setPeriod] = useState<StylePeriod>("threeMonths");
  const [chartMode, setChartMode] = useState<ChartMode>("relative");
  const [annualOpen, setAnnualOpen] = useState(false);
  const [selectedId, setSelectedId] = useState<StyleSnapshot["id"] | null>(null);
  const selected = STYLE_SNAPSHOTS.find((style) => style.id === selectedId);
  const scale = Math.max(...STYLE_SNAPSHOTS.map((style) => Math.abs(style.returnsPct[period] - WORLD_PARENT.returnsPct[period])));

  return <section className="style-comparison" aria-labelledby="style-comparison-title">
    <div className="style-comparison-head">
      <div>
        <h2 id="style-comparison-title">全球风格对比</h2>
        <p>MSCI World 的四种全球股票风格 · 美元，含股息再投资<br />主图为日收盘；行业与估值快照另按月末标日</p>
      </div>
    </div>
    <DailyStyleChart onBasisChange={onBasisChange} />
    <details className="style-period-details" onToggle={event => setAnnualOpen(event.currentTarget.open)}><summary>长期年度参考 · {STYLE_HISTORY_BASE_DATE} — {STYLE_HISTORY_SOURCE_DATE}</summary>
    <div className="style-history-header">
      <div>
        <h3>{chartMode === "relative" ? "相对 MSCI World，哪类风格走在前面？" : "同一笔起始金额，逐年走到哪里？"}</h3>
        <p>{chartMode === "relative" ? "向上表示该段跑赢母指数；高于100表示从2013年末起累计领先。" : "统一把2013年末设为100；向上表示自身赚钱，向下表示自身亏损。"}</p>
      </div>
      <div className="style-chart-modes" role="group" aria-label="切换图表视角">
        <button type="button" className={chartMode === "relative" ? "is-active" : ""} aria-pressed={chartMode === "relative"} onClick={() => setChartMode("relative")}>相对母指数</button>
        <button type="button" className={chartMode === "wealth" ? "is-active" : ""} aria-pressed={chartMode === "wealth"} onClick={() => setChartMode("wealth")}>累计路径</button>
      </div>
    </div>
    {annualOpen && <StyleHistoryChart mode={chartMode} />}
    <p className="style-history-note">此折叠参考仅为年度点，最后一点为2026年前9月收益；近期变化请看上方日线。</p>
    <details className="style-history-method">
      <summary>数据口径与官方来源</summary>
      <p>这里看各风格的相对强弱；动量本身是其中一种选股方法，偏向过去价格较强的股票。质量看盈利能力、盈利稳定性与低杠杆；价值看价格相对账面价值、预期盈利和股息；最小波动在约束下优化整个组合的波动。</p>
      <p>起点 {STYLE_HISTORY_BASE_DATE} 人为设为100；其后按官方公布的年度收益连乘，近似路径受收益四舍五入影响。2014—2025为完整年度，各指数均在此前正式发布；2026末点只到9月。美元毛总回报含股息再投资，未扣实际产品费用和税。相对曲线 = 风格累计价值 ÷ 母指数累计价值 × 100；不是百分比收益率。</p>
      <p>官方事实表：<a href={STYLE_HISTORY_SOURCES.momentum} target="_blank" rel="noopener noreferrer">动量 ↗</a> · <a href={STYLE_HISTORY_SOURCES.quality} target="_blank" rel="noopener noreferrer">质量 ↗</a> · <a href={STYLE_HISTORY_SOURCES.value} target="_blank" rel="noopener noreferrer">价值 ↗</a> · <a href={STYLE_HISTORY_SOURCES.minimumVolatility} target="_blank" rel="noopener noreferrer">最小波动 ↗</a>。这是固定资料阅读样例，不随市场视图切换；持续取数及展示许可尚待核实。</p>
    </details>
    </details>
    <details className="style-period-details">
      <summary>月末资料 · {STYLE_SNAPSHOT_DATE} · 收益、估值、行业与前十大持仓</summary>
      <div className="style-periods" role="group" aria-label="选择收益期间">
        {PERIODS.map((item) => <button key={item.id} type="button" className={period === item.id ? "is-active" : ""} aria-pressed={period === item.id} onClick={() => setPeriod(item.id)}>{item.label}</button>)}
      </div>
    <div className="style-table" role="table" aria-label="四类全球风格与 MSCI World 收益对比">
      <div className="style-table-header" role="row">
        <span role="columnheader">风格</span><span role="columnheader">自身收益</span><span role="columnheader">较母指数差额</span>
      </div>
      {STYLE_SNAPSHOTS.map((style) => {
        const difference = style.returnsPct[period] - WORLD_PARENT.returnsPct[period];
        const active = selectedId === style.id;
        return <div key={style.id} className={`style-table-row ${active ? "is-selected" : ""}`} role="row">
          <span role="cell"><button type="button" aria-expanded={active} aria-controls={`style-detail-${style.id}`} onClick={() => setSelectedId(active ? null : style.id)}>{style.name}<span aria-hidden="true">{active ? "收起" : "查看详情"}</span></button></span>
          <span role="cell" className={`style-return ${directionClass(style.returnsPct[period])}`}>{pct(style.returnsPct[period], true)}</span>
          <span role="cell"><DifferenceBar difference={difference} scale={scale} /></span>
        </div>;
      })}
    </div>
    <p className="style-parent-note">同期母指数收益 {pct(WORLD_PARENT.returnsPct[period], true)}；差额单位为百分点。此表固定为全球指数资料，不随 A 股或美股视图切换。</p>
    {selected && <ComparisonDetail style={selected} period={period} />}
    </details>
  </section>;
}
