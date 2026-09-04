import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { factorsApi, type FactorRow } from "../api/client";
import { fmt, pctClass } from "../utils/format";

/**
 * 因子观测台：常见因子读数 + 历史分位 + 板块 12-1 排名。
 *
 * 红线对齐（与后端 factor_panel.py 一致）：
 * - 全部 research_proxy，不出买卖点、不挡任何 LEI 技术信号；
 * - 评级卡来自后端 FACTOR_META 的实证留痕（2026-08-27 本地数据），
 *   前端只做展示，不得另造评级或阈值；
 * - 高分位提示（高波 / 短线超买）是「风险标注」不是看多/看空信号。
 */

const VERDICT_CN: Record<string, string> = {
  pass: "实证稳健",
  weak: "部分有效",
  inverse: "反向因子",
  fail: "未通过检验",
};

const GROUP_CN: Record<string, string> = {
  cn_etf: "A股ETF",
  cn_index: "A股指数",
  cn_stock: "A股个股",
  us_etf: "美股ETF",
  us_index: "美股指数",
  sector: "板块",
};

type SymSortKey = "code" | "rv20_ann" | "rv_pct" | "ivol_pct" | "mom_121" | "mom_20" | "adx14";

/** RV 分位小色条：低波冷色 → 高波暖色，≥0.8 加警示描边。 */
function PctBar({ v, warnAt = 0.8 }: { v: number | null; warnAt?: number }) {
  if (v == null) return <span className="text-faint">留痕中</span>;
  const pct = Math.round(v * 100);
  const hot = v >= warnAt;
  return (
    <span className="fp-pctcell">
      <span className={`fp-pctbar${hot ? " hot" : ""}`}>
        <span style={{ width: `${pct}%` }} />
      </span>
      <span className={hot ? "fp-hotnum" : ""}>{pct}%</span>
    </span>
  );
}

function Num({ v, digits = 1, suffix = "", signed = false }: {
  v: number | null; digits?: number; suffix?: string; signed?: boolean;
}) {
  if (v == null) return <span className="text-faint">-</span>;
  const text = `${signed && v > 0 ? "+" : ""}${v.toFixed(digits)}${suffix}`;
  return <span className={pctClass(signed ? v : null)}>{text}</span>;
}

function TrendDots({ row }: { row: FactorRow }) {
  if (row.above_ema20 == null || row.above_ema120 == null) {
    return <span className="text-faint">-</span>;
  }
  return (
    <span className="fp-trend" title="收盘 vs EMA20 / EMA120（上下文状态，非因子）">
      <span className={row.above_ema20 ? "up" : "down"}>E20{row.above_ema20 ? "↑" : "↓"}</span>
      <span className={row.above_ema120 ? "up" : "down"}>E120{row.above_ema120 ? "↑" : "↓"}</span>
    </span>
  );
}

/** 风险标注 chips（只标风险，不出买卖建议）。 */
function RiskChips({ row }: { row: FactorRow }) {
  const chips: { text: string; tone: string; title: string }[] = [];
  if (row.rv_pct != null && row.rv_pct >= 0.8) {
    chips.push({
      text: "高波·信号打折提示",
      tone: "warn",
      title: "实证：高波分位期趋势信号可信度打折（8年中6年跑输），仅分组提示不挡信号",
    });
  }
  if (row.mom_20_group_pct != null && row.mom_20_group_pct >= 0.8) {
    chips.push({
      text: "短线超买警示",
      tone: "caution",
      title: "实证：A股短动量为反向因子，组内高分位提示追高风险，与顶底结构判断互为印证",
    });
  }
  if (row.ivol_pct != null && row.ivol_pct >= 0.8) {
    chips.push({
      text: "彩票股警示",
      tone: "caution",
      title:
        "实证（F2/E2）：高特质波动个股 18 年系统性跑输（IC -0.09），裸标的层排雷有效；入口层提示，不作用于已确认信号",
    });
  }
  if (row.notes.some((n) => n.startsWith("数据较旧"))) {
    chips.push({ text: "数据较旧", tone: "dim", title: row.notes.join("；") });
  }
  if (!chips.length) return null;
  return (
    <span className="fp-chips">
      {chips.map((c) => (
        <span key={c.text} className={`stage-chip fp-chip-${c.tone}`} title={c.title}>
          {c.text}
        </span>
      ))}
    </span>
  );
}

export default function FactorPanelPage() {
  const queryClient = useQueryClient();
  const { data, error, isLoading } = useQuery({
    queryKey: ["factorPanel"],
    queryFn: () => factorsApi.panel(),
    staleTime: 5 * 60_000,
  });
  const [sortKey, setSortKey] = useState<SymSortKey>("rv_pct");
  const [sortDesc, setSortDesc] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);

  const symbols = useMemo(() => {
    if (!data) return [];
    const rows = [...data.symbols];
    rows.sort((a, b) => {
      if (sortKey === "code") return sortDesc ? b.code.localeCompare(a.code) : a.code.localeCompare(b.code);
      const va = a[sortKey] ?? -Infinity;
      const vb = b[sortKey] ?? -Infinity;
      return sortDesc ? vb - va : va - vb;
    });
    return rows;
  }, [data, sortKey, sortDesc]);

  if (isLoading) return <div className="page"><div className="legend">加载中…</div></div>;

  const miss = error != null || data == null;

  const head = (key: SymSortKey, label: string, title?: string) => (
    <th
      title={title}
      style={{ cursor: "pointer", userSelect: "none" }}
      onClick={() => {
        if (sortKey === key) setSortDesc((d) => !d);
        else { setSortKey(key); setSortDesc(true); }
      }}
    >
      {label}{sortKey === key ? (sortDesc ? " ▾" : " ▴") : ""}
    </th>
  );

  return (
    <div className="page">
      <div className="header">
        <h1>
          因子观测台{" "}
          <span className="fund-count">
            {data ? `${data.counts.symbols} 标的 · ${data.counts.sectors} 板块 · 数据截止 ${data.data_as_of}` : ""}
          </span>
        </h1>
        <span className="generated">
          快照 {data?.generated_at} · 评级留痕 {data?.study_date}
        </span>
        <span className="spacer" />
        <button
          className="btn primary"
          disabled={refreshing}
          onClick={async () => {
            setRefreshing(true);
            setRefreshError(null);
            try {
              await factorsApi.panel(true);
              await queryClient.invalidateQueries({ queryKey: ["factorPanel"] });
            } catch (e) {
              setRefreshError(e instanceof Error ? e.message : String(e));
            } finally {
              setRefreshing(false);
            }
          }}
          title="重读磁盘快照（真正重算需跑 scripts/precompute_factor_panel.py）"
        >
          {refreshing ? "刷新中…" : "刷新"}
        </button>
      </div>

      {refreshError && (
        <div className="fund-errors">刷新失败：{refreshError}</div>
      )}

      {data && <div className="legend">{data.research_proxy_note}</div>}

      {data?.market?.market_rv_pct != null && (
        <div
          className={`fp-market-strip${data.market.market_rv_pct >= 0.8 ? " hot" : ""}`}
          title={`口径：${data.market.market_basis}（截止 ${data.market.market_as_of}）。LEI 信号对账：市场高波期信号 60 日均值 4.98%→0.73%，胜率 53%→46%；趋势类模块（A/D）受害、2B/破底翻（C）反而受益。`}
        >
          市场 RV 分位（环境层）：
          <strong>{Math.round(data.market.market_rv_pct * 100)}%</strong>
          <span className="fp-market-ann">
            （RV20 年化 {((data.market.market_rv20_ann ?? 0) * 100).toFixed(1)}%）
          </span>
          {data.market.market_rv_pct >= 0.8
            ? "｜高波环境：趋势类信号可信度打折，2B/破底翻模块例外"
            : data.market.market_rv_pct <= 0.2
              ? "｜低波环境：趋势信号甜点区"
              : "｜中波环境"}
          <span className="fp-market-dim"> · 仅分组提示，不挡信号</span>
        </div>
      )}

      {miss && (
        <div className="fund-errors">
          <div className="fund-error">因子面板快照缺失。</div>
          <div className="fund-hint">请先在本机跑 scripts/precompute_factor_panel.py 生成快照。</div>
        </div>
      )}

      {data && (
        <>
          <h2 className="fund-section-title">
            因子评级卡 <span className="fund-count">实证 {data.study_date} · {data.study_ref}</span>
          </h2>
          <div className="fp-cards">
            {Object.entries(data.factors).map(([key, f]) => (
              <div key={key} className={`fp-card fp-v-${f.verdict_level}`}>
                <div className="fp-card-head">
                  <span className="fp-card-label">{f.label}</span>
                  <span className={`fp-verdict v-${f.verdict_level}`} title="本地数据实证留痕，随研究更新">
                    {VERDICT_CN[f.verdict_level] ?? f.verdict_level}
                  </span>
                </div>
                <div className="fp-card-formula">{f.formula}</div>
                <div className="fp-card-verdict">{f.verdict}</div>
                <div className="fp-card-evi" title={f.evidence}>证据：{f.evidence}</div>
                <div className="fp-card-usage">用法：{f.usage}</div>
              </div>
            ))}
          </div>

          <h2 className="fund-section-title">标的因子表</h2>
          <div className="fund-table-wrap">
            <table className="event-table fund-table">
              <thead>
                <tr>
                  {head("code", "代码")}
                  <th>组</th>
                  <th>收盘</th>
                  {head("rv20_ann", "RV20年化", "20日已实现波动率（年化）")}
                  {head("rv_pct", "RV 3年分位", "当前波动率在自身近3年历史的百分位")}
                  {head("ivol_pct", "IVOL分位", "特质波动率（个股层排雷）：60日超额收益（个股−等权市场）标准差年化，个股截面分位。≥80% 标红「彩票股警示」——实证 18 年高特质波动个股系统性跑输。仅个股层，不适用 ETF/板块；样本<3 只留空。")}
                  {head("mom_121", "12-1动量", "P(t-21)/P(t-252)-1，板块层有效/标的层参考")}
                  {head("mom_20", "20日动量", "反向因子：组内高分位=追高警示")}
                  <th>组内分位</th>
                  <th title="5日均量>20日均量：放量=趋势信号有量能配合（候补参考维度）">量能</th>
                  {head("adx14", "ADX14", "未通过稳健性检验，仅留痕")}
                  <th>EMA状态</th>
                  <th>截止</th>
                  <th>提示</th>
                </tr>
              </thead>
              <tbody>
                {symbols.map((r) => (
                  <tr key={r.code}>
                    <td>
                      {r.code}
                      {r.name ? <span className="fp-name"> {r.name}</span> : null}
                    </td>
                    <td className="text-dim">{GROUP_CN[r.subgroup] ?? r.group}</td>
                    <td>{fmt(r.close, 3)}</td>
                    <td><Num v={r.rv20_ann} digits={1} suffix="%" /></td>
                    <td><PctBar v={r.rv_pct} /></td>
                    <td>
                      {r.subgroup === "cn_stock" ? (
                        r.ivol_pct != null ? (
                          <PctBar v={r.ivol_pct} />
                        ) : (
                          <span className="text-faint" title={r.ivol60_ann != null ? `年化 ${r.ivol60_ann}%（个股样本<3，不排名）` : "留痕中"}>留痕中</span>
                        )
                      ) : (
                        <span className="text-faint" title="特质波动率仅个股层适用（ETF/板块不打分）">-</span>
                      )}
                    </td>
                    <td><Num v={r.mom_121 == null ? null : r.mom_121 * 100} digits={1} suffix="%" signed /></td>
                    <td><Num v={r.mom_20 == null ? null : r.mom_20 * 100} digits={1} suffix="%" signed /></td>
                    <td><PctBar v={r.mom_20_group_pct} /></td>
                    <td>
                      {r.vol_ok == null ? (
                        <span className="text-faint">-</span>
                      ) : r.vol_ok ? (
                        <span className="fp-vol up" title="放量：5日均量>20日均量，趋势信号有量能配合">放量</span>
                      ) : (
                        <span className="fp-vol down" title="缩量：5日均量<20日均量，信号质量参考性降低">缩量</span>
                      )}
                    </td>
                    <td><Num v={r.adx14} digits={1} /></td>
                    <td><TrendDots row={r} /></td>
                    <td className="text-dim">{r.as_of.slice(5)}</td>
                    <td><RiskChips row={r} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <h2 className="fund-section-title">
            板块 12-1 动量排名
            <span className="fund-count">
              板块层 IC +0.133（t=3.5，6/8年为正）· 信息维度，非轮动指令
            </span>
          </h2>
          <div className="fund-table-wrap">
            <table className="event-table fund-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>板块</th>
                  <th>12-1动量</th>
                  <th>20日动量</th>
                  <th>RV 3年分位</th>
                  <th>提示</th>
                </tr>
              </thead>
              <tbody>
                {data.sectors.map((r) => (
                  <tr key={r.code}>
                    <td className="text-dim">{r.mom_121_rank ?? "-"}</td>
                    <td>
                      {r.name ?? r.code}
                      <span className="fp-name"> {r.code.replace(".SECTOR", "")}</span>
                    </td>
                    <td><Num v={r.mom_121 == null ? null : r.mom_121 * 100} digits={1} suffix="%" signed /></td>
                    <td><Num v={r.mom_20 == null ? null : r.mom_20 * 100} digits={1} suffix="%" signed /></td>
                    <td><PctBar v={r.rv_pct} /></td>
                    <td><RiskChips row={r} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </>
      )}
    </div>
  );
}
