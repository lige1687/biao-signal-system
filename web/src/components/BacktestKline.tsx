import * as echarts from "echarts/core";
import { CandlestickChart } from "echarts/charts";
import {
  DataZoomComponent,
  GridComponent,
  MarkPointComponent,
  TooltipComponent,
} from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import { useEffect, useRef, useState } from "react";
import type { BacktestTrade } from "../types";

echarts.use([
  CandlestickChart,
  GridComponent,
  DataZoomComponent,
  TooltipComponent,
  MarkPointComponent,
  CanvasRenderer,
]);

interface KlinesResponse {
  symbol: string;
  count: number;
  dates: string[];
  ohlc: number[][];
}

interface Props {
  symbol: string;
  trades: BacktestTrade[];
}

const EXIT_CN: Record<string, string> = {
  structure_stop_C: "跌破止损位",
  exit_a6_1_costbasis: "跌破EMA20+抵扣价",
  exit_a6_2_top_plus_keywave: "顶部构造后关键波动",
  open_at_end: "持有至数据末尾",
  invalid_nonpositive_risk: "未执行",
};

/**
 * 回测 K 线 + 买卖点箭头：用回测池自己的日 K（约 10 年），
 * 买入=绿色上箭头（贴当根 low 下方），卖出=红色下箭头（贴当根 high 上方），
 * 悬停显示该笔交易的明细（价格/止损/实际盈亏 R/退出原因）。
 */
export default function BacktestKline({ symbol, trades }: Props) {
  const ref = useRef<HTMLDivElement>(null);
  const chartRef = useRef<echarts.ECharts | null>(null);
  const [data, setData] = useState<KlinesResponse | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/api/backtest/klines/${encodeURIComponent(symbol)}`)
      .then((r) => {
        if (!r.ok) throw new Error(`HTTP ${r.status}`);
        return r.json() as Promise<KlinesResponse>;
      })
      .then(setData)
      .catch((e: Error) => setError(e.message));
  }, [symbol]);

  useEffect(() => {
    if (!data || !ref.current) return;
    if (!chartRef.current) {
      chartRef.current = echarts.init(ref.current);
    }
    const chart = chartRef.current;
    const dateIndex = new Map(data.dates.map((d, i) => [d, i]));

    // markPoint 项带自定义扩展字段（tradeInfo/kind），官方类型不含，用宽类型
    type MarkItem = Record<string, unknown>;
    const marks: MarkItem[] = [];
    for (const t of trades) {
      const buyIdx = dateIndex.get(t.entry_date);
      if (buyIdx != null) {
        marks.push({
          coord: [buyIdx, data.ohlc[buyIdx][2]],
          symbol: "triangle",
          symbolSize: 11,
          symbolRotate: 0,
          itemStyle: { color: "#e33d47" },
          label: { show: false },
          tradeInfo: t,
          kind: "buy",
        });
      }
      if (t.exit_date) {
        const sellIdx = dateIndex.get(t.exit_date);
        if (sellIdx != null) {
          marks.push({
            coord: [sellIdx, data.ohlc[sellIdx][3]],
            symbol: "triangle",
            symbolSize: 11,
            symbolRotate: 180,
            itemStyle: { color: "#0b9b64" },
            label: { show: false },
            tradeInfo: t as unknown as Record<string, unknown>,
            kind: "sell",
          } as never);
        }
      }
    }

    chart.setOption(
      {
        animation: false,
        backgroundColor: "transparent",
        grid: { left: 56, right: 16, top: 24, bottom: 56 },
        tooltip: {
          trigger: "item",
          formatter: (params: { seriesType?: string; dataIndex?: number; data?: unknown; componentSubType?: string; marker?: string; name?: string; value?: unknown }) => {
            if (params.seriesType === "candlestick") {
              const i = params.dataIndex ?? 0;
              const [open, close, low, high] = data.ohlc[i];
              const up = close >= open;
              return [
                `<b>${data.dates[i]}</b>`,
                `开 ${open.toFixed(3)} 收 ${close.toFixed(3)}`,
                `低 ${low.toFixed(3)} 高 ${high.toFixed(3)}`,
                `<span style="color:${up ? "#e33d47" : "#0b9b64"}">${up ? "阳线" : "阴线"}</span>`,
              ].join("<br/>");
            }
            return "";
          },
        },
        xAxis: {
          type: "category",
          data: data.dates,
          axisLabel: { color: "#8a94a6", fontSize: 10 },
          axisLine: { lineStyle: { color: "#2a3244" } },
        },
        yAxis: {
          scale: true,
          axisLabel: { color: "#8a94a6", fontSize: 10 },
          splitLine: { lineStyle: { color: "rgba(42,50,68,0.5)" } },
        },
        dataZoom: [
          { type: "inside", start: 0, end: 100 },
          {
            type: "slider",
            height: 18,
            bottom: 8,
            borderColor: "#2a3244",
            textStyle: { color: "#8a94a6", fontSize: 10 },
          },
        ],
        series: [
          {
            type: "candlestick",
            data: data.ohlc,
            itemStyle: {
              color: "#e33d47",
              color0: "#0b9b64",
              borderColor: "#e33d47",
              borderColor0: "#0b9b64",
            },
          },
          {
            type: "line",
            data: [],
            markPoint: {
              symbol: "triangle",
              data: marks,
            },
            tooltip: {
              trigger: "item",
              formatter: (params: { data?: { tradeInfo?: BacktestTrade; kind?: string } }) => {
                const info = params.data?.tradeInfo;
                if (!info) return "";
                const isBuy = params.data?.kind === "buy";
                if (isBuy) {
                  return [
                    `<b style="color:#e33d47">▲ 买入 ${info.entry_date}</b>`,
                    `买入价 ${info.entry_price?.toFixed?.(3)}`,
                    `止损价 ${info.stop_price?.toFixed?.(3)}`,
                    `纸面盈亏比 ${info.reward_risk != null ? info.reward_risk.toFixed(1) : "—"}`,
                    info.is_first_touch ? "首次回撤" : "非首次回撤",
                  ].join("<br/>");
                }
                const r = info.r_net;
                return [
                  `<b style="color:#0b9b64">▼ 卖出 ${info.exit_date ?? "—"}</b>`,
                  `卖出价 ${info.exit_price?.toFixed?.(3)}`,
                  `买入价 ${info.entry_price?.toFixed?.(3)}（${info.entry_date}）`,
                  `实际盈亏 <b style="color:${(r ?? 0) >= 0 ? "#2ea86f" : "#d2504f"}">${r != null ? r.toFixed(2) : "—"} R</b>`,
                  `持有 ${info.holding_bars} 根K线`,
                  `原因：${EXIT_CN[info.exit_reason ?? ""] ?? info.exit_reason ?? "—"}`,
                ].join("<br/>");
              },
            },
          },
        ],
      },
      { notMerge: false },
    );
    const resize = () => chart.resize();
    window.addEventListener("resize", resize);
    return () => {
      window.removeEventListener("resize", resize);
    };
  }, [data, trades]);

  useEffect(
    () => () => {
      chartRef.current?.dispose();
      chartRef.current = null;
    },
    [],
  );

  if (error) return <div className="fund-errors">K线加载失败：{error}</div>;
  return (
    <div className="bt-kline">
      <div className="bt-kline-title">
        <b>{symbol}</b> 回测买卖点（{trades.length} 笔）
        <span className="bt-kline-legend">
          <span className="bt-legend-buy">▲ 买入</span>
          <span className="bt-legend-sell">▼ 卖出</span>
          <span>悬停箭头看明细；默认显示全部历史，滚轮/拖动可放大局部</span>
        </span>
      </div>
      {data ? (
        <div ref={ref} className="bt-kline-canvas" />
      ) : (
        <div className="bt-kline-canvas bt-kline-loading">K线加载中…</div>
      )}
    </div>
  );
}
