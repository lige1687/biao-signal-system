import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigate } from "react-router-dom";
import * as echarts from "echarts";
import { sectorsApi } from "../api/client";
import { etfsForSector } from "../data/sectorEtfMap";
import { fmt, fmtYi, pctClass } from "../utils/format";
import ColorBadge from "../components/ColorBadge";
import OverlayChart, { type OverlaySeries } from "../components/trend/OverlayChart";
import type {
  SectorTrendRow,
  SectorHistoryPoint,
  SectorMembersResponse,
  SectorWatchItem,
} from "../types";

// ── 阶段语义（LEI 口径，与 RRG 共用色板；注意与 A 股红涨绿跌无关）──
const STAGE_CN: Record<string, string> = {
  markup: "上升",
  accumulation: "筑底",
  distribution: "派发",
  decline: "下降",
};
const STAGE_ORDER: Record<string, number> = {
  markup: 4,
  accumulation: 3,
  distribution: 2,
  decline: 1,
  "": 0,
};
/** 亮色主题下调深后的阶段色（RRG 散点、统计条、chip 边框共用单一来源）。 */
const STAGE_HEX: Record<string, string> = {
  markup: "#12935d",
  accumulation: "#4d7fc4",
  distribution: "#c08a1f",
  decline: "#d24a43",
  "": "#9aa4b2",
};

const STARS_KEY = "lei.sector.stars";
const MACD_BLIND_SPOT =
  "MACD 盲区：柱/线背离需结合量价与均线斜率；本列为研究代理补充，非买卖建议。";

type SortKey =
  | "stage"
  | "rs_pctile"
  | "rs_pctile_delta_20"
  | "rs_chg_60"
  | "pct_change"
  | "b50"
  | "nh60"
  | "flow_20d_main_yi"
  | "pe_ttm";

/** 级别筛选：仅 L1（31 个一级行业）/ 含二级 / 全部层级。 */
type LevelMode = "l1" | "l2" | "all";
const LEVEL_MODES: { key: LevelMode; label: string; tip: string }[] = [
  { key: "l1", label: "仅L1", tip: "31 个一级行业，信号最干净（默认）" },
  { key: "l2", label: "含二级", tip: "加二级行业细分，看轮动更细" },
  { key: "all", label: "全部层级", tip: "含三级概念板块（噪声多，慎用）" },
];

const STAGE_FILTERS: { key: string | null; label: string; tip: string }[] = [
  { key: null, label: "全部阶段", tip: "不按阶段筛选" },
  { key: "markup", label: "上升", tip: "道路向上：三条件确立，机会区" },
  { key: "accumulation", label: "筑底", tip: "底部积累：RS 相对强，但道路条件未齐" },
  { key: "distribution", label: "派发", tip: "高位转弱：价格仍在 SMA60 上，斜率/宽度走坏" },
  { key: "decline", label: "下降", tip: "道路向下：价格 < SMA60 且斜率向下" },
];

function loadStars(): string[] {
  try {
    return JSON.parse(localStorage.getItem(STARS_KEY) ?? "[]");
  } catch {
    return [];
  }
}

function median(xs: number[]): number | null {
  if (xs.length === 0) return null;
  const s = [...xs].sort((a, b) => a - b);
  const mid = s.length >> 1;
  return s.length % 2 ? s[mid] : (s[mid - 1] + s[mid]) / 2;
}

export default function SectorsPage() {
  const queryClient = useQueryClient();
  const [sortKey, setSortKey] = useState<SortKey>("rs_pctile");
  const [sortAsc, setSortAsc] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [levelMode, setLevelMode] = useState<LevelMode>("l1");
  const [stageFilter, setStageFilter] = useState<string | null>(null);
  const [onlyStars, setOnlyStars] = useState(false);
  const [stars, setStars] = useState<string[]>(loadStars);
  const [selected, setSelected] = useState<SectorTrendRow | null>(null);
  const [membersCode, setMembersCode] = useState<string | null>(null);
  const [showTails, setShowTails] = useState(true);
  const [helpOpen, setHelpOpen] = useState(false);

  const { data, error } = useQuery({
    queryKey: ["sectorsTrend"],
    queryFn: () => sectorsApi.trend(false, "all"),
    staleTime: 5 * 60_000,
  });

  const refreshMutation = useMutation({
    mutationFn: () => sectorsApi.trend(true, "all"),
    onSuccess: (d) => {
      queryClient.setQueryData(["sectorsTrend"], d);
      queryClient.invalidateQueries({ queryKey: ["sectorsWatchlist"] });
    },
  });

  const rows: SectorTrendRow[] = useMemo(() => data?.boards ?? [], [data]);

  /** 级别过滤后的「市场全集」（统计条与 RRG / 动能榜共用口径）。 */
  const levelRows = useMemo(
    () =>
      rows.filter((b) =>
        levelMode === "l1" ? b.level === 1 : levelMode === "l2" ? b.level <= 2 : true,
      ),
    [rows, levelMode],
  );

  const visibleRows = useMemo(() => {
    let list = levelRows;
    if (onlyStars) list = list.filter((b) => stars.includes(b.code));
    if (stageFilter) list = list.filter((b) => (b.stage ?? "") === stageFilter);
    if (keyword.trim()) {
      const k = keyword.trim().toLowerCase();
      list = list.filter(
        (b) => b.name.toLowerCase().includes(k) || b.code.toLowerCase().includes(k),
      );
    }
    const dir = sortAsc ? 1 : -1;
    return [...list].sort((a, b) => {
      let av: number;
      let bv: number;
      if (sortKey === "stage") {
        av = STAGE_ORDER[a.stage ?? ""] ?? 0;
        bv = STAGE_ORDER[b.stage ?? ""] ?? 0;
      } else {
        av = (a[sortKey] as number | null) ?? -1e18;
        bv = (b[sortKey] as number | null) ?? -1e18;
      }
      return (bv - av) * dir;
    });
  }, [levelRows, onlyStars, keyword, stageFilter, sortKey, sortAsc, stars]);

  function toggleStar(code: string) {
    setStars((prev) => {
      const next = prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code];
      localStorage.setItem(STARS_KEY, JSON.stringify(next));
      return next;
    });
  }

  function pickByCode(code: string) {
    const r = rows.find((b) => b.code === code);
    if (r) setSelected(r);
  }

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortAsc(!sortAsc);
    else {
      setSortKey(key);
      setSortAsc(false);
    }
  }

  return (
    <div className="page sx-page">
      {/* ── 头部：一行说清「这是什么数据、多新」────────────────────── */}
      <div className="sx-header">
        <div className="sx-title">
          <h1>行业板块</h1>
          {data && (
            <span className="sx-meta">
              交易日 {data.trading_day} · 更新{" "}
              {new Date(data.as_of).toLocaleTimeString("zh-CN", {
                hour12: false,
                hour: "2-digit",
                minute: "2-digit",
              })}{" "}
              · 等权合成 research_proxy
            </span>
          )}
        </div>
        <div className="sx-header-actions">
          <button
            className={`btn small${helpOpen ? " primary" : ""}`}
            onClick={() => setHelpOpen((v) => !v)}
            title="指标口径与读法"
          >
            ? 说明
          </button>
          <button
            className="btn small primary"
            disabled={refreshMutation.isPending}
            onClick={() => refreshMutation.mutate()}
          >
            {refreshMutation.isPending ? "刷新中…" : "刷新"}
          </button>
        </div>
      </div>
      {helpOpen && <HelpCard note={data?.research_proxy_note} onClose={() => setHelpOpen(false)} />}
      {error && (
        <div className="fund-errors">
          加载失败：{(error as Error).message}
          <div className="fund-hint">请先在本机跑 scripts/precompute_sector_trend.py 生成快照。</div>
        </div>
      )}

      {/* ── 状态层：当前筛选集的实时统计（不是装饰，是市场宽度速览）── */}
      <StatsStrip rows={visibleRows} total={rows.length} />

      {/* ── 主体：左表格（核心） + 右轮动栏（sticky）──────────────── */}
      <div className="sx-main">
        <div className="sx-left">
          <div className="sx-toolbar">
            <input
              className="sx-search"
              placeholder="搜索板块…"
              value={keyword}
              onChange={(e) => setKeyword(e.target.value)}
            />
            <div className="sx-seg-group">
              <span className="sx-seg-label">阶段</span>
              <div className="sx-seg">
                {STAGE_FILTERS.map((f) => (
                  <button
                    key={f.key ?? "all"}
                    className={`sx-seg-btn${stageFilter === f.key ? " on" : ""}`}
                    onClick={() => setStageFilter(f.key)}
                    title={f.tip}
                  >
                    {f.label}
                  </button>
                ))}
              </div>
            </div>
            <div className="sx-seg-group">
              <span className="sx-seg-label">层级</span>
              <div className="sx-seg">
                {LEVEL_MODES.map((m) => (
                  <button
                    key={m.key}
                    className={`sx-seg-btn${levelMode === m.key ? " on" : ""}`}
                    onClick={() => setLevelMode(m.key)}
                    title={m.tip}
                  >
                    {m.label}
                  </button>
                ))}
              </div>
            </div>
            <button
              className={`btn small${onlyStars ? " primary" : ""}`}
              onClick={() => setOnlyStars((v) => !v)}
              title="只看标过 ★ 的板块（表格每行最左侧可加星）"
            >
              ★ 自选
            </button>
            <span className="sx-count">
              {visibleRows.length}/{rows.length}
            </span>
          </div>

          <div className="sx-tablewrap">
            <table className="sx-table">
              <thead>
                <tr>
                  <th className="col-star"></th>
                  <th title="板块名称与级别（L1=一级行业 / L2=二级细分 / L3=三级）；色点=LEI 长趋势">板块</th>
                  <SortableTh
                    label="阶段"
                    sortKey="stage"
                    cur={sortKey}
                    asc={sortAsc}
                    onToggle={toggleSort}
                    tip="LEI 市场阶段：上升=机会 / 筑底=中性 / 派发=谨慎 / 下降=危险（绿=上升与 A 股红涨无关）"
                  />
                  <SortableTh
                    label="RS位"
                    sortKey="rs_pctile"
                    cur={sortKey}
                    asc={sortAsc}
                    onToggle={toggleSort}
                    tip="相对全 A 等权基准的强弱百分位：0 最弱、100 最强，50 为强弱分界"
                  />
                  <SortableTh
                    label="RS20Δ"
                    sortKey="rs_pctile_delta_20"
                    cur={sortKey}
                    asc={sortAsc}
                    onToggle={toggleSort}
                    tip="RS 百分位近 20 日变化：正=相对强度在改善，负=走弱"
                  />
                  <SortableTh
                    label="60日%"
                    sortKey="rs_chg_60"
                    cur={sortKey}
                    asc={sortAsc}
                    onToggle={toggleSort}
                    tip="板块近 60 个交易日涨跌幅"
                  />
                  <SortableTh
                    label="当日%"
                    sortKey="pct_change"
                    cur={sortKey}
                    asc={sortAsc}
                    onToggle={toggleSort}
                    tip="板块当日涨跌幅（红涨绿跌）"
                  />
                  <SortableTh
                    label="b50"
                    sortKey="b50"
                    cur={sortKey}
                    asc={sortAsc}
                    onToggle={toggleSort}
                    tip="成分股站上 MA50 的比例：板块内部宽度，高=共识强"
                  />
                  <SortableTh
                    label="nh60"
                    sortKey="nh60"
                    cur={sortKey}
                    asc={sortAsc}
                    onToggle={toggleSort}
                    tip="60 日新高家数占比：板块内创新高的广度"
                  />
                  <SortableTh
                    label="20日主力"
                    sortKey="flow_20d_main_yi"
                    cur={sortKey}
                    asc={sortAsc}
                    onToggle={toggleSort}
                    tip="近 20 日主力（超大+大单）累计净流入（亿元，单据规模代理，覆盖约 14% 板块）"
                  />
                  <th className="num" title="均线排列 · MACD 形态（辅助验证）">
                    均线/MACD
                  </th>
                  <SortableTh
                    label="PE"
                    sortKey="pe_ttm"
                    cur={sortKey}
                    asc={sortAsc}
                    onToggle={toggleSort}
                    tip="市盈率 TTM，负值=亏损"
                  />
                  <th className="num" title="命中板块规则的成分股数 / 总成分股数">
                    成分
                  </th>
                </tr>
              </thead>
              <tbody>
                {visibleRows.map((b) => (
                  <tr key={b.code} className={b.level === 3 ? "dim" : ""} onClick={() => setSelected(b)}>
                    <td className="col-star" onClick={(e) => e.stopPropagation()}>
                      <button
                        className={`star-btn${stars.includes(b.code) ? " on" : ""}`}
                        onClick={() => toggleStar(b.code)}
                        title="加入板块自选"
                      >
                        ★
                      </button>
                    </td>
                    <td className="col-name">
                      <span
                        className="sx-lei-dot"
                        style={{ background: leiDotColor(b.signal_color) }}
                        title={`LEI 长趋势：${b.signal_color_cn ?? "-"}（${b.long_trend_cn ?? "-"}）`}
                      />
                      {b.name}
                      <span className="symbol">
                        L{b.level}·{b.code}
                      </span>
                    </td>
                    <td className="num">
                      {b.stage ? (
                        <span
                          className="sx-stage-chip"
                          style={{
                            color: STAGE_HEX[b.stage],
                            borderColor: STAGE_HEX[b.stage],
                            background: `${STAGE_HEX[b.stage]}12`,
                          }}
                          title={(b.stage_basis ?? []).join("；")}
                        >
                          {STAGE_CN[b.stage]}
                        </span>
                      ) : (
                        <span className="muted">样本不足</span>
                      )}
                    </td>
                    <td className="num">
                      <BarCell v={b.rs_pctile} digits={0} tick50 color="#4d7fc4" />
                    </td>
                    <td className={`num ${pctClass(b.rs_pctile_delta_20)}`}>
                      {fmt(b.rs_pctile_delta_20, 1)}
                    </td>
                    <td className={`num ${pctClass(b.rs_chg_60)}`}>{fmt(b.rs_chg_60, 1, "%")}</td>
                    <td className={`num ${pctClass(b.pct_change)} strong`}>
                      {fmt(b.pct_change, 2, "%")}
                    </td>
                    <td className="num">
                      <BarCell v={b.b50} digits={0} color="#c08a1f" />
                    </td>
                    <td className="num">{fmt(b.nh60, 0)}</td>
                    <td className={`num ${b.flow_20d_main_yi != null && b.flow_20d_main_yi > 0 ? "up" : b.flow_20d_main_yi != null && b.flow_20d_main_yi < 0 ? "down" : ""}`}>
                      {b.flow_20d_main_yi == null ? (
                        <span className="muted">-</span>
                      ) : (
                        <span
                          title={b.flow_vs_stage_cn ? `阶段交叉验证：${b.flow_vs_stage_cn}` : undefined}
                        >
                          {b.flow_20d_main_yi.toFixed(0)}
                        </span>
                      )}
                    </td>
                    <td
                      className="num sx-tech"
                      title={
                        b.macd_label_cn
                          ? `${b.alignment_cn ?? "-"}｜${b.macd_label_cn}｜${b.macd_detail_cn ?? ""}｜${MACD_BLIND_SPOT}`
                          : MACD_BLIND_SPOT
                      }
                    >
                      {(b.alignment_cn ?? "-").replace("排列", "")}
                      {b.macd_status ? ` · ${b.macd_status}` : ""}
                    </td>
                    <td className="num">
                      {b.pe_ttm == null ? "-" : b.pe_ttm < 0 ? "亏" : b.pe_ttm.toFixed(0)}
                    </td>
                    <td className="num sx-dim-num">
                      {b.hit_count}/{b.member_count}
                    </td>
                  </tr>
                ))}
                {visibleRows.length === 0 && (
                  <tr>
                    <td colSpan={13} className="muted">
                      无匹配板块（请先运行预计算脚本）
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* ── 轮动层：RRG + 动能榜 + 今日观察（随主表级别口径联动）── */}
        <aside className="sx-rail">
          <section className="sx-rail-card">
            <div className="sx-rail-head">
              <span className="sx-rail-title">轮动 RRG</span>
              <span className="sx-rail-sub">X=RS位 · Y=RS20Δ</span>
              <span className="spacer" />
              <button
                className={`sx-mini-btn${showTails ? " on" : ""}`}
                onClick={() => setShowTails((v) => !v)}
                title="显示近 8 日移动轨迹"
              >
                尾迹
              </button>
            </div>
            <RrgPanel rows={levelRows} showTails={showTails} onPick={pickByCode} />
            <div className="sx-rrg-quad">
              <span style={{ color: STAGE_HEX.markup }}>右上·领先</span>
              <span style={{ color: STAGE_HEX.accumulation }}>左上·改善</span>
              <span style={{ color: STAGE_HEX.distribution }}>右下·走弱</span>
              <span style={{ color: STAGE_HEX.decline }}>左下·滞后</span>
            </div>
          </section>

          <MoversCard rows={levelRows} onPick={pickByCode} />
          <WatchCard onPick={pickByCode} />
        </aside>
      </div>

      {selected && (
        <SectorTrendDrawer
          row={selected}
          onClose={() => setSelected(null)}
          onOpenMembers={(code) => setMembersCode(code)}
        />
      )}
      {membersCode && <MembersDrawer code={membersCode} onClose={() => setMembersCode(null)} />}
    </div>
  );
}

// ── 统计条：当前筛选集的市场宽度速览 ────────────────────────────────────────
function StatsStrip({ rows, total }: { rows: SectorTrendRow[]; total: number }) {
  const stats = useMemo(() => {
    const stages: Record<string, number> = { markup: 0, accumulation: 0, distribution: 0, decline: 0, "": 0 };
    let up = 0;
    let hasPct = 0;
    let rsStrong = 0;
    let hasRs = 0;
    for (const b of rows) {
      stages[b.stage ?? ""] = (stages[b.stage ?? ""] ?? 0) + 1;
      if (b.pct_change != null) {
        hasPct++;
        if (b.pct_change > 0) up++;
      }
      if (b.rs_pctile != null) {
        hasRs++;
        if (b.rs_pctile > 50) rsStrong++;
      }
    }
    return {
      stages,
      up,
      hasPct,
      rsStrong,
      hasRs,
      medB50: median(rows.map((b) => b.b50).filter((v): v is number => v != null)),
      medRsD20: median(
        rows.map((b) => b.rs_pctile_delta_20).filter((v): v is number => v != null),
      ),
    };
  }, [rows]);

  const n = rows.length;
  const stageEntries = (
    ["markup", "accumulation", "distribution", "decline", ""] as const
  ).map((k) => ({ key: k, cn: k ? STAGE_CN[k] : "样本不足", count: stats.stages[k] ?? 0 }));

  return (
    <div className="sx-stats">
      <div className="sx-stat sx-stat-wide">
        <div className="sx-stat-label">
          阶段分布
          <span className="sx-stat-sub">
            {n === total ? `全部 ${total} 板块` : `筛选后 ${n}/${total}`}
          </span>
        </div>
        <div className="sx-stagebar">
          {stageEntries.map(
            (s) =>
              s.count > 0 && (
                <div
                  key={s.key}
                  className="sx-stagebar-seg"
                  style={{ flexGrow: s.count, background: STAGE_HEX[s.key] }}
                  title={`${s.cn} ${s.count} 个`}
                />
              ),
          )}
        </div>
        <div className="sx-stagebar-legend">
          {stageEntries.map(
            (s) =>
              s.count > 0 && (
                <span key={s.key} style={{ color: STAGE_HEX[s.key] }}>
                  {s.cn} {s.count}
                </span>
              ),
          )}
        </div>
      </div>
      <div className="sx-stat">
        <div className="sx-stat-label">当日上涨</div>
        <div className="sx-stat-val">
          <span className="up">{stats.up}</span>
          <span className="sx-stat-dim">/{stats.hasPct}</span>
          <span className="sx-stat-sub">
            {stats.hasPct ? `${((stats.up / stats.hasPct) * 100).toFixed(0)}%` : "-"}
          </span>
        </div>
      </div>
      <div className="sx-stat">
        <div className="sx-stat-label">RS&gt;50 占比</div>
        <div className="sx-stat-val">
          <span>{stats.rsStrong}</span>
          <span className="sx-stat-dim">/{stats.hasRs}</span>
          <span className="sx-stat-sub">
            {stats.hasRs ? `${((stats.rsStrong / stats.hasRs) * 100).toFixed(0)}%` : "-"}
          </span>
        </div>
      </div>
      <div className="sx-stat">
        <div className="sx-stat-label">中位 b50</div>
        <div className="sx-stat-val">
          {stats.medB50 == null ? "-" : stats.medB50.toFixed(0)}
          <span className="sx-stat-sub">%在 MA50 上</span>
        </div>
      </div>
      <div className="sx-stat">
        <div className="sx-stat-label">中位 RS20Δ</div>
        <div className="sx-stat-val">
          <span className={pctClass(stats.medRsD20)}>{fmt(stats.medRsD20, 1)}</span>
          <span className="sx-stat-sub">轮动动能</span>
        </div>
      </div>
    </div>
  );
}

// ── 说明卡片（替代原「本页怎么看」大面板，按需展开）────────────────────────
function HelpCard({ note, onClose }: { note?: string; onClose: () => void }) {
  return (
    <div className="sx-help-overlay" onClick={onClose}>
      <div className="sx-help-card" onClick={(e) => e.stopPropagation()}>
        <div className="sx-help-head">
          <b>读法速览</b>
          <button className="sx-mini-btn" onClick={onClose}>
            收起
          </button>
        </div>
        <table className="sx-help-table">
          <tbody>
            <tr>
              <td>阶段</td>
              <td>上升=机会 / 筑底=中性 / 派发=谨慎 / 下降=危险。绿色系= LEI 阶段色，与 A 股红涨绿跌无关。</td>
            </tr>
            <tr>
              <td>RS位 / RS20Δ</td>
              <td>相对全 A 等权的强弱百分位（50 为分界）；RS20Δ 为其 20 日变化，正=动能改善。</td>
            </tr>
            <tr>
              <td>b50 / nh60</td>
              <td>成分股站上 MA50 比例 / 60 日新高占比：板块内部宽度，验证趋势共识。</td>
            </tr>
            <tr>
              <td>20日主力</td>
              <td>超大+大单净流入（单据规模代理），只做阶段交叉验证，覆盖约 14% 板块。</td>
            </tr>
            <tr>
              <td>RRG</td>
              <td>点位置=强弱，尾迹方向=趋势；右上领先、左上改善、右下走弱、左下滞后。</td>
            </tr>
            <tr>
              <td>操作</td>
              <td>点行开趋势抽屉（历史+宽度+资金+三条件）；★ 加自选；点表头排序。</td>
            </tr>
          </tbody>
        </table>
        {note && <div className="sx-help-note">{note}</div>}
      </div>
    </div>
  );
}

// ── 表头排序 ────────────────────────────────────────────────────────────────
function SortableTh({
  label,
  sortKey,
  cur,
  asc,
  onToggle,
  tip,
}: {
  label: string;
  sortKey?: SortKey;
  cur: SortKey;
  asc: boolean;
  onToggle: (k: SortKey) => void;
  tip?: string;
}) {
  if (!sortKey) return <th title={tip}>{label}</th>;
  const on = cur === sortKey;
  return (
    <th
      className={`num sortable${on ? " sorted" : ""}`}
      title={tip}
      onClick={() => onToggle(sortKey)}
    >
      {label}
      <span className="sort-ind">{on ? (asc ? "▲" : "▼") : "·"}</span>
    </th>
  );
}

/** 0–100 指标的内联横条：数字打底，条形给视觉扫描锚点，50% 处可带刻度。 */
function BarCell({
  v,
  digits = 0,
  color,
  tick50,
}: {
  v: number | null;
  digits?: number;
  color: string;
  tick50?: boolean;
}) {
  if (v == null) return <span className="muted">-</span>;
  return (
    <span className="sx-bar">
      <span className="sx-bar-num">{v.toFixed(digits)}</span>
      <span className="sx-bar-track">
        {tick50 && <i className="sx-bar-tick" />}
        <i className="sx-bar-fill" style={{ width: `${Math.min(100, Math.max(0, v))}%`, background: color }} />
      </span>
    </span>
  );
}

function leiDotColor(c: string | null): string {
  switch (c) {
    case "green":
      return "#0b9b64";
    case "gray":
      return "#8c96a8";
    case "black":
      return "#1f2937";
    default:
      return "transparent";
  }
}

// ── 动能榜：RS20Δ 改善最快 / 走弱最快（当前级别口径）───────────────────────
function MoversCard({ rows, onPick }: { rows: SectorTrendRow[]; onPick: (code: string) => void }) {
  const { gainers, losers } = useMemo(() => {
    const withD = rows.filter((b) => b.rs_pctile_delta_20 != null);
    const sorted = [...withD].sort(
      (a, b) => (b.rs_pctile_delta_20 ?? 0) - (a.rs_pctile_delta_20 ?? 0),
    );
    return { gainers: sorted.slice(0, 5), losers: sorted.slice(-5).reverse() };
  }, [rows]);
  return (
    <section className="sx-rail-card">
      <div className="sx-rail-head">
        <span className="sx-rail-title">动能榜</span>
        <span className="sx-rail-sub">RS20Δ 改善 / 走弱 Top5</span>
      </div>
      <div className="sx-movers">
        <div className="sx-movers-col">
          {gainers.map((b) => (
            <button key={b.code} className="sx-mover" onClick={() => onPick(b.code)}>
              <span className="sx-mover-name">{b.name}</span>
              <span className="num up">+{fmt(b.rs_pctile_delta_20, 1)}</span>
              <span className="sx-mover-rs">RS {fmt(b.rs_pctile, 0)}</span>
            </button>
          ))}
        </div>
        <div className="sx-movers-col">
          {losers.map((b) => (
            <button key={b.code} className="sx-mover" onClick={() => onPick(b.code)}>
              <span className="sx-mover-name">{b.name}</span>
              <span className={`num ${pctClass(b.rs_pctile_delta_20)}`}>
                {fmt(b.rs_pctile_delta_20, 1)}
              </span>
              <span className="sx-mover-rs">RS {fmt(b.rs_pctile, 0)}</span>
            </button>
          ))}
        </div>
      </div>
    </section>
  );
}

// ── 今日观察（道路层）：紧凑清单替代大卡片 ─────────────────────────────────
function WatchCard({ onPick }: { onPick: (code: string) => void }) {
  const { data } = useQuery({
    queryKey: ["sectorsWatchlist"],
    queryFn: () => sectorsApi.watchlist(5),
    staleTime: 5 * 60_000,
  });
  if (!data || data.groups.length === 0) return null;
  return (
    <section className="sx-rail-card">
      <div className="sx-rail-head">
        <span className="sx-rail-title">今日观察</span>
        <span className="sx-rail-sub">道路层 · {data.trading_day}</span>
      </div>
      <div className="sx-watch">
        {data.groups.map((g) => (
          <div key={g.key} className="sx-watch-group">
            <div className="sx-watch-group-head" title={g.desc}>
              {g.title}
              <span className="sx-watch-count">{g.items.length}</span>
            </div>
            {g.items.map((it) => (
              <WatchItemRow key={it.code} item={it} onPick={onPick} />
            ))}
          </div>
        ))}
      </div>
    </section>
  );
}

function WatchItemRow({ item, onPick }: { item: SectorWatchItem; onPick: (code: string) => void }) {
  return (
    <button className="sx-watch-item" onClick={() => onPick(item.code)} title={item.next_watch ?? ""}>
      <span className="sx-watch-item-head">
        <span className="sx-watch-item-name">
          {item.name ?? item.code}
          {item.flow_vs_stage === "conflict" && (
            <span className="sx-flow-tag warn" title={item.flow_vs_stage_cn ?? ""}>
              资金背离
            </span>
          )}
        </span>
        <span className="sx-watch-item-meta">
          RS {fmt(item.rs_pctile, 0)}
          {item.rs_pctile_delta_20 != null && (
            <span className={pctClass(item.rs_pctile_delta_20)}>
              {" "}
              {item.rs_pctile_delta_20 > 0 ? "+" : ""}
              {fmt(item.rs_pctile_delta_20, 1)}
            </span>
          )}
        </span>
      </span>
      {item.next_watch && <span className={`sx-watch-next ${item.next_watch_kind ?? ""}`}>{item.next_watch}</span>}
    </button>
  );
}

// ── RRG 轮动象限（echarts scatter，紧凑版）────────────────────────────────
function RrgPanel({
  rows,
  showTails,
  onPick,
}: {
  rows: SectorTrendRow[];
  showTails: boolean;
  onPick: (code: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const instRef = useRef<echarts.ECharts | null>(null);
  const [tails, setTails] = useState<Record<string, SectorHistoryPoint[]>>({});

  useEffect(() => {
    if (!showTails) {
      setTails({});
      return;
    }
    let cancelled = false;
    Promise.all(
      rows.slice(0, 80).map((b) =>
        sectorsApi
          .history(b.code, 60)
          .then((r) => [b.code, r.points] as const)
          .catch(() => [b.code, [] as SectorHistoryPoint[]] as const),
      ),
    ).then((res) => {
      if (!cancelled) setTails(Object.fromEntries(res));
    });
    return () => {
      cancelled = true;
    };
  }, [rows, showTails]);

  useEffect(() => {
    if (!ref.current) return;
    const inst = echarts.init(ref.current);
    instRef.current = inst;
    inst.on("click", (p: any) => {
      const code = p?.data?.[2];
      if (code) onPick(code);
    });
    const onResize = () => inst.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      inst.dispose();
      instRef.current = null;
    };
  }, [onPick]);

  useEffect(() => {
    const inst = instRef.current;
    if (!inst) return;
    const scatterData = rows.map((b) => [
      b.rs_pctile ?? 0,
      b.rs_pctile_delta_20 ?? 0,
      b.code,
      b.name,
      b.stage ?? "",
    ]);
    const yValues = rows.map((b) => b.rs_pctile_delta_20 ?? 0);
    const yMax = Math.ceil(Math.max(Math.max(...yValues, 5), Math.abs(Math.min(...yValues, -5))) * 1.15);
    const yMin = -yMax;
    const tailSeries = showTails
      ? rows
          .filter((b) => tails[b.code]?.length)
          .map((b) => ({
            type: "line" as const,
            data: tails[b.code]
              .slice(-8)
              .map((p) => [p.rs_pctile ?? 0, p.rs_pctile_delta_20 ?? 0]),
            lineStyle: { color: STAGE_HEX[b.stage ?? ""], width: 1, opacity: 0.35 },
            symbol: "none",
            silent: true,
            z: 1,
          }))
      : [];
    inst.setOption({
      grid: { left: 40, right: 10, top: 10, bottom: 26 },
      xAxis: {
        type: "value",
        min: 0,
        max: 100,
        axisLabel: { fontSize: 10, color: "#7b8494" },
        splitLine: { lineStyle: { color: "#eceff4" } },
      },
      yAxis: {
        type: "value",
        min: yMin,
        max: yMax,
        axisLabel: { fontSize: 10, color: "#7b8494" },
        splitLine: { lineStyle: { color: "#eceff4" } },
      },
      tooltip: {
        trigger: "item",
        formatter: (p: any) => {
          if (p.seriesType !== "scatter") return "";
          const d = p.data;
          return `<b>${d[3]}</b>（${d[2]}）<br/>RS位 ${fmt(d[0], 0)} · RS20Δ ${fmt(d[1], 1)}<br/>阶段 ${STAGE_CN[d[4]] ?? "-"}`;
        },
      },
      series: [
        ...tailSeries,
        {
          type: "scatter",
          symbolSize: 9,
          data: scatterData,
          itemStyle: { color: (p: any) => STAGE_HEX[p.data[4]] },
          z: 2,
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: "#b6c0cf", type: "dashed" },
            label: { show: false },
            data: [{ xAxis: 50 }, { yAxis: 0 }],
          },
        },
      ],
    });
  }, [rows, tails, showTails]);

  return <div ref={ref} style={{ width: "100%", height: 264 }} />;
}

// ── 趋势抽屉（保留：等权指数 + b50 宽度 + 三条件 + 资金流交叉验证）────────
function SectorTrendDrawer({
  row,
  onClose,
  onOpenMembers,
}: {
  row: SectorTrendRow;
  onClose: () => void;
  onOpenMembers: (code: string) => void;
}) {
  const navigate = useNavigate();
  const relatedEtfs = useMemo(() => etfsForSector(row.name), [row.name]);
  const { data: hist } = useQuery({
    queryKey: ["sectorHistory", row.code],
    queryFn: () => sectorsApi.history(row.code, 250),
    staleTime: 5 * 60_000,
  });

  const dates = (hist?.points ?? []).map((p) => p.date);
  const series: OverlaySeries[] = [
    {
      name: "板块等权指数",
      values: (hist?.points ?? []).map((p) => p.close),
      color: "#2563eb",
      axis: "left",
    },
    {
      name: "b50 宽度",
      values: (hist?.points ?? []).map((p) => p.b50),
      color: "#e0913a",
      axis: "breadth",
      dashed: true,
    },
  ];

  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-panel trend-drawer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <h2>
            {row.name}
            <span className="trend-subtitle">
              L{row.level} · {STAGE_CN[row.stage ?? ""] ?? "样本不足"}
            </span>
          </h2>
          <button className="btn" onClick={onClose}>
            关闭
          </button>
        </div>
        <div className="drawer-body trend-drawer-body">
          {relatedEtfs.length > 0 && (
            <div className="sector-etf-row">
              <span className="sector-etf-label">相关 ETF →</span>
              {relatedEtfs.map((etf) => (
                <button
                  key={etf.symbol}
                  type="button"
                  className="sector-etf-btn"
                  onClick={() => navigate(`/?symbol=${encodeURIComponent(etf.symbol)}`)}
                  title={`打开 ${etf.name}（${etf.symbol}）工作台`}
                >
                  {etf.name} <span className="symbol">{etf.symbol}</span>
                </button>
              ))}
              <span className="muted sector-etf-note">
                手工映射 · 板块指数与 ETF 跟踪指数口径不同（research_proxy）
              </span>
            </div>
          )}
          {/* startPercent=100：抽屉是回看全程用的，默认展开全部 250 日（滑块可再放大局部）。
              组件默认 15% 只留尾窗，250 日里只能看到最后 ~37 天。 */}
          <OverlayChart dates={dates} series={series} height={320} startPercent={100} />

          {row.next_watch && (
            <div className={`next-watch-banner ${row.next_watch_kind ?? ""}`}>
              <span className="nw-label">下一观察点</span>
              <span>{row.next_watch}</span>
            </div>
          )}
          {row.checkpoints && row.checkpoints.length > 0 && (
            <div className="checkpoint-list">
              <h5>道路确立三条件（升级为上升需全部满足）</h5>
              {row.checkpoints.map((c) => (
                <div key={c.key} className="checkpoint">
                  <span className={c.met ? "cp-met" : "cp-unmet"}>{c.met ? "✓" : "✗"}</span>
                  <span className="cp-label">{c.label}</span>
                  {c.detail && <span className="cp-detail">{c.detail}</span>}
                </div>
              ))}
            </div>
          )}

          <div className="trend-facts">
            <Fact label="阶段判定依据" value={(row.stage_basis ?? []).join("；") || "-"} />
            <Fact
              label="LEI 三色"
              value={
                <>
                  <ColorBadge color={row.signal_color} colorCn={row.signal_color_cn} />（
                  {row.long_trend_cn ?? "-"}）
                </>
              }
            />
            <Fact label="均线排列" value={row.alignment_cn ?? "-"} />
            <Fact
              label="MACD"
              value={`${row.macd_label_cn ?? "-"}${row.macd_detail_cn ? "｜" + row.macd_detail_cn : ""}`}
            />
            <Fact label="RS 百分位" value={fmt(row.rs_pctile, 1)} />
            <Fact label="RS 20日变化" value={fmt(row.rs_pctile_delta_20, 1)} />
            <Fact label="b50 / nh60" value={`${fmt(row.b50, 1)} / ${fmt(row.nh60, 1)}`} />
            <Fact label="宽度背离" value={row.breadth_divergence ? "是" : "否"} />
            <Fact label="成分命中" value={`${row.hit_count}/${row.member_count}`} />
            <Fact label="判定口径" value="research_proxy（研究代理，非 LEI 原始规则）" />
          </div>

          <h5>
            资金流（5/20/60 日累计，亿元 · 主力=超大+大单 / 散户=中+小单）
            {row.flow_vs_stage_cn && (
              <span className={`flow-badge ${row.flow_vs_stage === "confirm" ? "fb-ok" : "fb-warn"}`}>
                {row.flow_vs_stage_cn}
              </span>
            )}
          </h5>
          {row.flow_20d_main_yi != null || row.flow_20d_retail_yi != null ? (
            <>
              {row.flow_note_cn && <div className="flow-struct">{row.flow_note_cn}</div>}
              <div className="flow-grid">
                <FlowBar label="5日·主力" v={row.flow_5d_main_yi} highlight />
                <FlowBar label="5日·散户" v={row.flow_5d_retail_yi} />
                <FlowBar label="20日·主力" v={row.flow_20d_main_yi} highlight />
                <FlowBar label="20日·散户" v={row.flow_20d_retail_yi} />
                <FlowBar label="60日·主力" v={row.flow_60d_main_yi} highlight />
                <FlowBar label="60日·散户" v={row.flow_60d_retail_yi} />
              </div>
              <div className="muted" style={{ fontSize: 11, marginTop: 4 }}>
                单据规模代理（非真实机构/散户身份），仅作阶段交叉验证，不参与判定、不构成买卖建议。
              </div>
            </>
          ) : (
            <div className="muted">资金流数据不可用（DATA_UNAVAILABLE，不冒充）</div>
          )}

          <div className="drawer-actions">
            <button className="btn" onClick={() => onOpenMembers(row.code)}>
              查看成分股
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

function Fact({ label, value }: { label: string; value: ReactNode }) {
  return (
    <div className="fact">
      <span className="fact-label">{label}</span>
      <span className="fact-value">{value}</span>
    </div>
  );
}

function FlowBar({ label, v, highlight }: { label: string; v: number | null; highlight?: boolean }) {
  const val = v ?? 0;
  const tone = val > 0 ? "up" : val < 0 ? "down" : "flat";
  return (
    <div className={`flow-bar${highlight ? " hl" : ""}`}>
      <span className="flow-label">{label}</span>
      <span className={`flow-val ${tone}`}>{fmtYi(val)}</span>
    </div>
  );
}

// ── 成分股抽屉 ──────────────────────────────────────────────────────────────
function MembersDrawer({ code, onClose }: { code: string; onClose: () => void }) {
  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["sectorMembers", code],
    queryFn: () => sectorsApi.members(code, 50),
    staleTime: 5 * 60_000,
  });
  const members: SectorMembersResponse["members"] = data?.members ?? [];
  const navigate = useNavigate();
  const openSymbol = (symbol: string) => {
    onClose();
    navigate(`/?symbol=${encodeURIComponent(symbol)}`);
  };
  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div className="drawer-panel" onClick={(e) => e.stopPropagation()}>
        <div className="drawer-head">
          <h2>
            {data?.name ?? code} <span className="trend-subtitle">成分股（{members.length}）</span>
          </h2>
          <button className="btn" onClick={onClose}>
            关闭
          </button>
        </div>
        <div className="drawer-body">
          {isLoading ? (
            <div className="muted">加载中…</div>
          ) : error ? (
            <div className="fund-errors">
              成分股加载失败：{error instanceof Error ? error.message : String(error)}
              <div>
                <button className="btn small" style={{ marginTop: 8 }} onClick={() => refetch()}>
                  重试
                </button>
              </div>
            </div>
          ) : members.length === 0 ? (
            <div className="muted">该板块暂无成分股数据。</div>
          ) : (
            <table className="event-table fund-table">
              <thead>
                <tr>
                  <th>代码</th>
                  <th>名称</th>
                  <th className="num">当日涨幅</th>
                  <th className="num">总市值</th>
                  <th className="num">K线缓存</th>
                </tr>
              </thead>
              <tbody>
                {members.map((m) => (
                  <tr
                    key={m.symbol}
                    style={{ cursor: "pointer" }}
                    title="点击在看盘工作台打开该标的"
                    onClick={() => openSymbol(m.symbol)}
                  >
                    <td>{m.symbol}</td>
                    <td>{m.name ?? "-"}</td>
                    <td className={`num ${pctClass(m.pct_change)}`}>{fmt(m.pct_change, 2, "%")}</td>
                    <td className="num">{fmtYi(m.market_value_yi)}</td>
                    <td className="num">{m.in_kline_cache ? "✓" : "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </div>
    </div>
  );
}
