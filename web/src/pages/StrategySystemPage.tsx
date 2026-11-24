import { useEffect, useMemo, useRef, useState } from "react";
import type { CSSProperties } from "react";
import { useQuery } from "@tanstack/react-query";
import { Link, useSearchParams } from "react-router-dom";
import { marked } from "marked";
import DOMPurify from "dompurify";
import { strategyDocumentsApi } from "../api/client";
import { normalizeSelectedDocumentId, normalizeStrategyMarkdown, strategyReadingParams, RESEARCH_EXTENSIONS } from "./strategySystemLogic";
import type { StrategyDocumentHeading } from "../types";
import "./strategy-system.css";

const sourceLabels = {
  confirmed: "已确认来源",
  unchanged: "与接入时文件一致（研究参考）",
  changed: "源文件已变化，尚未确认",
  missing: "源文件缺失",
};

export default function StrategySystemPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const section = searchParams.get("section");
  const guide = searchParams.get("collection") === "factor-guide";
  const [activeHeading, setActiveHeading] = useState("");
  const [copyStatus, setCopyStatus] = useState("");
  const [readingOffset, setReadingOffset] = useState(110);
  const clickedSectionRef = useRef<string | null>(null);
  const articleRef = useRef<HTMLElement>(null);
  const mobileTocRef = useRef<HTMLDetailsElement>(null);
  const listQuery = useQuery({
    queryKey: ["strategy-documents", guide], queryFn: () => strategyDocumentsApi.list(guide), staleTime: 60_000, retry: false,
  });
  const ids = listQuery.data?.documents.map((item) => item.id) ?? [];
  const selectedId = normalizeSelectedDocumentId(searchParams.get("doc"), ids);
  const summary = listQuery.data?.documents.find((item) => item.id === selectedId);
  const detailQuery = useQuery({
    queryKey: ["strategy-document", guide, selectedId],
    queryFn: () => strategyDocumentsApi.detail(selectedId!, guide),
    enabled: selectedId != null, staleTime: 60_000, retry: false,
  });
  const detail = detailQuery.data;
  const source = detail ?? summary;
  const html = useMemo(() => {
    if (!detail) return "";
    // 桌面原文的部分表格在每行间有空行；仅在展示时连起表格行，不改源正文。
    const markdown = normalizeStrategyMarkdown(detail.markdown);
    return DOMPurify.sanitize(marked.parse(markdown, { async: false }) as string, {
      // 不执行原文 HTML；保留 Markdown 的标题、表格、列表、代码与链接。
      USE_PROFILES: { html: true }, FORBID_TAGS: ["style", "form", "input", "button", "iframe"],
      FORBID_ATTR: ["style", "id", "name"],
    });
  }, [detail]);

  useEffect(() => {
    const nav = document.querySelector(".top-nav");
    if (!nav) return;
    const measure = () => setReadingOffset(Math.ceil(nav.getBoundingClientRect().height) + 24);
    const observer = new ResizeObserver(measure);
    measure(); observer.observe(nav);
    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (selectedId && searchParams.get("doc") !== selectedId) {
      const next = new URLSearchParams(searchParams);
      next.set("doc", selectedId);
      setSearchParams(next, { replace: true });
    }
  }, [selectedId, searchParams, setSearchParams]);

  // 每份正文使用后端生成的锚点；目录、复制链接、刷新与前进后退共用同一身份。
  useEffect(() => {
    const article = articleRef.current;
    if (!article || !detail) return;
    const headings = Array.from(article.querySelectorAll<HTMLElement>("h1,h2,h3"));
    headings.forEach((node, index) => {
      const heading = detail.headings[index];
      if (!heading) return;
      node.id = heading.id;
      const link = document.createElement("a");
      link.className = "strategy-heading-link";
      link.textContent = "#";
      link.setAttribute("aria-label", `复制章节链接：${heading.text}`);
      link.href = `/strategy?${strategyReadingParams(detail.id, guide, heading.id)}`;
      node.appendChild(link);
    });
    setActiveHeading(detail.headings[0]?.id ?? "");
    // 在回调之间保存所有可见标题，避免只看本次变化的标题导致高亮跳动。
    const visible = new Set<Element>();
    const observer = new IntersectionObserver((entries) => {
      entries.forEach((entry) => {
        if (entry.isIntersecting) visible.add(entry.target);
        else visible.delete(entry.target);
      });
      const first = [...visible].sort((a, b) =>
        a.getBoundingClientRect().top - b.getBoundingClientRect().top)[0];
      if (first?.id) setActiveHeading(first.id);
    }, { rootMargin: `-${readingOffset}px 0px -70% 0px`, threshold: [0, 1] });
    headings.forEach((node) => observer.observe(node));
    // 长章节滚动时保留当前章；向上滚回章节之间时也能正确切换。
    let frame = 0;
    const trackPosition = () => {
      if (frame) return;
      frame = requestAnimationFrame(() => {
        frame = 0;
        const current = headings.filter((node) => node.id && node.getBoundingClientRect().top <= readingOffset + 10).slice(-1)[0];
        if (current) setActiveHeading(current.id);
      });
    };
    window.addEventListener("scroll", trackPosition, { passive: true });
    return () => {
      observer.disconnect();
      window.removeEventListener("scroll", trackPosition);
      cancelAnimationFrame(frame);
      // 查询刷新但 HTML 相同时，防止重复添加复制链接。
      article.querySelectorAll(".strategy-heading-link").forEach((node) => node.remove());
    };
  }, [detail, html, readingOffset, guide]);

  useEffect(() => {
    if (!detail || !articleRef.current) return;
    if (clickedSectionRef.current === section) {
      clickedSectionRef.current = null;
      return;
    }
    const target = Array.from(articleRef.current.querySelectorAll<HTMLElement>("h1,h2,h3"))
      .find((node) => node.id === section);
    if (!target) return;
    const frame = requestAnimationFrame(() => {
      target.scrollIntoView({ behavior: "auto", block: "start" });
      setActiveHeading(target.id);
    });
    return () => cancelAnimationFrame(frame);
  }, [detail, html, section, readingOffset]);

  function goToSection(heading: StrategyDocumentHeading) {
    if (!selectedId) return;
    const target = Array.from(articleRef.current?.querySelectorAll<HTMLElement>("h1,h2,h3") ?? [])
      .find((node) => node.id === heading.id);
    mobileTocRef.current?.removeAttribute("open");
    clickedSectionRef.current = heading.id;
    setSearchParams(strategyReadingParams(selectedId, guide, heading.id));
    target?.scrollIntoView({
      behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
      block: "start",
    });
    setActiveHeading(heading.id);
  }

  const toc = <ul>{detail?.headings.map((heading) => <li key={heading.id} data-level={heading.level}>
    <a href={`?${strategyReadingParams(selectedId!, guide, heading.id)}`}
      aria-current={activeHeading === heading.id ? "location" : undefined}
      onClick={(event) => { event.preventDefault(); goToSection(heading); }}>{heading.text}</a>
  </li>)}</ul>;

  return <main className="strategy-page"
    style={{ "--strategy-scroll-offset": `${readingOffset}px` } as CSSProperties}>
    <header className="strategy-header">
      <div><p className="strategy-eyebrow">LEI · {guide ? "只读研究资料" : "只读交易手册"}</p><h1>技术体系</h1></div>
      <nav className="strategy-document-tabs" aria-label="选择阅读资料">
        {[
          { label: "交易体系", id: "technical-system", guide: false },
          { label: "实现规范", id: "technical-implementation", guide: false },
          { label: "因子指南包", id: "research-guide", guide: true },
        ].map((item) => <button key={item.id} type="button"
          aria-pressed={item.guide === guide && (guide || selectedId === item.id)} onClick={() => {
            setCopyStatus(""); setActiveHeading("");
            setSearchParams(strategyReadingParams(item.id, item.guide));
            window.scrollTo({ top: 0, behavior: "auto" });
          }}>{item.label}</button>)}
      </nav>
      {source && <p className="strategy-source-status">
        {detailQuery.isError && detail ? "读取失败，显示上次成功读取的内容" : (guide && source.approvalStatus === "changed" ? "指南文件已变化" : sourceLabels[source.approvalStatus])}<br />
        <span>更新时间：{source.modifiedAt ? new Date(source.modifiedAt).toLocaleString("zh-CN") : "不可用"}</span>
      </p>}
    </header>
    {guide && <section className="strategy-guide-intro" aria-label="因子指南包说明">
      <p>研究指南、候选注册表与模板。候选登记和研究优先级不代表已验证、已实现或获准交易。
        指导包不替代两份权威技术文档；接入时指纹只用于识别文件变化。</p>
      <Link to="/factors">查看已接入研究结果</Link>
      <label htmlFor="strategy-guide-document">包内资料</label>
      <select id="strategy-guide-document" value={selectedId ?? ""} disabled={!ids.length}
        onChange={(event) => {
          setCopyStatus(""); setActiveHeading("");
          setSearchParams(strategyReadingParams(event.target.value, true));
          window.scrollTo({ top: 0, behavior: "auto" });
        }}>
        {listQuery.data?.documents.map((item) => <option key={item.id} value={item.id}>
          {item.title}{item.available ? "" : "（文件缺失）"}
        </option>)}
      </select>
    </section>}
    {listQuery.isPending && <p role="status">正在读取资料索引…</p>}
    {listQuery.isError && <p className="strategy-source-alert" role="alert">{listQuery.error.message}</p>}
    {source?.approvalStatus === "changed" && <div className="strategy-source-alert" role="alert">
      {guide ? "指南文件与接入时记录不同。当前内容可只读查阅，变化不代表新增研究或交易授权。"
        : "源文件已变化，尚未确认。当前内容可以阅读，但不能据此扩大或缩小因子研究范围。"}
    </div>}
    {source && <section className="strategy-provenance" aria-label="来源与职责">
      <p><strong>{source.title}</strong> · {source.role} · {sourceLabels[source.approvalStatus]} · 更新时间：{source.modifiedAt ? new Date(source.modifiedAt).toLocaleString("zh-CN") : "不可用"}</p>
      <details><summary>查看来源路径与指纹</summary><dl>
        <dt>真实路径</dt><dd>{source.path}</dd>
        <dt>当前 SHA-256</dt><dd>{source.currentSha256 ?? "源文件缺失，无法计算"}</dd>
        <dt>{guide ? "接入时 SHA-256" : "已确认 SHA-256"}</dt><dd>{guide ? source.baseline_sha256 : source.approved_sha256}</dd>
        <dt>{guide ? "接入日期" : "确认日期"}</dt><dd>{guide ? source.recorded_at : source.confirmed_at}</dd>
      </dl></details>
    </section>}
    {detailQuery.isFetching && !detail && selectedId && <p role="status">正在读取文档…</p>}
    {detailQuery.isError && <div className="strategy-source-alert" role="alert">
      <p>{detailQuery.error.message}</p>
      {detail && <p>当前正文、指纹和时间为上次成功读取的记录，尚未核对当前源文件。</p>}
      <p>请检查读取权限，并将 UTF-8 原文恢复到登记路径：{summary?.path}。恢复后重新读取。</p>
      <button type="button" onClick={() => { void listQuery.refetch(); void detailQuery.refetch(); }}>重新读取</button>
    </div>}
    {detail && <div className="strategy-reader-layout">
      <nav className="strategy-toc" aria-label="本文章节"><h2>章节目录</h2>{toc}</nav>
      <details className="strategy-mobile-toc" ref={mobileTocRef}>
        <summary>章节目录</summary><nav aria-label="本文章节（窄屏）">{toc}</nav>
      </details>
      <article ref={articleRef} className="strategy-markdown" dangerouslySetInnerHTML={{ __html: html }}
        onClick={(event) => {
          const link = (event.target as HTMLElement).closest<HTMLAnchorElement>("a.strategy-heading-link");
          if (!link) return;
          event.preventDefault();
          const url = new URL(link.href);
          const heading = detail.headings.find((item) => item.id === url.searchParams.get("section"));
          if (heading) goToSection(heading);
          void navigator.clipboard?.writeText(url.href).then(() => setCopyStatus("章节链接已复制"))
            .catch(() => setCopyStatus("可从地址栏复制章节链接"));
          if (!navigator.clipboard) setCopyStatus("可从地址栏复制章节链接");
        }} />
    </div>}
    <p className="strategy-copy-status" role="status" aria-live="polite">{copyStatus}</p>
    <section className="strategy-extensions" aria-labelledby="strategy-extensions-title">
      <h2 id="strategy-extensions-title">研究扩展与范围导航</h2>
      <p>这些入口用于查阅研究范围。已有原文定义也需要证据，研究入口不代表获准交易。</p>
      <div>{RESEARCH_EXTENSIONS.map((item) => <div className="strategy-extension" key={item.id}>
        <h3><Link to={item.to}>{item.name} <span aria-hidden="true">↗</span></Link></h3>
        <p>{item.plainDefinition}</p><p className="strategy-extension-class">{item.sourceClass}</p>
        <p className="strategy-extension-status">{item.status}</p>
      </div>)}</div>
    </section>
  </main>;
}
