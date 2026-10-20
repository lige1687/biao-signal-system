import type { ReactNode } from "react";
import { replyPreview } from "../../pages/agentWorkspaceLogic";

/**
 * UX 第一期（2026-09-13）：回答正文的首屏/收起展示（两入口共用）。
 * - 首屏只显示第一段结论（lead），其余收进"查看完整分析与依据详情"；
 * - 收起阈值 650 字符沿用既有工作台口径；expanded=true 时不折叠
 *   （"查看依据详情"动作展开本回答）；
 * - 只拆原文段落，绝不改写或推断结论。
 */
export default function AnswerText({ text, markdown, expanded = false }: {
  text: string;
  markdown: (t: string) => ReactNode;
  expanded?: boolean;
}) {
  const full = text || "";
  const { lead, rest } = replyPreview(full);
  if (!full) return null;
  if (lead) {
    return (
      <>
        <div className="ar-lead">{markdown(lead)}</div>
        {rest
          ? (expanded || rest.length < 650
              ? <div className="ar-body">{markdown(rest)}</div>
              : <details className="ar-details">
                  <summary>查看完整分析与依据详情</summary>
                  <div className="ar-body">{markdown(rest)}</div>
                </details>)
          : null}
      </>
    );
  }
  return <div className="ar-body">{markdown(full)}</div>;
}
