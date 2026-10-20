import { useState } from "react";
import type { TraceItem } from "../types";

/**
 * 溯源角标：默认只显示 ⓘ，点开浮层显示 rule_id / 研究代理 / 证据 / 规格引用。
 * 用户视角默认看不到工程信息；红线（可展开获得）不破。
 */
export default function ProvenanceBadge({ items }: { items: TraceItem[] }) {
  const [open, setOpen] = useState(false);
  if (items.length === 0) return null;
  return (
    <span className="prov-badge-wrap">
      <button
        className="prov-badge"
        title="溯源信息"
        onClick={() => setOpen((v) => !v)}
      >
        ⓘ
      </button>
      {open && (
        <div className="prov-popover">
          {items.map((t, i) => (
            <div key={i} className="prov-item">
              <div>{t.label}</div>
              {t.rule_id && <div className="muted">rule_id: {t.rule_id}</div>}
              {t.evidence_cn && <div className="muted">证据: {t.evidence_cn}</div>}
              <div className="muted">
                {t.principle_source ? `${t.principle_source} | ` : ""}
                {t.research_proxy ? "判定方式为研究代理" : ""}
              </div>
            </div>
          ))}
        </div>
      )}
    </span>
  );
}
