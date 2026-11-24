import ResearchResultsPanel from "../components/research-results/ResearchResultsPanel";
import { useEffect, useMemo, useRef } from "react";
import { useQuery } from "@tanstack/react-query";
import { marked } from "marked";
import { Link, useSearchParams } from "react-router-dom";
import { experimentsApi } from "../api/client";
import type { ExperimentReportItem, ExperimentVerdict } from "../types";
import "./page-reading.css";
import ReportReader from "./ReportReader";
import { patchReportLibraryParams, reportLibrarySearch } from "./reportLibraryUrl";
import "./reports-library.css";
import "./reports-library-ux.css";

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
  search,
}: {
  item: ExperimentReportItem;
  active: boolean;
  search: string;
}) {
  return (
    <Link className={`lib-row${active ? " active" : ""}`} to={{ search }} aria-current={active ? "page" : undefined}>
      <div className="lib-row-head">
        <span className="lib-row-date">{item.date}</span>
        <span className="lib-row-title">
          {item.isPrompt ? "〔任务书〕" : ""}
          {item.title}
        </span>
      </div>
      <div className="lib-row-meta">
        <span className={`lib-cat${item.pending ? " pending" : ""}`}>{item.category}</span>
        <span className="lib-completion">归档标记：{item.archived ? "已封存" : "未标封存"}</span>
        <span className="lib-verdict-label">研究结论：</span><VerdictBadge v={item.verdict} />
      </div>
      <div className="lib-row-oneliner">
        {item.oneLiner || "该报告尚未整理一句话结论，可打开正文查看。"}
      </div>
    </Link>
  );
}

export default function ReportsLibraryPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const category = searchParams.get("cat") ?? "";
  const verdict = searchParams.get("verdict") ?? "";
  const q = searchParams.get("q") ?? "";
  const hidePrompts = searchParams.get("prompts") !== "show";
  const selected = searchParams.get("report");
  const setFilter = (key: string, value: string | null) => setSearchParams(patchReportLibraryParams(searchParams, key, value), { replace: true });
  const returnToList = () => setSearchParams(patchReportLibraryParams(searchParams, "report", null));
  const readerRef = useRef<HTMLDivElement>(null);

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

  useEffect(() => {
    if (selected && detail.data?.name === selected) readerRef.current?.scrollIntoView({ block: "start", behavior: "auto" });
  }, [selected, detail.data]);

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
      <div className="page lib-page">
        <div className="pg-head">
          <div className="pg-head-title">
            <h1>实验报告库</h1>
            <span className="pg-head-sub">全部实验/调研报告的统一浏览入口 · 只读展示，不产生结论</span>
          </div>
          <div className="pg-head-kv">
            <span className="pg-kv"><span className="k">报告数</span><b>未知</b></span>
          </div>
        </div>
        <div className="fund-errors">加载失败：{(error as Error).message}</div>
      </div>
    );
  }

  const stats = data?.stats;
  const selectedMeta = data?.items.find((item) => item.name === selected);
  const html = detail.data ? (marked.parse(detail.data.markdown, { async: false }) as string) : "";

  return (
    <div className={`page lib-page${selected ? " lib-page--reading" : ""}`}>
      <div className="pg-head">
        <div className="pg-head-title">
          <h1>实验报告库</h1>
          <span className="pg-head-sub">全部实验/调研报告的统一浏览入口 · 只读展示，不产生结论</span>
        </div>
        <div className="pg-head-kv">
          <span className="pg-kv"><span className="k">报告数</span><b>{stats ? stats.total : "未知"}</b></span>
          <span className="pg-kv"><span className="k">已封存</span><b>{stats ? stats.archived : "-"}</b></span>
          <span className="pg-kv"><span className="k">结论成立</span><b>{stats ? (stats.byVerdict.passed ?? 0) : "-"}</b></span>
          <span className="pg-kv"><span className="k">证伪</span><b>{stats ? (stats.byVerdict.falsified ?? 0) : "-"}</b></span>
          <span className="pg-kv"><span className="k">有条件</span><b>{stats ? (stats.byVerdict.mixed ?? 0) : "-"}</b></span>
          <span className="pg-kv"><span className="k">观察</span><b>{stats ? (stats.byVerdict.watch ?? 0) : "-"}</b></span>
        </div>
        <div className="pg-head-actions">
          <label className="lib-toggle">
            <input type="checkbox" checked={hidePrompts} onChange={(e) => setFilter("prompts", e.target.checked ? null : "show")} />
            隐藏任务书
          </label>
        </div>
      </div>

      <div className="lib-filters">
        <select aria-label="报告分类" value={category} onChange={(e) => setFilter("cat", e.target.value)}>
          <option value="">全部分类</option>
          {(data?.categories ?? []).map((c) => (
            <option key={c} value={c}>
              {c}（{stats?.byCategory[c] ?? 0}）
            </option>
          ))}
        </select>
        <select aria-label="研究结论" value={verdict} onChange={(e) => setFilter("verdict", e.target.value)}>
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
          onChange={(e) => setFilter("q", e.target.value)}
        />
        <span className="count">{items.length} 份</span>
      </div>
      <p className="lib-verdict-note">归档标记来自文档标识，研究执行状态未单独登记；“成立”或“证伪”只针对报告提出的研究问题，不等于获准交易。</p>
      <details className="lib-maintenance-note"><summary>登记与维护说明{stats?.pending ? ` · ${stats.pending} 份待分类` : ""}</summary><p>未登记的报告在对应条目标为“待分类”。分类和研究结论来自 docs/experiments/registry.json；新报告按 AGENTS.md 的归档规约登记。未标封存不代表研究仍在进行。</p></details>

      <div className={`lib-layout${selected ? "" : " lib-layout--list-only"}`}>
        <div className="lib-list">
          {items.map((x) => (
            <ReportRow
              key={x.name}
              item={x}
              active={selected === x.name}
              search={reportLibrarySearch(searchParams, x.name)}
            />
          ))}
          {items.length === 0 && <div className="lib-empty">没有匹配的报告。</div>}
        </div>
        {selected && <div className="lib-reader" ref={readerRef}>
          <ReportReader selected={selected} report={detail.data} loading={detail.isPending} error={detail.error} onBack={returnToList}>
          {detail.data && (
            <>
              <div className="lib-reader-bar">
                <span className={`lib-cat${detail.data.category === "待分类" ? " pending" : ""}`}>
                  {detail.data.category}
                </span>
                <span className="lib-completion">归档标记：{selectedMeta ? (selectedMeta.archived ? "已封存" : "未标封存") : "未知"}</span>
                <span className="lib-verdict-label">研究结论：</span><VerdictBadge v={(detail.data.verdict || "") as ExperimentVerdict} />
                <span className="count">{detail.data.name}</span>
              </div>
              {detail.data.oneLiner && (
                <div className="lib-reader-oneliner">一句话结论：{detail.data.oneLiner}</div>
              )}
              <ResearchResultsPanel reportName={detail.data.name} />
              <div className="lib-markdown" dangerouslySetInnerHTML={{ __html: html }} />
            </>
          )}
          </ReportReader>
        </div>}
      </div>
    </div>
  );
}
