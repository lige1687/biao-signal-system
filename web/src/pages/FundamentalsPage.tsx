import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useMemo, useState } from "react";
import { fundamentalsApi } from "../api/client";
import type { FundamentalsOverview, IndustryBoard } from "../types";

type SortKey = "pct_change" | "main_net_inflow_yi" | "main_net_inflow_pct" | "turnover_rate";

const SORTS: { key: SortKey; label: string }[] = [
  { key: "pct_change", label: "涨跌幅" },
  { key: "main_net_inflow_yi", label: "主力净流入" },
  { key: "main_net_inflow_pct", label: "主力净占比" },
  { key: "turnover_rate", label: "换手率" },
];

function pctClass(v: number | null): string {
  if (v == null) return "";
  return v >= 0 ? "up" : "down";
}

function fmt(v: number | null, digits = 2, suffix = ""): string {
  return v == null ? "-" : `${v.toFixed(digits)}${suffix}`;
}

function fmtYi(v: number | null): string {
  return v == null ? "-" : `${v.toFixed(2)}亿`;
}

/** 宏观卡片：PMI/CPI/PPI。PMI 以 50 为荣枯线着色。 */
function MacroCards({ data }: { data: FundamentalsOverview }) {
  if (data.macro.length === 0) return null;
  return (
    <div className="macro-grid">
      {data.macro.map((m) => {
        const boom = m.key === "pmi" ? (m.value ?? 0) >= 50 : null;
        return (
          <div key={m.key} className="macro-card">
            <div className="macro-head">
              <span className="macro-name">{m.name_cn}</span>
              <span className="macro-period">{m.period ?? ""}</span>
            </div>
            <div className={`macro-value ${boom == null ? "" : boom ? "up" : "down"}`}>
              {m.key === "pmi" ? fmt(m.value, 1) : `${fmt(m.value, 1)}%`}
            </div>
            <div className="macro-note">{m.note_cn}</div>
          </div>
        );
      })}
    </div>
  );
}

/** 行业资金流抽屉：近 N 日主力净流入条形列表（纯 CSS 条形，免引入图表库）。 */
function IndustryFlowDrawer({ board, onClose }: { board: IndustryBoard; onClose: () => void }) {
  const { data, isLoading, error } = useQuery({
    queryKey: ["industryFlow", board.code],
    queryFn: () => fundamentalsApi.industryFlow(board.code, 20),
  });
  const points = data?.points ?? [];
  const maxAbs = Math.max(1e-9, ...points.map((p) => Math.abs(p.main_yi ?? 0)));
  const sum = points.reduce((acc, p) => acc + (p.main_yi ?? 0), 0);

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <h2>
            {board.name} <span className="symbol">{board.code}</span> 主力资金流
            {data && `（近 ${points.length} 日）`}
          </h2>
          <button className="btn" onClick={onClose}>
            关闭
          </button>
        </div>
        <div className="drawer-body">
          {isLoading && <div>加载中…</div>}
          {error && <div className="error-msg">{(error as Error).message}</div>}
          {!isLoading && !error && (
            <>
              <div className="flow-summary">
                {points.length} 日主力累计净流入：
                <span className={pctClass(sum)}>{fmtYi(sum)}</span>
                <span className="spacer" />
                今日涨跌幅：
                <span className={pctClass(board.pct_change)}>{fmt(board.pct_change, 2, "%")}</span>
              </div>
              <div className="flow-bars">
                {points.map((p) => {
                  const v = p.main_yi ?? 0;
                  const width = Math.max(2, (Math.abs(v) / maxAbs) * 100);
                  return (
                    <div key={p.date} className="flow-row">
                      <span className="flow-date">{p.date.slice(5)}</span>
                      <span className="flow-track">
                        <span
                          className={`flow-bar ${v >= 0 ? "up" : "down"}`}
                          style={{ width: `${width}%` }}
                        />
                      </span>
                      <span className={`flow-val ${pctClass(p.main_yi)}`}>{fmtYi(p.main_yi)}</span>
                    </div>
                  );
                })}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export default function FundamentalsPage() {
  const queryClient = useQueryClient();
  const [sortKey, setSortKey] = useState<SortKey>("main_net_inflow_yi");
  const [sortAsc, setSortAsc] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [selected, setSelected] = useState<IndustryBoard | null>(null);

  const { data, isLoading, error } = useQuery({
    queryKey: ["fundamentalsOverview"],
    queryFn: () => fundamentalsApi.overview(),
    staleTime: 5 * 60_000,
  });

  // 硬刷新：绕过服务端 TTL 重拉后写回缓存。
  const refreshMutation = useMutation({
    mutationFn: () => fundamentalsApi.overview(true),
    onSuccess: (fresh) => queryClient.setQueryData(["fundamentalsOverview"], fresh),
  });

  const boards = useMemo(() => {
    let list = data?.boards ?? [];
    if (keyword.trim()) {
      const k = keyword.trim().toLowerCase();
      list = list.filter((b) => b.name.toLowerCase().includes(k) || b.code.includes(k));
    }
    const dir = sortAsc ? 1 : -1;
    return [...list].sort((a, b) => ((b[sortKey] ?? -1e18) - (a[sortKey] ?? -1e18)) * dir);
  }, [data, keyword, sortKey, sortAsc]);

  return (
    <div className="page">
      <div className="header">
        <h1>基本面参考</h1>
        {data && (
          <span className="generated">
            更新于 {new Date(data.generated_at).toLocaleString("zh-CN", { hour12: false })}
          </span>
        )}
        <span className="spacer" />
        <button
          className="btn primary"
          disabled={refreshMutation.isPending}
          onClick={() => refreshMutation.mutate()}
        >
          {refreshMutation.isPending ? "刷新中…" : "刷新"}
        </button>
      </div>

      {data && <div className="legend">{data.disclaimer_cn}</div>}
      {data && data.errors.length > 0 && (
        <div className="fund-errors">
          部分数据源暂不可用（页面其余内容不受影响）：
          {data.errors.map((e, i) => (
            <div key={i}>· {e}</div>
          ))}
        </div>
      )}
      {error && <div className="fund-errors">加载失败：{(error as Error).message}</div>}

      {isLoading && (
        <>
          <div className="macro-grid">
            {Array.from({ length: 3 }).map((_, i) => (
              <div key={i} className="card-skeleton" />
            ))}
          </div>
          <div className="card-skeleton" style={{ height: 320, marginTop: 14 }} />
        </>
      )}

      {data && (
        <>
          <h2 className="fund-section-title">宏观环境</h2>
          <MacroCards data={data} />

          <h2 className="fund-section-title">
            行业板块全景 <span className="fund-count">{data.board_count} 个</span>
          </h2>
          <div className="fund-toolbar">
            <input
              className="fund-search"
              placeholder="搜索行业名 / 代码…"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
            {SORTS.map((s) => (
              <button
                key={s.key}
                className={`btn ${sortKey === s.key ? "primary" : ""}`}
                onClick={() => {
                  if (sortKey === s.key) setSortAsc(!sortAsc);
                  else {
                    setSortKey(s.key);
                    setSortAsc(false);
                  }
                }}
              >
                {s.label}
                {sortKey === s.key ? (sortAsc ? " ↑" : " ↓") : ""}
              </button>
            ))}
            <span className="fund-hint">点行看 20 日主力资金流</span>
          </div>

          <div className="fund-table-wrap">
            <table className="event-table fund-table">
              <thead>
                <tr>
                  <th>行业</th>
                  <th className="num">涨跌幅</th>
                  <th className="num">换手率</th>
                  <th className="num">主力净流入</th>
                  <th className="num">净占比</th>
                  <th className="num">涨/跌家数</th>
                  <th className="num">总市值</th>
                </tr>
              </thead>
              <tbody>
                {boards.map((b) => (
                  <tr key={b.code} onClick={() => setSelected(b)}>
                    <td>
                      {b.name} <span className="symbol">{b.code}</span>
                    </td>
                    <td className={`num ${pctClass(b.pct_change)}`}>
                      {fmt(b.pct_change, 2, "%")}
                    </td>
                    <td className="num">{fmt(b.turnover_rate, 2, "%")}</td>
                    <td className={`num ${pctClass(b.main_net_inflow_yi)}`}>
                      {fmtYi(b.main_net_inflow_yi)}
                    </td>
                    <td className={`num ${pctClass(b.main_net_inflow_pct)}`}>
                      {fmt(b.main_net_inflow_pct, 2, "%")}
                    </td>
                    <td className="num">
                      <span className="up">{b.up_count ?? "-"}</span>/
                      <span className="down">{b.down_count ?? "-"}</span>
                    </td>
                    <td className="num">{fmt(b.total_mv_yi, 0, "亿")}</td>
                  </tr>
                ))}
                {boards.length === 0 && (
                  <tr>
                    <td colSpan={7}>无匹配行业</td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}

      {selected && <IndustryFlowDrawer board={selected} onClose={() => setSelected(null)} />}
    </div>
  );
}
