import { useEffect, useRef } from "react";
import FlagshipSection from "../components/FlagshipSection";
import * as echarts from "echarts";
import {
  FALSIFIED,
  FUNDAMENTAL_PANEL,
  GATE_EVOLUTION,
  KPI_CARDS,
  MODULE_E,
  OPS_LINE,
  SESSION_META,
  SYMBOL_CARDS,
  WALK_FORWARD,
} from "../data/researchRound";

/**
 * 本轮研究展示页（静态数据，来源 docs/experiments 落盘 JSON）。
 * 只读展示，不调后端；数据更新在 researchRound.ts 同步。
 */
const th: React.CSSProperties = {
  textAlign: "left", padding: "6px 10px", color: "var(--text-faint)",
  fontWeight: 500, fontSize: 12, borderBottom: "1px solid var(--border)",
};
const td: React.CSSProperties = {
  padding: "6px 10px", fontSize: 13, borderBottom: "1px solid var(--border)",
  fontVariantNumeric: "tabular-nums",
};
const panel: React.CSSProperties = {
  background: "var(--bg-card)", borderRadius: 10, padding: "14px 16px",
  margin: "14px 0", border: "1px solid var(--border)",
};

function Section({ title, sub, children }: {
  title: string; sub?: string; children: React.ReactNode;
}) {
  return (
    <div style={panel}>
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
  return <div ref={ref} style={{ width: "100%", height: 240 }} />;
}

export default function ResearchPage() {
  return (
    <div style={{ maxWidth: 1080, margin: "0 auto", padding: "18px 16px 60px" }}>
      <h2 style={{ marginBottom: 4 }}>
        {SESSION_META.title}
        <span className="count" style={{ marginLeft: 10 }}>
          {SESSION_META.dateRange} · {SESSION_META.rounds} 轮 · 判定量约 {SESSION_META.hypothesisCount} 组
        </span>
      </h2>
      <div style={{ color: "var(--text-dim)", fontSize: 13, marginBottom: 8 }}>
        所有结论都先写死标准再跑数据（防止事后找理由）· 每个结果都重跑两遍验证一致 · {OPS_LINE}
      </div>

      <div className="card-grid" style={{ gridTemplateColumns: "repeat(auto-fill,minmax(300px,1fr))" }}>
        {KPI_CARDS.map((k) => (
          <div className="card" key={k.label} style={{ cursor: "default" }}>
            <div className="row">
              <span className="name" style={{ fontSize: 13 }}>{k.label}</span>
            </div>
            <div style={{
              fontSize: 24, fontWeight: 700, margin: "6px 0 2px",
              color: k.tone === "warn" ? "#d9a441" : k.tone === "down" ? "var(--down)" : "var(--up)",
            }}>{k.value}</div>
            <div style={{ fontSize: 12, color: "var(--text-faint)" }}>{k.sub}</div>
          </div>
        ))}
      </div>

      <FlagshipSection />
      <Section title="报告存档" sub="自包含离线 HTML · 仓库 web/public/reports/ · 拉库后可直接双击打开">
        <div style={{ display: "flex", flexWrap: "wrap", gap: 10, marginTop: 4 }}>
          {[
            ["旗舰三组合总览（净值·买卖点·仓位带，2026-09-01）", "/reports/flagship-2026-09-01.html"],
            ["两只版逐笔调仓明细（139 笔，2026-09-01）", "/reports/duo-trades-2026-09-01.html"],
            ["本轮总报告（宽度/ETF/虹吸全档案，2026-08-31）", "/reports/round-2026-08-31.html"],
            ["上轮总报告（B 形态终审矩阵，2026-08-28）", "/reports/round-2026-08-28.html"],
          ].map(([label, href]) => (
            <a key={href} href={href} target="_blank" rel="noreferrer"
               style={{ fontSize: 13, padding: "8px 12px", border: "1px solid var(--border)",
                        borderRadius: 8, textDecoration: "none", color: "var(--text-main)",
                        background: "var(--bg-card)" }}>
              📄 {label}
            </a>
          ))}
        </div>
      </Section>
      <Section title="① 仓位方案比拼" sub="同样 100 万 · 同样十年 · 同样的买卖点，只有仓位管法不同">
        <GateChart />
        <table style={{ width: "100%", borderCollapse: "collapse", marginTop: 8 }}>
          <thead>
            <tr>
              <th style={th}>臂</th><th style={th}>终值(万)</th><th style={th}>全局DD</th>
              <th style={th}>阴跌段</th><th style={th}>2026背离</th><th style={th}>备注</th>
            </tr>
          </thead>
          <tbody>
            {GATE_EVOLUTION.map((r) => (
              <tr key={r.arm} style={r.arm.includes("★") ? { background: "rgba(77,163,255,.08)" } : undefined}>
                <td style={{ ...td, fontWeight: 600 }}>{r.arm}</td>
                <td style={td}>{r.final.toFixed(1)}</td>
                <td style={td}>{r.dd}%</td>
                <td style={td}>{r.seg}%</td>
                <td style={td}>{r.dd26}%</td>
                <td style={{ ...td, color: "var(--text-faint)" }}>{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section title="② 严格考试：只用过去的数据做决定" sub={WALK_FORWARD.benchmark}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={th}>版本</th><th style={th}>年化</th><th style={th}>最大回撤</th>
              <th style={th}>干净度</th><th style={th}>判定</th><th style={th}>说明</th>
            </tr>
          </thead>
          <tbody>
            {WALK_FORWARD.rows.map((r) => (
              <tr key={r.version}>
                <td style={{ ...td, fontWeight: 600 }}>{r.version}</td>
                <td style={{ ...td, color: "var(--up)" }}>{r.cagr}</td>
                <td style={{ ...td, color: "var(--down)" }}>{r.dd}</td>
                <td style={{ ...td, color: "var(--text-faint)" }}>{r.clean}</td>
                <td style={td}>{r.verdict}</td>
                <td style={{ ...td, color: "var(--text-faint)" }}>{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <ul style={{ margin: "10px 0 0", paddingLeft: 18, fontSize: 13, color: "var(--text-dim)" }}>
          {WALK_FORWARD.conclusions.map((c) => <li key={c}>{c}</li>)}
        </ul>
      </Section>

      <Section title="③ 美股『市场恐慌到极端时买入』策略" sub="美股 1986-2026 · 40 年 · 极端恐慌才动手">
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr><th style={th}>臂</th><th style={th}>终值</th><th style={th}>年化</th><th style={th}>备注</th></tr>
          </thead>
          <tbody>
            {MODULE_E.rows.map((r) => (
              <tr key={r.arm}>
                <td style={{ ...td, fontWeight: 600 }}>{r.arm}</td>
                <td style={td}>{r.final}</td><td style={td}>{r.cagr}</td>
                <td style={{ ...td, color: "var(--text-faint)" }}>{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ fontSize: 13, marginTop: 8 }}>
          40 年里 14 次触发（全是历史大底）：
          {MODULE_E.v3Signals.map((s) => (
            <span key={s} className="tag" style={{ margin: 2, display: "inline-block" }}>{s}</span>
          ))}
          <div style={{ color: "var(--text-dim)", marginTop: 6 }}>{MODULE_E.verdict}</div>
        </div>
      </Section>

      <Section title="④ 单个标的的成绩单（表现最好的 8 个）" sub={SYMBOL_CARDS.insight}>
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={th}>标的</th><th style={th}>笔数</th><th style={th}>累计R</th>
              <th style={th}>策略回撤</th><th style={th}>对照（持有 年化/回撤）</th>
            </tr>
          </thead>
          <tbody>
            {SYMBOL_CARDS.top.map((r) => (
              <tr key={r.sym}>
                <td style={{ ...td, fontWeight: 600 }}>{r.sym} <span style={{ color: "var(--text-faint)", fontSize: 11 }}>{r.name}</span></td>
                <td style={td}>{r.n}</td>
                <td style={{ ...td, color: "var(--up)" }}>{r.r}</td>
                <td style={td}>{r.dd}</td>
                <td style={{ ...td, color: "var(--text-faint)" }}>{r.bh}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Section>

      <Section title="⑤ 各种信息源大比拼（12 个指标）" sub="指标出现极端后，指数未来 12 个月的平均涨跌">
        <table style={{ width: "100%", borderCollapse: "collapse" }}>
          <thead>
            <tr>
              <th style={th}>指标</th><th style={th}>极端高时之后</th><th style={th}>极端低时之后</th>
              <th style={th}>平常时</th><th style={th}>表面看</th><th style={th}>严格重考后</th>
            </tr>
          </thead>
          <tbody>
            {FUNDAMENTAL_PANEL.rows.map((r) => (
              <tr key={r.ind}>
                <td style={{ ...td, fontWeight: 600 }}>{r.ind}</td>
                <td style={{ ...td, color: r.hi.startsWith("−") ? "var(--down)" : "var(--up)" }}>{r.hi}</td>
                <td style={{ ...td, color: r.lo.startsWith("−") ? "var(--down)" : "var(--up)" }}>{r.lo}</td>
                <td style={td}>{r.base}</td>
                <td style={td}>{r.verdict}</td>
                <td style={{ ...td, color: "var(--text-faint)" }}>{r.final}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <div style={{ marginTop: 8, fontSize: 13, color: "#d9a441" }}>⚠ {FUNDAMENTAL_PANEL.lesson}</div>
      </Section>

      <Section title="⑥ 试过、否掉、封存的方向" sub="别再浪费时间重测">
        <div>
          {FALSIFIED.map((f) => (
            <span key={f} className="tag" style={{
              display: "inline-block", margin: 3, opacity: 0.75,
              textDecoration: "line-through",
            }}>{f}</span>
          ))}
        </div>
      </Section>

      <div style={{ fontSize: 12, color: "var(--text-faint)", marginTop: 16 }}>
        详细档案（给接手的人看）：{SESSION_META.reports.join(" · ")}
      </div>
    </div>
  );
}
