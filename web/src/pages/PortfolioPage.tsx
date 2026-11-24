import { useMemo, useRef, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { api, portfolioApi } from "../api/client";
import { agentConsoleStore } from "../App";
import { ReviewFetcher, TradeConfirmCard, TradesLedgerView } from "../components/copilot/CopilotCards";
import PortfolioTechnicalDetail from "../components/portfolio/PortfolioTechnicalDetail";
import PortfolioTrackBenchmarkPanel from "../components/portfolio/PortfolioTrackBenchmarkPanel";
import SmartSymbolPromptCard from "../components/smart-prompts/SmartSymbolPromptCard";
import { fmtChange } from "../utils/format";
import { classifySymbol, mapHoldingsToSymbols, type SymbolSource } from "../utils/portfolioSymbols";
import { TRACK_BENCHMARKS } from "../utils/portfolioTrackBenchmarks";
import type { PortfolioGroup, PortfolioHolding, TradePreview } from "../types";
import "./portfolio.css";
import { patchPortfolioParams } from "./portfolioUrl";

type Row = { holding: PortfolioHolding; group: PortfolioGroup };
type SortKey = "amount" | "return" | "return_asc";
const money = (v: number) => `¥${v.toLocaleString("zh-CN", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
const pct = (v: number) => `${v.toFixed(1)}%`;
const marketName: Record<string, string> = { cn: "A股", hk: "港股", us: "美股", other: "其他" };

function QuickTradeBox({ holding, asOf }: { holding: PortfolioHolding; asOf: string }) {
  const [side, setSide] = useState<"buy" | "sell" | "">("");
  const [preview, setPreview] = useState<TradePreview | null>(null);
  if (!holding.code || !/^[0-9]{6}$/.test(holding.code)) return null;
  return (
    <details className="pl-quick-trade">
      <summary>登记这只基金的实际成交</summary>
      {!preview ? (
        <div className="pl-quick-trade-row">
          <select
            aria-label="成交方向"
            value={side}
            onChange={(e) => setSide(e.target.value as typeof side)}
          >
            <option value="">选择方向</option>
            <option value="buy">买入</option>
            <option value="sell">卖出</option>
          </select>
          <button
            type="button"
            className="btn small"
            disabled={!side}
            onClick={() =>
              side &&
              setPreview({
                fund_code: holding.code,
                fund_name: holding.name,
                side,
                side_cn: side === "buy" ? "买入" : "卖出",
                amount: null,
                trade_date: asOf,
                missing: ["成交金额"],
                note_cn: "手动登记实际成交",
              })
            }
          >
            填写成交卡
          </button>
        </div>
      ) : (
        <TradeConfirmCard preview={preview} />
      )}
    </details>
  );
}

/**
 * 我的持仓（重构版：赛道主导的「持仓全景」+「成交台账」双页签）。
 * 合并原割裂的「今日持仓 / 全部持仓」双列表，去掉场外基金满屏「资料缺口/未完成」焦虑，
 * 按仓位从重到轻先看赛道外部顺逆风，点赛道即联动筛选下方基金明细。
 */
export default function PortfolioPage() {
  const [params, setParams] = useSearchParams();
  const tab: "overview" | "trades" = params.get("tab") === "trades" ? "trades" : "overview";
  const update = (values: Record<string, string | null>, replace = true) =>
    setParams(patchPortfolioParams(params, values), { replace });
  const setTab = (next: typeof tab) => update({ tab: next === "overview" ? null : next }, false);

  const { data, error, isLoading } = useQuery({
    queryKey: ["portfolio"],
    queryFn: portfolioApi.get,
    staleTime: 5 * 60_000,
  });
  const { data: dashboard } = useQuery({
    queryKey: ["cards"],
    queryFn: () => api.dashboard(),
    staleTime: 60_000,
  });
  const { data: catalog } = useQuery({
    queryKey: ["sectors"],
    queryFn: () => api.sectors(),
    staleTime: Infinity,
  });

  const search = params.get("q") ?? "";
  const groupFilter = params.get("group") ?? "all";
  const rawSort = params.get("sort");
  const sort: SortKey =
    rawSort === "return" || rawSort === "return_asc" ? rawSort : "amount";
  const selectedId = params.get("holding");
  const detailRef = useRef<HTMLElement>(null);

  const selectHolding = (holdingId: string) => {
    update({ holding: holdingId }, false);
    const detail = detailRef.current;
    if (!detail) return;
    const navigationHeight = document.querySelector(".top-nav")?.getBoundingClientRect().height ?? 60;
    detail.style.scrollMarginTop = `${navigationHeight + 12}px`;
    detail.scrollIntoView({
      block: window.matchMedia("(max-width: 1100px)").matches ? "start" : "nearest",
      behavior: "auto",
    });
  };

  const rows = useMemo<Row[]>(
    () => data?.groups.flatMap((group) => group.holdings.map((holding) => ({ holding, group }))) ?? [],
    [data],
  );

  const symbolMap = useMemo(() => {
    const sources: SymbolSource[] = [
      ...(dashboard?.cards ?? [])
        .filter((c) => !c.error)
        .map((c) => ({
          symbol: c.symbol,
          name: c.display_name,
          identity: c.group === "watchlist" ? classifySymbol(c.symbol) : ("insufficient" as const),
        })),
      ...(catalog?.us_etfs ?? []).map((s) => ({
        symbol: s.symbol,
        name: s.name,
        identity: "us_etf_catalog" as const,
      })),
    ];
    return mapHoldingsToSymbols(rows.map((r) => r.holding), sources);
  }, [rows, dashboard, catalog]);

  const visible = useMemo(
    () =>
      rows
        .filter(
          ({ holding, group }) =>
            (groupFilter === "all" || group.group_key === groupFilter) &&
            (!search.trim() ||
              `${holding.name} ${holding.code ?? ""} ${group.name}`
                .toLocaleLowerCase()
                .includes(search.trim().toLocaleLowerCase())),
        )
        .sort((a, b) => {
          if (sort === "return") {
            return (
              (b.holding.return_pct ?? -Infinity) - (a.holding.return_pct ?? -Infinity) ||
              a.holding.name.localeCompare(b.holding.name, "zh-CN")
            );
          }
          if (sort === "return_asc") {
            return (
              (a.holding.return_pct ?? Infinity) - (b.holding.return_pct ?? Infinity) ||
              a.holding.name.localeCompare(b.holding.name, "zh-CN")
            );
          }
          return (
            (b.holding.market_value ?? -Infinity) - (a.holding.market_value ?? -Infinity) ||
            a.holding.name.localeCompare(b.holding.name, "zh-CN")
          );
        }),
    [rows, groupFilter, search, sort],
  );

  const selected = visible.find((r) => r.holding.holding_id === selectedId) ?? visible[0];

  if (isLoading) return <div className="page pl-page">加载持仓中…</div>;
  if (error || !data) {
    return (
      <div className="page pl-page" role="alert">
        持仓数据加载失败：{(error as Error | null)?.message ?? "未知错误"}
      </div>
    );
  }

  const max = Math.max(0, ...rows.map((r) => r.holding.market_value));
  const sortedGroups = [...data.groups].sort((a, b) => b.amount - a.amount);
  const activeGroupObj = data.groups.find((g) => g.group_key === groupFilter) ?? null;
  const selectedMapped = selected ? symbolMap.get(selected.holding.holding_id) : undefined;
  const selectedTrackRefSym = selected
    ? TRACK_BENCHMARKS[selected.group.group_key]?.referenceSymbols?.[0] ?? null
    : null;

  return (
    <div className="page pl-page">
      <header className="pl-header">
        <div>
          <h1>我的持仓</h1>
          <p>
            持仓记录 {data.as_of} · {data.holdings_count} 只基金（不含现金）
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <Link to="/onepage" className="btn small">
            一页看全 →
          </Link>
          <Link to="/?view=compare&scope=portfolio" className="btn small">
            横向比强弱 →
          </Link>
        </div>
      </header>

      <div className="pl-overview" aria-label="持仓概览">
        <div>
          <span>所录基金金额</span>
          <strong>{rows.length ? money(data.total_value) : "—"}</strong>
        </div>
        <div>
          <span>基金只数</span>
          <strong>{data.holdings_count}</strong>
        </div>
        <div>
          <span>最大单只占比</span>
          <strong>{rows.length && data.total_value > 0 ? pct((max / data.total_value) * 100) : "—"}</strong>
        </div>
        <div>
          <span>前三大方向权重</span>
          <strong style={{ fontSize: 13.5, fontWeight: 600, whiteSpace: "normal", lineHeight: 1.35 }}>
            {sortedGroups
              .slice(0, 3)
              .map((g) => `${g.name} ${pct(g.pct)}`)
              .join(" · ") || "—"}
          </strong>
        </div>
      </div>

      <div className="pl-tabs" role="tablist" aria-label="持仓页面">
        <button
          type="button"
          role="tab"
          aria-selected={tab === "overview"}
          onClick={() => setTab("overview")}
        >
          持仓全景（{data.holdings_count}）
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === "trades"}
          onClick={() => setTab("trades")}
        >
          成交台账
        </button>
      </div>

      {tab === "overview" ? (
        <>
          <PortfolioTrackBenchmarkPanel
            groups={data.groups}
            activeGroupKey={groupFilter}
            onSelectGroup={(gk) =>
              update({ group: gk === "all" ? null : gk, holding: null }, false)
            }
          />

          <div className="pl-toolbar">
            <label>
              赛道
              <select
                value={groupFilter}
                onChange={(e) =>
                  update({ group: e.target.value === "all" ? null : e.target.value, holding: null })
                }
              >
                <option value="all">全部赛道</option>
                {sortedGroups.map((g) => (
                  <option key={g.group_key} value={g.group_key}>
                    {g.name}（{g.holdings.length}）
                  </option>
                ))}
              </select>
            </label>
            <label>
              搜索
              <input
                type="search"
                placeholder="基金名称或代码"
                value={search}
                onChange={(e) => update({ q: e.target.value, holding: null })}
              />
            </label>
            <label>
              排序
              <select
                value={sort}
                onChange={(e) => update({ sort: e.target.value === "amount" ? null : e.target.value })}
              >
                <option value="amount">仓位金额从高到低</option>
                <option value="return">收益率从高到低</option>
                <option value="return_asc">收益率从低到高（先看亏损）</option>
              </select>
            </label>
            {activeGroupObj && (
              <button
                type="button"
                className="btn small"
                onClick={() => update({ group: null, holding: null })}
              >
                赛道：{activeGroupObj.name} ✕
              </button>
            )}
            <span>
              显示 {visible.length} / {rows.length} 只
            </span>
          </div>

          <div className="pl-workspace">
            <section className="pl-list" aria-label="基金清单">
              <div className="pl-list-scroll">
                <table>
                  <thead>
                    <tr>
                      <th>基金 / 赛道</th>
                      <th className="pl-num">金额</th>
                      <th className="pl-num">占比</th>
                      <th className="pl-num">持有收益</th>
                    </tr>
                  </thead>
                  <tbody>
                    {visible.map(({ holding, group }) => {
                      const ret = fmtChange(holding.return_pct);
                      const mapped = symbolMap.get(holding.holding_id);
                      const weightPct =
                        data.total_value > 0 ? (holding.market_value / data.total_value) * 100 : 0;
                      return (
                        <tr
                          key={holding.holding_id}
                          className={
                            selected?.holding.holding_id === holding.holding_id ? "pl-selected" : ""
                          }
                        >
                          <td>
                            <button
                              type="button"
                              className="pl-row-select"
                              aria-pressed={selected?.holding.holding_id === holding.holding_id}
                              onClick={() => selectHolding(holding.holding_id)}
                            >
                              <strong>
                                {holding.name}
                                {mapped && <span className="pl-live-dot">有图</span>}
                              </strong>
                              <span>
                                {holding.code ?? "无代码"} · {group.name}
                              </span>
                            </button>
                          </td>
                          <td className="pl-num">{money(holding.market_value)}</td>
                          <td className="pl-num">
                            <div>{pct(weightPct)}</div>
                            <div className="pl-mini-bar" aria-hidden="true">
                              <i style={{ width: `${Math.min(100, weightPct * 4).toFixed(0)}%` }} />
                            </div>
                          </td>
                          <td className={`pl-num ${ret.cls}`}>{ret.text}</td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>
              {visible.length === 0 && (
                <p className="pl-empty">
                  {rows.length ? "没有符合条件的基金，调整赛道或搜索词后再看。" : "暂无基金持仓记录。"}
                </p>
              )}
            </section>

            <aside ref={detailRef} className="pl-detail" aria-label="单只基金档案" aria-live="polite">
              {selected ? (
                <>
                  <div className="pl-detail-head">
                    <span>{selected.group.name}</span>
                    <h2>{selected.holding.name}</h2>
                    <p>{selected.holding.code ?? "代码未记录"}</p>
                  </div>
                  <dl className="pl-facts">
                    <div>
                      <dt>持仓金额</dt>
                      <dd>{money(selected.holding.market_value)}</dd>
                    </div>
                    <div>
                      <dt>仓位占比</dt>
                      <dd>
                        {data.total_value > 0
                          ? pct((selected.holding.market_value / data.total_value) * 100)
                          : "—"}
                      </dd>
                    </div>
                    <div>
                      <dt>持有收益率</dt>
                      <dd className={fmtChange(selected.holding.return_pct).cls}>
                        {fmtChange(selected.holding.return_pct).text}
                      </dd>
                    </div>
                  </dl>

                  <div className="pl-actions" style={{ marginTop: 0, marginBottom: 12 }}>
                    {selectedMapped ? (
                      <Link to={`/?symbol=${encodeURIComponent(selectedMapped.symbol)}`}>
                        看行情 K 线 →
                      </Link>
                    ) : selectedTrackRefSym ? (
                      <Link to={`/?symbol=${encodeURIComponent(selectedTrackRefSym)}`}>
                        看同赛道参考 K 线 →
                      </Link>
                    ) : null}
                    <button
                      type="button"
                      onClick={() =>
                        agentConsoleStore.openConsole(
                          selectedMapped?.symbol ?? selectedTrackRefSym ?? null,
                          `帮我核对「${selected.holding.name}${selected.holding.code ? `(${selected.holding.code})` : ""}」目前仓位占比 ${
                            data.total_value > 0
                              ? pct((selected.holding.market_value / data.total_value) * 100)
                              : "—"
                          }、收益率 ${fmtChange(selected.holding.return_pct).text}，接下来怎么处理？`,
                        )
                      }
                    >
                      问 AI 这笔持仓
                    </button>
                  </div>

                  {selected.holding.code && <SmartSymbolPromptCard symbol={selected.holding.code} />}

                  <section className="pl-quarter">
                    <h3>季报前十大持仓</h3>
                    {selected.holding.top10_total_pct == null ? (
                      <p className="muted">暂无已披露季报前十大资料。</p>
                    ) : (
                      <>
                        <p>
                          季报 {selected.holding.report_quarter ?? "—"} · 前十大合计占净值{" "}
                          <b>{pct(selected.holding.top10_total_pct)}</b>
                        </p>
                        <p>
                          {Object.entries(selected.holding.top10_by_market_pct)
                            .filter(([, v]) => v > 0)
                            .map(([m, v]) => `${marketName[m] ?? m} ${pct(v)}`)
                            .join(" · ") || "地域拆分未提供"}
                        </p>
                      </>
                    )}
                  </section>

                  {selectedMapped && (
                    <PortfolioTechnicalDetail holding={selected.holding} map={selectedMapped} />
                  )}

                  <QuickTradeBox
                    key={selected.holding.holding_id}
                    holding={selected.holding}
                    asOf={data.as_of}
                  />

                  {selected.holding.note && (
                    <details className="pl-item-note">
                      <summary>原持仓备注</summary>
                      <p>{selected.holding.note}</p>
                    </details>
                  )}
                </>
              ) : (
                <p className="pl-empty">选择一只基金查看档案。</p>
              )}
            </aside>
          </div>

          <details className="pl-history">
            <summary>
              历史组合备注与计划入口 <span>旧研究文字记录 · 计划待办管理</span>
            </summary>
            <div style={{ margin: "10px 0 6px" }}>
              <Link to="/plans" className="btn small">
                打开计划待办管理 →
              </Link>
            </div>
            <section>
              <h3>原始录入来源</h3>
              <p>{data.data_source_cn}</p>
            </section>
            {data.observations.length > 0 && (
              <section>
                <h3>组合提示</h3>
                <ul>
                  {data.observations.map((o, i) => (
                    <li key={i}>{o}</li>
                  ))}
                </ul>
              </section>
            )}
            {data.advices.length > 0 && (
              <section>
                <h3>原调仓建议</h3>
                {data.advices.map((a) => (
                  <article key={a.advice_id}>
                    <h4>
                      {a.title_cn} <small>{a.strength_cn}</small>
                    </h4>
                    <p>{a.detail_cn}</p>
                  </article>
                ))}
              </section>
            )}
            {data.groups.map((g) => (
              <section key={g.group_key}>
                <h3>{g.name} · 原分组说明</h3>
                <p>{g.verdict_cn}</p>
              </section>
            ))}
          </details>
        </>
      ) : (
        <section className="pl-trades" role="tabpanel">
          <p>手动成交台账（独立维护，不自动改动上方持仓金额）。</p>
          <div className="pl-trade-review">
            <ReviewFetcher weekly />
          </div>
          <TradesLedgerView />
        </section>
      )}
    </div>
  );
}
