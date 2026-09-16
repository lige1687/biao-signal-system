import { useEffect, useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { useSearchParams } from "react-router-dom";
import { learningApi } from "../api/client";
import type { LearningEntry, LearningPaper, LearningResponse } from "../types";

/**
 * 文献学习库：以论文为线索的学习目录（独立学习层，不参与交易判定）。
 * 数据来自只读接口 GET /api/learning（docs/literature-learning/learning-seed.json）。
 *
 * 约定（见交接稿 literature-learning-library-handoff-2026-09-08.md）：
 * - 深链接 /learning?paper=lo2000&entry=lo2000-lesson-1；筛选也进 URL，
 *   刷新 / 复制链接 / 浏览器返回都不丢定位。选论文压入历史（返回可回目录），
 *   改筛选只替换当前历史记录。
 * - 未知论文 ID 显示「未找到」，绝不回落到第一篇。
 * - 数值门槛为 null 时明确显示「未提取已核实的数值标准」，不显示 0 / 已通过。
 * - 教学例子必须带「教学假设」标注；「我们从中学什么」标注为本库理解。
 * - 本页无写接口、无登录、无进度存储；方法被研究采用 ≠ 策略已验证有效。
 */

/** 发表类型 → 中文标签（未知类型原样显示，不臆造归类）。 */
const KIND_LABELS: Record<string, string> = {
  journalArticle: "期刊论文",
  workingPaper: "工作论文",
  report: "机构/研究报告",
};
const kindLabel = (k: string) => KIND_LABELS[k] ?? k;

const paperHaystack = (p: LearningPaper) =>
  [p.title, p.authors.join(" / "), p.selection_label, p.venue ?? "", String(p.year)]
    .join(" ")
    .toLowerCase();
const entryHaystack = (e: LearningEntry) =>
  [
    e.title,
    e.question,
    e.author_finding_summary,
    e.our_learning,
    e.example?.text ?? "",
    e.applicability,
    e.review_question,
    (e.method_acceptance?.checks ?? []).join(" "),
  ]
    .join(" ")
    .toLowerCase();

export default function LearningLibraryPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const paperId = searchParams.get("paper");
  const entryId = searchParams.get("entry");
  const q = searchParams.get("q") ?? "";
  const category = searchParams.get("cat") ?? "";
  const kind = searchParams.get("kind") ?? "";
  const pathId = searchParams.get("path") ?? "";
  const sort = searchParams.get("sort") === "year" ? "year" : "recommended";

  const { data, error } = useQuery({
    queryKey: ["learning"],
    queryFn: learningApi.get,
    staleTime: 5 * 60_000,
  });

  /** patch 为 null/"" 的键从 URL 删除；replace=false 压入历史（返回可回退）。 */
  const updateParams = (patch: Record<string, string | null>, replace: boolean) => {
    const next = new URLSearchParams(searchParams);
    for (const [k, v] of Object.entries(patch)) {
      if (v == null || v === "") next.delete(k);
      else next.set(k, v);
    }
    setSearchParams(next, { replace });
  };
  const setFilter = (patch: Record<string, string | null>) => updateParams(patch, true);

  const paperById = useMemo(
    () => new Map((data?.papers ?? []).map((p) => [p.id, p])),
    [data],
  );
  const entryById = useMemo(
    () => new Map((data?.entries ?? []).map((e) => [e.id, e])),
    [data],
  );
  const entriesByPaper = useMemo(() => {
    const m = new Map<string, LearningEntry[]>();
    for (const e of data?.entries ?? []) {
      const list = m.get(e.paper_id) ?? [];
      list.push(e);
      m.set(e.paper_id, list);
    }
    return m;
  }, [data]);

  // 深链接自愈：?entry= 无所属论文或与 paper 不符时，按条目归属校正 URL。
  useEffect(() => {
    if (!entryId || !data) return;
    const entry = entryById.get(entryId);
    if (!entry) {
      setFilter({ entry: null });
      return;
    }
    if (!paperId) updateParams({ paper: entry.paper_id }, true);
    else if (paperId !== entry.paper_id) updateParams({ paper: entry.paper_id }, true);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [entryId, paperId, data]);

  const kindOptions = useMemo(() => {
    const kinds = [...new Set((data?.papers ?? []).map((p) => p.publication_kind))];
    return kinds.map((k) => ({ value: k, label: kindLabel(k) }));
  }, [data]);

  const activePath = data?.reading_paths.find((p) => p.id === pathId);
  const pathEntryIds = useMemo(
    () => new Set(activePath?.entry_ids ?? []),
    [activePath],
  );

  /** 筛选后的论文 + 每篇应展示的条目。搜索命中论文meta时展示全条目，否则只展命中条目。 */
  const visible = useMemo<LRow[]>(() => {
    const qn = q.trim().toLowerCase();
    let papers = data?.papers ?? [];
    if (kind) papers = papers.filter((p) => p.publication_kind === kind);
    const out: LRow[] = [];
    papers.forEach((p, seedIdx) => {
      const all = entriesByPaper.get(p.id) ?? [];
      const matched = all.filter(
        (e) =>
          (!category || e.category === category) &&
          (!pathEntryIds.size || pathEntryIds.has(e.id)) &&
          (!qn || entryHaystack(e).includes(qn)),
      );
      const paperHits = qn !== "" && paperHaystack(p).includes(qn);
      if (!paperHits && matched.length === 0) return;
      const narrowed = Boolean(qn && !paperHits) || category !== "" || pathEntryIds.size > 0;
      const shown = narrowed ? matched : all;
      if (shown.length === 0) return;
      out.push({
        paper: p,
        entries: shown,
        seedIdx,
        minPriority: Math.min(...all.map((e) => e.priority)),
      });
    });
    out.sort((a, b) =>
      sort === "year"
        ? b.paper.year - a.paper.year || a.seedIdx - b.seedIdx
        : a.minPriority - b.minPriority || a.seedIdx - b.seedIdx,
    );
    return out;
  }, [data, q, kind, category, pathEntryIds, sort, entriesByPaper]);

  // 条目定位：参数变化且详情已渲染时滚动并短暂高亮。
  useEffect(() => {
    if (!paperId || !entryId || !data) return;
    const el = document.getElementById(entryId);
    if (!el) return;
    el.scrollIntoView({ behavior: "smooth", block: "start" });
    el.classList.add("lr-highlight");
    const t = setTimeout(() => el.classList.remove("lr-highlight"), 1800);
    return () => clearTimeout(t);
  }, [paperId, entryId, data]);

  if (error) {
    return (
      <div className="page">
        <div className="header"><h1>文献学习库</h1></div>
        <div className="fund-errors">学习资料暂不可用：{(error as Error).message}（稍后重试；这不是资料缺失的结论）</div>
      </div>
    );
  }

  const stats = data?.stats;
  const integrityCount = stats
    ? stats.integrity.orphanEntryIds.length +
      stats.integrity.missingRelatedIds.length +
      stats.integrity.brokenPathIds.length
    : 0;
  const selected = paperId ? paperById.get(paperId) : undefined;

  return (
    <div className="page lib-page learning-page">
      <div className="header">
        <h1>文献学习库</h1>
        <span className="generated">
          {stats
            ? `${stats.papers} 篇文献 · ${stats.entries} 条学习内容 · ${stats.paths} 条学习路线 · 内容版本 ${data?.updated_at}`
            : "加载中…"}
        </span>
        <span className="spacer" />
        <span className="lr-purpose">从文献中学习研究方法与投资思考。</span>
      </div>

      {integrityCount > 0 && (
        <div className="lib-pending-tip">
          ⚠ 学习内容引用核对发现 {integrityCount} 处缺失（条目→论文 {stats?.integrity.orphanEntryIds.length ?? 0}、
          相关论文 {stats?.integrity.missingRelatedIds.length ?? 0}、路线→条目 {stats?.integrity.brokenPathIds.length ?? 0}）——
          请按 docs/literature-learning/README.md 修订内容文件，本页不做静默兜底。
        </div>
      )}

      <div className="lib-filters">
        <select value={pathId} onChange={(e) => setFilter({ path: e.target.value })} aria-label="学习路线">
          <option value="">全部（含学习路线）</option>
          {(data?.reading_paths ?? []).map((p) => (
            <option key={p.id} value={p.id}>{p.title}</option>
          ))}
        </select>
        <select value={category} onChange={(e) => setFilter({ cat: e.target.value })} aria-label="内容主题">
          <option value="">全部主题</option>
          {(data?.categories ?? []).map((c) => (
            <option key={c} value={c}>{c}（{stats?.byCategory[c] ?? 0}）</option>
          ))}
        </select>
        <select value={kind} onChange={(e) => setFilter({ kind: e.target.value })} aria-label="文献类型">
          <option value="">全部类型</option>
          {kindOptions.map((k) => (
            <option key={k.value} value={k.value}>{k.label}</option>
          ))}
        </select>
        <input
          className="lib-search"
          placeholder="搜条目 / 问题 / 作者 / 英文题名 / 学习正文…"
          value={q}
          onChange={(e) => setFilter({ q: e.target.value })}
        />
        <select value={sort} onChange={(e) => setFilter({ sort: e.target.value })} aria-label="排序">
          <option value="recommended">推荐顺序</option>
          <option value="year">年份（新→旧）</option>
        </select>
        <span className="count">{visible.length} 篇 / {visible.reduce((n, x) => n + x.entries.length, 0)} 条</span>
      </div>

      <div className="lib-layout">
        <div className="lib-list" aria-label="论文目录">
          {visible.map(({ paper, entries }) => (
            <div
              key={paper.id}
              className={`lr-card${paperId === paper.id ? " active" : ""}`}
              onClick={() => updateParams({ paper: paper.id, entry: null }, false)}
            >
              <div className="lr-card-head">
                <span className="lr-sel-label">{paper.selection_label}</span>
                <span className="lr-year">{paper.year}</span>
                <span className="lr-kind">{kindLabel(paper.publication_kind)}</span>
                <span className="count">{entries.length} 条</span>
              </div>
              <div className="lr-card-titles">
                {entries.map((e) => <span key={e.id} className="lr-entry-title">{e.title}</span>)}
              </div>
              <div className="lr-card-authors">
                {paper.authors.join(" / ")}{paper.venue ? ` · ${paper.venue}` : ""}
              </div>
              <div className="lr-card-entitle" lang="en">{paper.title}</div>
              <div className="lr-card-reading">阅读情况：{paper.reading_level}</div>
            </div>
          ))}
          {data && visible.length === 0 && <div className="lib-empty">没有匹配的文献——清空筛选或换关键词再试。</div>}
        </div>

        <div className="lib-reader">
          {paperId != null && !selected ? (
            <div className="lr-notfound">
              <p>未找到论文「{paperId}」——目录里没有这个编号，链接可能已失效。</p>
              <button className="btn small" onClick={() => updateParams({ paper: null, entry: null }, false)}>
                返回目录
              </button>
            </div>
          ) : selected ? (
            <PaperDetail
              paper={selected}
              entries={entriesByPaper.get(selected.id) ?? []}
              data={data!}
              onOpen={(pid, eid) => updateParams({ paper: pid, entry: eid ?? null }, false)}
              onBack={() => updateParams({ paper: null, entry: null }, false)}
            />
          ) : data ? (
            <Overview data={data} onOpenEntry={(eid) => {
              const e = entryById.get(eid);
              if (e) updateParams({ paper: e.paper_id, entry: eid }, false);
            }} />
          ) : (
            <div className="lib-empty">学习资料加载中…</div>
          )}
        </div>
      </div>
    </div>
  );
}

type LRow = { paper: LearningPaper; entries: LearningEntry[]; seedIdx: number; minPriority: number };

function PaperDetail({
  paper, entries, data, onOpen, onBack,
}: {
  paper: LearningPaper;
  entries: LearningEntry[];
  data: LearningResponse;
  onOpen: (paperId: string, entryId?: string) => void;
  onBack: () => void;
}) {
  const paperById = new Map(data.papers.map((p) => [p.id, p]));
  return (
    <div className="lr-detail">
      <div className="lr-detail-bar">
        <button className="btn small" onClick={onBack}>← 返回目录</button>
        <span className="lr-sel-label">{paper.selection_label}</span>
      </div>

      <section className="lr-block">
        <h2>这篇值得学什么</h2>
        <ol className="lr-index">
          {entries.map((e) => (
            <li key={e.id}>
              <a href={`#${e.id}`} onClick={(ev) => { ev.preventDefault(); onOpen(paper.id, e.id); }}>
                {e.title}
              </a>
              <span className="lr-index-q">——{e.question}</span>
            </li>
          ))}
        </ol>
      </section>

      <section className="lr-block lr-paperinfo">
        <h2>论文信息与阅读情况</h2>
        <div className="lr-paperinfo-grid">
          <span className="k">作者</span><span>{paper.authors.join(" / ")}（{paper.year}）</span>
          <span className="k">原题名</span><span lang="en">{paper.title}</span>
          <span className="k">载体</span>
          <span>{paper.venue ?? "—"} · {kindLabel(paper.publication_kind)} · 版本 {paper.read_version ?? "—"}</span>
          <span className="k">阅读情况</span><span>{paper.reading_level}</span>
          <span className="k">复现状态</span><span>{paper.replication_status}</span>
          <span className="k">内容核对</span><span>{paper.checked_at}</span>
          <span className="k">来源定位</span>
          <details className="lr-locator">
            <summary>展开查看</summary>
            <p>{paper.source_locator}</p>
          </details>
        </div>
        <div className="lr-links">
          {paper.source_url && <a href={paper.source_url} target="_blank" rel="noreferrer">原文 ↗</a>}
          {paper.doi && <a href={`https://doi.org/${paper.doi}`} target="_blank" rel="noreferrer">DOI ↗</a>}
          {paper.zotero_uri && (
            <a href={paper.zotero_uri} title={`Zotero 条目 ${paper.zotero_item_key ?? ""}`}>在 Zotero 中打开 ↗</a>
          )}
        </div>
      </section>

      {entries.map((e) => (
        <EntryArticle key={e.id} entry={e} paperById={paperById} onOpen={onOpen} />
      ))}
    </div>
  );
}

function EntryArticle({
  entry: e, paperById, onOpen,
}: {
  entry: LearningEntry;
  paperById: Map<string, LearningPaper>;
  onOpen: (paperId: string, entryId?: string) => void;
}) {
  const th = e.method_acceptance;
  return (
    <article id={e.id} className="lr-entry">
      <h3>
        {e.title}
        <span className="lr-cat">{e.category}</span>
        <span className={`lr-pri pri-${e.priority}`} title="编辑建议阅读顺序，不是收益得分">
          {e.priority === 1 ? "优先" : e.priority === 2 ? "延伸" : "有限材料"}
        </span>
      </h3>

      <div className="lr-sec"><span className="lr-label">要学会回答的问题</span><p>{e.question}</p></div>
      <div className="lr-sec"><span className="lr-label">作者研究了什么（转述摘要，非原文引用）</span><p>{e.author_finding_summary}</p></div>
      <div className="lr-sec">
        <span className="lr-label">我们从中学什么<em className="lr-tag ours">本库理解</em></span>
        <p>{e.our_learning}</p>
      </div>
      <div className="lr-sec">
        <span className="lr-label">一个好懂的例子<em className="lr-tag hypo">{e.example?.kind || "教学假设"}</em></span>
        <p>{e.example?.text}</p>
      </div>

      {e.practice_steps.length > 0 && (
        <div className="lr-sec">
          <span className="lr-label">应用步骤</span>
          <ol className="lr-list">{e.practice_steps.map((s, i) => <li key={i}>{s}</li>)}</ol>
        </div>
      )}
      <div className="lr-sec">
        <span className="lr-label">可以怎样检查<em className="lr-tag">{th?.origin?.startsWith("本库") ? "本库整理的检查建议" : "作者原方法"}</em></span>
        <ul className="lr-list">{(th?.checks ?? []).map((c, i) => <li key={i}>{c}</li>)}</ul>
        <p className="lr-threshold">
          {th?.paper_numeric_threshold != null
            ? `数值门槛：${th.paper_numeric_threshold}${th.threshold_note ? `——${th.threshold_note}` : ""}`
            : `数值门槛：${th?.threshold_note || "本条未提取已核实的数值标准，不设通用数字。"}`}
        </p>
      </div>
      <div className="lr-sec"><span className="lr-label">适用条件与不能推出的结论</span><p>{e.applicability}</p></div>

      <div className="lr-sec lr-sec-links">
        <span className="lr-label">关联</span>
        <div className="lr-links">
          {e.related_paper_ids.map((rid) => {
            const rp = paperById.get(rid);
            return rp ? (
              <a key={rid} href={`#/learning`} onClick={(ev) => { ev.preventDefault(); onOpen(rid); }}>
                相关文献：{rp.selection_label}（{rp.year}）↗
              </a>
            ) : (
              <span key={rid} className="lr-missing">相关文献 {rid} 不在库内</span>
            );
          })}
          {e.local_research_path && e.local_research_available && (
            <a href={`/library?report=${encodeURIComponent(e.local_research_path)}`}>本地研究报告 ↗</a>
          )}
          {e.local_research_path && !e.local_research_available && (
            <span className="lr-missing">链接的本地报告暂缺（{e.local_research_path}）</span>
          )}
        </div>
        <p className="lr-footnote">{e.system_relation}（{e.adoption_status}；{e.content_status}）</p>
      </div>

      <details className="lr-quiz">
        <summary>自测：{e.review_question}</summary>
        <p>{e.answer_hint}</p>
      </details>
    </article>
  );
}

function Overview({ data, onOpenEntry }: { data: LearningResponse; onOpenEntry: (entryId: string) => void }) {
  const entryById = new Map(data.entries.map((e) => [e.id, e]));
  return (
    <div className="lr-overview">
      {/* 用途说明用页面固定文案；seed.purpose 是内容维护备注，不面向用户展示。 */}
      <p className="lr-overview-lead">从文献中学习研究方法与投资思考。</p>
      <section className="lr-block">
        <h2>学习路线（编辑建议的阅读顺序）</h2>
        {data.reading_paths.map((p, i) => (
          <div key={p.id} className="lr-path">
            <div className="lr-path-title">{i + 1}. {p.title}</div>
            <ol className="lr-index">
              {p.entry_ids.map((eid) => {
                const e = entryById.get(eid);
                if (!e) return <li key={eid} className="lr-missing">路线引用的条目 {eid} 不在库内</li>;
                return (
                  <li key={eid}>
                    <a href={`#${eid}`} onClick={(ev) => { ev.preventDefault(); onOpenEntry(eid); }}>{e.title}</a>
                    <span className="lr-index-q">——{e.question}</span>
                  </li>
                );
              })}
            </ol>
          </div>
        ))}
        <p className="lr-footnote">路线只是编辑建议的顺序，不代表其他文献没有价值。</p>
      </section>
      <section className="lr-block">
        <h2>使用边界</h2>
        <ul className="lr-list">
          <li>「方法已在某次研究采用」不等于「策略已被验证有效」；本库不提供一键采用参数、修改交易规则或启动实验的按钮。</li>
          <li>第一版只读浏览：无登录、无学习进度存储、无收藏；Zotero 未打开时中文内容照常可读。</li>
          <li>链接只通向：论文原文（HTTPS）、本系统报告、Zotero 对应条目。</li>
          <li>假设例子有明显文字标注，与真实回测严格分开；未提取的数值门槛显示「未提取」，不显示为 0 或已通过。</li>
        </ul>
      </section>
    </div>
  );
}
