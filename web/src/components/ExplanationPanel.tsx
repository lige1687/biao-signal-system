import type { EventItem, Explanation, StructureBrief } from "../types";

/** 右侧解释面板要展示的一次「选中」。 */
export interface Selection {
  /** 面板标题上方的小字：这是从图上哪种标记点进来的 */
  source: string;
  /** 图上该标记对应的日期（用于「发生于」一行） */
  date?: string;
  price?: number;
  explanation: Explanation | null;
  structure?: StructureBrief | null;
  /** B1 线专属：该前高的摆动日与当前距离 */
  b1PivotDate?: string;
  b1DistancePct?: number;
  /** 与该结构/该日绑定的事件，按可用日倒序（按需从 /events 端点加载） */
  events?: EventItem[];
  /** 事件仍在加载中 */
  eventsLoading?: boolean;
}

interface Props {
  selection: Selection | null;
  onClose: () => void;
}

function fmt(v: number | null | undefined): string {
  return v == null ? "—" : v.toFixed(2);
}

function Section({ label, text }: { label: string; text: string }) {
  if (!text) return null;
  return (
    <div className="exp-section">
      <div className="exp-label">{label}</div>
      <div className="exp-text">{text}</div>
    </div>
  );
}

/**
 * 右侧滑出解释面板：点图上的菱形/×/竖线后，说明「这是什么信号 + 怎么用」。
 *
 * 设计取舍：详情页不再把结构诊断与 60 行事件表堆在 K 线下方（无法与图对照），
 * 改为点图上标记按需在此展开——信息密度不变，但阅读路径与看图一致。
 */
export default function ExplanationPanel({ selection, onClose }: Props) {
  if (!selection) {
    return (
      <aside className="exp-panel empty">
        <div className="exp-hint">
          <div className="exp-hint-icon">◆</div>
          <div>
            点击 K 线图上的标记查看信号解释
            <ul>
              <li>
                <span className="mk mk-bottom">◆</span> 绿色菱形 = 底部结构确认
              </li>
              <li>
                <span className="mk mk-top">◆</span> 红色菱形 = 顶部结构确认
              </li>
              <li>
                <span className="mk mk-dead">✕</span> 灰色叉 = 结构失效日
              </li>
              <li>
                <span className="mk mk-kv">│</span> 竖线 = 关键性波动（转绿/转黑）
              </li>
            </ul>
          </div>
        </div>
      </aside>
    );
  }

  const {
    source,
    date,
    price,
    explanation,
    structure,
    events,
    eventsLoading,
    b1PivotDate,
    b1DistancePct,
  } = selection;

  return (
    <aside className="exp-panel">
      <div className="exp-head">
        <div>
          <div className="exp-source">{source}</div>
          <h3>{explanation?.title ?? "信号详情"}</h3>
        </div>
        <button className="btn small" onClick={onClose} title="关闭">
          ✕
        </button>
      </div>

      {(date || price != null) && (
        <div className="exp-meta">
          {date && <span>发生于 {date}</span>}
          {price != null && <span>价位 {fmt(price)}</span>}
        </div>
      )}

      {(b1PivotDate || b1DistancePct != null) && (
        <div className="exp-section">
          <div className="exp-label">本条线的当前数值</div>
          {b1PivotDate && (
            <div className="exp-kv">
              <span>前高摆动日</span>
              <b>{b1PivotDate}</b>
            </div>
          )}
          {b1DistancePct != null && (
            <div className="exp-kv">
              <span>当前距该阻力</span>
              <b>{b1DistancePct.toFixed(2)}%</b>
            </div>
          )}
        </div>
      )}

      {explanation ? (
        <>
          <Section label="这是什么" text={explanation.definition} />
          <Section label="计算口径" text={explanation.formula} />
          <Section label="怎么用" text={explanation.usage} />
          <Section label="客观失效条件" text={explanation.invalidation} />
          <Section label="下一步等待什么" text={explanation.next_step} />
          {explanation.caveat && (
            <div className="exp-caveat">
              <div className="exp-label">口径提醒</div>
              <div className="exp-text">{explanation.caveat}</div>
            </div>
          )}
        </>
      ) : (
        <div className="exp-text muted">该标记暂无术语解释条目。</div>
      )}

      {structure && (
        <div className="exp-section">
          <div className="exp-label">本结构当前状态</div>
          <div className="exp-kv">
            <span>类型</span>
            <b>
              {structure.structure_type_cn}（{structure.side === "bottom" ? "底部" : "顶部"}）
            </b>
          </div>
          <div className="exp-kv">
            <span>状态</span>
            <b>{structure.status_cn}</b>
          </div>
          <div className="exp-kv">
            <span>C 点（失效线）</span>
            <b>{fmt(structure.c_price)}</b>
          </div>
          {structure.neckline != null && (
            <div className="exp-kv">
              <span>颈线</span>
              <b>{fmt(structure.neckline)}</b>
            </div>
          )}
          {structure.distance_to_c_pct != null && (
            <div className="exp-kv">
              <span>距 C 点</span>
              <b className={structure.distance_to_c_pct >= 0 ? "down" : "up"}>
                {structure.distance_to_c_pct >= 0
                  ? `高于 ${structure.distance_to_c_pct.toFixed(1)}%`
                  : `跌破 ${Math.abs(structure.distance_to_c_pct).toFixed(1)}%`}
              </b>
            </div>
          )}
          <div className="exp-kv">
            <span>发现日 / 确认日</span>
            <b>
              {structure.detected_date} / {structure.confirmed_date ?? "未确认"}
            </b>
          </div>
          {structure.invalidated_date && (
            <div className="exp-kv">
              <span>失效日</span>
              <b>{structure.invalidated_date}</b>
            </div>
          )}
          {structure.invalidated_reason && (
            <div className="exp-kv">
              <span>失效原因</span>
              <b>{structure.invalidated_reason}</b>
            </div>
          )}
        </div>
      )}

      {eventsLoading && (
        <div className="exp-section">
          <div className="exp-label">相关事件</div>
          <div className="exp-text muted">加载中…</div>
        </div>
      )}

      {!eventsLoading && events && events.length === 0 && structure && (
        <div className="exp-section">
          <div className="exp-label">相关事件</div>
          <div className="exp-text muted">该结构没有绑定的独立事件记录。</div>
        </div>
      )}

      {events && events.length > 0 && (
        <div className="exp-section">
          <div className="exp-label">相关事件（{events.length}）</div>
          {events.map((e) => (
            <div className="exp-event" key={e.event_id}>
              <div className="exp-event-head">
                <span className={`sev-chip ${e.severity}`}>{e.severity_cn}</span>
                <b>
                  {e.rule_cn}
                  {e.sub_rule_cn ? ` · ${e.sub_rule_cn}` : ""}
                </b>
                <span className="muted">{e.available_date}</span>
              </div>
              <div className="exp-text">{e.reason_cn}</div>
              {Object.keys(e.evidence).length > 0 && (
                <details className="exp-details">
                  <summary>成立时的数值</summary>
                  <pre>{JSON.stringify(e.evidence, null, 1)}</pre>
                </details>
              )}
              {Object.keys(e.invalidation).length > 0 && (
                <details className="exp-details">
                  <summary>客观失效条件</summary>
                  <pre>{JSON.stringify(e.invalidation, null, 1)}</pre>
                </details>
              )}
            </div>
          ))}
        </div>
      )}
    </aside>
  );
}
