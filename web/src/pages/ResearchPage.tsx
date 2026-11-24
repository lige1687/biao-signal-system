import { useEffect, useRef } from "react";
import FlagshipSection from "../components/FlagshipSection";
import { REPORTS_INDEX } from "../data/reportsIndex";
import * as echarts from "echarts";
import "./page-reading.css";
import {
  FALSIFIED,
  FUNDAMENTAL_PANEL,
  GATE_EVOLUTION,
  KPI_CARDS,
  MODULE_E,
  OPS_LINE,
  SEMANTIC_CLOSEOUT,
  SESSION_META,
  SYMBOL_CARDS,
  WALK_FORWARD,
} from "../data/researchRound";

/**
 * 本轮研究展示页（静态数据，来源 docs/experiments 落盘 JSON）。
 * 只读展示，不调后端；数据更新在 researchRound.ts 同步。
 * 样式收编在 styles.css 的 rs-* 段（2026-09 密度重构，去内联）。
 */
function Section({ title, sub, children }: {
  title: string; sub?: string; children: React.ReactNode;
}) {
  return (
    <div className="rs-section">
      <div className="section-title">
        {title} {sub && <span className="count">{sub}</span>}
      </div>
      {children}
    </div>
  );
}

function GateChart() {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const chart = echarts.init(ref.current);
    const arms = GATE_EVOLUTION.filter((r) => !r.arm.includes("★"));
    chart.setOption({
      grid: { left: 70, right: 60, top: 30, bottom: 60 },
      tooltip: { trigger: "axis" },
      legend: { data: ["终值(万)", "全局回撤(%)"], top: 0 },
      xAxis: { type: "value" },
      yAxis: {
        type: "category",
        data: [...arms.map((r) => r.arm)].reverse(),
        axisLabel: { fontSize: 11 },
      },
      series: [
        {
          name: "终值(万)", type: "bar",
          data: [...arms.map((r) => r.final)].reverse(),
          itemStyle: { color: "#4da3ff" }, barWidth: 12,
          label: { show: true, position: "right", fontSize: 11 },
        },
        {
          name: "全局回撤(%)", type: "bar",
          data: [...arms.map((r) => -r.dd)].reverse(),
          itemStyle: { color: "#e06c5a" }, barWidth: 12,
          label: { show: true, position: "left", fontSize: 11 },
        },
      ],
    });
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => { window.removeEventListener("resize", onResize); chart.dispose(); };
  }, []);
  return <div ref={ref} className="rs-chart" />;
}

export default function ResearchPage() {
  return (
    <div className="page rs-page">
      <div className="pg-head">
        <div className="pg-head-title">
          <h1>历史研究回顾</h1>
          <span className="pg-head-sub">
            所有结论都先写死标准再跑数据（防止事后找理由）· 每个结果都重跑两遍验证一致
          </span>
        </div>
        <div className="pg-head-kv">
          <span className="pg-kv"><span className="k">周期</span><b>{SESSION_META.dateRange}</b></span>
          <span className="pg-kv"><span className="k">轮次</span><b>{SESSION_META.rounds} 轮</b></span>
          <span className="pg-kv"><span className="k">判定量</span><b>约 {SESSION_META.hypothesisCount} 组</b></span>
          <span className="pg-kv"><span className="k">详细档案</span><b>{SESSION_META.reports.length} 份，见下方</b></span>
        </div>
      </div>
      <p className="rs-history-note">{SESSION_META.title} · {SESSION_META.dateRange}。这是当时的研究记录；查看已接入的因子证据请到 <a href="/factors">因子研究</a>。</p>
      <details className="rs-source-paths"><summary>查看当时的原始档案路径</summary><ul>{SESSION_META.reports.map(path => <li key={path}><code>{path}</code></li>)}</ul></details>
      <div className="rs-lede">
        <strong>当时的运行安排：</strong>{OPS_LINE}
      </div>

      <div className="card-grid">
        {KPI_CARDS.map((k) => (
          <div className="card" key={k.label} style={{ cursor: "default" }}>
            <div className="row">
              <span className="name">{k.label}</span>
            </div>
            <div className={`rs-kpi-value tone-${k.tone === "warn" ? "warn" : k.tone === "down" ? "down" : "up"}`}>
              {k.value}
            </div>
            <div className="rs-kpi-sub">{k.sub}</div>
          </div>
        ))}
      </div>

      <FlagshipSection />
      <Section
        title="语义组合收口轮"
        sub={`${SEMANTIC_CLOSEOUT.dateRange} · ${SEMANTIC_CLOSEOUT.meta}`}
      >
        <table className="rs-table">
          <thead>
            <tr>
              <th>方向</th><th>判定</th><th>关键发现</th><th>归档</th>
            </tr>
          </thead>
          <tbody>
            {SEMANTIC_CLOSEOUT.rows.map((r) => (
              <tr key={r.name} className={r.name.includes("★") ? "star" : undefined}>
                <td className="strong" style={{ whiteSpace: "nowrap" }}>{r.name}</td>
                <td style={{ whiteSpace: "nowrap" }}>{r.verdict}</td>
                <td>{r.key}</td>
                <td className="faint">{r.report}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="rs-takeaway">{SEMANTIC_CLOSEOUT.takeaway}</div>
      </Section>
      <Section title="报告存档" sub="多路回测统一归档 · 自包含离线 HTML">
        <div className="rs-report-wall">
          {REPORTS_INDEX.map((r) => (
            <a key={r.id} href={r.href} target="_blank" rel="noreferrer" className="rs-report-link">
              {r.status === "falsified" ? "❌" : r.status === "passed" ? "✅" : r.status === "watch" ? "👁" : "⚖️"}{" "}
              [{r.team}] {r.title}
            </a>
          ))}
        </div>
        <details className="rs-note"><summary>维护说明</summary><p>新增报告：HTML 放 web/public/reports/，条目追加到 web/src/data/reportsIndex.ts（只追加，不改别人的）。</p></details>
      </Section>
      <Section title="① 仓位方案比拼" sub="同样 100 万 · 同样十年 · 同样的买卖点，只有仓位管法不同">
        <GateChart />
        <table className="rs-table" style={{ marginTop: 8 }}>
          <thead>
            <tr>
              <th>臂</th><th>终值(万)</th><th>全局DD</th>
              <th>阴跌段</th><th>2026背离</th><th>备注</th>
            </tr>
          </thead>
          <tbody>
            {GATE_EVOLUTION.map((r) => (
              <tr key={r.arm} className={r.arm.includes("★") ? "star" : undefined}>
                <td className="strong">{r.arm}</td>
                <td>{r.final.toFixed(1)}</td>
                <td>{r.dd}%</td>
                <td>{r.seg}%</td>
                <td>{r.dd26}%</td>
                <td className="faint">{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section title="② 严格考试：只用过去的数据做决定" sub={WALK_FORWARD.benchmark}>
        <table className="rs-table">
          <thead>
            <tr>
              <th>版本</th><th>年化</th><th>最大回撤</th>
              <th>干净度</th><th>判定</th><th>说明</th>
            </tr>
          </thead>
          <tbody>
            {WALK_FORWARD.rows.map((r) => (
              <tr key={r.version}>
                <td className="strong">{r.version}</td>
                <td className="up">{r.cagr}</td>
                <td className="down">{r.dd}</td>
                <td className="faint">{r.clean}</td>
                <td>{r.verdict}</td>
                <td className="faint">{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <ul className="rs-conclusion-list">
          {WALK_FORWARD.conclusions.map((c) => <li key={c}>{c}</li>)}
        </ul>
      </Section>

      <Section title="③ 美股『市场恐慌到极端时买入』策略" sub="美股 1986-2026 · 40 年 · 极端恐慌才动手">
        <table className="rs-table">
          <thead>
            <tr><th>臂</th><th>终值</th><th>年化</th><th>备注</th></tr>
          </thead>
          <tbody>
            {MODULE_E.rows.map((r) => (
              <tr key={r.arm}>
                <td className="strong">{r.arm}</td>
                <td>{r.final}</td><td>{r.cagr}</td>
                <td className="faint">{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ fontSize: "var(--fs-xs)", marginTop: 8 }}>
          40 年里 14 次触发（全是历史大底）：
          {MODULE_E.v3Signals.map((s) => (
            <span key={s} className="tag" style={{ margin: 2, display: "inline-block" }}>{s}</span>
          ))}
          <div className="rs-note">{MODULE_E.verdict}</div>
        </div>
      </Section>

      <Section title="④ 单个标的的成绩单（表现最好的 8 个）" sub={SYMBOL_CARDS.insight}>
        <table className="rs-table">
          <thead>
            <tr>
              <th>标的</th><th>笔数</th><th>累计R</th>
              <th>策略回撤</th><th>对照（持有 年化/回撤）</th>
            </tr>
          </thead>
          <tbody>
            {SYMBOL_CARDS.top.map((r) => (
              <tr key={r.sym}>
                <td className="strong">{r.sym} <span className="faint">{r.name}</span></td>
                <td>{r.n}</td>
                <td className="up">{r.r}</td>
                <td>{r.dd}</td>
                <td className="faint">{r.bh}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section title="⑤ 各种信息源大比拼（12 个指标）" sub="指标出现极端后，指数未来 12 个月的平均涨跌">
        <table className="rs-table">
          <thead>
            <tr>
              <th>指标</th><th>极端高时之后</th><th>极端低时之后</th>
              <th>平常时</th><th>表面看</th><th>严格重考后</th>
            </tr>
          </thead>
          <tbody>
            {FUNDAMENTAL_PANEL.rows.map((r) => (
              <tr key={r.ind}>
                <td className="strong">{r.ind}</td>
                <td className={r.hi.startsWith("−") ? "down" : "up"}>{r.hi}</td>
                <td className={r.lo.startsWith("−") ? "down" : "up"}>{r.lo}</td>
                <td>{r.base}</td>
                <td>{r.verdict}</td>
                <td className="faint">{r.final}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div className="rs-lesson">⚠ {FUNDAMENTAL_PANEL.lesson}</div>
      </Section>

      <Section title="⑥ 试过、否掉、封存的方向" sub="别再浪费时间重测">
        <div>
          {FALSIFIED.map((f) => (
            <span key={f} className="tag rs-falsified">{f}</span>
          ))}
        </div>
      </Section>
    </div>
  );
}
