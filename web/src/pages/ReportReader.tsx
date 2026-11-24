import type { ReactNode } from "react";
import type { ExperimentReportDetail } from "../types";

export default function ReportReader({ selected, report, loading, error, children, onBack }: {
  selected: string | null; report?: ExperimentReportDetail; loading: boolean; error: unknown;
  children?: ReactNode; onBack: () => void;
}) {
  if (!selected) return <div className="lib-empty">← 点左侧任意报告阅读全文。</div>;
  return <section aria-label="所选报告正文">
    <button type="button" className="lib-reader-back" onClick={onBack}>← 返回报告列表</button>
    {loading ? <p role="status">正在加载所选报告正文…</p>
      : error ? <p role="alert" className="fund-errors">报告正文加载失败：{error instanceof Error ? error.message : String(error)}。可返回列表重新选择。</p>
      : report?.name === selected ? children
      : <p role="alert">所选报告尚未返回对应正文，请返回列表核对报告身份。</p>}
  </section>;
}
