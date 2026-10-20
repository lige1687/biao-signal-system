import { useState } from "react";
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
      <span>当前回撤 <b>缺资料</b> <small>这份月末事实表未提供可计算的近期净值序列</small></span>
    </div>
    <div className="style-detail-valuation" aria-label="月末估值与股息率">
      <span>市盈率 <b>{style.pe.toFixed(2)}</b> <small>母指数 {parent.pe.toFixed(2)}</small></span>
      <span>市净率 <b>{style.pb.toFixed(2)}</b> <small>母指数 {parent.pb.toFixed(2)}</small></span>
      <span>股息率 <b>{pct(style.dividendYieldPct)}</b> <small>母指数 {pct(parent.dividendYieldPct)}</small></span>
    </div>
    <p className="style-detail-context">{STYLE_RISK_BASIS}，数值越大表示涨跌起伏越大。估值是当期数据，不能据此说历史上处于便宜位置。{style.note ? ` ${style.note}` : ""}</p>
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

export default function StyleComparison() {
  const [period, setPeriod] = useState<StylePeriod>("threeMonths");
  const [selectedId, setSelectedId] = useState<StyleSnapshot["id"] | null>(null);
  const selected = STYLE_SNAPSHOTS.find((style) => style.id === selectedId);
  const scale = Math.max(...STYLE_SNAPSHOTS.map((style) => Math.abs(style.returnsPct[period] - WORLD_PARENT.returnsPct[period])));

  return <section className="style-comparison" aria-labelledby="style-comparison-title">
    <div className="style-comparison-head">
      <div>
        <h2 id="style-comparison-title">全球风格对比</h2>
        <p>发达市场 · MSCI World 母指数 · 美元，含股息再投<br />月末资料：{STYLE_SNAPSHOT_DATE}</p>
      </div>
      <div className="style-periods" role="group" aria-label="选择收益期间">
        {PERIODS.map((item) => <button key={item.id} type="button" className={period === item.id ? "is-active" : ""} aria-pressed={period === item.id} onClick={() => setPeriod(item.id)}>{item.label}</button>)}
      </div>
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
  </section>;
}
