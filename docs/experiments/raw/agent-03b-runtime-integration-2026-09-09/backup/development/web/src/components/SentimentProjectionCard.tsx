import { useEffect, useMemo, useRef, useState } from "react";
import * as echarts from "echarts";
import { useQuery } from "@tanstack/react-query";
import { api, fundamentalsApi } from "../api/client";
import { fmt, pctClass } from "../utils/format";

/**
 * 情绪 × 标普500 投影散点（关系图）。
 *
 * X = 情绪读数（AAII 看涨-看跌净值 / NAAIM 暴露指数），Y = 此后 N 周标普500 涨跌幅。
 * 发布时间对齐（无前视）：入场价 = available_at（调查周四发布）当天或之后第一个收盘价，
 * 出场价 = 入场日 + N 周后第一个收盘价。红点 = 后续上涨，绿点 = 后续下跌；
 * 灰虚线 = 阈值（AAII ±25 / NAAIM 40、80）与 0 轴；蓝虚线 = 最小二乘拟合。
 * 与同页「同窗对照」互补：对照看拐点叙事，投影看关系强度与极端区的后续分布。
 */

type SeriesKey = "aaii" | "naaim";

const HORIZONS = [4, 8, 13] as const;
type Horizon = (typeof HORIZONS)[number];

const META: Record<
  SeriesKey,
  { title: string; xName: string; cuts: [number, number]; thresholds: number[] }
> = {
  aaii: {
    title: "AAII 多空净值",
    xName: "看涨-看跌（%）",
    cuts: [-25, 25],
    thresholds: [-25, 25],
  },
  naaim: {
    title: "NAAIM 暴露指数",
    xName: "暴露指数（%）",
    cuts: [40, 80],
    thresholds: [40, 80],
  },
};

interface ProjPoint {
  week: string;
  x: number;
  fwd: number;
  entryDay: string;
  exitDay: string;
}

/** 升序日期数组里找第一个 >= day 的下标。 */
function lowerBound(dates: string[], day: string): number | null {
  let lo = 0;
  let hi = dates.length;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (dates[mid] < day) lo = mid + 1;
    else hi = mid;
  }
  return lo < dates.length ? lo : null;
}

function addDays(day: string, n: number): string {
  const d = new Date(`${day}T00:00:00Z`);
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

function pearson(pts: ProjPoint[]): number | null {
  const n = pts.length;
  if (n < 3) return null;
  const mx = pts.reduce((a, p) => a + p.x, 0) / n;
  const my = pts.reduce((a, p) => a + p.fwd, 0) / n;
  let sxy = 0;
  let sxx = 0;
  let syy = 0;
  for (const p of pts) {
    sxy += (p.x - mx) * (p.fwd - my);
    sxx += (p.x - mx) ** 2;
    syy += (p.fwd - my) ** 2;
  }
  if (sxx === 0 || syy === 0) return null;
  return sxy / Math.sqrt(sxx * syy);
}

export default function SentimentProjectionCard() {
  const [series, setSeries] = useState<SeriesKey>("aaii");
  const [horizon, setHorizon] = useState<Horizon>(4);
  const meta = META[series];

  // 与 OverlaySection / SentimentSp500Card 共享同一 queryKey，不产生重复请求
  const { data: ov } = useQuery({
    queryKey: ["fundOverlay", 20],
    queryFn: () => fundamentalsApi.overlayHistory(20),
    staleTime: 12 * 3600_000,
    retry: 1,
  });
  const { data: hist, isLoading } = useQuery({
    queryKey: ["sentimentHistory", series],
    queryFn: () => api.marketContextSentimentHistory(series),
    staleTime: 5 * 60_000,
  });

  const sp = ov?.series?.sp500;
  const dates = useMemo(() => sp?.dates ?? [], [sp]);
  const values = useMemo(() => sp?.values ?? [], [sp]);

  const { points, pending } = useMemo(() => {
    const out: ProjPoint[] = [];
    let latest: { week: string; x: number } | null = null;
    for (const o of hist?.observations ?? []) {
      const x = series === "aaii" ? o.bull_bear : o.exposure_index;
      if (x == null) continue;
      // 发布时间对齐：available_at 缺失时退回调查周周一 + 3 天（AAII/NAAIM 均周四发布）
      const avail = (o.available_at?.slice(0, 10) ?? addDays(o.survey_week, 3));
      const ei = lowerBound(dates, avail);
      if (ei == null) continue;
      latest = { week: o.survey_week, x };
      const xi = lowerBound(dates, addDays(dates[ei], horizon * 7));
      if (xi == null) continue; // 最近 N 周内无完整前瞻窗口
      out.push({
        week: o.survey_week,
        x,
        fwd: (values[xi] / values[ei] - 1) * 100,
        entryDay: dates[ei],
        exitDay: dates[xi],
      });
    }
    return { points: out, pending: latest };
  }, [hist, dates, values, series, horizon]);

  const corr = useMemo(() => pearson(points), [points]);

  const buckets = useMemo(() => {
    const [lo, hi] = meta.cuts;
    const defs = [
      { name: series === "aaii" ? `极度看跌（< ${lo}）` : `低敞口（< ${lo}）`, pick: (x: number) => x < lo },
      { name: "中间区", pick: (x: number) => x >= lo && x <= hi },
      { name: series === "aaii" ? `极度看涨（> ${hi}）` : `高敞口（> ${hi}）`, pick: (x: number) => x > hi },
    ];
    return defs.map((d) => {
      const inb = points.filter((p) => d.pick(p.x));
      const n = inb.length;
      const mean = n ? inb.reduce((a, p) => a + p.fwd, 0) / n : null;
      const median = n
        ? [...inb].sort((a, b) => a.fwd - b.fwd)[Math.floor((n - 1) / 2)].fwd
        : null;
      const hit = n ? inb.filter((p) => p.fwd > 0).length / n : null;
      return { name: d.name, n, mean, median, hit };
    });
  }, [points, meta, series]);

  const chartRef = useRef<HTMLDivElement>(null);
  const instRef = useRef<echarts.ECharts | null>(null);

  useEffect(() => {
    if (!chartRef.current) return;
    const inst = echarts.init(chartRef.current, undefined, { renderer: "canvas" });
    instRef.current = inst;
    const ro = new ResizeObserver(() => inst.resize());
    ro.observe(chartRef.current);
    return () => {
      ro.disconnect();
      inst.dispose();
      instRef.current = null;
    };
  }, []);

  useEffect(() => {
    const inst = instRef.current;
    if (!inst) return;
    const xs = points.map((p) => p.x);
    const reg: [number, number][] = [];
    if (points.length >= 3 && corr != null) {
      const mx = xs.reduce((a, b) => a + b, 0) / xs.length;
      const my = points.reduce((a, p) => a + p.fwd, 0) / points.length;
      let sxx = 0;
      let sxy = 0;
      for (const p of points) {
        sxx += (p.x - mx) ** 2;
        sxy += (p.x - mx) * (p.fwd - my);
      }
      if (sxx > 0) {
        const slope = sxy / sxx;
        const x0 = Math.min(...xs);
        const x1 = Math.max(...xs);
        reg.push([x0, my + slope * (x0 - mx)], [x1, my + slope * (x1 - mx)]);
      }
    }
    inst.setOption(
      {
        grid: { left: 56, right: 24, top: 34, bottom: 44 },
        tooltip: {
          trigger: "item",
          formatter: (p: unknown) => {
            const d = p as {
              data: { week?: string; entryDay?: string; exitDay?: string };
              value: [number, number];
            };
            const [x, fwd] = d.value ?? [0, 0];
            const span = d.data?.entryDay
              ? `${d.data.entryDay} → ${d.data.exitDay}`
              : "-";
            return [
              `调查周 ${d.data?.week ?? "-"}`,
              `${meta.xName}：${fmt(x, 1)}`,
              `标普 ${horizon} 周后：<span class="${pctClass(fwd)}">${fmt(fwd, 2, "%")}</span>`,
              `窗口 ${span}`,
            ].join("<br/>");
          },
        },
        xAxis: {
          type: "value",
          name: meta.xName,
          nameLocation: "middle",
          nameGap: 30,
          nameTextStyle: { fontSize: 11, color: "#6b7280" },
          axisLabel: { fontSize: 10, color: "#6b7280" },
          splitLine: { lineStyle: { color: "#eef1f5" } },
        },
        yAxis: {
          type: "value",
          name: `标普 ${horizon} 周后（%）`,
          nameTextStyle: { fontSize: 11, color: "#6b7280" },
          axisLabel: { fontSize: 10, color: "#6b7280" },
          splitLine: { lineStyle: { color: "#eef1f5" } },
        },
        series: [
          {
            name: "投影点",
            type: "scatter",
            symbolSize: 9,
            // 越新的点越实、越旧的点越淡：既保住关系形态，又能看出关系是否随时间稳定
            data: points.map((p, i) => {
              const alpha = points.length > 1 ? 0.35 + 0.6 * (i / (points.length - 1)) : 0.8;
              return {
                value: [p.x, p.fwd],
                week: p.week,
                entryDay: p.entryDay,
                exitDay: p.exitDay,
                itemStyle: {
                  color: p.fwd >= 0 ? `rgba(227,61,71,${alpha})` : `rgba(22,163,74,${alpha})`,
                  borderColor: p.fwd >= 0 ? "#e33d47" : "#16a34a",
                },
              };
            }),
            markLine: {
              symbol: "none",
              silent: true,
              animation: false,
              lineStyle: { type: "dashed", color: "#9ca3af", width: 1 },
              label: { fontSize: 10, color: "#6b7280" },
              data: [
                ...meta.thresholds.map((t) => ({ xAxis: t, label: { formatter: `${t}` } })),
                { yAxis: 0, label: { formatter: "0" } },
                // 当前读数落在 X 轴哪里：一眼看出"现在处于历史分布的什么位置"
                ...(pending != null
                  ? [
                      {
                        xAxis: pending.x,
                        lineStyle: { type: "solid" as const, color: "#f59e0b", width: 1.6 },
                        label: { formatter: `当前 ${pending.x.toFixed(1)}`, color: "#f59e0b" },
                      },
                    ]
                  : []),
              ],
            },
          },
          ...(reg.length
            ? [
                {
                  name: "拟合线",
                  type: "line" as const,
                  data: reg,
                  silent: true,
                  symbol: "none",
                  lineStyle: { type: "dashed" as const, color: "#3a7bd5", width: 1.4 },
                  tooltip: { show: false },
                },
              ]
            : []),
        ],
      },
      true,
    );
  }, [points, pending, corr, meta, horizon]);

  if (isLoading) {
    return <div className="card-skeleton" style={{ height: 300 }} />;
  }
  if (!sp || dates.length < 2) {
    return (
      <div className="macro-card todo-card">
        <div className="macro-head"><span className="macro-name">情绪 × 标普500 投影</span></div>
        <div className="macro-note">标普500 长周期历史加载中或不可用，稍后自动重试。</div>
      </div>
    );
  }
  if ((hist?.observations?.length ?? 0) === 0) {
    return (
      <div className="macro-card todo-card">
        <div className="macro-head"><span className="macro-name">情绪 × 标普500 投影</span></div>
        <div className="macro-note">暂无情绪读数：每周四 launchd 自动抓取 NAAIM/AAII，攒满后此处显示关系图。</div>
      </div>
    );
  }

  return (
    <div className="macro-card">
      <div className="macro-head">
        <span className="macro-name">情绪 × 标普500 投影（逆向验证）</span>
        {pending && (
          <span className="macro-chip neutral">
            最新 {meta.title} {fmt(pending.x, 1)}（{pending.week}）
          </span>
        )}
      </div>
      <div className="overlay-market-controls" style={{ gap: 4, marginBottom: 6 }}>
        {(["aaii", "naaim"] as SeriesKey[]).map((k) => (
          <button
            key={k}
            type="button"
            className={`ma-toggle${series === k ? " on" : ""}`}
            onClick={() => setSeries(k)}
          >
            {META[k].title}
          </button>
        ))}
        <span className="muted" style={{ margin: "0 2px" }}>·</span>
        {HORIZONS.map((h) => (
          <button
            key={h}
            type="button"
            className={`ma-toggle${horizon === h ? " on" : ""}`}
            onClick={() => setHorizon(h)}
          >
            {h} 周
          </button>
        ))}
        <span className="muted" style={{ marginLeft: 8, fontSize: 12 }}>
          相关系数 {corr == null ? "—" : corr.toFixed(2)}（n={points.length}）
        </span>
      </div>
      <div ref={chartRef} className="macro-chart" style={{ height: 320 }} />
      <div className="proj-buckets">
        {buckets.map((b) => (
          <div key={b.name} className="proj-bucket">
            <div className="proj-bucket-name">
              {b.name}
              {b.n > 0 && b.n < 8 && <span title="样本过少，统计意义有限"> ⚠</span>}
            </div>
            <div className="proj-bucket-n">{b.n} 期</div>
            <div className={`proj-bucket-mean ${b.mean == null ? "" : pctClass(b.mean)}`}>
              {b.mean == null ? "—" : `平均 ${fmt(b.mean, 2, "%")}`}
              {b.median == null ? "" : ` · 中位 ${fmt(b.median, 2, "%")}`}
            </div>
            <div className="proj-bucket-hit">
              上涨率 {b.hit == null ? "—" : `${(b.hit * 100).toFixed(0)}%`}
            </div>
          </div>
        ))}
      </div>
      <div className="macro-note">
        X = {meta.title}（灰虚线 {meta.thresholds.join(" / ")} 为经验阈值，
        <span style={{ color: "#f59e0b" }}>橙色实线 = 当前读数位置</span>），Y = 发布后 {horizon} 周标普涨跌；
        红点涨 / 绿点跌，点越淡 = 越早的样本，蓝虚线为最小二乘拟合。负相关 = 情绪越乐观后续越弱（逆向指标特征）。
        入场价取 available_at（周四发布）当天或之后首个收盘，无前视；周频采样与 {horizon} 周窗口存在重叠，
        相关系数与分桶按「有效样本」解读而非独立样本；样本自 {points[0]?.week ?? "-"} 起、
        相关≠因果，仅作研究参考，不构成投资建议。
      </div>
    </div>
  );
}
