import type { ReactNode } from "react";

interface Props {
  tip: string;
  children: ReactNode;
}

/**
 * 术语悬浮解释：鼠标悬停显示「人话」说明。
 * 文案唯一来源是后端 /api/backtest/options 的 glossary（与 explanations.py
 * 「文案集中在后端」的项目惯例一致），前端不另写一套。
 */
export default function InfoTip({ tip, children }: Props) {
  return (
    <span className="bt-tip" tabIndex={0}>
      {children}
      <span className="bt-tip-icon" aria-hidden>
        ?
      </span>
      <span className="bt-tip-pop" role="tooltip">
        {tip}
      </span>
    </span>
  );
}
