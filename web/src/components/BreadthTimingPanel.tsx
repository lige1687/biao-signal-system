import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import { timingBacktestApi } from "../api/client";
import type { TimingOptions, TimingRunResult, TimingRunSummary, TimingSignal } from "../types";

/**
 * 宽度择时回测面板（B20/B50/B200 → 阶梯/极值反转/趋势闸门）。
 *
 * 用户视角：选标的（自动配对宽度）→ 选策略与分批参数 → 一键回测 →
 * 看年化 vs 买入持有、超额、回撤、逐年表、净值曲线与仓位叠加图；
 * 历史运行可勾选（≤5 条）叠加净值曲线对比不同分批效果。
 * 数据诚实声明（幸存者偏差等）常驻页面底部。
 */

const STRATEGY_CN: Record<string, string> = { ladder: "阶梯分批", reversal: "极值反转" };
const GATE_CN: Record<string, string> = { off: "关闭", ma200: "MA200 闸门" };
const DIRECTION_CN: Record<string, string> = { contrarian: "逆势(低宽高仓)", momentum: "顺势(高宽高仓)" };
const BATCH_CN: Record<string, string> = { time: "时间均分(N日每日一批)", band: "档位跟随(每10宽度点一批)" };

function pct(v: number | null | undefined, digits = 1): string {
  if (v == null || Number.isNaN(v)) return "—";
  return `${(v * 100).toFixed(digits)}%`;
}

function num(v: number | null | undefined, digits = 2): string {
  if (v == null || Number.isNaN(v)) return "—";
  return v.toFixed(digits);
}

interface FormState {
  symbol: string;
  strategy: "ladder" | "reversal";
  indicator: string;
  n_bands: number;
  edge_mode: string;
  direction: string;
  low_extreme: number;
  high_extreme: number;
  confirm: number;
  batch_mode: string;
  batches: number;
  gate_mode: string;
  gate_cap: number;
  min_weight: number;
  gamma: string;
  low_edge: string;
  high_edge: string;
  batch_ratio: string;
  band_step: string;
  trigger_mode: string;
  sell_batches: string;
  sell_ratio: string;
  vol_target: string;
  cash_rate: string;
  fee_bps: string;
  start: string;
  end: string;
}

const DEFAULT_FORM: FormState = {
  symbol: "000300",
  strategy: "ladder",
  indicator: "b200",
  n_bands: 5,
  edge_mode: "fixed",
  direction: "contrarian",
  low_extreme: 20,
  high_extreme: 80,
  confirm: 5,
  batch_mode: "time",
  batches: 5,
  gate_mode: "off",
  gate_cap: 0,
  min_weight: 0,
  gamma: "",
  low_edge: "",
  high_edge: "",
  batch_ratio: "",
  band_step: "",
  trigger_mode: "rebound",
  sell_batches: "",
  sell_ratio: "",
  vol_target: "",
  cash_rate: "",
  fee_bps: "",
  start: "",
  end: "",
};

export default function BreadthTimingPanel() {
  const [options, setOptions] = useState<TimingOptions | null>(null);
  const [form, setForm] = useState<FormState>(DEFAULT_FORM);
  const [presetKey, setPresetKey] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<TimingRunResult | null>(null);
  const [runs, setRuns] = useState<TimingRunSummary[]>([]);
  const [compareIds, setCompareIds] = useState<string[]>([]);
  const [compareRuns, setCompareRuns] = useState<TimingRunResult[]>([]);
  const [onlyMajorTrades, setOnlyMajorTrades] = useState(true);
  const [signals, setSignals] = useState<TimingSignal[]>([]);

  const equityRef = useRef<HTMLDivElement | null>(null);
  const overlayRef = useRef<HTMLDivElement | null>(null);
  const klineRef = useRef<HTMLDivElement | null>(null);
  const equityInst = useRef<echarts.ECharts | null>(null);
  const overlayInst = useRef<echarts.ECharts | null>(null);
  const klineInst = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    timingBacktestApi.signals().then(setSignals).catch(() => undefined);
    timingBacktestApi.options().then((o) => {
      setOptions(o);
      const first = o.instruments.find((i) => i.data_start) ?? o.instruments[0];
      if (first) setForm((f) => ({ ...f, symbol: first.symbol }));
    }).catch((e) => setError((e as Error).message));
    refreshRuns();
  }, []);

  const refreshRuns = () => {
    timingBacktestApi.listRuns().then(setRuns).catch(() => undefined);
  };

  const currentInstrument = useMemo(
    () => options?.instruments.find((i) => i.symbol === form.symbol),
    [options, form.symbol],
  );

  const applyPreset = (key: string) => {
    setPresetKey(key);
    const preset = options?.presets.find((p) => p.key === key);
    if (!preset) return;
    setForm((f) => ({
      ...f,
      ...DEFAULT_FORM,
      ...(preset.params as Partial<FormState>),
      fee_bps: "",
    }));
  };

  const run = async () => {
    setRunning(true);
    setError(null);
    try {
      const body: Record<string, string | number | null> = {
        symbol: form.symbol,
        strategy: form.strategy,
        indicator: form.indicator,
        gate_mode: form.gate_mode,
        gate_cap: form.gate_cap,
        vol_target: form.vol_target.trim() === "" ? 0 : Number(form.vol_target) / 100,
        cash_rate: form.cash_rate.trim() === "" ? 0 : Number(form.cash_rate) / 100,
        fee_bps: form.fee_bps.trim() === "" ? null : Number(form.fee_bps),
        start: form.start.trim() === "" ? null : form.start.trim(),
        end: form.end.trim() === "" ? null : form.end.trim(),
      };
      if (form.strategy === "ladder") {
        body.n_bands = form.n_bands;
        body.edge_mode = form.edge_mode;
        body.direction = form.direction;
        body.min_weight = form.min_weight;
        body.gamma = form.gamma.trim() === "" ? 1.0 : Number(form.gamma);
        body.low_edge = form.low_edge.trim() === "" ? 0.0 : Number(form.low_edge);
        body.high_edge = form.high_edge.trim() === "" ? 100.0 : Number(form.high_edge);
      } else {
        body.low_extreme = form.low_extreme;
        body.high_extreme = form.high_extreme;
        body.confirm = form.confirm;
        body.batch_mode = form.batch_mode;
        body.batches = form.batches;
        body.batch_ratio = form.batch_ratio.trim() === "" ? 1.0 : Number(form.batch_ratio);
        body.band_step = form.band_step.trim() === "" ? 10.0 : Number(form.band_step);
        body.trigger_mode = form.trigger_mode;
        body.sell_batches = form.sell_batches.trim() === "" ? null : Number(form.sell_batches);
        body.sell_ratio = form.sell_ratio.trim() === "" ? null : Number(form.sell_ratio);
      }
      const res = await timingBacktestApi.createRun(body);
      setResult(res);
      refreshRuns();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setRunning(false);
    }
  };

  // 图表实例生命周期
  useEffect(() => {
    const mk = (ref: React.RefObject<HTMLDivElement | null>) => {
      if (!ref.current) return null;
      const inst = echarts.init(ref.current, undefined, { renderer: "canvas" });
      const ro = new ResizeObserver(() => inst.resize());
      ro.observe(ref.current);
      return { inst, ro };
    };
    const a = mk(equityRef);
    const b = mk(overlayRef);
    const c = mk(klineRef);
    equityInst.current = a?.inst ?? null;
    overlayInst.current = b?.inst ?? null;
    klineInst.current = c?.inst ?? null;
    return () => {
      a?.ro.disconnect();
      b?.ro.disconnect();
      c?.ro.disconnect();
      a?.inst.dispose();
      b?.inst.dispose();
      c?.inst.dispose();
      equityInst.current = null;
      overlayInst.current = null;
      klineInst.current = null;
    };
  }, []);

  // 图 1：净值对比（当前结果 + 勾选的历史运行叠加）
  useEffect(() => {
    if (!equityInst.current || !result) return;
    const series: echarts.SeriesOption[] = [
      {
        name: "策略净值",
        type: "line",
        data: result.daily.equity,
        showSymbol: false,
        lineStyle: { width: 1.6 },
      },
      {
        name: "买入持有",
        type: "line",
        data: result.daily.benchmark,
        showSymbol: false,
        lineStyle: { width: 1.2, type: "dashed" },
      },
      ...compareRuns.map((r) => ({
        name: `${r.params.symbol ?? r.symbol}·${STRATEGY_CN[String(r.params.strategy)] ?? r.params.strategy}`,
        type: "line" as const,
        data: r.daily.equity,
        showSymbol: false,
        lineStyle: { width: 1, opacity: 0.7 },
      })),
    ];
    equityInst.current.setOption(
      {
        tooltip: { trigger: "axis" },
        legend: { top: 0, textStyle: { fontSize: 11 } },
        grid: { left: 48, right: 16, top: 30, bottom: 26 },
        xAxis: {
          type: "category",
          data: result.daily.date,
          boundaryGap: false,
          axisLabel: { fontSize: 10, hideOverlap: true },
        },
        yAxis: {
          type: "log",
          axisLabel: { fontSize: 10, formatter: (v: number) => String(v) },
        },
        series,
      },
      true,
    );
  }, [result, compareRuns]);

  // 图 2：指数点位 + 宽度（右轴）+ 仓位色带
  useEffect(() => {
    if (!overlayInst.current || !result) return;
    overlayInst.current.setOption(
      {
        tooltip: { trigger: "axis" },
        legend: { top: 0, textStyle: { fontSize: 11 }, data: ["点位", "宽度%", "仓位"] },
        grid: { left: 52, right: 46, top: 30, bottom: 26 },
        xAxis: {
          type: "category",
          data: result.daily.date,
          boundaryGap: false,
          axisLabel: { fontSize: 10, hideOverlap: true },
        },
        yAxis: [
          { type: "value", scale: true, axisLabel: { fontSize: 10 } },
          { type: "value", min: 0, max: 100, axisLabel: { fontSize: 10 } },
        ],
        series: [
          {
            name: "点位",
            type: "line",
            data: result.daily.close,
            showSymbol: false,
            lineStyle: { width: 1.2 },
          },
          {
            name: "宽度%",
            type: "line",
            yAxisIndex: 1,
            data: result.daily.breadth,
            showSymbol: false,
            lineStyle: { width: 1, opacity: 0.85 },
          },
          {
            name: "仓位",
            type: "line",
            yAxisIndex: 1,
            data: result.daily.weight.map((w) => w * 100),
            showSymbol: false,
            lineStyle: { width: 0 },
            areaStyle: { opacity: 0.18 },
          },
        ],
      },
      true,
    );
  }, [result]);

  // 图 3：K 线 + 买卖点（T+1 开盘成交价，箭头大小 = 调仓幅度）
  useEffect(() => {
    if (!klineInst.current || !result) return;
    const d = result.daily;
    const dateIdx = new Map<string, number>(d.date.map((dt, i) => [dt, i]));
    const trades = onlyMajorTrades
      ? result.trades.filter((t) => t.turnover >= 0.2)
      : result.trades;
    const buys = trades.filter((t) => t.new_weight > t.prev_weight);
    const sells = trades.filter((t) => t.new_weight <= t.prev_weight);
    const mkScatter = (list: typeof trades, color: string, rotate: number) => ({
      name: rotate === 0 ? "买入" : "卖出",
      type: "scatter" as const,
      data: list
        .map((t) => ({ value: [dateIdx.get(t.date) ?? NaN, t.price, t], idx: dateIdx.get(t.date) ?? NaN }))
        .filter((p) => Number.isFinite(p.idx)),
      symbol: "triangle",
      symbolRotate: rotate,
      symbolSize: (val: unknown[]) => {
        const t = val[2] as { turnover: number } | undefined;
        return 7 + Math.min(1, t?.turnover ?? 0.5) * 11;
      },
      itemStyle: { color },
      z: 5,
    });
    klineInst.current.setOption(
      {
        tooltip: {
          trigger: "axis",
          axisPointer: { type: "cross" },
        },
        legend: { top: 0, textStyle: { fontSize: 11 }, data: ["买入", "卖出"] },
        grid: { left: 52, right: 16, top: 30, bottom: 56 },
        xAxis: {
          type: "category",
          data: d.date,
          axisLabel: { fontSize: 10, hideOverlap: true },
        },
        yAxis: { scale: true, axisLabel: { fontSize: 10 } },
        dataZoom: [
          { type: "inside", start: 0, end: 100 },
          { type: "slider", height: 18, bottom: 8 },
        ],
        series: [
          {
            name: "K线",
            type: "candlestick",
            data: d.date.map((_, i) => [d.open[i], d.close[i], d.low[i], d.high[i]]),
            itemStyle: {
              color: "#e04b4b",
              color0: "#2eaa5e",
              borderColor: "#e04b4b",
              borderColor0: "#2eaa5e",
            },
          },
          mkScatter(buys, "#e04b4b", 0),
          mkScatter(sells, "#2eaa5e", 180),
        ],
      },
      true,
    );
  }, [result, onlyMajorTrades]);

  const toggleCompare = async (runId: string) => {
    const next = compareIds.includes(runId)
      ? compareIds.filter((id) => id !== runId)
      : [...compareIds, runId].slice(-5);
    setCompareIds(next);
    const loaded = await Promise.all(next.map((id) => timingBacktestApi.getRun(id).catch(() => null)));
    setCompareRuns(loaded.filter((r): r is TimingRunResult => r != null));
  };

  const m = result?.metrics;
  const cards: Array<[string, string, string?]> = m
    ? [
        ["策略年化", pct(m.strategy_cagr), m.strategy_cagr >= m.benchmark_cagr ? "positive" : "negative"],
        ["买入持有年化", pct(m.benchmark_cagr)],
        ["超额年化", pct(m.excess_cagr), m.excess_cagr > 0 ? "positive" : "negative"],
        ["最大回撤", pct(m.strategy_mdd), "negative"],
        ["基准回撤", pct(m.benchmark_mdd)],
        ["Calmar", num(m.calmar)],
        ["Sharpe", num(m.sharpe)],
        ["平均仓位", pct(m.avg_weight, 0)],
        ["调仓次数", String(Math.round(m.n_trades))],
      ]
    : [];

  return (
    <div>
      <div className="header">
        <h1>宽度择时回测 · B20/B50/B200</h1>
        <p className="bt-sub">
          用市场宽度做阶段性顶部分批卖出 / 底部分批买入。信号 T 日收盘、T+1 开盘成交；
          A股标的配全A宽度，美股标的配 SP500 成分宽度。
        </p>
      </div>

      <section className="bt-section">
        <h3>今日执行信号（按手册配置，含 5% 最小调仓与 ETF 费率）</h3>
        <div className="bt-trades-scroll">
          <table className="bt-table">
            <thead>
              <tr>
                <th>配置</th>
                <th>数据截至</th>
                <th>宽度现值</th>
                <th>目标仓位</th>
                <th>引擎（RS提示灯）</th>
                <th>触发条件</th>
                <th>全史年化</th>
                <th>回撤</th>
              </tr>
            </thead>
            <tbody>
              {(signals ?? []).map((sg) => (
                <tr key={sg.key}>
                  <td>{sg.label}{sg.error ? `（${sg.error}）` : ""}</td>
                  <td>{sg.as_of ?? "—"}</td>
                  <td>{sg.breadth_now != null ? sg.breadth_now.toFixed(1) : "—"}</td>
                  <td style={{ fontWeight: 700 }}>
                    {sg.weight_now != null ? `${Math.round(sg.weight_now * 100)}%` : "—"}
                  </td>
                  <td
                    style={{
                      fontWeight: 700,
                      color: sg.siphon ? "#e3745f" : undefined,
                      whiteSpace: "normal",
                      maxWidth: 170,
                    }}
                  >
                    {sg.engine != null
                      ? `${sg.engine}${
                          sg.rs120 != null ? `（RS120 ${sg.rs120 > 0 ? "+" : ""}${sg.rs120}pp）` : ""
                        }`
                      : "—"}
                  </td>
                  <td style={{ whiteSpace: "normal", maxWidth: 380 }}>{sg.trigger ?? "—"}</td>
                  <td className={(sg.full_cagr ?? 0) > 0 ? "positive" : "negative"}>
                    {sg.full_cagr != null ? pct(sg.full_cagr) : "—"}
                  </td>
                  <td className="negative">{sg.full_mdd != null ? pct(sg.full_mdd) : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="bt-meta">
          宽度数据截至最近回填日（A 股 {signals.find((s) => s.symbol === "159915")?.as_of ?? "—"}，
         美股 {signals.find((s) => s.symbol === "SPY")?.as_of ?? "—"}）；重跑
          scripts/backfill_timing_data.py 可刷新。历史最优不等于未来最优。
        </p>
      </section>

      {error && <div className="fund-errors">{error}</div>}

      <section className="bt-panel">
        <div className="bt-form">
          <label>
            预设
            <select value={presetKey} onChange={(e) => applyPreset(e.target.value)}>
              <option value="">— 自定义 —</option>
              {(options?.presets ?? []).map((p) => (
                <option key={p.key} value={p.key}>{p.label}</option>
              ))}
            </select>
          </label>
          <label>
            标的
            <select value={form.symbol} onChange={(e) => setForm({ ...form, symbol: e.target.value })}>
              {(options?.instruments ?? []).map((i) => (
                <option key={i.symbol} value={i.symbol}>
                  {i.name}（{i.data_start ? `${i.data_start.slice(0, 4)}起` : "无数据"}）
                </option>
              ))}
            </select>
          </label>
          <label>
            宽度指标
            <select value={form.indicator} onChange={(e) => setForm({ ...form, indicator: e.target.value })}>
              {(options?.indicators ?? []).map((i) => (
                <option key={i.key} value={i.key}>{i.label}</option>
              ))}
            </select>
          </label>
          <label>
            策略
            <select
              value={form.strategy}
              onChange={(e) => setForm({ ...form, strategy: e.target.value as FormState["strategy"] })}
            >
              <option value="ladder">阶梯分批（顶部卖/底部买）</option>
              <option value="reversal">极值反转（底买顶卖）</option>
            </select>
          </label>
          {form.strategy === "ladder" && (
            <>
              <label>
                档位数
                <select
                  value={form.n_bands}
                  onChange={(e) => setForm({ ...form, n_bands: Number(e.target.value) })}
                >
                  {(options?.strategies.ladder.n_bands_choices ?? [3, 5, 9]).map((n) => (
                    <option key={n} value={n}>{n} 档</option>
                  ))}
                </select>
              </label>
              <label>
                阈值模式
                <select value={form.edge_mode} onChange={(e) => setForm({ ...form, edge_mode: e.target.value })}>
                  <option value="fixed">固定阈值</option>
                  <option value="preq">起点前分位数(无前视)</option>
                </select>
              </label>
              <label>
                方向
                <select value={form.direction} onChange={(e) => setForm({ ...form, direction: e.target.value })}>
                  <option value="contrarian">{DIRECTION_CN.contrarian}</option>
                  <option value="momentum">{DIRECTION_CN.momentum}</option>
                </select>
              </label>
              <label>
                底仓(0-100%)
                <input
                  type="number"
                  min={0}
                  max={100}
                  step={5}
                  value={Math.round(form.min_weight * 100)}
                  onChange={(e) => setForm({ ...form, min_weight: Math.max(0, Math.min(100, Number(e.target.value))) / 100 })}
                />
              </label>
              <label>
                陡度γ(&gt;1深极值重仓)
                <input
                  type="text"
                  placeholder="1"
                  value={form.gamma}
                  onChange={(e) => setForm({ ...form, gamma: e.target.value })}
                />
              </label>
              <label>
                边界范围(低/高)
                <input
                  type="text"
                  placeholder="如 15 / 85"
                  style={{ width: 52 }}
                  value={form.low_edge}
                  onChange={(e) => setForm({ ...form, low_edge: e.target.value })}
                />
                <input
                  type="text"
                  placeholder="100"
                  style={{ width: 52, marginLeft: 4 }}
                  value={form.high_edge}
                  onChange={(e) => setForm({ ...form, high_edge: e.target.value })}
                />
              </label>
            </>
          )}
          {form.strategy === "reversal" && (
            <>
              <label>
                下极值
                <input
                  type="number"
                  min={1}
                  max={50}
                  value={form.low_extreme}
                  onChange={(e) => setForm({ ...form, low_extreme: Number(e.target.value) })}
                />
              </label>
              <label>
                上极值
                <input
                  type="number"
                  min={50}
                  max={99}
                  value={form.high_extreme}
                  onChange={(e) => setForm({ ...form, high_extreme: Number(e.target.value) })}
                />
              </label>
              <label>
                确认幅度
                <input
                  type="number"
                  min={1}
                  max={20}
                  value={form.confirm}
                  onChange={(e) => setForm({ ...form, confirm: Number(e.target.value) })}
                />
              </label>
              <label>
                分批方式
                <select value={form.batch_mode} onChange={(e) => setForm({ ...form, batch_mode: e.target.value })}>
                  <option value="time">{BATCH_CN.time}</option>
                  <option value="band">{BATCH_CN.band}</option>
                </select>
              </label>
              <label>
                批数
                <select value={form.batches} onChange={(e) => setForm({ ...form, batches: Number(e.target.value) })}>
                  {[3, 5, 8].map((n) => (
                    <option key={n} value={n}>{n} 批</option>
                  ))}
                </select>
              </label>
              <label>
                触发模式
                <select value={form.trigger_mode} onChange={(e) => setForm({ ...form, trigger_mode: e.target.value })}>
                  <option value="rebound">回升确认(防接飞刀)</option>
                  <option value="immediate">进区即买(越跌越买)</option>
                  <option value="extreme_confirm">离最低点回升(早入场)</option>
                  <option value="linger">磨底K日后(时间确认)</option>
                </select>
              </label>
              <label>
                批次比例(&gt;1首批重)
                <input
                  type="text"
                  placeholder="1（等分）"
                  value={form.batch_ratio}
                  onChange={(e) => setForm({ ...form, batch_ratio: e.target.value })}
                />
              </label>
              <label>
                卖出批数(空=同买入)
                <input
                  type="text"
                  placeholder="同买入"
                  value={form.sell_batches}
                  onChange={(e) => setForm({ ...form, sell_batches: e.target.value })}
                />
              </label>
              <label>
                档位步长(宽度点)
                <input
                  type="text"
                  placeholder="10"
                  value={form.band_step}
                  onChange={(e) => setForm({ ...form, band_step: e.target.value })}
                />
              </label>
            </>
          )}
          <label>
            趋势闸门
            <select value={form.gate_mode} onChange={(e) => setForm({ ...form, gate_mode: e.target.value })}>
              <option value="off">{GATE_CN.off}</option>
              <option value="ma200">{GATE_CN.ma200}</option>
            </select>
          </label>
          <label>
            现金年化利率(%)
            <input
              type="text"
              placeholder="0"
              value={form.cash_rate}
              onChange={(e) => setForm({ ...form, cash_rate: e.target.value })}
            />
          </label>
          <label>
            波动率目标%(0=关)
            <input
              type="text"
              placeholder="0"
              value={form.vol_target}
              onChange={(e) => setForm({ ...form, vol_target: e.target.value })}
            />
          </label>
          <label>
            单边费率(bp)
            <input
              type="text"
              placeholder={currentInstrument ? String(currentInstrument.fee_default_bps) : "默认"}
              value={form.fee_bps}
              onChange={(e) => setForm({ ...form, fee_bps: e.target.value })}
            />
          </label>
          <label>
            开始日期
            <input
              type="text"
              placeholder={currentInstrument?.data_start ?? "YYYY-MM-DD"}
              value={form.start}
              onChange={(e) => setForm({ ...form, start: e.target.value })}
            />
          </label>
          <label>
            结束日期
            <input
              type="text"
              placeholder={currentInstrument?.data_end ?? "YYYY-MM-DD"}
              value={form.end}
              onChange={(e) => setForm({ ...form, end: e.target.value })}
            />
          </label>
          <button className="bt-run" onClick={run} disabled={running}>
            {running ? "回测中…" : "运行回测"}
          </button>
        </div>
        {currentInstrument && (
          <p className="bt-meta">
            {currentInstrument.name} ← {currentInstrument.breadth_label}
            （数据 {currentInstrument.data_start ?? "缺失"} → {currentInstrument.data_end ?? "—"}，
            宽度自 {currentInstrument.breadth_start ?? "—"} 起） · {currentInstrument.note}
          </p>
        )}
      </section>

      {result && m && (
        <>
          <div className="bt-cards">
            {cards.map(([label, value, tone]) => (
              <div key={label} className="bt-card">
                <div className="bt-card-label">{label}</div>
                <div className={`bt-card-value ${tone ?? ""}`}>{value}</div>
              </div>
            ))}
          </div>

          <section className="bt-section">
            <h3>净值曲线（对数轴）—— 策略 vs 买入持有{compareRuns.length > 0 ? ` + 叠加 ${compareRuns.length} 条历史` : ""}</h3>
            <div ref={equityRef} style={{ height: 300 }} />
          </section>

          <section className="bt-section">
            <h3>点位 · 宽度 · 仓位（仓位为背景色带，右侧 0-100）</h3>
            <div ref={overlayRef} style={{ height: 280 }} />
          </section>

          <section className="bt-section">
            <div className="bt-trades-head">
              <h3>K线 · 买卖点（箭头在 T+1 开盘成交价上，大小=调仓幅度；滚轮/滑块缩放）</h3>
              <label style={{ display: "flex", gap: 6, alignItems: "center", fontSize: 12 }}>
                <input
                  type="checkbox"
                  checked={onlyMajorTrades}
                  onChange={(e) => setOnlyMajorTrades(e.target.checked)}
                />
                只看 ≥20% 的大额调仓
              </label>
            </div>
            <div ref={klineRef} style={{ height: 380 }} />
          </section>

          <section className="bt-section">
            <h3>逐年收益</h3>
            <table className="bt-table">
              <thead>
                <tr>
                  <th>年份</th>
                  <th>策略</th>
                  <th>买入持有</th>
                  <th>差值</th>
                </tr>
              </thead>
              <tbody>
                {result.yearly.map((y) => {
                  const diff = y.strategy - y.benchmark;
                  return (
                    <tr key={y.year}>
                      <td>{y.year}</td>
                      <td className={y.strategy > 0 ? "positive" : "negative"}>{pct(y.strategy)}</td>
                      <td className={y.benchmark > 0 ? "positive" : "negative"}>{pct(y.benchmark)}</td>
                      <td className={diff > 0 ? "positive" : "negative"}>{pct(diff)}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </section>

          <section className="bt-section">
            <div className="bt-trades-head">
              <h3>调仓明细（{result.trades.length} 次）</h3>
            </div>
            <div className="bt-trades-scroll">
              <table className="bt-table">
                <thead>
                  <tr>
                    <th>日期</th>
                    <th>仓位变化</th>
                    <th>成交价(开盘)</th>
                    <th>费用</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trades.map((t, i) => (
                    <tr key={`${t.date}-${i}`}>
                      <td>{t.date}</td>
                      <td>{pct(t.prev_weight, 0)} → {pct(t.new_weight, 0)}</td>
                      <td>{t.price}</td>
                      <td>{t.fee.toFixed(4)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      <section className="bt-section">
        <h3>历史运行（勾选 ≤5 条叠加到净值曲线）</h3>
        <div className="bt-trades-scroll">
          <table className="bt-table">
            <thead>
              <tr>
                <th>叠加</th>
                <th>时间</th>
                <th>标的</th>
                <th>策略</th>
                <th>指标</th>
                <th>年化</th>
                <th>基准</th>
                <th>超额</th>
                <th>回撤</th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.run_id}>
                  <td>
                    <input
                      type="checkbox"
                      checked={compareIds.includes(r.run_id)}
                      onChange={() => toggleCompare(r.run_id)}
                    />
                  </td>
                  <td>{r.created_at}</td>
                  <td>{r.name}</td>
                  <td>{STRATEGY_CN[String(r.params.strategy)] ?? String(r.params.strategy)}</td>
                  <td>{String(r.params.indicator ?? "")}</td>
                  <td className={(r.metrics?.strategy_cagr ?? 0) > 0 ? "positive" : "negative"}>
                    {pct(r.metrics?.strategy_cagr)}
                  </td>
                  <td>{pct(r.metrics?.benchmark_cagr)}</td>
                  <td className={(r.metrics?.excess_cagr ?? 0) > 0 ? "positive" : "negative"}>
                    {pct(r.metrics?.excess_cagr)}
                  </td>
                  <td className="negative">{pct(r.metrics?.strategy_mdd)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </section>

      <section className="bt-section">
        <h3>数据声明</h3>
        <ul className="breadth-reason-list">
          {(options?.disclaimers ?? []).map((d) => (
            <li key={d}>· {d}</li>
          ))}
        </ul>
      </section>
    </div>
  );
}
