/** 危机管理状态机横幅（环境层参考事件，研究代理，提示不挡信号）。
 *
 *  数据：global-strip CN_ALL_A 面板的 crisis_alerts / crisis_readings
 *  （后端 market_context/crisis_events.py，V4 刚崩警示 / V3 出清企稳）。
 *  数据不合格时明确显示未知与资料日期；有事件时显示完整读数。
 *  口径与历史效果见 docs/research-round5-cross-market.md R1-3。
 */
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { CrisisAlert, CrisisReading } from "../types";
import "./crisis-banner.css";

function readingTitle(rs: CrisisReading[] | undefined, symbol?: string): string {
  const r = rs?.find((x) => x.symbol === symbol);
  if (!r) return "";
  return (
    `指数截至 ${r.as_of} · 宽度截至 ${r.breadth_as_of}\n` +
    `dev60=${r.dev60_pct ?? "未知"}% · 宽度MA50=${r.breadth_ma50_now ?? "未知"}%\n` +
    `20日变化${r.breadth_delta_20 ?? "?"}pp · 1年分位${r.breadth_pctile_1y ?? "?"}% · ` +
    `5日变化${r.breadth_delta_5 ?? "?"}pp`
  );
}

export default function CrisisBanner({ hideUnknown = false }: { hideUnknown?: boolean }) {
  const { data } = useQuery({
    queryKey: ["globalStripCrisis"],
    queryFn: () => api.marketContextGlobalStrip(),
    staleTime: 60_000,
    retry: false,
  });
  const cn = data?.panels?.find((p) => p.market_id === "CN_ALL_A");
  const alerts: CrisisAlert[] = cn?.crisis_alerts ?? [];
  const readings = cn?.crisis_readings;
  const unknown = hideUnknown
    ? []
    : readings?.filter((r) => r.quality_status === "unknown" || r.state === "unknown") ?? [];
  if (alerts.length === 0 && unknown.length === 0) return null;
  return (
    <div className="crisis-banner-wrap">
      {unknown.length > 0 && (
        <div className="crisis-banner crisis-unknown" role="status">
          <b>危机环境状态未知</b>
          <span className="crisis-desc">
            {unknown.map((r) => `${r.name}：指数 ${r.as_of ?? "未提供"} / 宽度 ${r.breadth_as_of ?? "未提供"}`).join("；")}。
            <details><summary>资料资格未通过 · 查看原因</summary>{Array.from(new Set(unknown.map(r => r.quality_reason || "资料尚未核实"))).map(reason => <p key={reason}>{reason}</p>)}</details>
          </span>
        </div>
      )}
      {alerts.map((a) => (
        <div
          key={`${a.type}-${a.symbol ?? ""}`}
          className={`crisis-banner ${a.level === "opportunity" ? "opportunity" : "danger"}`}
          title={readingTitle(readings, a.symbol)}
        >
          <b>{a.level === "opportunity" ? "◆" : "⚠"} {a.title}</b>
          <span className="crisis-desc">{a.desc}</span>
          <span className="crisis-dates">{readingTitle(readings, a.symbol).split("\n")[0]}</span>
        </div>
      ))}
    </div>
  );
}
