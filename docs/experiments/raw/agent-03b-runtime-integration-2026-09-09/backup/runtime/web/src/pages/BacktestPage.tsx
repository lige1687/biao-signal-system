import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { backtestApi } from "../api/client";
import InfoTip from "../components/InfoTip";
import BacktestKline from "../components/BacktestKline";
import BreadthTimingPanel from "../components/BreadthTimingPanel";
import type {
  BacktestMetrics,
  BacktestOptions,
  BacktestRunResult,
  BacktestRunSummary,
  BacktestTrade,
} from "../types";

/**
 * 回测工作台（模块 A，规格 §15/§16）。
 *
 * 用户视角：自己选盈亏比门槛/入场版本/退出方式/费用档与标的范围 → 一键回测 →
 * 看总览指标（每个术语带悬浮解释）、分组对比、以及每个标的的逐笔买卖点明细；
 * 历史回测记录留存可回看。判定全部在后端（与 live 同一份检测器），前端只展示。
 */

const EXIT_REASON_CN: Record<string, string> = {
  structure_stop_C: "跌破止损位",
  exit_a6_1_costbasis: "跌破EMA20+抵扣价",
  exit_a6_2_top_plus_keywave: "顶部构造后关键波动",
  open_at_end: "持有至数据末尾",
  invalid_nonpositive_risk: "风险非正（未执行）",
};

function fmtNum(v: number | null | undefined, digits = 2): string {
  if (v == null || Number.isNaN(v)) return "—";
  return v.toFixed(digits);
}

function fmtPct(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return "—";
  return `${(v * 100).toFixed(0)}%`;
}

function tone(v: number | null | undefined): string {
  if (v == null) return "neutral";
  return v > 0 ? "positive" : v < 0 ? "negative" : "neutral";
}

type GroupKey = "分年份" | "牛/熊/横盘（基准时钟）" | "样本内外" | "按标的";

const GROUP_TABS: GroupKey[] = [
  "分年份",
  "牛/熊/横盘（基准时钟）",
  "样本内外",
  "按标的",
];

export default function BacktestPage() {
  const [tab, setTab] = useState<"tech" | "timing">("tech");
  const [options, setOptions] = useState<BacktestOptions | null>(null);
  const [rrMin, setRrMin] = useState<string>("3");
  const [module, setModule] = useState("A");
  const [entryVariant, setEntryVariant] = useState("early");
  const [exitVariant, setExitVariant] = useState("a6_1_costbasis");
  const [feeLabel, setFeeLabel] = useState("standard");
  const [volumeConfirm, setVolumeConfirm] = useState("off"); // off | 1 | 5
  const [profileFilter, setProfileFilter] = useState("none");
  const [symbolsInput, setSymbolsInput] = useState("");
  const [runId, setRunId] = useState<string | null>(null);
  const [status, setStatus] = useState<string>("idle");
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<BacktestRunResult | null>(null);
  const [runs, setRuns] = useState<BacktestRunSummary[]>([]);
  const [groupTab, setGroupTab] = useState<GroupKey>("分年份");
  const [tradeFilter, setTradeFilter] = useState("");
  const [klineSymbol, setKlineSymbol] = useState<string | null>(null);
  const [overrides, setOverrides] = useState<Record<string, string>>({});
  const pollRef = useRef<number | null>(null);

  useEffect(() => {
    backtestApi.options().then((o) => {
      setOptions(o);
      setRrMin(String(o.defaults.rr_min));
      setModule(o.defaults.module ?? "A");
      setEntryVariant(o.defaults.entry_variant);
      setExitVariant(o.defaults.exit_variant);
      setFeeLabel(o.defaults.fee_label);
    }).catch((e: Error) => setError(`参数加载失败：${e.message}`));
    backtestApi.listRuns().then(setRuns).catch(() => undefined);
    return () => {
      if (pollRef.current) window.clearInterval(pollRef.current);
    };
  }, []);

  const poll = useCallback((id: string) => {
    if (pollRef.current) window.clearInterval(pollRef.current);
    pollRef.current = window.setInterval(async () => {
      try {
        const data = await backtestApi.getRun(id);
        const st = (data as BacktestRunSummary).status ?? "unknown";
        setStatus(st);
        if (st === "done") {
          if (pollRef.current) window.clearInterval(pollRef.current);
          setResult(data as BacktestRunResult);
          backtestApi.listRuns().then(setRuns).catch(() => undefined);
        } else if (st === "failed") {
          if (pollRef.current) window.clearInterval(pollRef.current);
          setError((data as BacktestRunSummary).error ?? "回测失败");
        }
      } catch (e) {
        if (pollRef.current) window.clearInterval(pollRef.current);
        setError((e as Error).message);
      }
    }, 2000);
  }, []);

  const startBacktest = async () => {
    setError(null);
    setResult(null);
    const symbols = symbolsInput
      .split(/[,，\s]+/)
      .map((s) => s.trim())
      .filter(Boolean);
    try {
      const { run_id } = await backtestApi.createRun({
        symbols: symbols.length ? symbols : null,
        module,
        rr_min: rrMin === "none" ? null : Number(rrMin),
        entry_variant: entryVariant || null,
        overrides: Object.fromEntries(
          Object.entries(overrides)
            .filter(([k, v]) => {
              const spec = options?.param_specs?.[k];
              return spec && String(v) !== String(spec.default);
            })
            .map(([k, v]) => [k, Number(v)]),
        ),
        exit_variant: exitVariant,
        fee_label: feeLabel,
        volume_confirm: volumeConfirm !== "off",
        volume_confirm_window: volumeConfirm === "off" ? 5 : Number(volumeConfirm),
        profile_filter: profileFilter,
      });
      setRunId(run_id);
      setStatus("running");
      poll(run_id);
    } catch (e) {
      setError((e as Error).message);
    }
  };

  const glossary = options?.glossary ?? {};
  const tip = (key: string, fallback: string) => glossary[key]?.tip ?? fallback;

  const groups = result?.groups?.True ?? {};
  const overview: BacktestMetrics | undefined = groups["总览"]?.[0];
  const groupRows: BacktestMetrics[] = useMemo(
    () => groups[groupTab] ?? [],
    [groups, groupTab],
  );
  const filteredTrades: BacktestTrade[] = useMemo(() => {
    if (!result) return [];
    const f = tradeFilter.trim().toUpperCase();
    if (!f) return result.trades;
    return result.trades.filter((t) => t.symbol.toUpperCase().includes(f));
  }, [result, tradeFilter]);

  return (
    <div className="page">
      <div className="bt-tabs">
        <button
          className={`bt-tab ${tab === "tech" ? "active" : ""}`}
          onClick={() => setTab("tech")}
        >
          技术信号回测
        </button>
        <button
          className={`bt-tab ${tab === "timing" ? "active" : ""}`}
          onClick={() => setTab("timing")}
        >
          宽度择时回测
        </button>
      </div>
      {tab === "timing" && <BreadthTimingPanel />}
      {tab === "tech" && (
        <>
      <div className="header">
        <h1>回测工作台 · 模块 A（稳定上涨回调）</h1>
        <p className="bt-sub">
          自己选参数、跑全池或单个标的、看每笔买卖点。所有信号与
          <b>线上系统用同一套规则</b>计算；术语悬停有解释。
        </p>
      </div>

      {error && <div className="fund-errors">{error}</div>}

      <section className="bt-panel">
        <div className="bt-form">
          <label>
            交易模块
            <select value={module} onChange={(e) => {
              setModule(e.target.value);
              const mod = options?.modules.find((m) => m.value === e.target.value);
              setEntryVariant(mod ? Object.keys(mod.variants)[0] : "");
            }}>
              {(options?.modules ?? []).map((m) => (
                <option key={m.value} value={m.value}>{m.label}</option>
              ))}
            </select>
          </label>
          <label>
            <InfoTip tip={tip("rr_min", "开仓前的纸面赔率门槛")}>盈亏比门槛</InfoTip>
            <select value={rrMin} onChange={(e) => setRrMin(e.target.value)}>
              {(options?.rr_levels ?? []).map((o) => (
                <option key={String(o.value)} value={o.value === null ? "none" : String(o.value)}>
                  {o.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <InfoTip tip={tip("entry_variant", "入场触发条件版本")}>入场版本</InfoTip>
            <select value={entryVariant} onChange={(e) => setEntryVariant(e.target.value)}>
              {Object.entries(
                options?.modules.find((m) => m.value === module)?.variants ?? {},
              ).map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
          </label>
          <label>
            <InfoTip tip={tip("exit_variant", "卖出规则版本")}>退出方式</InfoTip>
            <select value={exitVariant} onChange={(e) => setExitVariant(e.target.value)}>
              {(options?.exit_variants ?? []).map((o) => (
                <option key={String(o.value)} value={String(o.value)}>{o.label}</option>
              ))}
            </select>
          </label>
          <label>
            费用档
            <select value={feeLabel} onChange={(e) => setFeeLabel(e.target.value)}>
              {(options?.fee_labels ?? []).map((o) => (
                <option key={String(o.value)} value={String(o.value)}>{o.label}</option>
              ))}
            </select>
          </label>
          <label>
            <InfoTip tip={tip("volume_confirm", "近 N 日异常大量确认，默认关")}>量能确认</InfoTip>
            <select value={volumeConfirm} onChange={(e) => setVolumeConfirm(e.target.value)}>
              <option value="off">关</option>
              {(options?.volume_confirm_windows ?? []).map((o) => (
                <option key={String(o.value)} value={String(o.value)}>{o.label}</option>
              ))}
            </select>
          </label>
          <label>
            <InfoTip tip={tip("profile_filter", "筹码分布代理过滤，默认关")}>筹码过滤</InfoTip>
            <select value={profileFilter} onChange={(e) => setProfileFilter(e.target.value)}>
              {(options?.profile_filters ?? [{ value: "none", label: "关" }]).map((o) => (
                <option key={String(o.value)} value={String(o.value)}>{o.label}</option>
              ))}
            </select>
          </label>
          <label className="bt-symbols">
            标的范围
            <input
              value={symbolsInput}
              onChange={(e) => setSymbolsInput(e.target.value)}
              placeholder="留空 = 全部标的；单个如 510300.SS；多个逗号分隔"
            />
          </label>
          {(Object.keys(options?.param_specs ?? {}).length > 0) && (
            <span className="bt-ov-sep">检测器参数（实验档，来源规格 §17 敏感性）：</span>
          )}
          {Object.entries(options?.param_specs ?? {}).map(([key, spec]) => (
            <label key={key}>
              <InfoTip tip={spec.tip}>{spec.label}</InfoTip>
              <select
                value={overrides[key] ?? String(spec.default)}
                onChange={(e) => setOverrides((prev) => ({ ...prev, [key]: e.target.value }))}
              >
                {spec.levels.map((lv) => (
                  <option key={lv} value={String(lv)}>
                    {lv === spec.default ? `${lv}（默认）` : lv}
                  </option>
                ))}
              </select>
            </label>
          ))}
          <button
            className="bt-run"
            onClick={startBacktest}
            disabled={status === "running"}
          >
            {status === "running" ? "回测运行中…" : "开始回测"}
          </button>
        </div>
        {status === "running" && (
          <p className="bt-running">
            正在回测（全池约 1–3 分钟，首次需加载行情）… 完成后自动显示结果。
          </p>
        )}
      </section>

      {result && overview && (
        <>
          <section className="bt-cards">
            {[
              { key: "trade_count", label: "笔数", value: String(overview.trade_count), t: "neutral" },
              { key: "open_count", label: "未平仓", value: String(overview.open_count), t: "neutral" },
              { key: "win_rate", label: "胜率", value: fmtPct(overview.win_rate), t: "neutral" },
              { key: "expectancy_r", label: "期望 R", value: fmtNum(overview.expectancy_r), t: tone(overview.expectancy_r) },
              { key: "profit_factor", label: "盈利因子", value: fmtNum(overview.profit_factor), t: "neutral" },
              { key: "max_consecutive_losses", label: "最大连亏", value: String(overview.max_consecutive_losses), t: "neutral" },
              { key: "max_drawdown_1r", label: "1R 最大回撤", value: fmtNum(overview.max_drawdown_1r, 1), t: "negative" },
              { key: "avg_holding_bars", label: "平均持仓(根K)", value: fmtNum(overview.avg_holding_bars, 1), t: "neutral" },
              { key: "total_r", label: "累计 R", value: fmtNum(overview.total_r), t: tone(overview.total_r) },
            ].map((c) => (
              <div key={c.key} className={`bt-card ${c.t}`}>
                <div className="bt-card-label">
                  <InfoTip tip={tip(c.key, "")}>{c.label}</InfoTip>
                </div>
                <div className="bt-card-value">{c.value}</div>
              </div>
            ))}
          </section>

          <p className="bt-meta">
            数据 {result.data_range.start} ~ {result.data_range.end} ·{" "}
            {result.data_range.symbols_count} 个标的 · 样本外起点{" "}
            {result.data_range.out_of_sample_start} · 事件漏斗：触碰{" "}
            {result.funnel.touched} → 入场信号 {result.funnel.confirmed} →
            盈亏比过滤剔除 {result.funnel.filtered_by_rr} · 目标不可计算{" "}
            {result.funnel.no_target}。{result.disclaimer}
          </p>

          <section className="bt-section">
            <div className="bt-tabs">
              {GROUP_TABS.map((g) => (
                <button
                  key={g}
                  className={groupTab === g ? "bt-tab active" : "bt-tab"}
                  onClick={() => setGroupTab(g)}
                >
                  {g.replace("（基准时钟）", "")}
                </button>
              ))}
            </div>
            <table className="bt-table">
              <thead>
                <tr>
                  <th>分组</th>
                  <th><InfoTip tip={tip("trade_count", "")}>笔数</InfoTip></th>
                  <th>未平</th>
                  <th><InfoTip tip={tip("win_rate", "")}>胜率</InfoTip></th>
                  <th><InfoTip tip={tip("avg_win_r", "")}>均盈R</InfoTip></th>
                  <th><InfoTip tip={tip("avg_loss_r", "")}>均亏R</InfoTip></th>
                  <th><InfoTip tip={tip("expectancy_r", "")}>期望R</InfoTip></th>
                  <th><InfoTip tip={tip("profit_factor", "")}>盈利因子</InfoTip></th>
                  <th><InfoTip tip={tip("max_consecutive_losses", "")}>最大连亏</InfoTip></th>
                  <th><InfoTip tip={tip("max_drawdown_1r", "")}>1R回撤</InfoTip></th>
                  {groupTab === "按标的" && <th>K线</th>}
                </tr>
              </thead>
              <tbody>
                {groupRows.map((m) => (
                  <tr key={m.label}>
                    <td>{m.label}</td>
                    <td>{m.trade_count}</td>
                    <td>{m.open_count}</td>
                    <td>{fmtPct(m.win_rate)}</td>
                    <td className={tone(m.avg_win_r)}>{fmtNum(m.avg_win_r)}</td>
                    <td className={tone(m.avg_loss_r)}>{fmtNum(m.avg_loss_r)}</td>
                    <td className={tone(m.expectancy_r)}>{fmtNum(m.expectancy_r)}</td>
                    <td>{fmtNum(m.profit_factor)}</td>
                    <td>{m.max_consecutive_losses}</td>
                    <td>{fmtNum(m.max_drawdown_1r, 1)}</td>
                    {groupTab === "按标的" && (
                      <td>
                        <button
                          className="bt-load"
                          onClick={() => setKlineSymbol(m.label)}
                        >
                          看K线
                        </button>
                      </td>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
          </section>

          {klineSymbol && result && (
            <section className="bt-section bt-kline-wrap">
              <button className="bt-kline-close" onClick={() => setKlineSymbol(null)}>
                关闭K线
              </button>
              <BacktestKline
                symbol={klineSymbol}
                trades={result.trades.filter((t) => t.symbol === klineSymbol)}
              />
            </section>
          )}

          <section className="bt-section">
            <div className="bt-trades-head">
              <h3>逐笔买卖点（{result.trades.length} 笔）</h3>
              <div className="bt-trades-actions">
                <input
                  value={tradeFilter}
                  onChange={(e) => setTradeFilter(e.target.value)}
                  placeholder="按标的筛选，如 510300"
                />
                <button
                  className="bt-load"
                  disabled={!filteredTrades.length}
                  onClick={() => {
                    const first = filteredTrades[0];
                    if (first) setKlineSymbol(first.symbol);
                  }}
                >
                  在K线上看{tradeFilter.trim() ? ` ${filteredTrades[0]?.symbol ?? ""}` : "（先筛选标的）"}
                </button>
              </div>
            </div>
            <div className="bt-trades-scroll">
              <table className="bt-table">
                <thead>
                  <tr>
                    <th>标的</th>
                    <th>信号日</th>
                    <th>买入日</th>
                    <th>买入价</th>
                    <th>止损价</th>
                    <th>卖出日</th>
                    <th>卖出价</th>
                    <th><InfoTip tip={tip("r_multiple", "")}>实际盈亏(R)</InfoTip></th>
                    <th><InfoTip tip={tip("reward_risk", "")}>当时盈亏比</InfoTip></th>
                    <th>持有(K)</th>
                    <th>退出原因</th>
                    <th><InfoTip tip={tip("is_first_touch", "")}>首次回撤</InfoTip></th>
                    <th>依据</th>
                  </tr>
                </thead>
                <tbody>
                  {filteredTrades.map((t) => (
                    <tr key={`${t.symbol}-${t.signal_date}-${t.ma_period}-${t.entry_date}`}>
                      <td>{t.symbol}</td>
                      <td>{t.signal_date}</td>
                      <td>{t.entry_date}</td>
                      <td>{fmtNum(t.entry_price)}</td>
                      <td>{fmtNum(t.stop_price)}</td>
                      <td>{t.exit_date ?? "持有中"}</td>
                      <td>{t.exit_price != null ? fmtNum(t.exit_price) : "—"}</td>
                      <td className={tone(t.r_net)}>{fmtNum(t.r_net)}</td>
                      <td>{t.reward_risk != null ? fmtNum(t.reward_risk, 1) : "—"}</td>
                      <td>{t.holding_bars}</td>
                      <td>{EXIT_REASON_CN[t.exit_reason ?? ""] ?? t.exit_reason ?? "—"}</td>
                      <td>{t.is_first_touch ? "是" : "否"}</td>
                      <td className="bt-reason" title={t.entry_reason ?? ""}>
                        {(t.entry_reason ?? "").slice(0, 24) || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </section>
        </>
      )}

      <section className="bt-section">
        <h3>历史回测记录</h3>
        {runs.length === 0 && <p className="muted-chip">还没有记录，跑一次就有了。</p>}
        {runs.length > 0 && (
          <table className="bt-table">
            <thead>
              <tr>
                <th>时间</th>
                <th>盈亏比门槛</th>
                <th>入场</th>
                <th>退出</th>
                <th>费用</th>
                <th>标的数</th>
                <th>笔数</th>
                <th>期望R</th>
                <th>盈利因子</th>
                <th>状态</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {runs.map((r) => (
                <tr key={r.run_id}>
                  <td>{r.created_at ?? "—"}</td>
                  <td>
                    {(r.params as { rr_min?: number | null } | undefined)?.rr_min ?? "—"}
                  </td>
                  <td>{String((r.params as { entry_variant?: string } | undefined)?.entry_variant ?? "—")}</td>
                  <td>{String((r.params as { exit_variant?: string } | undefined)?.exit_variant ?? "—").slice(0, 12)}</td>
                  <td>{String((r.params as { fee_label?: string } | undefined)?.fee_label ?? "—")}</td>
                  <td>{r.symbols_count ?? "—"}</td>
                  <td>{r.trade_count ?? "—"}</td>
                  <td className={tone(r.expectancy_r)}>{fmtNum(r.expectancy_r)}</td>
                  <td>{fmtNum(r.profit_factor)}</td>
                  <td>{r.status}{Object.keys((r.params as { overrides?: Record<string, number> } | undefined)?.overrides ?? {}).length ? " 🧪" : ""}</td>
                  <td>
                    {r.status === "done" && (
                      <button
                        className="bt-load"
                        onClick={() => {
                          backtestApi.getRun(r.run_id).then((d) => {
                            if ((d as BacktestRunSummary).status === "done") {
                              setResult(d as BacktestRunResult);
                              setStatus("done");
                              setRunId(r.run_id);
                              window.scrollTo({ top: 0, behavior: "smooth" });
                            }
                          });
                        }}
                      >
                        查看
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
        {runId && status !== "running" && (
          <p className="bt-meta">当前结果来自记录 {runId}</p>
        )}
      </section>
        </>
      )}
    </div>
  );
}
