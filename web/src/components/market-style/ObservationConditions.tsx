import { useMemo, useState } from "react";
import TrendChart, { type LineSeries } from "./MarketTrendChart";
import "./observation-conditions.css";

export type LocalVolatilityObservation = {
  name: string;
  unit: string;
  dates: string[];
  rv20: (number | null)[];
  rv60: (number | null)[];
  available: boolean;
  latest20?: number;
  latest60?: number;
  observation_date?: string;
  definition: string;
  limitation: string;
  source_url: string;
};

export type NfciObservation = {
  dates: string[];
  values: number[];
  observation_date: string;
  published_at: string;
  verified_at: string;
  source_url: string;
  method_url: string;
  coverage: string;
  reading: string;
};

export type ObservationConditionsProps = {
  volatility?: LocalVolatilityObservation;
  nfci?: NfciObservation;
  loading: boolean;
  error: boolean;
};

const hasNumber = (value: number | null | undefined): value is number =>
  typeof value === "number" && Number.isFinite(value);

export default function ObservationConditions({ volatility, nfci, loading, error }: ObservationConditionsProps) {
  const [showThreeYears, setShowThreeYears] = useState(false);
  const latest20 = volatility?.latest20;
  const latest60 = volatility?.latest60;
  const volatilityValid = !!volatility?.available && volatility.dates.length > 1
    && volatility.dates.length === volatility.rv20.length
    && volatility.dates.length === volatility.rv60.length
    && volatility.rv20.filter(hasNumber).length > 1 && volatility.rv60.filter(hasNumber).length > 1;
  const volatilityView = useMemo(() => {
    if (!volatilityValid || !volatility) return { dates: [] as string[], rv20: [] as (number | null)[], rv60: [] as (number | null)[] };
    const last = volatility.dates[volatility.dates.length - 1];
    const cutoff = showThreeYears ? "" : new Date(Date.parse(`${last}T00:00:00Z`) - 365 * 86400000).toISOString().slice(0, 10);
    const first = volatility.dates.findIndex((date) => date >= cutoff);
    const start = first < 0 ? 0 : first;
    return { dates: volatility.dates.slice(start), rv20: volatility.rv20.slice(start), rv60: volatility.rv60.slice(start) };
  }, [volatility, volatilityValid, showThreeYears]);
  const volatilitySeries = useMemo<LineSeries[]>(() => [
    { name: "20日", values: volatilityView.rv20, color: "#476f9d" },
    { name: "60日", values: volatilityView.rv60, color: "#9c7655" },
  ], [volatilityView]);
  const nfciValid = !!nfci && nfci.dates.length === 5 && nfci.values.length === 5
    && nfci.dates[0] === "2026-09-11" && nfci.dates[4] === "2026-10-09"
    && nfci.values.every(hasNumber);
  const nfciSeries = useMemo<LineSeries[]>(() => [
    { name: "NFCI", values: nfciValid ? nfci!.values : [], color: "#647d99" },
  ], [nfci, nfciValid]);

  return <section className="observation-conditions" aria-labelledby="observation-conditions-title">
    <header className="oc-header">
      <h2 id="observation-conditions-title">本地波动与美国金融条件</h2>
      <p>分别看市场实际起伏和美国资金环境；资料日期各按原来源标明。</p>
    </header>
    {error && <p className="oc-fetch-error" role="alert">资料请求失败；下方仅展示已收到且可核的内容，缺项暂不判断。</p>}
    <div className="oc-grid">
      <article className="oc-card">
        <header className="oc-card-head">
          <div><h3>{volatility?.name ?? "本地指数已实现波动"}</h3><p>过去20／60个交易日的涨跌起伏，按年表示</p></div>
          <div className="oc-window" role="group" aria-label="本地波动曲线范围">
            <button type="button" aria-pressed={!showThreeYears} onClick={() => setShowThreeYears(false)}>近1年</button>
            <button type="button" aria-pressed={showThreeYears} onClick={() => setShowThreeYears(true)}>全3年</button>
          </div>
        </header>
        {volatilityValid ? <>
          <p className="oc-current">20日 <b>{hasNumber(latest20) ? latest20.toFixed(2) : "—"}</b> · 60日 <b>{hasNumber(latest60) ? latest60.toFixed(2) : "—"}</b> {volatility?.unit} <small>数据截至 {volatility?.observation_date ?? volatilityView.dates[volatilityView.dates.length - 1]}</small></p>
          <TrendChart dates={volatilityView.dates} series={volatilitySeries} unit={volatility?.unit ?? ""} height={220} />
          <p className="oc-range">图中日期 {volatilityView.dates[0]}—{volatilityView.dates[volatilityView.dates.length - 1]} · 20／60日年化波动</p>
        </> : <p className="oc-empty">{loading ? "本地波动资料加载中" : error ? "本地波动资料读取失败" : "本地波动资料不足，暂不画曲线"}</p>}
        <details className="oc-details"><summary>口径与来源</summary>
          <p>{volatility?.definition ?? "20日和60日数值由系统按指数收益计算。"}</p>
          {volatility?.limitation && <p>{volatility.limitation}</p>}
          {volatility?.source_url && <p><a href={volatility.source_url} target="_blank" rel="noreferrer">查看指数资料来源 ↗</a></p>}
        </details>
      </article>

      <article className="oc-card">
        <header className="oc-card-head"><div><h3>NFCI · 美国金融条件</h3><p>数值上升表示资金环境向偏紧方向移动</p></div></header>
        <p className="oc-range oc-range-lead">5周已核快照 · 2026-09-11—2026-10-09<br />完整历史及自动更新未接通</p>
        {nfciValid ? <>
          <p className="oc-current">最新 <b>{nfci!.values[4].toFixed(3)}</b> <small>数据截至 {nfci!.observation_date} · 发布日 {nfci!.published_at.slice(0, 10)}（UTC）</small></p>
          <TrendChart dates={nfci!.dates} series={nfciSeries} unit="" height={220} />
          <p className="oc-range">仍为负值表示相对长期平均偏宽松；这条线不提供买卖指令。</p>
        </> : <p className="oc-empty">{loading ? "NFCI已核快照加载中" : error ? "NFCI资料读取失败" : "五周资料缺失或范围不符，暂不画曲线"}</p>}
        <details className="oc-details"><summary>读法与来源</summary>
          {nfci?.reading && <p>{nfci.reading}</p>}
          {nfci?.coverage && <p>覆盖：{nfci.coverage}</p>}
          {nfci?.verified_at && <p>核验：{nfci.verified_at}</p>}
          {nfci?.source_url && <p><a href={nfci.source_url} target="_blank" rel="noreferrer">FRED · 芝加哥联储数据 ↗</a></p>}
          {nfci?.method_url && <p><a href={nfci.method_url} target="_blank" rel="noreferrer">官方方法说明 ↗</a></p>}
        </details>
      </article>
    </div>
  </section>;
}
