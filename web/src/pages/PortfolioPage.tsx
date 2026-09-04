import { useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import * as echarts from "echarts";
import { portfolioApi } from "../api/client";
import InfoTip from "../components/InfoTip";
import { fmtChange } from "../utils/format";
import type { PortfolioAdvice, PortfolioGroup, PortfolioHolding } from "../types";

/**
 * 我的持仓（持仓体检页 v1，2026-09-04）。
 *
 * 数据来自 GET /api/portfolio（截图录入的持仓快照，存 SQLite）。
 * 页面回答三个问题：钱在哪儿（环形图）→ 每块怎么看（分组结论卡，
 * 后端写入的已验证结论大白话翻译）→ 整个组合要注意什么（组合级提示）。
 * 展示层不计算任何信号；组金额/占比/加权收益均由后端算好。
 */

const TIPS = {
  weighted: "把组内每只基金的持有收益率按当前市值加权平均，用于组间粗略对比；不是精确业绩归因，精确数字看每只基金自己的收益率。",
  qdii: "QDII = 投海外市场的基金（要外汇额度，申赎比普通基金慢几天）。你买的纳指、标普、全球科技基金都属于这类。",
  dingtou: "定投 = 系统里登记了该基金在自动定期买入（App 截图标注）。定投中的基金操作纪律 = 按计划继续投，不因涨跌停投。",
  verdict: "「系统怎么看」= 把系统用历史数据反复检验过的结论，翻译成大白话。它只做参考与纪律提示，不构成买卖指令；未验证区域会明确标注。",
  top10: "季报穿透 = 基金公司每季度公布前十大持仓，按市场分类后统计。「占净值比例」指这些股票市值占基金总净值的比重——前十大通常只覆盖四到六成仓位，所以这是部分口径的真实暴露，不是全部。",
  adviceStrength: "证据强度：已认证 = 多轮历史回测+对照检验过线的结论；候选 = 边界结论已验证、但用到你的组合上是新应用；观察 = 数据标注（如季报），不做交易依据；管理建议 = 纯打理常识，无回测依据。",
};

/** 环形图配色：8 组固定色，与分组卡片左侧色条一一对应。 */
const GROUP_COLORS = [
  "#2563eb", // us_index  海外指数（主题蓝）
  "#7c3aed", // us_tech_active 全球科技
  "#38bdf8", // us_growth_em
  "#e33d47", // cn_info（红=A股主赛道）
  "#b45309", // cn_metal
  "#65a30d", // cn_green
  "#8c96a8", // hk_tech（灰=未验证区域）
  "#0d9488", // stable
];

function colorForGroup(index: number): string {
  return GROUP_COLORS[index % GROUP_COLORS.length];
}

/** 配置环形图（按组金额占比）。 */
function AllocationRing({ groups }: { groups: PortfolioGroup[] }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!ref.current || groups.length === 0) return;
    const chart = echarts.init(ref.current);
    chart.setOption({
      tooltip: {
        trigger: "item",
        formatter: (p: { name: string; value: number; percent: number }) =>
          `${p.name}<br/>¥${p.value.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}（${p.percent}%）`,
      },
      series: [
        {
          type: "pie",
          radius: ["48%", "72%"],
          center: ["50%", "50%"],
          avoidLabelOverlap: true,
          itemStyle: { borderColor: "#fff", borderWidth: 2 },
          label: {
            formatter: "{b}\n{d}%",
            fontSize: 11,
            color: "#5b6473",
            lineHeight: 15,
          },
          labelLine: { length: 8, length2: 6 },
          data: groups.map((g, i) => ({
            name: g.name.replace(/^[^·]*·/, ""),
            value: g.amount,
            itemStyle: { color: colorForGroup(i) },
          })),
        },
      ],
    });
    const onResize = () => chart.resize();
    window.addEventListener("resize", onResize);
    return () => {
      window.removeEventListener("resize", onResize);
      chart.dispose();
    };
  }, [groups]);

  return <div ref={ref} style={{ width: "100%", height: 300 }} />;
}

function ReturnCell({ v }: { v: number | null }) {
  const { text, cls } = fmtChange(v);
  return <span className={cls}>{text}</span>;
}

/** 市场代码 -> 短名（与后端 MARKET_CN 一致的展示层映射） */
const MARKET_SHORT: Record<string, string> = { cn: "A股", hk: "港股", us: "美股", other: "其他" };

/** 一只基金的真实暴露 chips（前十大口径）。 */
function ExposureChips({ h }: { h: PortfolioHolding }) {
  if (h.top10_total_pct == null) return <span className="flat">—</span>;
  const parts = Object.entries(h.top10_by_market_pct)
    .filter(([, v]) => v >= 1)
    .map(([m, v]) => `${MARKET_SHORT[m] ?? m}${Math.round(v)}%`);
  return (
    <span className="portfolio-expo" title={`季报 ${h.report_quarter}；前十大合计占净值 ${h.top10_total_pct}%`}>
      {parts.join(" · ")}
    </span>
  );
}

/** 组级真实分布行：名义分组 vs 穿透后。 */
function GroupRealShare({ share }: { share: Record<string, number> | null }) {
  if (!share) return null;
  const parts = Object.entries(share).map(([m, v]) => `${MARKET_SHORT[m] ?? m}${v.toFixed(0)}%`);
  return (
    <div className="portfolio-real-share">
      <InfoTip tip={TIPS.top10}>真实分布</InfoTip>：{parts.join(" · ")}
    </div>
  );
}

/** 建议强度徽章配色。 */
const STRENGTH_CLS: Record<string, string> = {
  certified: "pos",
  candidate: "imp",
  observation: "mid",
  management: "muted-chip",
};

function AdviceCard({ a }: { a: PortfolioAdvice }) {
  return (
    <div className={`card portfolio-advice-card ${a.strength}`}>
      <div className="portfolio-advice-head">
        <span className={`chip ${STRENGTH_CLS[a.strength] ?? ""}`} title={TIPS.adviceStrength}>
          {a.strength_cn}
        </span>
        <span className="portfolio-advice-title">{a.title_cn}</span>
      </div>
      <p className="portfolio-advice-detail">{a.detail_cn}</p>
      {a.evidence.length > 0 && (
        <div className="portfolio-advice-evidence">
          {a.evidence.map((e, i) => (
            <span key={i} className="portfolio-advice-ev" title={e.ref}>
              ✓ {e.label}
            </span>
          ))}
        </div>
      )}
      {(a.trigger_cn || a.execution_cn) && (
        <div className="portfolio-advice-actions">
          {a.trigger_cn && a.trigger_cn !== "—" && (
            <div><span className="portfolio-advice-k">时机</span>{a.trigger_cn}</div>
          )}
          {a.execution_cn && a.execution_cn !== "—" && (
            <div><span className="portfolio-advice-k">执行</span>{a.execution_cn}</div>
          )}
        </div>
      )}
    </div>
  );
}

function GroupCard({ group, index }: { group: PortfolioGroup; index: number }) {
  return (
    <div className="card portfolio-group-card" style={{ borderLeft: `4px solid ${colorForGroup(index)}` }}>
      <div className="portfolio-group-head">
        <div>
          <span className="portfolio-group-name">{group.name}</span>
          <span className="chip">{group.market_cn}</span>
        </div>
        <div className="portfolio-group-nums">
          <span className="portfolio-amount">¥{group.amount.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}</span>
          <span className="portfolio-pct">{group.pct.toFixed(1)}%</span>
          <span className="portfolio-ret">
            组收益 <InfoTip tip={TIPS.weighted}><ReturnCell v={group.avg_return_pct} /></InfoTip>
          </span>
        </div>
      </div>

      <div className="portfolio-verdict">
        <div className="portfolio-verdict-title">
          系统怎么看
          <InfoTip tip={TIPS.verdict}>
            <span className="portfolio-verdict-badge">?</span>
          </InfoTip>
        </div>
        <p>{group.verdict_cn}</p>
        {group.verdict_basis && group.verdict_basis !== "—" && (
          <div className="portfolio-verdict-basis">依据：{group.verdict_basis}</div>
        )}
        <GroupRealShare share={group.real_market_share} />
      </div>

      <table className="portfolio-table">
        <thead>
          <tr>
            <th>基金</th>
            <th>代码</th>
            <th className="num">金额（元）</th>
            <th className="num">持有收益率</th>
            <th>
              <InfoTip tip={TIPS.top10}>真实暴露</InfoTip>
            </th>
            <th>标签</th>
          </tr>
        </thead>
        <tbody>
          {group.holdings.map((h) => {
            const ret = fmtChange(h.return_pct);
            return (
              <tr key={h.holding_id}>
                <td className="portfolio-holding-name">
                  {h.name}
                  {h.note && <div className="portfolio-holding-note">{h.note}</div>}
                </td>
                <td className="flat">{h.code ?? "待补"}</td>
                <td className="num">{h.market_value.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}</td>
                <td className={`num ${ret.cls}`}>{ret.text}</td>
                <td><ExposureChips h={h} /></td>
                <td>
                  {h.tags.map((t) => (
                    <span key={t} className="tag" title={t === "QDII" ? TIPS.qdii : t === "定投" ? TIPS.dingtou : undefined}>
                      {t}
                    </span>
                  ))}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export default function PortfolioPage() {
  const { data, error, isLoading } = useQuery({
    queryKey: ["portfolio"],
    queryFn: portfolioApi.get,
    staleTime: 5 * 60_000,
  });

  const totalText = useMemo(
    () => (data ? `¥${data.total_value.toLocaleString("zh-CN", { minimumFractionDigits: 2 })}` : "--"),
    [data],
  );

  /** 海外/A股/港股 三大市场占比（组占比按市场加总，"其他"不入列）。 */
  const marketSplit = useMemo(() => {
    if (!data) return "--";
    const byMarket = data.groups.reduce<Record<string, number>>((acc, g) => {
      acc[g.market] = (acc[g.market] ?? 0) + g.pct;
      return acc;
    }, {});
    return `${(byMarket.us ?? 0).toFixed(0)}% : ${(byMarket.cn ?? 0).toFixed(0)}% : ${(byMarket.hk ?? 0).toFixed(0)}%`;
  }, [data]);

  if (isLoading) return <div className="page"><p className="flat">加载持仓中…</p></div>;
  if (error || !data) {
    return (
      <div className="page">
        <div className="card error">
          <p>持仓数据加载失败：{(error as Error | null)?.message ?? "未知错误"}</p>
          <p className="flat">首次使用请先运行：python3 scripts/seed_portfolio.py</p>
        </div>
      </div>
    );
  }

  return (
    <div className="page">
      <div className="section-title">
        <h1>我的持仓</h1>
        <span className="count">
          {data.holdings_count} 只 · 数据截至 {data.as_of} · {data.data_source_cn}
        </span>
      </div>

      {/* 组合总览条 */}
      <div className="card portfolio-summary">
        <div className="portfolio-summary-item">
          <div className="portfolio-summary-label">持仓总市值</div>
          <div className="portfolio-summary-value">{totalText}</div>
        </div>
        <div className="portfolio-summary-item">
          <div className="portfolio-summary-label">基金只数 / 分组</div>
          <div className="portfolio-summary-value">
            {data.holdings_count} / {data.groups.length}
          </div>
        </div>
        <div className="portfolio-summary-item">
          <div className="portfolio-summary-label">海外 : A股 : 港股</div>
          <div className="portfolio-summary-value">{marketSplit}</div>
        </div>
      </div>

      {/* 组合级提示 */}
      {data.observations.length > 0 && (
        <div className="card portfolio-observations">
          <div className="portfolio-observations-title">整个组合要注意什么（大白话）</div>
          <ul>
            {data.observations.map((o, i) => (
              <li key={i}>{o}</li>
            ))}
          </ul>
        </div>
      )}

      {/* 调仓建议：R1~R7 规则引擎输出（判定在后端，页面只展示） */}
      {data.advices.length > 0 && (
        <div className="portfolio-advice-section">
          <div className="section-title">
            <h2 style={{ fontSize: 15 }}>调仓建议</h2>
            <span className="count">
              按优先级排序 · {data.advices.length} 条 · 建议级非指令，采纳与否你拍板
            </span>
          </div>
          <div className="portfolio-advice-grid">
            {data.advices.map((a) => (
              <AdviceCard key={a.advice_id} a={a} />
            ))}
          </div>
        </div>
      )}

      {/* 左：配置环形图（吸顶）；右：分组卡片流 */}
      <div className="portfolio-layout">
        <div className="portfolio-chart-col">
          <div className="card">
            <div className="section-title" style={{ marginTop: 0 }}>
              <h2 style={{ fontSize: 15 }}>钱在哪儿</h2>
            </div>
            <AllocationRing groups={data.groups} />
          </div>
        </div>
        <div className="portfolio-groups-col">
          {data.groups.map((g, i) => (
            <GroupCard key={g.group_key} group={g} index={i} />
          ))}
        </div>
      </div>
    </div>
  );
}
