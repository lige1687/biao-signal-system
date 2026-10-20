import type { ReactNode } from "react";
import { bpLocatable, findPriceMentions, type AgentPriceLevel } from "./agent/priceLinks";

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
  priceLevels: AgentPriceLevel[] = [],
  onPrice?: (level: AgentPriceLevel) => void,
): ReactNode[] {
  const mentions = onPrice ? findPriceMentions(text, priceLevels) : [];
  const plain = (fragment: string, offset: number): ReactNode => {
    const parts: ReactNode[] = [];
    let cursor = 0;
    for (const mention of mentions) {
      const from = mention.start - offset, to = mention.end - offset;
      if (from < 0 || to > fragment.length) continue;
      parts.push(fragment.slice(cursor, from));
      parts.push(<button key={mention.start} type="button" className="ar-price-link" onClick={() => onPrice?.(mention.level)} aria-label={`${mention.level.role} ${mention.level.price}，在图上定位`} title={`系统价位 · ${mention.level.from_cn}`}>{fragment.slice(from, to)}<span aria-hidden="true"> ↗</span></button>);
      cursor = to;
    }
    parts.push(fragment.slice(cursor));
    return parts;
  };
  // 同时匹配三种行内元素；用捕获组区分类型
  const re = /(\*\*([^*]+)\*\*)|(`([^`]+)`)|(买点\s*([①②③④⑤⑥⑦⑧⑨⑩]|[1-9][0-9]?|一|二|三|四|五|六|七|八|九|十))/g;
  const out: ReactNode[] = [];
  let last = 0;
  let key = 0;
  for (const m of text.matchAll(re)) {
    const start = m.index ?? 0;
    if (start > last) out.push(plain(text.slice(last, start), last));
    if (m[2] != null) {
      out.push(<strong key={`b${key++}`}>{plain(m[2], start + 2)}</strong>);
    } else if (m[4] != null) {
      out.push(<code key={`c${key++}`} className="md-code">{plain(m[4], start + 1)}</code>);
    } else if (m[5] != null) {
      const idx = parseBpIndex(m[6]);
      if (bpLocatable(idx, notableCount)) {
        out.push(
          <button
            key={`bp${key++}`}
            className="bp-inline"
            onClick={() => onBp(idx!)}
            title="点击在图上定位该买点（系统候选）"
          >
            买点{circled(idx!)}
          </button>,
        );
      } else {
        // 没有对应的系统候选数据：渲染为普通文字，不是点击无反应的假按钮。
        out.push(
          <span
            key={`bp${key++}`}
            className="bp-inline dim"
            title="本条回复没有对应的系统候选数据，无法定位"
          >
            买点{circled(idx ?? 0)}
          </span>,
        );
      }
    }
    last = start + m[0].length;
  }
  if (last < text.length) out.push(plain(text.slice(last), last));
  return out;
}

/**
 * 极简 markdown 渲染：只覆盖表达层 LLM 实际会输出的结构
 *（标题 ##/###/####、分割线 ---、无序列表 -、引用 >、加粗、代码、买点① chip）。
 * 不引第三方依赖；表格/嵌套等复杂语法不在表达层输出范围内。
 *
 * 「买点①」只有调用方能证明序号与候选绑定（notableCount 覆盖，且候选就是
 * 这段文字所指的候选）时才渲染成可点 chip——目前只有买点分析抽屉满足
 * （打开即取当次审阅，对话与同一份审阅锚定）。其余上下文（工作台、控制台）
 * 传 notableCount=0：渲染为普通文字（暗态），不留假按钮。
 */
export default function AgentMarkdown({
  text,
  onBp,
  notableCount,
  priceLevels = [],
  onPrice,
}: {
  text: string;
  onBp: (index: number) => void;
  notableCount: number;
  priceLevels?: AgentPriceLevel[];
  onPrice?: (level: AgentPriceLevel) => void;
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
      const content = renderInline(h[2], onBp, notableCount, priceLevels, onPrice);
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
          {renderInline(quoteLines.join(" "), onBp, notableCount, priceLevels, onPrice)}
        </blockquote>,
      );
      continue;
    }

    // 无序列表
    if (/^[-*+]\s+/.test(trimmed)) {
      const items: ReactNode[] = [];
      while (i < lines.length && /^[-*+]\s+/.test(lines[i].trim())) {
        const item = lines[i].trim().replace(/^[-*+]\s+/, "");
        items.push(<li key={items.length}>{renderInline(item, onBp, notableCount, priceLevels, onPrice)}</li>);
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
        items.push(<li key={items.length}>{renderInline(item, onBp, notableCount, priceLevels, onPrice)}</li>);
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
    blocks.push(<p key={key++} className="md-p">{renderInline(para.join(" "), onBp, notableCount, priceLevels, onPrice)}</p>);
  }

  return <div className="md-body">{blocks}</div>;
}
