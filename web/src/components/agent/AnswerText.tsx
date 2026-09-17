import type { ReactNode } from "react";
import { replyPreview } from "../../pages/agentWorkspaceLogic";

/**
 * UX 第一期（2026-09-13）：回答正文的首屏/收起展示（两入口共用）。
 * - 首屏只显示第一段结论（lead），其余收进"查看完整分析与依据详情"；
 * - 收起阈值 650 字符沿用既有工作台口径；expanded=true 时不折叠
 *   （"查看依据详情"动作展开本回答）；
 * - 只拆原文段落，绝不改写或推断结论。
 * UX 第二轮（2026-09-17）：新增 middle 插槽——系统价位卡插在结论与正文
 * 之间，形成「结论 → 系统价位与条件 → 完整分析（可展开）→ 依据卡」层级；
 * 不传时行为与原来完全一致。正文没有可拆的结论段时，价位卡仍排在正文
 * 之后，避免把系统资料压在回答前面。
 */
export default function AnswerText({ text, markdown, expanded = false, middle }: {
  text: string;
  markdown: (t: string) => ReactNode;
  expanded?: boolean;
  middle?: ReactNode;
}) {
  const full = text || "";
  const { lead, rest } = replyPreview(full);
  if (!full) return middle ?? null;
  if (lead) {
    return (
      <>
        <div className="ar-lead">{markdown(lead)}</div>
        {middle}
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
  return (
    <>
      <div className="ar-body">{markdown(full)}</div>
      {middle}
    </>
  );
}
