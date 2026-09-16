import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { researchApi } from "../api/client";
import type { SignalEdgeRow } from "../types";

/**
 * 信号含金量表（研究层展示，2026-09-05 文主任增量 #1）。
 *
 * 大白话口径（表头即解释）：
 * - 胜率 = 历史上该信号出现后，持有 N 天价格上涨的比例；
 * - 基准 = 同一批标的上"不看信号随便挑一天"做的胜率；
 * - 超额 = 胜率减基准，高于 0 才说明信号本身有含金量；
 * - 盈亏比 = 平均每次赚的幅度 ÷ 平均每次亏的幅度（大于是赚多亏少）。
 * 判定权在后端规则层，本表只读展示，统计结果不回写任何过滤器。
 */

const HORIZONS = [5, 10, 20, 60];

type SortKey = "label" | "samples" | "win" | "excess" | "payoff" | "ret";

function pct(v: number | null | undefined, digits = 1): string {
  if (v == null) return "—";
  return `${(v * 100).toFixed(digits)}%`;
}

function signed(v: number | null | undefined, digits = 1): string {
  if (v == null) return "—";
  const s = v > 0 ? "+" : "";
  return `${s}${v.toFixed(digits)}`;
}

function ppTone(v: number | null | undefined): string {
  if (v == null) return "neutral";
  return v > 0 ? "up" : v < 0 ? "down" : "neutral";
}

function GroupTag({ group }: { group: string }) {
  // 入场触发=四个交易模块的买点；预警路牌=只提醒不必然反向的风险提示
  return group === "trigger" ? (
    <span className="tag" title="四个交易模块（A/B/C/D）的入场确认买点">触发</span>
  ) : (
    <span className="tag" style={{ background: "#3a3f4b" }} title="预警类路牌：只提醒，不必然反向，不构成卖点">路牌</span>
  );
}

export default function SignalEdgePanel() {
  const [horizon, setHorizon] = useState(20);
  const [sortKey, setSortKey] = useState<SortKey>("excess");
  const [sortDesc, setSortDesc] = useState(true);

  const { data, isLoading, error, refetch, isFetching } = useQuery({
    queryKey: ["signalEdge"],
    queryFn: () => researchApi.signalEdge(),
    staleTime: 10 * 60_000,
  });

  const rows = useMemo(() => {
    const base = data?.rows ?? [];
    const pick = (r: SignalEdgeRow) =>
      r.horizons.find((h) => h.horizon === horizon);
    const val = (r: SignalEdgeRow): number | string => {
      const h = pick(r);
      switch (sortKey) {
        case "label": return r.label_cn;
        case "samples": return h?.sample_count ?? -1;
        case "win": return h?.win_rate ?? -1;
        case "excess": return h?.excess_win_rate ?? -999;
        case "payoff": return h?.payoff ?? -1;
        case "ret": return h?.mean_return ?? -999;
      }
    };
    const sorted = [...base].sort((a, b) => {
      const va = val(a);
      const vb = val(b);
      const cmp = typeof va === "string" || typeof vb === "string"
        ? String(va).localeCompare(String(vb), "zh")
        : (va as number) - (vb as number);
      return sortDesc ? -cmp : cmp;
    });
    return sorted;
  }, [data, horizon, sortKey, sortDesc]);

  const onSort = (key: SortKey) => {
    if (key === sortKey) {
      setSortDesc((d) => !d);
    } else {
      setSortKey(key);
      setSortDesc(true);
    }
  };

  const Th = ({ k, title, hint }: { k: SortKey; title: string; hint: string }) => (
    <th onClick={() => onSort(k)} title={hint} style={{ cursor: "pointer" }}>
      {title}
      {sortKey === k ? (sortDesc ? " ▾" : " ▴") : ""}
    </th>
  );

  if (isLoading) {
    return <div className="bt-section"><span className="muted">信号含金量统计中（首次需跑一遍自选分析，约几十秒）…</span></div>;
  }
  if (error) {
    return (
      <div className="bt-section">
        <div className="error">加载失败：{(error as Error).message}</div>
        <button onClick={() => refetch()}>重试</button>
      </div>
    );
  }
  if (!data || data.rows.length === 0) {
    return <div className="bt-section"><span className="muted">{data?.disclaimer_cn || "暂无数据"}</span></div>;
  }

  return (
    <div className="bt-section">
      <div className="header">
        <h1>信号含金量表</h1>
        <p className="bt-sub">
          每个信号/路牌历史上出现后，持有 {horizon} 天的成绩单，跟"随便挑一天做"的基准比。
          超额胜率大于 0 才说明信号本身有含金量；路牌类只预警不必然反向。
          <button className="btn-link" onClick={() => refetch()} disabled={isFetching}
            style={{ marginLeft: 8 }}>
            {isFetching ? "刷新中…" : "刷新"}
          </button>
        </p>
      </div>
      <div style={{ marginBottom: 8, display: "flex", gap: 8, alignItems: "center" }}>
        <span className="muted">持有期：</span>
        {HORIZONS.map((h) => (
          <button
            key={h}
            className={`bt-tab ${horizon === h ? "active" : ""}`}
            onClick={() => setHorizon(h)}
          >
            {h} 天
          </button>
        ))}
        <span className="muted" style={{ marginLeft: 12 }}>
          {data.n_symbols} 只标的 · {data.start_date} → {data.end_date}
        </span>
      </div>
      <table className="bt-table" style={{ width: "100%" }}>
        <thead>
          <tr>
            <Th k="label" title="信号" hint="信号名称（触发=四个交易模块的买点；路牌=预警类提示）" />
            <th title="方向语义">方向</th>
            <Th k="samples" title="样本数" hint="历史出现次数（完成持有期的才算进胜率）" />
            <Th k="win" title="胜率" hint="出现后 N 天内上涨的比例" />
            <th title="基准胜率：同一批标的上不看信号随便挑一天做的胜率">基准</th>
            <Th k="excess" title="超额胜率" hint="胜率−基准：大于 0 才是信号自己的含金量" />
            <Th k="ret" title="平均收益" hint="出现后持有 N 天的平均涨跌幅（%）" />
            <th title="超额收益：平均收益−基准平均收益（百分点）">超额收益</th>
            <Th k="payoff" title="盈亏比" hint="平均每次赚的幅度÷平均每次亏的幅度" />
            <th title="基准盈亏比：基准口径的盈亏比">基准盈亏比</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((r) => {
            const h = r.horizons.find((x) => x.horizon === horizon);
            return (
              <tr key={r.key}>
                <td className="strong">{r.label_cn} <GroupTag group={r.group} /></td>
                <td className="faint">{r.direction_cn}</td>
                <td>
                  {h?.sample_count ?? 0}
                  {(h?.incomplete_count ?? 0) > 0 && (
                    <span className="faint" title={`另有 ${h?.incomplete_count} 次出现太靠近现在，还没走完持有期，不进胜率`}>
                      (+{h?.incomplete_count}未完)
                    </span>
                  )}
                </td>
                <td>{pct(h?.win_rate)}</td>
                <td className="faint">{pct(h?.baseline_win_rate)}</td>
                <td className={ppTone(h?.excess_win_rate)}>
                  {h?.excess_win_rate == null ? "—" : `${(h.excess_win_rate * 100).toFixed(1)}pp`}
                </td>
                <td className={ppTone(h?.mean_return)}>{signed(h?.mean_return)}%</td>
                <td className={ppTone(h?.excess_mean_return)}>{signed(h?.excess_mean_return)}pp</td>
                <td className={ppTone(h?.payoff)}>{h?.payoff?.toFixed(2) ?? "—"}</td>
                <td className="faint">{h?.baseline_payoff?.toFixed(2) ?? "—"}</td>
              </tr>
            );
          })}
        </tbody>
      </table>
      <div className="rs-note" style={{ marginTop: 8 }}>{data.disclaimer_cn}</div>
      {data.symbols_failed.length > 0 && (
        <div className="rs-note">
          以下标的行情缺失未计入：{data.symbols_failed.join("、")}
        </div>
      )}
    </div>
  );
}
