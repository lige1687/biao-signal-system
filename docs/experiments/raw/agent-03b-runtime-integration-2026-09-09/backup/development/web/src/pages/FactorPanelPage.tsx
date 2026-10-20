import { useMemo, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { factorsApi, type FactorRow, type FactorLabSnapshot } from "../api/client";
import { buildRiskChips, groupFactorCards, marketRegimePhrase, VERIFY_NOTE } from "./factorPanelLogic";
import { fmt, pctClass } from "../utils/format";

/**
 * 因子观测台：常见因子读数 + 历史分位 + 板块 12-1 排名。
 *
 * 红线对齐（与后端 factor_panel.py 一致）：
 * - 全部 research_proxy，不出买卖点、不挡任何 LEI 技术信号；
 * - 评级卡来自后端 FACTOR_META 的实证留痕（2026-08-27 本地数据），
 *   前端只做展示，不得另造评级或阈值；
 * - 信息架构按 2026-09-05 价值复核（docs/experiments/factor-panel-value-
 *   2026-09-05.md，8561 条信号对账）重排：有效（pass）前排展开；弱/否决
 *   （weak/inverse/fail）与「打折/超买」类提示默认折叠或降级为读数——
 *   它们对已确认信号无预测力或方向相反，不得误导看信号的人。
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

/** 极简 markdown 加粗：`**x**` → <strong>（FACTOR_META 文本带 ** 语法，纯文本渲染会漏星号）。 */
function mdBold(text: string): React.ReactNode {
  return text.split(/\*\*(.+?)\*\*/g).map((p, i) =>
    i % 2 === 1 ? <strong key={i}>{p}</strong> : <span key={i}>{p}</span>,
  );
}

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

/** 风险标注 chips（口径与文案见 factorPanelLogic.ts，2026-09-05 复核）。 */
function RiskChips({ row }: { row: FactorRow }) {
  const chips = buildRiskChips(row);
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

/** 因子实验台区块（文主任增量 #6，2026-09-05 追加）：组合回测 + L1-L6 + 估值分位。 */
function FactorLabSections({ lab }: { lab: FactorLabSnapshot | undefined }) {
  if (!lab) return null;
  const ports = lab.portfolios;
  const grades = lab.risk_grades;
  const val = lab.valuation;
  return (
    <details className="fp-lab" open={false}>
      <summary>
        🧪 实验台（追加段 · 2026-09-05 文主任增量 #6）：全市场因子组合 · L1-L6 市场难度分级 · 估值分位
        <span className="fund-count">全部 research_proxy，不进主判定链</span>
      </summary>
      <div className="legend">{lab.note_cn}</div>

      {ports?.available === false && <div className="fund-errors">{ports.reason_cn}</div>}
      {ports?.portfolios?.length ? (
        <>
          <h3 className="fund-section-title">{ports.title_cn}</h3>
          <div className="fund-table-wrap">
            <table className="event-table fund-table">
              <thead>
                <tr>
                  <th>组合</th><th>月数</th><th>区间</th><th>累计</th>
                  <th title="几何年化，未计手续费/滑点/涨跌停">年化</th>
                  <th title="等权全市场基准（同月度再平衡）">基准年化</th>
                  <th title="年化减基准年化（百分点）">超额</th>
                </tr>
              </thead>
              <tbody>
                {ports.portfolios.map((r) => (
                  <tr key={r.label}>
                    <td className="strong">{r.label}</td>
                    <td>{r.n_months}</td>
                    <td className="text-dim">{r.start}→{r.end}</td>
                    <td>{r.total_return_pct}%</td>
                    <td>{r.cagr_pct}%</td>
                    <td className="text-dim">{r.benchmark_cagr_pct}%</td>
                    <td className={pctClass(r.excess_cagr_pct ?? null)}>
                      {r.excess_cagr_pct == null ? "-" : `${r.excess_cagr_pct > 0 ? "+" : ""}${r.excess_cagr_pct}pp`}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="rs-note">{ports.note_cn}</div>
          {ports.restricted.map((r) => (
            <div key={r} className="rs-note">⚠ 数据受限：{r}</div>
          ))}
        </>
      ) : null}

      {grades?.available && grades.current && (
        <>
          <h3 className="fund-section-title">
            L1-L6 市场难度分级（周度）
            <span className="fund-count">
              当前 <strong>{grades.current.grade}</strong>（评分 {grades.current.score}/100，{grades.current.date}）
            </span>
          </h3>
          <div className="fund-table-wrap">
            <table className="event-table fund-table">
              <thead>
                <tr>
                  <th>档位</th><th>历史天数</th>
                  <th title="该档出现后 20 个交易日的市场平均已实现波动（年化）——重叠样本描述统计">之后20日平均波动</th>
                  <th title="该档出现后 20 个交易日的市场平均收益">之后20日平均收益</th>
                </tr>
              </thead>
              <tbody>
                {Object.keys(grades.by_grade ?? {}).sort().map((g) => {
                  const st = grades.by_grade![g];
                  return (
                    <tr key={g} className={grades.current?.grade === g ? "star" : undefined}>
                      <td className="strong">{g}{grades.current?.grade === g ? " ←当前" : ""}</td>
                      <td>{st.n_days}</td>
                      <td>{st.fwd_rv20_mean_pct}%</td>
                      <td className={pctClass(st.fwd_ret20_mean_pct)}>{st.fwd_ret20_mean_pct > 0 ? "+" : ""}{st.fwd_ret20_mean_pct}%</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
          <div className="rs-note">{grades.note_cn}「难度高」只说明随后波动大，不等于要卖出（高分档后收益并不更差）。</div>
        </>
      )}
      {grades?.available === false && <div className="rs-note">L1-L6 分级：{grades.reason_cn}</div>}

      {val?.available && val.chips ? (
        <>
          <h3 className="fund-section-title">主要指数估值分位（背景标注）</h3>
          <div className="fp-chips" style={{ flexWrap: "wrap" }}>
            {val.chips.map((c) => (
              <span
                key={c.index_code}
                className={`stage-chip fp-chip-${c.pe_percentile >= 80 ? "warn" : c.pe_percentile <= 20 ? "cold" : "info"}`}
                title={`${c.name_cn} 市盈率(PE-TTM) ${c.pe_ttm}，处于历史约近10年的 ${c.pe_percentile}% 分位`}
              >
                {c.name_cn} PE分位 {c.pe_percentile}%
              </span>
            ))}
          </div>
          <div className="rs-note">{val.note_cn}</div>
        </>
      ) : (
        val && <div className="rs-note">估值分位：{val.reason_cn}（不冒充）</div>
      )}
    </details>
  );
}

export default function FactorPanelPage() {
  const queryClient = useQueryClient();
  const { data, error, isLoading } = useQuery({
    queryKey: ["factorPanel"],
    queryFn: () => factorsApi.panel(),
    staleTime: 5 * 60_000,
  });
  // 实验台快照（独立文件，miss 时对应区块整体隐藏，不影响主面板）
  const { data: lab } = useQuery({
    queryKey: ["factorLab"],
    queryFn: () => factorsApi.lab(),
    staleTime: 5 * 60_000,
    retry: false,
  });
  const [sortKey, setSortKey] = useState<SymSortKey>("rv_pct");
  const [sortDesc, setSortDesc] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [refreshError, setRefreshError] = useState<string | null>(null);
  // 弱因子列（20日动量/组内分位/量能/ADX）：2026-09-05 复核信号层无预测力或反向，默认折叠。
  const [showWeakCols, setShowWeakCols] = useState(false);

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

  const cardGroups = useMemo(
    () => (data ? groupFactorCards(data.factors) : { primary: [], weak: [] }),
    [data],
  );

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
          <span className="tag" title="页面下半部分含 2026-09-05 新增的实验台模块（组合回测/L1-L6/估值分位），全部为研究代理，连续 8 周无有效结论即下架对应模块">
            🧪 含实验模块
          </span>{" "}
          <span className="fund-count">
            {data ? `${data.counts.symbols} 标的 · ${data.counts.sectors} 板块 · 数据截止 ${data.data_as_of}` : ""}
          </span>
        </h1>
        <span className="generated">
          快照 {data?.generated_at} · 评级留痕 {data?.study_date} · 价值复核 2026-09-05
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
          title={`口径：${data.market.market_basis}（截止 ${data.market.market_as_of}）。2026-09-05 复核（8561 条信号）：市场 RV 分位对信号质量的作用是模块分层的——高波期 C 模块（2B/破底翻）是全场最强段（60 日 +6.9%/胜率 59%），非高波期 C 最弱；「高波期信号整体打折」的旧口径未复现（当前信号流九成来自 C 模块）。该读数联动今日信号横幅的路由提示，仅分组提示不挡信号。`}
        >
          市场 RV 分位（环境层）：
          <strong>{Math.round(data.market.market_rv_pct * 100)}%</strong>
          <span className="fp-market-ann">
            （RV20 年化 {((data.market.market_rv20_ann ?? 0) * 100).toFixed(1)}%）
          </span>
          ｜{marketRegimePhrase(data.market.market_rv_pct)}
          <span className="fp-market-dim"> · 仅分组提示，不挡信号</span>
        </div>
      )}

      {miss && (
        <div className="fund-errors">
          <div className="fund-error">因子面板快照缺失。</div>
          <div className="fund-hint">请先在本机跑 scripts/precompute_factor_panel.py 生成快照。</div>
        </div>
      )}

      {/* 实验台追加段（文主任增量 #6）：折叠展示，不干扰主面板信息架构 */}
      <FactorLabSections lab={lab} />

      {data && (
        <>
          <h2 className="fund-section-title">
            板块 12-1 动量排名
            <span className="fund-count">
              板块层 IC +0.133（t=3.5，6/8年为正）· 信息维度，非轮动指令 · {VERIFY_NOTE}：标的层高半区 60 日 +6.1% vs 低半区 +3.3%（亦有分离）
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

          <h2 className="fund-section-title">
            因子评级卡 <span className="fund-count">实证 {data.study_date} · {data.study_ref} · 排列按 {VERIFY_NOTE}</span>
          </h2>
          <div className="fp-cards">
            {cardGroups.primary.map(([key, f]) => (
              <div key={key} className={`fp-card fp-v-${f.verdict_level}`}>
                <div className="fp-card-head">
                  <span className="fp-card-label">{f.label}</span>
                  <span className={`fp-verdict v-${f.verdict_level}`} title="本地数据实证留痕，随研究更新">
                    {VERDICT_CN[f.verdict_level] ?? f.verdict_level}
                  </span>
                </div>
                <div className="fp-card-formula">{f.formula}</div>
                <div className="fp-card-verdict">{mdBold(f.verdict)}</div>
                <details className="fp-card-detail">
                  <summary>证据与用法</summary>
                  <div className="fp-card-evi">{mdBold(f.evidence)}</div>
                  <div className="fp-card-usage">{mdBold(f.usage)}</div>
                </details>
              </div>
            ))}
          </div>
          {cardGroups.weak.length > 0 && (
            <details className="fp-weak-cards">
              <summary>
                弱/否决因子卡（{cardGroups.weak.length}）· 默认折叠——{VERIFY_NOTE}：信号层无预测力或反向
              </summary>
              <div className="fp-cards">
                {cardGroups.weak.map(([key, f]) => (
                  <div key={key} className={`fp-card fp-v-${f.verdict_level}`}>
                    <div className="fp-card-head">
                      <span className="fp-card-label">{f.label}</span>
                      <span className={`fp-verdict v-${f.verdict_level}`} title="本地数据实证留痕，随研究更新">
                        {VERDICT_CN[f.verdict_level] ?? f.verdict_level}
                      </span>
                    </div>
                    <div className="fp-card-formula">{f.formula}</div>
                    <div className="fp-card-verdict">{mdBold(f.verdict)}</div>
                    <details className="fp-card-detail">
                      <summary>证据与用法</summary>
                      <div className="fp-card-evi">{mdBold(f.evidence)}</div>
                      <div className="fp-card-usage">{mdBold(f.usage)}</div>
                    </details>
                  </div>
                ))}
              </div>
            </details>
          )}

          <h2 className="fund-section-title">
            标的因子表
            <span className="fund-count">
              弱因子列（20日动量/组内分位/量能/ADX）默认折叠——{VERIFY_NOTE}：对已确认信号无预测力
            </span>
          </h2>
          <div className="fund-table-wrap">
            <table className="event-table fund-table">
              <thead>
                <tr>
                  {head("code", "代码")}
                  <th>组</th>
                  <th>收盘</th>
                  {head("rv20_ann", "RV20年化", "20日已实现波动率（年化）")}
                  {head("rv_pct", "RV 3年分位", `当前波动率在自身近3年历史的百分位。${VERIFY_NOTE}：高波分位对已确认信号无打折预测力，仅环境读数`)}
                  {head("ivol_pct", "IVOL分位", `特质波动率（个股层排雷）：60日超额收益（个股−等权市场）标准差年化，个股截面分位。实证：高特质波动个股 18 年系统性跑输——排雷只用于自选池入口；${VERIFY_NOTE}：对已确认信号反向（高IVOL信号 60 日 +12.1%），不否决信号。仅个股层；样本<3 只留空。`)}
                  {head("mom_121", "12-1动量", `P(t-21)/P(t-252)-1，板块层有效/标的层参考。${VERIFY_NOTE}：标的层高半区 60 日 +6.1% vs 低半区 +3.3%，亦有分离`)}
                  {showWeakCols && head("mom_20", "20日动量", `反向因子（仅裸标的层）。${VERIFY_NOTE}：对已确认信号无预测力（p=0.10）`)}
                  {showWeakCols && <th title={`组内分位（20日动量截面）。${VERIFY_NOTE}：仅裸标的追高参考，不否决信号`}>组内分位</th>}
                  {showWeakCols && <th title={`5日均量>20日均量。${VERIFY_NOTE}：信号层无增强（p=0.11），仅组合级风控参考`}>量能</th>}
                  {showWeakCols && head("adx14", "ADX14", `未通过稳健性检验，仅留痕`)}
                  <th>EMA状态</th>
                  <th>截止</th>
                  <th>提示</th>
                  <th>
                    <button
                      className="btn small"
                      onClick={() => setShowWeakCols((v) => !v)}
                      title="弱因子列：2026-09-05 复核对已确认信号无预测力或反向，默认折叠"
                    >
                      {showWeakCols ? "隐藏弱列" : "弱列"}
                    </button>
                  </th>
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
                    {showWeakCols && <td><Num v={r.mom_20 == null ? null : r.mom_20 * 100} digits={1} suffix="%" signed /></td>}
                    {showWeakCols && <td><PctBar v={r.mom_20_group_pct} /></td>}
                    {showWeakCols && (
                      <td>
                        {r.vol_ok == null ? (
                          <span className="text-faint">-</span>
                        ) : r.vol_ok ? (
                          <span className="fp-vol up" title="放量：5日均量>20日均量（组合级风控参考，信号层无增强）">放量</span>
                        ) : (
                          <span className="fp-vol down" title="缩量：5日均量<20日均量（组合级风控参考，信号层无增强）">缩量</span>
                        )}
                      </td>
                    )}
                    {showWeakCols && <td><Num v={r.adx14} digits={1} /></td>}
                    <td><TrendDots row={r} /></td>
                    <td className="text-dim">{r.as_of.slice(5)}</td>
                    <td><RiskChips row={r} /></td>
                    <td></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="rs-note" style={{ marginTop: 16 }}>
            🧪 实验台下架条件：本页实验模块（组合回测 / L1-L6 分级 / 估值分位）连续 8 周
            无有效结论（不能产出一个被后续数据支持的新判断）即下架对应模块——
            实验要有退出机制，不无限占页面。
          </div>
        </>
      )}
    </div>
  );
}
