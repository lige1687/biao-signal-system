import { createContext, useContext, type ReactNode } from "react";
import { Link } from "react-router-dom";

export const ResultContext = createContext<{
  inspectSymbol?: (symbol: string) => void;
  ask?: (message: string) => void;
  readOnly?: boolean;
}>({});

/** 同一份结果可用于独立页面或对话；对话内看图不丢失当前会话。 */
export function ResultSymbol({ symbol, children }: { symbol: string; children: ReactNode }) {
  const { inspectSymbol } = useContext(ResultContext);
  return inspectSymbol
    ? <button type="button" className="cp-sym ar-symbol-link" onClick={() => inspectSymbol(symbol)} title="在工作台查看图表">{children}</button>
    : <Link to={`/symbol/${encodeURIComponent(symbol)}`} className="cp-sym">{children}</Link>;
}
