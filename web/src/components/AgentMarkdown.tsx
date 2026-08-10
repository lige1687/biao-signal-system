import type { ReactNode } from "react";

/** 圆圈数字，与 BuyPointDrawer 一致。 */
const CIRCLED = "①②③④⑤⑥⑦⑧⑨⑩";
function circled(n: number): string {
  return CIRCLED[n] ?? String(n + 1);
}

/** 把匹配到的序号 token 转成 0 起的候选下标。 */
function parseBpIndex(token: string): number | null {
  const ci = CIRCLED.indexOf(token);
  if (ci >= 0) return ci;
  const cni = "一二三四五六七八九十".indexOf(token);
  if (cni >= 0) return cni;
  const n = Number(token);
  if (Number.isInteger(n) && n >= 1) return n - 1;
  return null;
}

/** 行内解析：**加粗** / `代码` / 买点①可点 chip，其余为纯文本。 */
function renderInline(
  text: string,
  onBp: (index: number) => void,
  notableCount: number,
): ReactNode[] {
  // 同时匹配三种行内元素；用捕获组区分类型
  const re = /(\*\*([^*]+)\*\*)|(`([^`]+)`)|(买点\s*([①②③④⑤⑥⑦⑧⑨⑩]|[1-9][0-9]?|一|二|三|四|五|六|七|八|九|十))/g;
  const out: ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const m of text.matchAll(re)) {
    const start = m.index ?? 0;
    if (start > last) out.push(text.slice(last, start));
    if (m[2] != null) {
      out.push(<strong key={`b${key++}`}>{m[2]}</strong>);
    } else if (m[4] != null) {
      out.push(<code key={`c${key++}`} className="md-code">{m[4]}</code>);
    } else if (m[5] != null) {
      const idx = parseBpIndex(m[6]);
      const inRange = idx != null && idx < notableCount;
      out.push(
        <button
          key={`bp${key++}`}
          className={`bp-inline ${inRange ? "" : "dim"}`}
          onClick={() => inRange && idx != null && onBp(idx)}
          title={inRange ? "点击在图上高亮该买点" : "无对应候选"}
        >
          买点{circled(idx ?? 0)}
        </button>,
      );
    }
    last = start + m[0].length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

/**
 * 极简 markdown 渲染：只覆盖表达层 LLM 实际会输出的结构
 *（标题 ##/###/####、分割线 ---、无序列表 -、引用 >、加粗、代码、买点① chip）。
 * 不引第三方依赖；表格/嵌套等复杂语法不在表达层输出范围内。
 *
 * 「买点①」仍渲染成可点 chip，点了联动主图与卡片（双向高亮不丢）。
 */
export default function AgentMarkdown({
  text,
  onBp,
  notableCount,
}: {
  text: string;
  onBp: (index: number) => void;
  notableCount: number;
}) {
  const lines = text.split("\n");
  const blocks: ReactNode[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];
    const trimmed = line.trim();

    // 空行：跳过（段落分隔）
    if (trimmed === "") {
      i++;
      continue;
    }

    // 分割线
    if (/^-{3,}$|^\*{3,}$|^_{3,}$/.test(trimmed)) {
      blocks.push(<hr key={key++} className="md-hr" />);
      i++;
      continue;
    }

    // 标题
    const h = /^(#{1,6})\s+(.*)$/.exec(trimmed);
    if (h) {
      const level = h[1].length;
      const content = renderInline(h[2], onBp, notableCount);
      if (level <= 2) {
        blocks.push(<h4 key={key++} className="md-h2">{content}</h4>);
      } else if (level === 3) {
        blocks.push(<h5 key={key++} className="md-h3">{content}</h5>);
      } else {
        blocks.push(<h6 key={key++} className="md-h4">{content}</h6>);
      }
      i++;
      continue;
    }

    // 引用
    if (/^>\s?/.test(trimmed)) {
      const quoteLines: string[] = [];
      while (i < lines.length && /^>\s?/.test(lines[i].trim())) {
        quoteLines.push(lines[i].trim().replace(/^>\s?/, ""));
        i++;
      }
      blocks.push(
        <blockquote key={key++} className="md-quote">
          {renderInline(quoteLines.join(" "), onBp, notableCount)}
        </blockquote>,
      );
      continue;
    }

    // 无序列表
    if (/^[-*+]\s+/.test(trimmed)) {
      const items: ReactNode[] = [];
      while (i < lines.length && /^[-*+]\s+/.test(lines[i].trim())) {
        const item = lines[i].trim().replace(/^[-*+]\s+/, "");
        items.push(<li key={items.length}>{renderInline(item, onBp, notableCount)}</li>);
        i++;
      }
      blocks.push(<ul key={key++} className="md-ul">{items}</ul>);
      continue;
    }

    // 有序列表
    if (/^\d+[.、]\s+/.test(trimmed)) {
      const items: ReactNode[] = [];
      while (i < lines.length && /^\d+[.、]\s+/.test(lines[i].trim())) {
        const item = lines[i].trim().replace(/^\d+[.、]\s+/, "");
        items.push(<li key={items.length}>{renderInline(item, onBp, notableCount)}</li>);
        i++;
      }
      blocks.push(<ol key={key++} className="md-ol">{items}</ol>);
      continue;
    }

    // 段落：连续非空、非特殊行合成一段
    const para: string[] = [];
    while (
      i < lines.length &&
      lines[i].trim() !== "" &&
      !/^(#{1,6})\s+/.test(lines[i].trim()) &&
      !/^[-*+]\s+/.test(lines[i].trim()) &&
      !/^\d+[.、]\s+/.test(lines[i].trim()) &&
      !/^>\s?/.test(lines[i].trim()) &&
      !/^-{3,}$/.test(lines[i].trim())
    ) {
      para.push(lines[i].trim());
      i++;
    }
    blocks.push(<p key={key++} className="md-p">{renderInline(para.join(" "), onBp, notableCount)}</p>);
  }

  return <div className="md-body">{blocks}</div>;
}
