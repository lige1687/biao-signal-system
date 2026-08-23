import { useEffect, useMemo, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import * as echarts from "echarts";
import { sectorsApi } from "../api/client";
import { fmt, fmtYi, pctClass } from "../utils/format";
import ColorBadge from "../components/ColorBadge";
import CollapsiblePanel from "../components/CollapsiblePanel";
import OverlayChart, { type OverlaySeries } from "../components/trend/OverlayChart";
import type {
  SectorTrendRow,
  SectorHistoryPoint,
  SectorMembersResponse,
  SectorWatchItem,
} from "../types";

// 阶段 → 红绿语义 tone（与 macro-chip 一致）：②上升=机会 / ①筑底=中性 / ③派发=谨慎 / ④下降=危险
const STAGE_TONE: Record<string, string> = {
  markup: "opportunity",
  accumulation: "neutral",
  distribution: "caution",
  decline: "danger",
};
const STAGE_CN: Record<string, string> = {
  markup: "上升",
  accumulation: "筑底",
  distribution: "派发",
  decline: "下降",
};
// 排序序位：上升 > 筑底 > 派发 > 下降 > 样本不足
const STAGE_ORDER: Record<string, number> = {
  markup: 4,
  accumulation: 3,
  distribution: 2,
  decline: 1,
  "": 0,
};

const STARS_KEY = "lei.sector.stars";
const MACD_BLIND_SPOT =
  "MACD 盲区：柱/线背离需结合量价与均线斜率；本列为研究代理补充，非买卖建议。";

type SortKey =
  | "stage"
  | "rs_pctile"
  | "rs_pctile_delta_20"
  | "b50"
  | "rs_chg_60"
  | "main_net_inflow_yi"
  | "flow_20d_main_yi";

const SORTS: { key: SortKey; label: string }[] = [
  { key: "stage", label: "阶段" },
  { key: "rs_pctile", label: "RS百分位" },
  { key: "rs_pctile_delta_20", label: "RS变化" },
  { key: "b50", label: "b50" },
  { key: "rs_chg_60", label: "RS60%" },
  { key: "main_net_inflow_yi", label: "主力净流入" },
  { key: "flow_20d_main_yi", label: "20日主力净" },
];

function loadStars(): string[] {
  try {
    return JSON.parse(localStorage.getItem(STARS_KEY) ?? "[]");
  } catch {
    return [];
  }
}

export default function SectorsPage() {
  const queryClient = useQueryClient();
  const [sortKey, setSortKey] = useState<SortKey>("rs_pctile");
  const [sortAsc, setSortAsc] = useState(false);
  const [keyword, setKeyword] = useState("");
  const [dedupe, setDedupe] = useState(true); // 同产业链父子去重（默认只出最高层）
  const [onlyStars, setOnlyStars] = useState(false);
  const [stars, setStars] = useState<string[]>(loadStars);
  const [selected, setSelected] = useState<SectorTrendRow | null>(null);
  const [membersCode, setMembersCode] = useState<string | null>(null);
  const [showTails, setShowTails] = useState(true);
  const [rrgLevel, setRrgLevel] = useState<"l1" | "l2">("l1");

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

  const visibleRows = useMemo(() => {
    let list = rows;
    if (dedupe) list = list.filter((b) => b.parent === null);
    if (onlyStars) list = list.filter((b) => stars.includes(b.code));
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
  }, [rows, dedupe, onlyStars, keyword, sortKey, sortAsc, stars]);

  // 自选切换
  function toggleStar(code: string) {
    setStars((prev) => {
      const next = prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code];
      localStorage.setItem(STARS_KEY, JSON.stringify(next));
      return next;
    });
  }

  return (
    <div className="page">
      <div className="header">
        <h1>行业板块趋势</h1>
        {data && (
          <span className="generated">
            更新于 {new Date(data.as_of).toLocaleString("zh-CN", { hour12: false })}
            （代表交易日 {data.trading_day}）
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

      {data && <div className="legend">{data.research_proxy_note}</div>}
      {error && (
        <div className="fund-errors">
          加载失败：{(error as Error).message}
          <div className="fund-hint">请先在本机跑 scripts/precompute_sector_trend.py 生成快照。</div>
        </div>
      )}

      <CollapsiblePanel title="📖 本页怎么看" defaultCollapsed={false} storageKey="sectors.help">
        <div className="sectors-help">
          <div className="help-section">
            <h4>1. 今日板块观察（道路层）</h4>
            <p>
              按「均线方向是道路」分组回答三问：看哪个板块（分组即答案）、盯什么
              （每条带「下一观察点」，如价格上穿 SMA60 还差百分之几）、依据
              （点开板块可看阶段判定依据与三条件清单）。
            </p>
          </div>
          <div className="help-section">
            <h4>2. 板块轮动 RRG 图</h4>
            <p>
              横轴 = 相对强度（RS）百分位，0 最弱、100 最强；纵轴 = RS 近 20 日变化，+ 表示相对动能在改善。
              右上为强势区、左下为弱势区；板块点从哪来、往哪去，比它在哪里更重要。
            </p>
            <div className="rrg-quadrants">
              <span className="rrg-q lagging">左上·改善</span>
              <span className="rrg-q leading">右上·领先</span>
              <span className="rrg-q weakening">左下·滞后</span>
              <span className="rrg-q weakening-strong">右下·走弱</span>
            </div>
            <ul>
              <li>
                <strong>颜色</strong>：绿=上升 / 蓝=筑底 / 黄=派发 / 红=下降 / 灰=样本不足（此为 LEI 阶段色，与 A 股红涨绿跌无关）
              </li>
              <li>
                <strong>尾迹</strong>：显示该板块最近 8 个交易日的移动轨迹，帮助判断方向是否持续
              </li>
              <li>
                <strong>分层</strong>：L1 是一级行业，L2 是二级细分；默认「仅 L1」减少噪声，可切换「L1+L2」看全貌
              </li>
            </ul>
          </div>
          <div className="help-section">
            <h4>3. 趋势表关键列</h4>
            <ul>
              <li>
                <strong>阶段</strong>：LEI 市场阶段 — 上升=机会 / 筑底=中性 / 派发=谨慎 / 下降=危险
              </li>
              <li>
                <strong>LEI 色</strong>：长趋势颜色 — 绿=向上 / 灰=震荡 / 黑=向下 / 虚线=未知
              </li>
              <li>
                <strong>RS 百分位</strong>：板块相对全 A 等权基准的强弱排名，数值越大相对越强势
              </li>
              <li>
                <strong>RS20 变化</strong>：RS 百分位近 20 日的变化，+ 代表相对强度在改善
              </li>
              <li>
                <strong>RS60%</strong>：板块近 60 个交易日涨跌幅
              </li>
              <li>
                <strong>b50</strong>：成分股中站上 MA50 的比例，反映板块内部宽度与共识
              </li>
              <li>
                <strong>nh60</strong>：60 日新高家数占比，衡量板块内创新高个股的广度
              </li>
              <li>
                <strong>均线状态 / MACD</strong>：均线排列与 MACD 形态，作为阶段判定的辅助验证
              </li>
            </ul>
          </div>
          <div className="help-section">
            <h4>4. 常用操作</h4>
            <ul>
              <li>点击表格任意行 → 打开趋势抽屉，查看该板块历史走势、宽度与主力资金流</li>
              <li>点击行尾 ★ → 加入自选；再用「自选」过滤只看关注板块</li>
              <li>「父子去重」默认开启：只保留产业链最高层，避免父板块被子板块重复刷屏</li>
              <li>表格支持按阶段、RS 百分位、b50 等排序，快速定位当前强势或弱势方向</li>
            </ul>
          </div>
        </div>
      </CollapsiblePanel>

      {/* ── 今日板块观察（道路层，策略溯源 trading-spec §2.2）── */}
      <WatchlistPanel
        onPick={(code) => {
          const r = rows.find((b) => b.code === code);
          if (r) setSelected(r);
        }}
      />

      {/* ── RRG 轮动象限 ── */}
      <h2 className="fund-section-title">
        板块轮动 RRG <span className="fund-count">X=RS百分位 · Y=RS 20日变化</span>
      </h2>
      <RrgPanel
        rows={rows}
        level={rrgLevel}
        showTails={showTails}
        onPick={(code) => {
          const r = rows.find((b) => b.code === code);
          if (r) setSelected(r);
        }}
      />
      <div className="fund-toolbar">
        <button
          className={`btn ${rrgLevel === "l1" ? "primary" : ""}`}
          onClick={() => setRrgLevel("l1")}
        >
          仅 L1
        </button>
        <button
          className={`btn ${rrgLevel === "l2" ? "primary" : ""}`}
          onClick={() => setRrgLevel("l2")}
        >
          L1+L2
        </button>
        <button
          className={`btn ${showTails ? "primary" : ""}`}
          onClick={() => setShowTails((v) => !v)}
        >
          尾迹 {showTails ? "开" : "关"}
        </button>
      </div>

      {/* ── 主表 ── */}
      <h2 className="fund-section-title">
        板块趋势表 <span className="fund-count">{visibleRows.length} 行</span>
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
        <button
          className={`btn ${dedupe ? "primary" : ""}`}
          onClick={() => setDedupe((v) => !v)}
          title="只保留产业链最高层（去掉被父板块完全包含的显示行）"
        >
          父子去重
        </button>
        <button
          className={`btn ${onlyStars ? "primary" : ""}`}
          onClick={() => setOnlyStars((v) => !v)}
        >
          ★ 自选
        </button>
      </div>

      <div className="fund-table-wrap">
        <table className="event-table fund-table">
          <thead>
            <tr>
              <th title="板块名称与级别（L1=一级行业 / L2=二级细分 / L3=三级）">板块(级别)</th>
              <th className="num" title="LEI 市场阶段：上升=机会 / 筑底=中性 / 派发=谨慎 / 下降=危险">阶段</th>
              <th className="num" title="长趋势颜色：绿=向上 / 灰=震荡 / 黑=向下 / 虚线=未知">LEI色</th>
              <th className="num" title="相对全 A 等权基准的强弱百分位，0 最弱、100 最强">RS百分位</th>
              <th className="num" title="RS 百分位近 20 日变化，+ 表示相对强度在改善">RS20变化</th>
              <th className="num" title="板块近 60 个交易日涨跌幅">RS60%</th>
              <th className="num" title="成分股中站上 MA50 的比例，反映板块内部宽度">b50</th>
              <th className="num" title="60 日新高家数占比，衡量板块内创新高广度">nh60</th>
              <th className="num" title="均线排列状态（如多头排列 / 空头排列 / 均线纠结）">均线状态</th>
              <th className="num" title="MACD 形态与背离提示，仅作辅助参考">MACD</th>
              <th className="num" title="板块当日涨跌幅">当日涨幅</th>
              <th className="num" title="近 20 日主力（超大+大单）累计净流入，单据规模代理（research_proxy）">20日主力净</th>
              <th className="num" title="命中本板块规则的成分股数 / 总成分股数">成分数</th>
              <th className="num" title="市盈率 TTM，负值表示亏损">PE</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {visibleRows.map((b) => (
              <tr
                key={b.code}
                className={b.level === 3 ? "dim" : ""}
                onClick={() => setSelected(b)}
              >
                <td>
                  {b.name} <span className="symbol">L{b.level}·{b.code}</span>
                </td>
                <td className="num">
                  {b.stage ? (
                    <span className={`macro-chip ${STAGE_TONE[b.stage]}`}>
                      {STAGE_CN[b.stage]}
                    </span>
                  ) : (
                    <span className="muted">样本不足</span>
                  )}
                </td>
                <td className="num">
                  <ColorBadge color={b.signal_color} colorCn={b.signal_color_cn} />
                </td>
                <td className="num">{fmt(b.rs_pctile, 1)}</td>
                <td className={`num ${pctClass(b.rs_pctile_delta_20)}`}>
                  {fmt(b.rs_pctile_delta_20, 1)}
                </td>
                <td className={`num ${pctClass(b.rs_chg_60)}`}>{fmt(b.rs_chg_60, 1, "%")}</td>
                <td className="num">{fmt(b.b50, 1)}</td>
                <td className="num">{fmt(b.nh60, 1)}</td>
                <td className="num">{b.alignment_cn ?? "-"}</td>
                <td
                  className="num"
                  title={
                    b.macd_label_cn
                      ? `${b.macd_label_cn}｜${b.macd_detail_cn ?? ""}｜${MACD_BLIND_SPOT}`
                      : MACD_BLIND_SPOT
                  }
                >
                  {b.macd_status ? (
                    <span className={`macro-chip ${macdTone(b.macd_status)}`}>
                      {b.macd_status}
                    </span>
                  ) : (
                    "-"
                  )}
                </td>
                <td className={`num ${pctClass(b.pct_change)}`}>{fmt(b.pct_change, 2, "%")}</td>
                <td className={`num ${flowClass(b.flow_20d_main_yi)}`}>
                  {b.flow_20d_main_yi == null ? (
                    "-"
                  ) : (
                    <span title={b.flow_vs_stage_cn ? `阶段交叉验证：${b.flow_vs_stage_cn}` : undefined}>
                      {b.flow_20d_main_yi.toFixed(1)}
                      {b.flow_vs_stage_cn ? `（${b.flow_vs_stage_cn}）` : ""}
                    </span>
                  )}
                </td>
                <td className="num">
                  {b.hit_count}/{b.member_count}
                </td>
                <td className="num">
                  {b.pe_ttm == null ? "-" : b.pe_ttm < 0 ? "亏" : b.pe_ttm.toFixed(1)}
                </td>
                <td onClick={(e) => e.stopPropagation()}>
                  <button
                    className={`star-btn${stars.includes(b.code) ? " on" : ""}`}
                    onClick={() => toggleStar(b.code)}
                    title="加入板块自选"
                  >
                    ★
                  </button>
                </td>
              </tr>
            ))}
            {visibleRows.length === 0 && (
              <tr>
                <td colSpan={15}>无匹配板块（请先运行预计算脚本）</td>
              </tr>
            )}
          </tbody>
        </table>
      </div>

      {selected && (
        <SectorTrendDrawer
          row={selected}
          onClose={() => setSelected(null)}
          onOpenMembers={(code) => setMembersCode(code)}
        />
      )}
      {membersCode && (
        <MembersDrawer code={membersCode} onClose={() => setMembersCode(null)} />
      )}
    </div>
  );
}

function flowClass(v: number | null): string {
  if (v == null) return "";
  return v > 0 ? "up" : v < 0 ? "down" : "";
}

function macdTone(status: string | null): string {
  if (!status) return "";
  if (status.includes("多头")) return "opportunity";
  if (status.includes("空头")) return "danger";
  return "neutral";
}

// ── 今日板块观察（道路层分组）：回答「看哪个板块 / 盯什么 / 依据」────────────
function WatchlistPanel({ onPick }: { onPick: (code: string) => void }) {
  const { data } = useQuery({
    queryKey: ["sectorsWatchlist"],
    queryFn: () => sectorsApi.watchlist(5),
    staleTime: 5 * 60_000,
  });
  if (!data || data.groups.length === 0) return null;
  return (
    <>
      <h2 className="fund-section-title">
        今日板块观察{" "}
        <span className="fund-count">
          道路层 · 代表交易日 {data.trading_day}（research_proxy）
        </span>
      </h2>
      <div className="watch-grid">
        {data.groups.map((g) => (
          <div key={g.key} className="watch-card">
            <div className="watch-card-head">
              <span className="watch-card-title">{g.title}</span>
              <span className="watch-card-count">{g.items.length}</span>
            </div>
            <div className="watch-card-desc">{g.desc}</div>
            <div className="watch-items">
              {g.items.map((it) => (
                <WatchItemRow key={it.code} item={it} onPick={onPick} />
              ))}
              {g.items.length === 0 && (
                <div className="muted watch-empty">今日无符合板块</div>
              )}
            </div>
          </div>
        ))}
      </div>
    </>
  );
}

function WatchItemRow({
  item,
  onPick,
}: {
  item: SectorWatchItem;
  onPick: (code: string) => void;
}) {
  return (
    <div className="watch-item" onClick={() => onPick(item.code)}>
      <div className="watch-item-head">
        <span className="watch-item-name">
          {item.name ?? item.code}
          {item.flow_vs_stage_cn && (
            <span
              className={`flow-badge ${item.flow_vs_stage === "confirm" ? "fb-ok" : "fb-warn"}`}
              title="资金交叉验证（单据规模代理，research_proxy）"
            >
              {item.flow_vs_stage_cn}
            </span>
          )}
        </span>
        <span className="watch-item-meta">
          RS {fmt(item.rs_pctile, 0)}
          {item.rs_pctile_delta_20 != null && (
            <span className={pctClass(item.rs_pctile_delta_20)}>
              {" "}
              ({item.rs_pctile_delta_20 > 0 ? "+" : ""}
              {fmt(item.rs_pctile_delta_20, 1)})
            </span>
          )}
          {item.b50 != null && ` · b50 ${fmt(item.b50, 0)}`}
        </span>
      </div>
      {item.next_watch && (
        <div className={`watch-next ${item.next_watch_kind ?? ""}`}>
          {item.next_watch}
        </div>
      )}
      {(item.flow_20d_main_yi != null || item.flow_20d_retail_yi != null) && (
        <div className="watch-flow">
          20日主力 {fmtYi(item.flow_20d_main_yi)} · 散户 {fmtYi(item.flow_20d_retail_yi)}
          {item.flow_note_cn ? ` · ${item.flow_note_cn}` : ""}
        </div>
      )}
    </div>
  );
}

// ── RRG 轮动象限（echarts scatter）────────────────────────────────────────
function RrgPanel({
  rows,
  level,
  showTails,
  onPick,
}: {
  rows: SectorTrendRow[];
  level: "l1" | "l2";
  showTails: boolean;
  onPick: (code: string) => void;
}) {
  const ref = useRef<HTMLDivElement>(null);
  const instRef = useRef<echarts.ECharts | null>(null);
  const [tails, setTails] = useState<Record<string, SectorHistoryPoint[]>>({});

  const points = useMemo(
    () => rows.filter((b) => (level === "l1" ? b.level === 1 : b.level <= 2)),
    [rows, level],
  );

  useEffect(() => {
    if (!showTails) {
      setTails({});
      return;
    }
    let cancelled = false;
    Promise.all(
      points.map((b) =>
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
  }, [points, showTails]);

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
    const scatterData = points.map((b) => [
      b.rs_pctile ?? 0,
      b.rs_pctile_delta_20 ?? 0,
      b.code,
      b.name,
      b.stage ?? "",
    ]);
    const yValues = points.map((b) => b.rs_pctile_delta_20 ?? 0);
    const yRawMax = Math.max(...yValues, 5);
    const yRawMin = Math.min(...yValues, -5);
    const yMax = Math.ceil(Math.max(yRawMax, Math.abs(yRawMin)) * 1.15);
    const yMin = -yMax;
    const tailSeries = showTails
      ? points
          .filter((b) => tails[b.code]?.length)
          .map((b) => ({
            type: "line" as const,
            data: tails[b.code]
              .slice(-8)
              .map((p) => [p.rs_pctile ?? 0, p.rs_pctile_delta_20 ?? 0]),
            lineStyle: { color: stageColor(b.stage), width: 1, opacity: 0.4 },
            symbol: "none",
            silent: true,
            z: 1,
          }))
      : [];
    inst.setOption({
      grid: { left: 48, right: 24, top: 24, bottom: 40 },
      xAxis: {
        type: "value",
        min: 0,
        max: 100,
        name: "RS 百分位",
        splitLine: { lineStyle: { color: "#2a2f3a" } },
      },
      yAxis: {
        type: "value",
        min: yMin,
        max: yMax,
        name: "RS 20日变化",
        splitLine: { lineStyle: { color: "#2a2f3a" } },
      },
      tooltip: {
        formatter: (p: any) => {
          const d = p.data;
          return `${d[3]}（${d[2]}）<br/>RS百分位 ${fmt(d[0], 1)} · RS变化 ${fmt(
            d[1],
            1,
          )}<br/>阶段 ${STAGE_CN[d[4]] ?? "-"}`;
        },
      },
      series: [
        ...tailSeries,
        {
          type: "scatter",
          symbolSize: 14,
          data: scatterData,
          itemStyle: {
            color: (p: any) => stageColor(p.data[4]),
          },
          z: 2,
          markArea: {
            silent: true,
            data: [
              [
                {
                  name: "领先",
                  xAxis: 100,
                  yAxis: yMax,
                  itemStyle: { color: "rgba(46, 204, 113, 0.06)" },
                  label: { color: "rgba(46,204,113,0.35)", fontSize: 16, fontWeight: "bold" },
                },
                { xAxis: 50, yAxis: 0 },
              ],
              [
                {
                  name: "改善",
                  xAxis: 50,
                  yAxis: yMax,
                  itemStyle: { color: "rgba(91, 155, 213, 0.06)" },
                  label: { color: "rgba(91,155,213,0.35)", fontSize: 16, fontWeight: "bold" },
                },
                { xAxis: 0, yAxis: 0 },
              ],
              [
                {
                  name: "走弱",
                  xAxis: 100,
                  yAxis: 0,
                  itemStyle: { color: "rgba(224, 169, 58, 0.06)" },
                  label: { color: "rgba(224,169,58,0.35)", fontSize: 16, fontWeight: "bold" },
                },
                { xAxis: 50, yAxis: yMin },
              ],
              [
                {
                  name: "滞后",
                  xAxis: 50,
                  yAxis: 0,
                  itemStyle: { color: "rgba(224, 91, 91, 0.06)" },
                  label: { color: "rgba(224,91,91,0.35)", fontSize: 16, fontWeight: "bold" },
                },
                { xAxis: 0, yAxis: yMin },
              ],
            ],
          },
          markLine: {
            silent: true,
            symbol: "none",
            lineStyle: { color: "#5a6172", type: "dashed" },
            data: [
              {
                xAxis: 50,
                label: { formatter: "强/弱分界", position: "end", distance: 8 },
              },
              {
                yAxis: 0,
                label: { formatter: "改善/走弱分界", position: "end", distance: 8 },
              },
            ],
          },
        },
      ],
    });
  }, [points, tails, showTails]);

  return <div ref={ref} style={{ width: "100%", height: 420 }} />;
}

function stageColor(stage: string | null): string {
  switch (stage) {
    case "markup":
      return "#2ecc71";
    case "accumulation":
      return "#5b9bd5";
    case "distribution":
      return "#e0a93a";
    case "decline":
      return "#e05b5b";
    default:
      return "#888";
  }
}

// ── 趋势抽屉（OverlayChart 三轴：指数 + 全A等权基准 + b50 宽度）─────────────
function SectorTrendDrawer({
  row,
  onClose,
  onOpenMembers,
}: {
  row: SectorTrendRow;
  onClose: () => void;
  onOpenMembers: (code: string) => void;
}) {
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
          <OverlayChart dates={dates} series={series} height={320} />

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
                  <span className={c.met ? "cp-met" : "cp-unmet"}>
                    {c.met ? "✓" : "✗"}
                  </span>
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
              value={`${row.signal_color_cn ?? "-"}（${row.long_trend_cn ?? "-"})`}
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
              <span
                className={`flow-badge ${row.flow_vs_stage === "confirm" ? "fb-ok" : "fb-warn"}`}
              >
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

function Fact({ label, value }: { label: string; value: string }) {
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
  const { data, isLoading } = useQuery({
    queryKey: ["sectorMembers", code],
    queryFn: () => sectorsApi.members(code, 50),
    staleTime: 5 * 60_000,
  });
  const members: SectorMembersResponse["members"] = data?.members ?? [];
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
                  <tr key={m.symbol}>
                    <td>{m.symbol}</td>
                    <td>{m.name ?? "-"}</td>
                    <td className={`num ${pctClass(m.pct_change)}`}>
                      {fmt(m.pct_change, 2, "%")}
                    </td>
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
