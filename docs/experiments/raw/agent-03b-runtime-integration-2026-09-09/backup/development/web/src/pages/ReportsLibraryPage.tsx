import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { marked } from "marked";
import { experimentsApi } from "../api/client";
import type { ExperimentReportItem, ExperimentVerdict } from "../types";

/**
 * 实验报告库：历史上所有实验/调研文档的统一浏览入口。
 * 数据来自后端扫描 docs/experiments + docs/research-*（文件全量）与
 * registry.json 登记簿（分类/判定状态权威）。本页只读展示，不产生结论。
 *
 * 规约提醒（详见 AGENTS.md）：
 * - 未登记 registry.json 的报告会标「待分类」红条；
 * - 没写「## 一句话结论（大白话）」小节的报告结论列显示占位提示。
 */

const VERDICT_META: Record<Exclude<ExperimentVerdict, "">, { label: string; cls: string }> = {
  passed: { label: "成立", cls: "vd-passed" },
  falsified: { label: "证伪", cls: "vd-falsified" },
  mixed: { label: "有条件/证据不足", cls: "vd-mixed" },
  watch: { label: "观察中", cls: "vd-watch" },
};

function VerdictBadge({ v }: { v: ExperimentVerdict }) {
  if (!v) return <span className="vd-badge vd-none">未标</span>;
  const m = VERDICT_META[v];
  return <span className={`vd-badge ${m.cls}`}>{m.label}</span>;
}

function ReportRow({
  item,
  active,
  onClick,
}: {
  item: ExperimentReportItem;
  active: boolean;
  onClick: () => void;
}) {
  return (
    <div className={`lib-row${active ? " active" : ""}`} onClick={onClick}>
      <div className="lib-row-head">
        <span className="lib-row-date">{item.date}</span>
        <span className="lib-row-title">
          {item.isPrompt ? "〔任务书〕" : ""}
          {item.title}
        </span>
        {item.archived && <span className="lib-row-archived">归档</span>}
      </div>
      <div className="lib-row-meta">
        <span className={`lib-cat${item.pending ? " pending" : ""}`}>{item.category}</span>
        <VerdictBadge v={item.verdict} />
      </div>
      <div className="lib-row-oneliner">
        {item.oneLiner || "（未写「一句话结论」小节——点开看正文；新报告请按规约补写）"}
      </div>
    </div>
  );
}

export default function ReportsLibraryPage() {
  const [category, setCategory] = useState<string>("");
  const [verdict, setVerdict] = useState<string>("");
  const [q, setQ] = useState("");
  const [hidePrompts, setHidePrompts] = useState(true);
  const [selected, setSelected] = useState<string | null>(null);

  const { data, error } = useQuery({
    queryKey: ["experiments"],
    queryFn: experimentsApi.list,
    staleTime: 5 * 60_000,
  });

  const detail = useQuery({
    queryKey: ["experiment", selected],
    queryFn: () => experimentsApi.detail(selected!),
    enabled: selected != null,
    staleTime: 5 * 60_000,
  });

  const items = useMemo(() => {
    let list = data?.items ?? [];
    if (category) list = list.filter((x) => x.category === category);
    if (verdict) list = verdict === "none" ? list.filter((x) => !x.verdict) : list.filter((x) => x.verdict === verdict);
    if (hidePrompts) list = list.filter((x) => !x.isPrompt);
    if (q.trim()) {
      const kw = q.trim().toLowerCase();
      list = list.filter(
        (x) =>
          x.title.toLowerCase().includes(kw) ||
          x.oneLiner.toLowerCase().includes(kw) ||
          x.name.toLowerCase().includes(kw),
      );
    }
    return list;
  }, [data, category, verdict, q, hidePrompts]);

  if (error) {
    return (
      <div className="page">
        <div className="header"><h1>实验报告库</h1></div>
        <div className="fund-errors">加载失败：{(error as Error).message}</div>
      </div>
    );
  }

  const stats = data?.stats;
  const html = detail.data ? (marked.parse(detail.data.markdown, { async: false }) as string) : "";

  return (
    <div className="page lib-page">
      <div className="header">
        <h1>实验报告库</h1>
        <span className="generated">
          {stats ? `${stats.total} 份报告 · 成立 ${stats.byVerdict.passed ?? 0} / 证伪 ${stats.byVerdict.falsified ?? 0} / 有条件 ${stats.byVerdict.mixed ?? 0} / 观察 ${stats.byVerdict.watch ?? 0}` : "加载中…"}
        </span>
        <span className="spacer" />
        <label className="lib-toggle">
          <input type="checkbox" checked={hidePrompts} onChange={(e) => setHidePrompts(e.target.checked)} />
          隐藏任务书
        </label>
      </div>

      {stats && stats.pending > 0 && (
        <div className="lib-pending-tip">
          ⚠ {stats.pending} 份报告未在 registry.json 登记（列表中标「待分类」）——
          按 AGENTS.md 归档规约补登记后此处消失。
        </div>
      )}

      <div className="lib-filters">
        <select value={category} onChange={(e) => setCategory(e.target.value)}>
          <option value="">全部分类</option>
          {(data?.categories ?? []).map((c) => (
            <option key={c} value={c}>
              {c}（{stats?.byCategory[c] ?? 0}）
            </option>
          ))}
        </select>
        <select value={verdict} onChange={(e) => setVerdict(e.target.value)}>
          <option value="">全部结论</option>
          <option value="passed">成立</option>
          <option value="falsified">证伪</option>
          <option value="mixed">有条件/证据不足</option>
          <option value="watch">观察中</option>
          <option value="none">未标</option>
        </select>
        <input
          className="lib-search"
          placeholder="搜索标题 / 结论 / 文件名…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
        />
        <span className="count">{items.length} 份</span>
      </div>

      <div className="lib-layout">
        <div className="lib-list">
          {items.map((x) => (
            <ReportRow
              key={x.name}
              item={x}
              active={selected === x.name}
              onClick={() => setSelected(x.name)}
            />
          ))}
          {items.length === 0 && <div className="lib-empty">没有匹配的报告。</div>}
        </div>
        <div className="lib-reader">
          {detail.data ? (
            <>
              <div className="lib-reader-bar">
                <span className={`lib-cat${detail.data.category === "待分类" ? " pending" : ""}`}>
                  {detail.data.category}
                </span>
                <VerdictBadge v={(detail.data.verdict || "") as ExperimentVerdict} />
                <span className="count">{detail.data.name}</span>
              </div>
              {detail.data.oneLiner && (
                <div className="lib-reader-oneliner">一句话结论：{detail.data.oneLiner}</div>
              )}
              <div className="lib-markdown" dangerouslySetInnerHTML={{ __html: html }} />
            </>
          ) : (
            <div className="lib-empty">← 点左侧任意报告阅读全文。</div>
          )}
        </div>
      </div>
    </div>
  );
}
