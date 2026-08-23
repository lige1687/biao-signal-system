import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { dailyBriefApi } from "../api/client";
import { fmt } from "../utils/format";
import type { DailyBriefResponse } from "../types";

// verdict 档位着色（继承机会扫描语义：actionable > waiting > blocked/none）
function verdictTone(verdict: string | null): string {
  switch (verdict) {
    case "actionable":
      return "opportunity";
    case "waiting":
      return "neutral";
    case "blocked":
      return "caution";
    default:
      return "muted-chip";
  }
}

const SLOT_CN: Record<string, string> = {
  "1445": "盘中预判 · 14:45（未收盘）",
  "1645": "收盘复核 · 16:45",
};

export default function DailyBriefPage() {
  const [slot, setSlot] = useState<string | null>(null);
  const { data, error } = useQuery({
    queryKey: ["dailyBriefLatest"],
    queryFn: () => dailyBriefApi.latest(),
    staleTime: 5 * 60_000,
  });

  if (error) {
    return (
      <div className="page">
        <div className="header">
          <h1>收盘简报</h1>
        </div>
        <div className="fund-errors">
          加载失败：{(error as Error).message}
          <div className="fund-hint">请先在本机跑 scripts/precompute_daily_brief.py 生成简报。</div>
        </div>
      </div>
    );
  }
  if (!data) {
    return (
      <div className="page">
        <div className="header">
          <h1>收盘简报</h1>
        </div>
        <div className="muted">加载中…</div>
      </div>
    );
  }

  const activeSlot = slot && data.slots_available.includes(slot) ? slot : data.slot;
  const brief =
    activeSlot === data.slot
      ? data.brief
      : // 切槽位时按日期重新取
        null;

  return (
    <div className="page">
      <div className="header">
        <h1>收盘简报</h1>
        {brief !== null || activeSlot === data.slot ? (
          <>
            <span className="generated">
              {data.date} · {SLOT_CN[activeSlot] ?? activeSlot} · 生成于 {data.brief.generated_at}
              （表达层：{data.brief.summary.generated_by === "llm" ? "LLM" : "模板"}）
            </span>
            <span className="spacer" />
            {data.slots_available.length > 1 &&
              data.slots_available.map((s) => (
                <button
                  key={s}
                  className={`btn ${s === activeSlot ? "primary" : ""}`}
                  onClick={() => setSlot(s)}
                >
                  {s === "1445" ? "14:45 预判" : "16:45 收盘"}
                </button>
              ))}
          </>
        ) : null}
      </div>

      {activeSlot !== data.slot ? (
        <SlotView date={data.date} slot={activeSlot} />
      ) : (
        <BriefBody brief={data.brief} />
      )}
    </div>
  );
}

function SlotView({ date, slot }: { date: string; slot: string }) {
  const { data } = useQuery({
    queryKey: ["dailyBrief", date, slot],
    queryFn: () => dailyBriefApi.byDate(date),
    staleTime: 5 * 60_000,
  });
  if (!data || data.slot !== slot) return <div className="muted">加载中…</div>;
  return <BriefBody brief={data.brief} />;
}

function BriefBody({ brief }: { brief: DailyBriefResponse["brief"] }) {
  const env = brief.env;
  const wl = brief.watchlist;
  const changed = brief.watchlist.items.filter((it) => it.n_changes > 0 || it.is_new);

  return (
    <>
      {/* ── ① 市场环境 ── */}
      <h2 className="fund-section-title">
        ① 市场环境 <span className="fund-count">异常驱动 · A股 + 美股宽度</span>
      </h2>
      {env.anomalies.length > 0 ? (
        <div className="brief-anomalies">
          {env.anomalies.map((a, i) => (
            <div key={i} className={`brief-anomaly ${(a.pctile_250d ?? 50) >= 90 ? "high" : "low"}`}>
              ⚠ {a.note_cn}
              {a.day_change != null && `（较前日 ${a.day_change > 0 ? "+" : ""}${a.day_change}pct）`}
            </div>
          ))}
        </div>
      ) : (
        <div className="muted" style={{ marginBottom: 8 }}>
          环境无异常变动（宽度均在正常分位区间）
        </div>
      )}
      <div className="fund-table-wrap">
        <table className="event-table fund-table">
          <thead>
            <tr>
              <th>市场</th>
              <th className="num">宽度</th>
              <th className="num">现值</th>
              <th className="num">较前日</th>
              <th className="num">近一年分位</th>
              <th>数据日</th>
            </tr>
          </thead>
          <tbody>
            {env.breadth_context.map((c, i) => (
              <tr key={i}>
                <td>{c.market}</td>
                <td className="num">{c.metric}</td>
                <td className="num">{fmt(c.value, 1)}%</td>
                <td className={`num ${c.day_change != null && c.day_change >= 0 ? "up" : "down"}`}>
                  {c.day_change != null ? `${c.day_change > 0 ? "+" : ""}${c.day_change}` : "-"}
                </td>
                <td className="num">{c.pctile_250d != null ? `${c.pctile_250d}%` : "-"}</td>
                <td>{c.date ?? "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {env.macro.line_cn && <div className="brief-macro">背景：{env.macro.line_cn}</div>}

      {/* ── ② 自选重点变化 ── */}
      <h2 className="fund-section-title">
        ② 自选重点变化{" "}
        <span className="fund-count">
          档位继承机会扫描 · {wl.items.length} 项个股/ETF + {wl.sector_watch_count} 项板块自选
        </span>
      </h2>
      {changed.length > 0 ? (
        <div className="brief-watch">
          {changed.map((it) => (
            <div key={it.symbol} className="brief-watch-item">
              <div className="brief-watch-head">
                <span className="watch-item-name">
                  {it.display_name ?? it.symbol}
                  <span className="symbol"> {it.symbol}</span>
                </span>
                {it.verdict_cn && (
                  <span className={`macro-chip ${verdictTone(it.verdict)}`}>{it.verdict_cn}</span>
                )}
              </div>
              {it.changes.slice(0, 5).map((ch, i) => (
                <div key={i} className="brief-change-line">
                  · {ch}
                </div>
              ))}
            </div>
          ))}
        </div>
      ) : (
        <div className="muted" style={{ marginBottom: 8 }}>自选无变化</div>
      )}
      {wl.unchanged_count > 0 && (
        <div className="muted" style={{ fontSize: 12 }}>
          其余 {wl.unchanged_count} 项无变化
        </div>
      )}

      {/* ── ③ 板块观察池 ── */}
      <h2 className="fund-section-title">
        ③ 板块观察池 <span className="fund-count">近几日持续上榜 · 临近升级/资金印证/动能前五</span>
      </h2>
      {brief.pool.items.length > 0 ? (
        <div className="fund-table-wrap">
          <table className="event-table fund-table">
            <thead>
              <tr>
                <th>板块</th>
                <th className="num">连续天数</th>
                <th>在池理由</th>
                <th className="num">RS分位</th>
                <th className="num">PE</th>
                <th className="num">20日主力</th>
                <th>下一观察点</th>
              </tr>
            </thead>
            <tbody>
              {brief.pool.items.map((it) => (
                <tr key={it.code}>
                  <td>
                    {it.name ?? it.code} <span className="symbol">{it.code}</span>
                  </td>
                  <td className="num">{it.streak >= 3 ? `🔥${it.streak}` : it.streak}</td>
                  <td>{it.tags.join(" · ")}</td>
                  <td className="num">{fmt(it.rs_pctile, 0)}</td>
                  <td className="num">
                    {it.pe_ttm == null ? "-" : it.pe_ttm < 0 ? "亏" : it.pe_ttm.toFixed(0)}
                  </td>
                  <td
                    className={`num ${it.flow_20d_main_yi != null && it.flow_20d_main_yi > 0 ? "up" : "down"}`}
                  >
                    {it.flow_20d_main_yi != null ? `${it.flow_20d_main_yi.toFixed(0)}亿` : "-"}
                  </td>
                  <td className="brief-next">{it.next_watch ?? "-"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="muted">当前无持续上榜板块</div>
      )}

      {/* ── LLM/模板全文 ── */}
      <h2 className="fund-section-title">
        简报全文 <span className="fund-count">表达层 {brief.summary.generated_by === "llm" ? "LLM" : "模板"}</span>
      </h2>
      <pre className="brief-text">{brief.summary.text}</pre>

      <div className="legend" style={{ marginTop: 10 }}>
        research_proxy 研究代理，非买卖建议。盘中版（14:45）为未收盘临时判定，收盘版（16:45）复核。
        板块资金流「主力=超大+大单、散户=中+小单」为单据规模代理。
      </div>
    </>
  );
}
