import { useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { portfolioApi } from "../api/client";
import type { Card } from "../types";
import { fmtChange } from "../utils/format";
import { classifySymbol, mapHoldingsToSymbols, type SymbolSource } from "../utils/portfolioSymbols";
import { TRACK_BENCHMARKS } from "../utils/portfolioTrackBenchmarks";
import ColorBadge from "./ColorBadge";
import "./cross-section-compare.css";

type ScopeFilter = "core" | "portfolio" | "index" | "etf" | "sector" | "all";
type QuickFilter = "all" | "bull" | "near_ma";
type SortField = "status" | "mom121" | "ret20" | "ema20" | "change";

function isNearMaBull(c: Card): boolean {
  return c.color === "green" && c.dist_ema20_pct != null && c.dist_ema20_pct >= -2 && c.dist_ema20_pct <= 6;
}

interface Props {
  cards: Card[];
  selected: string;
  onSelectSymbol: (symbol: string) => void;
}

function isSectorSymbol(symbol: string): boolean {
  return symbol.endsWith(".SECTOR");
}

function statusScore(card: Card): number {
  const colorRank = card.color === "green" ? 300 : card.color === "gray" ? 200 : card.color === "black" ? 100 : 0;
  const w = card.weekly_long_trend_cn ?? "";
  const weeklyRank = w.includes("多头") && !w.includes("转弱")
    ? 40
    : w.includes("改善") || w.includes("转弱")
      ? 25
      : w.includes("空头")
        ? 5
        : 15;
  const tradableRank = card.tradable === true ? 8 : 0;
  const momTie = card.mom_121_pct != null ? Math.max(-5, Math.min(5, card.mom_121_pct / 20)) : 0;
  return colorRank + weeklyRank + tradableRank + momTie;
}

function fmtSignedPct(value: number | null | undefined, digits = 1): string {
  if (value == null || !Number.isFinite(value)) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(digits)}%`;
}

function shortDate(isoDate: string | null | undefined): string {
  if (!isoDate) return "";
  return isoDate.length === 10 ? isoDate.slice(5) : isoDate;
}

function trendToneClass(text: string | null | undefined): string {
  if (!text || text === "数据不足") return "csc-pill-muted";
  if (text.includes("多头") && !text.includes("转弱")) return "csc-pill-support";
  if (text.includes("空头") || text.includes("恶化")) return "csc-pill-caution";
  return "csc-pill-neutral";
}

export default function CrossSectionComparePanel({ cards, selected, onSelectSymbol }: Props) {
  const [params] = useSearchParams();
  const [scope, setScope] = useState<ScopeFilter>(() =>
    params.get("scope") === "portfolio" ? "portfolio" : "core",
  );
  const [quickFilter, setQuickFilter] = useState<QuickFilter>("all");
  const [sortBy, setSortBy] = useState<SortField>("status");
  const [sortDesc, setSortDesc] = useState(true);

  useEffect(() => {
    if (params.get("scope") === "portfolio") setScope("portfolio");
  }, [params]);

  // 复用既有持仓精确映射逻辑：只对满足身份核验的产品标「已关联持仓」，不把场外联接混同指数本身
  const { data: portfolio } = useQuery({
    queryKey: ["portfolio"],
    queryFn: portfolioApi.get,
    staleTime: 5 * 60_000,
  });

  const heldSymbolNames = useMemo(() => {
    const map = new Map<string, string[]>();
    if (!portfolio) return map;
    const holdings = portfolio.groups.flatMap((g) => g.holdings);
    const sources: SymbolSource[] = cards
      .filter((c) => !c.error)
      .map((c) => ({
        symbol: c.symbol,
        name: c.display_name,
        identity: c.group === "watchlist" ? classifySymbol(c.symbol) : ("insufficient" as const),
      }));
    const linked = mapHoldingsToSymbols(holdings, sources);
    for (const h of holdings) {
      const m = linked.get(h.holding_id);
      if (m) {
        const prev = map.get(m.symbol) ?? [];
        prev.push(h.name);
        map.set(m.symbol, prev);
      }
    }
    return map;
  }, [portfolio, cards]);

  // 同方向市场参考映射（明确标注为赛道公开参考，与「已关联自身行情」严格区分）
  const trackRefBySymbol = useMemo(() => {
    const map = new Map<string, { label: string; totalPct: number; fullNames: string[] }>();
    if (!portfolio) return map;
    for (const g of portfolio.groups) {
      if (g.pct <= 0) continue;
      const spec = TRACK_BENCHMARKS[g.group_key];
      if (!spec) continue;
      for (const sym of spec.referenceSymbols) {
        const prev = map.get(sym);
        if (!prev) {
          map.set(sym, {
            label: spec.shortLabel,
            totalPct: g.pct,
            fullNames: [`${g.name} (${g.pct.toFixed(1)}%)`],
          });
        } else {
          prev.totalPct += g.pct;
          prev.fullNames.push(`${g.name} (${g.pct.toFixed(1)}%)`);
        }
      }
    }
    return map;
  }, [portfolio]);

  const validCards = useMemo(() => cards.filter((c) => !c.error), [cards]);

  const isPortfolioRelated = (c: Card) =>
    heldSymbolNames.has(c.symbol) || trackRefBySymbol.has(c.symbol);

  const counts = useMemo(() => {
    let core = 0;
    let pf = 0;
    let index = 0;
    let etf = 0;
    let sector = 0;
    for (const c of validCards) {
      if (isPortfolioRelated(c)) pf += 1;
      if (isSectorSymbol(c.symbol)) {
        sector += 1;
      } else {
        core += 1;
        if (c.group === "index") index += 1;
        else etf += 1;
      }
    }
    return { core, pf, index, etf, sector, all: validCards.length };
  }, [validCards, heldSymbolNames, trackRefBySymbol]);

  const scopeFiltered = useMemo(() => {
    return validCards.filter((c) => {
      if (scope === "core") return !isSectorSymbol(c.symbol);
      if (scope === "portfolio") return isPortfolioRelated(c);
      if (scope === "index") return c.group === "index";
      if (scope === "etf") return c.group === "watchlist" && !isSectorSymbol(c.symbol);
      if (scope === "sector") return isSectorSymbol(c.symbol);
      return true;
    });
  }, [validCards, scope, heldSymbolNames, trackRefBySymbol]);

  const filtered = useMemo(() => {
    const list = scopeFiltered.filter((c) => {
      if (quickFilter === "bull") return c.color === "green";
      if (quickFilter === "near_ma") return isNearMaBull(c);
      return true;
    });

    const metricOf = (c: Card): number | null => {
      switch (sortBy) {
        case "status":
          return statusScore(c);
        case "mom121":
          return c.mom_121_pct ?? null;
        case "ret20":
          return c.ret_20d_pct ?? null;
        case "ema20":
          return c.dist_ema20_pct ?? null;
        case "change":
          return c.change_pct ?? null;
      }
    };

    return [...list].sort((a, b) => {
      const av = metricOf(a);
      const bv = metricOf(b);
      if (av == null && bv == null) return a.display_name.localeCompare(b.display_name, "zh-CN");
      if (av == null) return 1;
      if (bv == null) return -1;
      return sortDesc ? bv - av : av - bv;
    });
  }, [scopeFiltered, quickFilter, sortBy, sortDesc]);

  const toggleSort = (field: SortField) => {
    if (sortBy === field) {
      setSortDesc((d) => !d);
    } else {
      setSortBy(field);
      setSortDesc(true);
    }
  };

  const sortArrow = (field: SortField) =>
    sortBy === field ? (sortDesc ? " ↓" : " ↑") : "";

  const greenCount = scopeFiltered.filter((c) => c.color === "green").length;
  const nearMaCount = scopeFiltered.filter(isNearMaBull).length;
  const grayCount = scopeFiltered.filter((c) => c.color === "gray").length;
  const blackCount = scopeFiltered.filter((c) => c.color === "black").length;

  return (
    <section className="csc-panel" aria-label="核心标的横向强弱对比">
      <div className="csc-head">
        <div className="csc-head-left">
          <h2 className="csc-title">横向比强弱</h2>
          <span
            className="ctl-help-btn"
            tabIndex={0}
            title={
              "读数说明：\n" +
              "• 顺势贴均线：绿色多头且最新价在 20 日均线 -2% ~ +6% 区间（贴近成本、不追高）\n" +
              "• 中期动量：近一年剔除近一月涨跌幅，用于横向比强弱\n" +
              "• 「参考·赛道%」为与场外持仓同方向的公开参考标的"
            }
          >
            ?
          </span>
          <div className="csc-quick-filters" role="group" aria-label="实战快捷筛选">
            <button
              type="button"
              className={`csc-qf-btn${quickFilter === "all" ? " active" : ""}`}
              onClick={() => setQuickFilter("all")}
            >
              全部 ({scopeFiltered.length})
            </button>
            <button
              type="button"
              className={`csc-qf-btn is-bull${quickFilter === "bull" ? " active" : ""}`}
              onClick={() => setQuickFilter(quickFilter === "bull" ? "all" : "bull")}
            >
              ● 多头顺势 ({greenCount})
            </button>
            <button
              type="button"
              className={`csc-qf-btn is-sweet${quickFilter === "near_ma" ? " active" : ""}`}
              onClick={() => setQuickFilter(quickFilter === "near_ma" ? "all" : "near_ma")}
              title="多头状态且距 20 日均线在 -2% ~ +6% 区间，适合重点挑图"
            >
              🎯 顺势贴均线 ({nearMaCount})
            </button>
          </div>
        </div>
        <div className="csc-summary-pills" aria-label="当前分组道路分布">
          <span className="csc-stat">绿 <b>{greenCount}</b></span>
          <span className="csc-stat">灰 <b>{grayCount}</b></span>
          <span className="csc-stat">黑 <b>{blackCount}</b></span>
          <Link to="/portfolio" className="csc-portfolio-link">我的持仓 ({portfolio?.holdings_count ?? "—"}) →</Link>
        </div>
      </div>

      <div className="csc-toolbar">
        <div className="csc-scopes" role="tablist" aria-label="标的分组筛选">
          <button
            type="button"
            role="tab"
            aria-selected={scope === "core"}
            className={`csc-scope-btn${scope === "core" ? " active" : ""}`}
            onClick={() => setScope("core")}
          >
            核心宽基与ETF ({counts.core})
          </button>
          {counts.pf > 0 && (
            <button
              type="button"
              role="tab"
              aria-selected={scope === "portfolio"}
              className={`csc-scope-btn${scope === "portfolio" ? " active" : ""}`}
              onClick={() => setScope("portfolio")}
              title="筛选与我的持仓赛道同方向的公开指数/ETF参考"
            >
              持仓方向参考 ({counts.pf})
            </button>
          )}
          <button
            type="button"
            role="tab"
            aria-selected={scope === "index"}
            className={`csc-scope-btn${scope === "index" ? " active" : ""}`}
            onClick={() => setScope("index")}
          >
            大盘宽基 ({counts.index})
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={scope === "etf"}
            className={`csc-scope-btn${scope === "etf" ? " active" : ""}`}
            onClick={() => setScope("etf")}
          >
            自选ETF ({counts.etf})
          </button>
          {counts.sector > 0 && (
            <button
              type="button"
              role="tab"
              aria-selected={scope === "sector"}
              className={`csc-scope-btn${scope === "sector" ? " active" : ""}`}
              onClick={() => setScope("sector")}
            >
              行业板块指数 ({counts.sector})
            </button>
          )}
          <button
            type="button"
            role="tab"
            aria-selected={scope === "all"}
            className={`csc-scope-btn${scope === "all" ? " active" : ""}`}
            onClick={() => setScope("all")}
          >
            全部 ({counts.all})
          </button>
        </div>
        <div className="csc-sort-pills" aria-label="快捷排序">
          <span className="csc-sort-hint">排序：</span>
          <button type="button" className={`csc-mini-sort${sortBy === "status" ? " active" : ""}`} onClick={() => toggleSort("status")}>
            趋势状态{sortArrow("status")}
          </button>
          <button type="button" className={`csc-mini-sort${sortBy === "mom121" ? " active" : ""}`} onClick={() => toggleSort("mom121")}>
            12-1动量{sortArrow("mom121")}
          </button>
          <button type="button" className={`csc-mini-sort${sortBy === "ema20" ? " active" : ""}`} onClick={() => toggleSort("ema20")}>
            距EMA20{sortArrow("ema20")}
          </button>
          <button type="button" className={`csc-mini-sort${sortBy === "ret20" ? " active" : ""}`} onClick={() => toggleSort("ret20")}>
            20日偏离{sortArrow("ret20")}
          </button>
        </div>
      </div>

      <div className="csc-table-wrap">
        <table className="csc-table">
          <thead>
            <tr>
              <th>标的 / 截止日</th>
              <th className="csc-num">
                <button type="button" className="csc-th-btn" onClick={() => toggleSort("change")}>
                  最新 / 日涨跌{sortArrow("change")}
                </button>
              </th>
              <th>
                <button type="button" className="csc-th-btn" onClick={() => toggleSort("status")}>
                  道路与阶段{sortArrow("status")}
                </button>
              </th>
              <th>周 / 日长趋势</th>
              <th className="csc-num">
                <button type="button" className="csc-th-btn" onClick={() => toggleSort("ema20")}>
                  均线偏离 (20 / 60){sortArrow("ema20")}
                </button>
              </th>
              <th className="csc-num">
                <button type="button" className="csc-th-btn" onClick={() => toggleSort("mom121")}>
                  12-1动量 / 20日{sortArrow("mom121")}
                </button>
              </th>
              <th>前低支撑与看图</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((card) => {
              const chg = fmtChange(card.change_pct);
              const isSelected = card.symbol === selected;
              const heldNames = heldSymbolNames.get(card.symbol);
              const trackRef = !heldNames ? trackRefBySymbol.get(card.symbol) : undefined;
              const distC = card.primary_structure?.distance_to_c_pct ?? null;
              const nearPriorLow = distC != null && distC >= 0 && distC <= 8;
              const stretchedShortTerm =
                card.ret_20d_pct != null && card.ret_20d_pct >= 8 && !nearPriorLow;

              return (
                <tr
                  key={card.symbol}
                  className={`csc-row${isSelected ? " is-selected" : ""}`}
                  onClick={() => onSelectSymbol(card.symbol)}
                >
                  <td className="csc-cell-name">
                    <div className="csc-name-line">
                      <strong>{card.display_name}</strong>
                      {heldNames && (
                        <span className="csc-held-chip" title={`已关联自身持仓：${heldNames.join("、")}`}>
                          持仓
                        </span>
                      )}
                      {trackRef && (
                        <span
                          className="csc-ref-chip"
                          title={`同方向公开参考（非场外基金自身净值）：对应 ${trackRef.fullNames.join(" + ")}`}
                        >
                          参考·{trackRef.label} {trackRef.totalPct.toFixed(0)}%
                        </span>
                      )}
                    </div>
                    <div className="csc-meta-line" title={card.last_bar_date ? `行情截至 ${card.last_bar_date}` : undefined}>
                      {card.symbol}
                      {card.market_cn ? ` · ${card.market_cn}` : ""}
                      {card.last_bar_date ? ` · ${shortDate(card.last_bar_date)}` : ""}
                    </div>
                  </td>

                  <td className="csc-num">
                    <div className="csc-price">{card.price != null ? card.price.toFixed(2) : "—"}</div>
                    <div className={`csc-chg ${chg.cls}`}>{chg.text}</div>
                  </td>

                  <td>
                    <div className="csc-color-wrap">
                      <ColorBadge color={card.color} colorCn={card.color_cn} />
                      {card.color_days != null && (
                        <span className="csc-days">{card.color_days}天</span>
                      )}
                    </div>
                    <div className="csc-sub-meta">
                      {card.stage_cn || "—"}
                      {card.tradable === false ? " · 暂不宜追" : ""}
                    </div>
                  </td>

                  <td>
                    <div className="csc-trends">
                      {card.weekly_long_trend_cn && card.weekly_long_trend_cn !== "数据不足" && (
                        <span className={`csc-pill ${trendToneClass(card.weekly_long_trend_cn)}`}>
                          周·{card.weekly_long_trend_cn}
                        </span>
                      )}
                      <span className={`csc-pill ${trendToneClass(card.daily_long_trend_cn)}`}>
                        日·{card.daily_long_trend_cn || "—"}
                      </span>
                    </div>
                  </td>

                  <td className="csc-num csc-mono">
                    {(() => {
                      const d20 = card.dist_ema20_pct;
                      const barW = d20 != null ? Math.min(100, (Math.abs(d20) / 15) * 100) : 0;
                      const tone =
                        d20 == null
                          ? ""
                          : d20 >= -2 && d20 <= 6
                            ? "is-sweet"
                            : d20 > 10
                              ? "is-hot"
                              : d20 < 0
                                ? "is-neg"
                                : "is-pos";
                      return (
                        <>
                          <div className={`csc-metric-bar ${tone}`}>
                            {d20 != null && <i style={{ width: `${barW.toFixed(0)}%` }} />}
                            <span>20日 {fmtSignedPct(d20)}</span>
                          </div>
                          <div className="csc-sub-num">60日 {fmtSignedPct(card.dist_ema60_pct)}</div>
                        </>
                      );
                    })()}
                  </td>

                  <td className="csc-num csc-mono">
                    {(() => {
                      const m = card.mom_121_pct;
                      const barW = m != null ? Math.min(100, (Math.abs(m) / 40) * 100) : 0;
                      const tone = m == null ? "" : m >= 15 ? "is-pos" : m < 0 ? "is-neg" : "";
                      return (
                        <>
                          <div className={`csc-metric-bar ${tone}`}>
                            {m != null && <i style={{ width: `${barW.toFixed(0)}%` }} />}
                            <span className="csc-mom-main">{fmtSignedPct(m)}</span>
                          </div>
                          <div className="csc-sub-num">
                            20日 {fmtSignedPct(card.ret_20d_pct)}
                            {stretchedShortTerm && (
                              <span className="csc-stretch-warn" title="近20日涨幅较大且无邻近前低支撑，留意短线追高回撤">
                                偏高
                              </span>
                            )}
                          </div>
                        </>
                      );
                    })()}
                  </td>

                  <td className="csc-defense">
                    {nearPriorLow ? (
                      <span
                        className="csc-c-dist"
                        title={`离近期底部前低支撑价 ${card.primary_structure?.c_price ?? ""} 还有 ${fmtSignedPct(distC)}（跌破则底部形态失效）`}
                      >
                        离前低 {fmtSignedPct(distC)}
                      </span>
                    ) : (
                      <span className="csc-dash" title="当前无邻近（8%以内）前低支撑线，先参考20日/60日均线位置">
                        看均线
                      </span>
                    )}
                    <button
                      type="button"
                      className="csc-go-btn"
                      onClick={(e) => {
                        e.stopPropagation();
                        onSelectSymbol(card.symbol);
                      }}
                    >
                      看图 →
                    </button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <p className="csc-empty">
            当前筛选下暂无符合条件的标的。
            {quickFilter !== "all" && (
              <button
                type="button"
                className="btn small"
                style={{ marginLeft: 8 }}
                onClick={() => setQuickFilter("all")}
              >
                查看全部
              </button>
            )}
          </p>
        )}
      </div>
    </section>
  );
}
