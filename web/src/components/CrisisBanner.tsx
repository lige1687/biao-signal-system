/** 危机管理状态机横幅（环境层参考事件，研究代理，提示不挡信号）。
 *
 *  数据：global-strip CN_ALL_A 面板的 crisis_alerts / crisis_readings
 *  （后端 market_context/crisis_events.py，V4 刚崩警示 / V3 出清企稳）。
 *  零触发不渲染（零噪音）；触发时在顶栏下方全宽显示，悬停看完整读数。
 *  口径与历史效果见 docs/research-round5-cross-market.md R1-3。
 */
import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import type { CrisisAlert, CrisisReading } from "../types";

function readingTitle(rs: CrisisReading[] | undefined, symbol?: string): string {
  const r = rs?.find((x) => x.symbol === symbol);
  if (!r) return "";
  return (
    `指数截至 ${r.as_of} · 宽度截至 ${r.breadth_as_of}\n` +
    `dev60=${r.dev60_pct}% · 宽度MA50=${r.breadth_ma50_now}%\n` +
    `20日变化${r.breadth_delta_20 ?? "?"}pp · 1年分位${r.breadth_pctile_1y ?? "?"}% · ` +
    `5日变化${r.breadth_delta_5 ?? "?"}pp`
  );
}

export default function CrisisBanner() {
  const { data } = useQuery({
    queryKey: ["globalStripCrisis"],
    queryFn: () => api.marketContextGlobalStrip(),
    staleTime: 60_000,
    retry: false,
  });
  const cn = data?.panels?.find((p) => p.market_id === "CN_ALL_A");
  const alerts: CrisisAlert[] = cn?.crisis_alerts ?? [];
  const readings = cn?.crisis_readings;
  if (alerts.length === 0) return null;
  return (
    <div className="crisis-banner-wrap">
      {alerts.map((a) => (
        <div
          key={`${a.type}-${a.symbol ?? ""}`}
          className={`crisis-banner ${a.level === "opportunity" ? "opportunity" : "danger"}`}
          title={readingTitle(readings, a.symbol)}
        >
          <b>{a.level === "opportunity" ? "◆" : "⚠"} {a.title}</b>
          <span className="crisis-desc">{a.desc}</span>
        </div>
      ))}
    </div>
  );
}
