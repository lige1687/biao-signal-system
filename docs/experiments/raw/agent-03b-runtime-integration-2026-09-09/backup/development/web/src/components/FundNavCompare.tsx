import { useEffect, useMemo, useRef, useState } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { portfolioApi } from "../api/client";
import InfoTip from "./InfoTip";
import type { FundNavItem } from "../types";

/** 净值对比可选基金（来自持仓快照，按市值降序）。 */
export interface FundNavPick {
  code: string;
  name: string;
  amount: number;
}

const MAX_PICK = 6;
const PALETTE = ["#2563eb", "#e33d47", "#0d9488", "#b45309", "#7c3aed", "#65a30d"];
const WINDOWS: { key: number; label: string }[] = [
  { key: 182, label: "近6月" },
  { key: 365, label: "近1年" },
  { key: 1095, label: "近3年" },
  { key: 0, label: "成立以来" },
];

const TIPS = {
  logAxis:
    "对数轴：竖直方向上同样的高度 = 同样的涨跌「比例」。普通坐标里净值从 1 涨到 2（翻倍）只画出从 2 涨到 4（也翻倍）一半的高度，早期波动看着被压扁；对数轴把两个翻倍画成一样高，看长期涨跌幅不失真。",
  pctView:
    "涨跌幅%：把窗口内第一天的净值定为 100，之后每个点都除以它再乘 100。线上的数字直接就是「从窗口起点到现在涨跌了百分之几」，几只基金可以直接比大小。",
  accNav:
    "累计净值 = 单位净值 + 历次分红加回。基金分红当天单位净值会人为「跳水」——那是把钱分给你了，不是亏损；看长期涨跌幅用累计净值才不失真。单位净值是你实际申赎的价格口径。",
};

interface AlignedRow {
  item: FundNavItem;
  /** 按全表并集日期轴对齐后的原始净值（缺交易日为 null）。 */
  values: (number | null)[];
  /** 该基金自己在窗口内的首个有效净值（涨跌幅%视图的基准）。 */
  base: number | null;
  /** 该基金最后一个有效点的序号（图例后缀「区间涨跌幅」用）。 */
  lastIndex: number;
}

/**
 * 基金净值对比（涨跌幅视角）：把几只基金放到同一把尺子下看涨跌。
 *
 * 解决的问题：外部 App 的净值图是普通坐标 + 各画各的，长期涨幅把早期
 * 波动压扁、分红日人为跳水、不同净值基数的基金没法比。这里提供三个
 * 开关：涨跌幅%（起点=100）/ 对数轴 / 累计净值。纯展示层——不在前端
 * 产生任何判定，数据（含窗口裁剪）全部来自后端 nav-series 接口。
 */
export default function FundNavCompare({ funds }: { funds: FundNavPick[] }) {
  // null = 尚未初始化（等持仓数据到了再默认勾市值前 3）
  const [selected, setSelected] = useState<string[] | null>(null);
  const [days, setDays] = useState<number>(1095);
  const [mode, setMode] = useState<"pct" | "nav">("pct");
  const [navKind, setNavKind] = useState<"acc" | "unit">("acc");
  const [logScale, setLogScale] = useState(true);

  useEffect(() => {
    if (selected === null && funds.length > 0) {
      setSelected(funds.slice(0, 3).map((f) => f.code));
    }
  }, [funds, selected]);

  const picked = selected ?? [];

  const { data, isFetching, error } = useQuery({
    queryKey: ["fundNavSeries", picked.join(","), days],
    queryFn: () => portfolioApi.navSeries(picked, days),
    enabled: picked.length > 0,
    staleTime: 30 * 60_000, // 净值一天更新一次
    placeholderData: keepPreviousData,
  });

  /** 各基金日期轴不同（QDII 缺 A 股交易日），并成一张并集轴再对齐。 */
  const alignedData = useMemo<{ unionDates: string[]; rows: AlignedRow[] } | null>(() => {
    if (!data || data.items.length === 0) return null;
    const unionDates = Array.from(new Set(data.items.flatMap((i) => i.dates))).sort();
    const rows = data.items.map((item) => {
      const idxByDate = new Map<string, number>();
      item.dates.forEach((d, i) => idxByDate.set(d, i));
      const raw = navKind === "acc" ? item.acc_nav : item.unit_nav;
      const values = unionDates.map((d) => {
        const i = idxByDate.get(d);
        return i == null ? null : raw[i];
      });
      let base: number | null = null;
      let lastIndex = -1;
      values.forEach((v, i) => {
        if (v != null && v > 0) {
          if (base == null) base = v;
          lastIndex = i;
        }
      });
      return { item, values, base, lastIndex };
    });
    return { unionDates, rows };
  }, [data, navKind]);

  const chartRef = useRef<HTMLDivElement>(null);
  const instRef = useRef<echarts.ECharts | null>(null);
  const showChart = picked.length > 0;

  // 图表容器只在选中了基金后才挂载（null → 有），实例初始化必须跟着这个
  // 开关走：只在首挂载时建一次的写法会拿到 null 容器，图永远空白。
  useEffect(() => {
    if (!showChart) return;
    const el = chartRef.current;
    if (!el) return;
    const inst = echarts.init(el, undefined, { renderer: "canvas" });
    instRef.current = inst;
    const ro = new ResizeObserver(() => inst.resize());
    ro.observe(el);
    return () => {
      ro.disconnect();
      inst.dispose();
      instRef.current = null;
    };
  }, [showChart]);

  useEffect(() => {
    const inst = instRef.current;
    if (!inst || !alignedData) return;
    const { unionDates, rows } = alignedData;
    const toDisplay = (row: AlignedRow) =>
      mode === "nav"
        ? row.values
        : row.values.map((v) =>
            v == null || row.base == null || row.base <= 0 ? null : (v / row.base) * 100,
          );
    const pctOf = (row: AlignedRow): number | null => {
      if (row.base == null || row.lastIndex < 0) return null;
      const v = row.values[row.lastIndex];
      if (v == null) return null;
      return (v / row.base - 1) * 100;
    };

    const seriesOpt: echarts.LineSeriesOption[] = rows.map((row, i) => ({
      name: row.item.name,
      type: "line",
      data: toDisplay(row),
      showSymbol: false,
      connectNulls: true, // QDII 与 A 股基金交易日不同，缺日连过去而不是断线
      lineStyle: { width: 1.6, color: PALETTE[i % PALETTE.length] },
      itemStyle: { color: PALETTE[i % PALETTE.length] },
    }));
    // 涨跌幅%视图的 100 基准线挂到隐形式锚点序列（与 TrendChart 同款手法：
    // 不占图例、用户关掉任何一条线基准线都还在；data 必须是等长 null 数组，
    // 否则 ECharts 会把 markLine 画成 X 形交叉）。
    if (mode === "pct" && seriesOpt.length > 0) {
      seriesOpt.push({
        name: "__fnav_anchor__",
        type: "line",
        data: new Array(unionDates.length).fill(null),
        showSymbol: false,
        silent: true,
        tooltip: { show: false },
        lineStyle: { opacity: 0 },
        itemStyle: { opacity: 0 },
        markLine: {
          symbol: "none",
          silent: true,
          lineStyle: { color: "#94a3b8", type: "dashed", width: 1 },
          label: { formatter: "起点 100", fontSize: 10, color: "#94a3b8" },
          data: [{ yAxis: 100 }],
        },
      });
    }

    const nDates = unionDates.length;
    const dataZoomOpt: echarts.EChartsOption["dataZoom"] =
      nDates > 60
        ? [
            { type: "inside", start: 0, end: 100, zoomOnMouseWheel: true, moveOnMouseMove: true },
            { type: "slider", start: 0, end: 100, bottom: 4, height: 18 },
          ]
        : undefined;

    inst.setOption(
      {
        tooltip: {
          trigger: "axis",
          formatter: (params: unknown) => {
            type TipParam = {
              axisValue?: string;
              seriesName?: string;
              dataIndex?: number;
              value?: number | null;
              marker?: string;
            };
            const arr0 = params as TipParam | TipParam[];
            const arr = Array.isArray(arr0) ? arr0 : [arr0];
            const head = (arr[0]?.axisValue as string) ?? "";
            const lines = arr
              .filter((p) => p.seriesName !== "__fnav_anchor__" && p.value != null)
              .map((p) => {
                const row = rows.find((r) => r.item.name === p.seriesName);
                const raw = row ? row.values[p.dataIndex ?? 0] : null;
                const pct = row ? pctOf(row) : null;
                const pctText = pct == null ? "" : `${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`;
                return mode === "pct"
                  ? `${p.marker}${p.seriesName}：${pctText}${raw != null ? `（净值 ${raw.toFixed(4)}）` : ""}`
                  : `${p.marker}${p.seriesName}：${Number(p.value).toFixed(4)}${pctText ? `（较起点 ${pctText}）` : ""}`;
              });
            return [head, ...lines].join("<br/>");
          },
        },
        legend:
          rows.length > 1
            ? {
                top: 0,
                textStyle: { fontSize: 11 },
                data: rows.map((r) => r.item.name),
                // 图例直接带区间涨跌幅后缀，不悬停也能读结论
                formatter: (name: string) => {
                  const row = rows.find((r) => r.item.name === name);
                  const pct = row ? pctOf(row) : null;
                  return pct == null ? name : `${name} ${pct >= 0 ? "+" : ""}${pct.toFixed(1)}%`;
                },
              }
            : undefined,
        grid: { left: 52, right: 16, top: rows.length > 1 ? 30 : 18, bottom: dataZoomOpt ? 46 : 24 },
        xAxis: {
          type: "category",
          data: unionDates,
          boundaryGap: false,
          axisLabel: { fontSize: 10, color: "#6b7280", hideOverlap: true },
          axisLine: { lineStyle: { color: "#d6dde6" } },
        },
        yAxis: {
          type: logScale ? "log" : "value",
          scale: true,
          logBase: 10,
          name: mode === "pct" ? "涨跌幅%（起点=100）" : "净值（元）",
          nameTextStyle: { fontSize: 10, color: "#94a3b8", align: "left" },
          axisLabel: { fontSize: 10, color: "#6b7280" },
          splitLine: { lineStyle: { color: "#eef1f5" } },
        },
        ...(dataZoomOpt ? { dataZoom: dataZoomOpt } : {}),
        series: seriesOpt,
      },
      true,
    );
  }, [alignedData, mode, logScale]);

  const toggle = (code: string) => {
    setSelected((prev) => {
      const cur = prev ?? [];
      if (cur.includes(code)) return cur.filter((c) => c !== code);
      if (cur.length >= MAX_PICK) return cur;
      return [...cur, code];
    });
  };

  return (
    <div className="card fnav-card">
      <div className="section-title" style={{ marginTop: 0 }}>
        <h2 style={{ fontSize: 15 }}>
          基金净值 · 涨跌幅对比
          <InfoTip tip={TIPS.pctView}>
            <span className="portfolio-verdict-badge">?</span>
          </InfoTip>
        </h2>
        <span className="count">最多 {MAX_PICK} 只 · 同一把尺子下看涨跌</span>
      </div>

      <div className="fnav-controls">
        <div className="seg">
          <button type="button" className={`seg-btn${mode === "pct" ? " on" : ""}`} onClick={() => setMode("pct")}>
            <InfoTip tip={TIPS.pctView}>涨跌幅%</InfoTip>
          </button>
          <button type="button" className={`seg-btn${mode === "nav" ? " on" : ""}`} onClick={() => setMode("nav")}>
            净值
          </button>
        </div>
        <div className="seg">
          <button
            type="button"
            className={`seg-btn${logScale ? " on" : ""}`}
            onClick={() => setLogScale(true)}
          >
            <InfoTip tip={TIPS.logAxis}>对数轴</InfoTip>
          </button>
          <button type="button" className={`seg-btn${!logScale ? " on" : ""}`} onClick={() => setLogScale(false)}>
            普通轴
          </button>
        </div>
        <div className="seg">
          <button
            type="button"
            className={`seg-btn${navKind === "acc" ? " on" : ""}`}
            onClick={() => setNavKind("acc")}
          >
            <InfoTip tip={TIPS.accNav}>累计净值</InfoTip>
          </button>
          <button
            type="button"
            className={`seg-btn${navKind === "unit" ? " on" : ""}`}
            onClick={() => setNavKind("unit")}
          >
            单位净值
          </button>
        </div>
        <div className="seg">
          {WINDOWS.map((w) => (
            <button
              key={w.key}
              type="button"
              className={`seg-btn${days === w.key ? " on" : ""}`}
              onClick={() => setDays(w.key)}
            >
              {w.label}
            </button>
          ))}
        </div>
      </div>

      <div className="fnav-picks">
        {funds.map((f) => {
          const on = picked.includes(f.code);
          const disabled = !on && picked.length >= MAX_PICK;
          return (
            <button
              key={f.code}
              type="button"
              className={`chip${on ? " on" : ""}`}
              disabled={disabled}
              onClick={() => toggle(f.code)}
              title={disabled ? `一次最多对比 ${MAX_PICK} 只` : `${f.name}（${f.code}）`}
            >
              {f.name}
            </button>
          );
        })}
      </div>

      {picked.length === 0 ? (
        <div className="fnav-empty">在上方点几只基金开始对比（已按持仓市值排序）。</div>
      ) : (
        <div ref={chartRef} className="fnav-chart" style={{ height: 360 }} />
      )}
      {isFetching && <div className="fnav-hint">取数中…外部接口有限速，每只基金约 1 秒，第一次选会稍等。</div>}
      {error && <div className="fnav-errors">净值取数失败：{(error as Error).message}</div>}
      {data && data.errors.length > 0 && (
        <div className="fnav-errors">
          {data.errors.map((e) => (
            <div key={e.code}>{e.code} {e.reason_cn}</div>
          ))}
        </div>
      )}

      <div className="fnav-note">
        涨跌幅% = 窗口第一天定为 100，线上数字即「起点至今涨跌百分之几」；对数轴让同样的高度代表同样的涨跌比例
        （普通轴会把早期波动压扁）；累计净值把分红加回、避免分红日「假跳水」。滚轮可缩放看细节，起点固定在所选窗口第一天。
        本图只帮你看清涨跌幅度，不产生任何买卖信号。
      </div>
    </div>
  );
}
