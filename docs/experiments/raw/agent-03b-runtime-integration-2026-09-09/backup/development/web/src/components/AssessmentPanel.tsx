import type { Assessment } from "../types";
import ColorBadge from "./ColorBadge";

interface Props {
  assessment: Assessment;
  /** 点击颜色/阶段/风险徽章时，请求右侧面板展示对应概念解释。 */
  onPickConcept?: (conceptKey: string, sourceCn: string) => void;
}

/** 当前观察：颜色 / 阶段 / 风险 / 支持 / 冲突 / 风险提示。 */
export default function AssessmentPanel({ assessment: a, onPickConcept }: Props) {
  const isRisk = a.risk_state !== "normal";
  const clickable = (key: string, src: string) =>
    onPickConcept
      ? { onClick: () => onPickConcept(key, src), style: { cursor: "pointer" }, title: "点击查看解释" }
      : {};
  return (
    <div className="panel">
      <h3>当前观察（{a.as_of}）</h3>
      <div className="assessment-grid">
        <div className="item" {...clickable("signal_color", "当前观察 · LEI 颜色")}>
          <div className="label">LEI 颜色</div>
          <ColorBadge color={a.color} colorCn={a.color_cn} />
        </div>
        <div className="item" {...clickable("stage", "当前观察 · 机会阶段")}>
          <div className="label">机会阶段</div>
          <span className="stage-chip">{a.opportunity_stage_cn}</span>
        </div>
        <div className="item" {...clickable("risk_state", "当前观察 · 风险状态")}>
          <div className="label">风险状态</div>
          <span className={`stage-chip ${isRisk ? "risky" : ""}`}>{a.risk_state_cn}</span>
        </div>
        <div className="item">
          <div className="label">双均线共同确认</div>
          <span>{a.joint_confirmed_now ? "是" : "否"}</span>
        </div>
      </div>

      {a.stage_change_reason_cn && (
        <div className="stage-reason">{a.stage_change_reason_cn}</div>
      )}

      {Object.keys(a.dimensions).length > 0 && (
        <div style={{ marginTop: 12 }}>
          {Object.entries(a.dimensions).map(([k, v]) => (
            <span key={k} className="stage-chip" style={{ marginRight: 8 }}>
              {k}: {v}
            </span>
          ))}
        </div>
      )}

      <div className="two-col" style={{ marginTop: 14 }}>
        <div>
          <div className="label" style={{ color: "var(--text-faint)", fontSize: 12, marginBottom: 6 }}>
            支持因素
          </div>
          {a.supports.length === 0 ? (
            <div className="muted">无</div>
          ) : (
            <ul className="factor-list">
              {a.supports.map((f, i) => (
                <li key={i}>
                  <span className="dim">{f.dimension}</span>
                  <b>{f.label_cn}</b> — {f.detail_cn}
                </li>
              ))}
            </ul>
          )}
        </div>
        <div>
          <div className="label" style={{ color: "var(--text-faint)", fontSize: 12, marginBottom: 6 }}>
            冲突因素
          </div>
          {a.conflicts.length === 0 ? (
            <div className="muted">无</div>
          ) : (
            <ul className="factor-list conflicts">
              {a.conflicts.map((f, i) => (
                <li key={i}>
                  <span className="dim">{f.dimension}</span>
                  <b>{f.label_cn}</b> — {f.detail_cn}
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {a.risks.length > 0 && (
        <div style={{ marginTop: 14 }}>
          <div className="label" style={{ color: "var(--text-faint)", fontSize: 12, marginBottom: 6 }}>
            风险提示
          </div>
          <ul className="factor-list risk-list">
            {a.risks.map((r, i) => (
              <li key={i}>
                <b>{r.label_cn}</b> — {r.detail_cn}
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}
