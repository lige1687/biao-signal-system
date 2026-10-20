import { subjectLabel } from "../../utils/agentUx";
import type { NextStep } from "../../types";

/**
 * UX 第一期（2026-09-13）：回答下方的"接下来"动作条（两入口共用）。
 * - 最多 3 个动作，来自服务端 `_build_next_steps`（既有事实推导）；
 * - 讨论类动作只把完整中文问题放进输入框（用户可改后发送），不自动发；
 * - 动作绑定该回答实际生效的标的（draft_cn 里带代码），切换标的后
 *   点旧按钮不会串对象；条上明示"针对 XXX"。
 * - 没有实现的能力不做按钮：kind 未识别的动作直接不渲染。
 */
export default function NextStepsBar({ steps, symbol, displayName, disabled, onDraft, onExpand, onPrepareBacktest }: {
  steps: NextStep[] | null | undefined;
  symbol: string | null | undefined;
  displayName?: string | null;
  disabled?: boolean;
  /** 把完整中文问题放进输入框（用户可修改后自行发送）。 */
  onDraft: (message: string) => void;
  /** 展开本回答的完整内容与依据。 */
  onExpand?: () => void;
  /** 打开中文补测选择面板（绑定本回答的原标的）。 */
  onPrepareBacktest?: (boundSymbol: string) => void;
}) {
  const list = (steps ?? []).filter(s => s && s.label_cn).slice(0, 3);
  if (!list.length) return null;
  return (
    <div className="agent-next-steps">
      <span className="agent-next-steps-label">
        接下来{symbol ? `（针对 ${subjectLabel(symbol, displayName)}）` : ""}
      </span>
      <div className="agent-next-steps-actions">
        {list.map(s => {
          const key = s.kind;
          let onClick: (() => void) | null = null;
          if (s.kind === "expand_evidence" && onExpand) onClick = onExpand;
          else if (s.kind === "prepare_backtest" && onPrepareBacktest && symbol) {
            onClick = () => onPrepareBacktest(symbol);
          } else if (s.draft_cn && onDraft) {
            // U1 返修：任何带完整中文问题草稿的动作都走"填入输入框"，
            // 包括拦截回合本地的"继续讨论"（kind=draft_discussion）——
            // 不自动发送，用户可改后发送。
            onClick = () => onDraft(s.draft_cn!);
          }
          if (!onClick) return null; // 没有对应能力的动作不渲染成按钮
          return (
            <button
              key={key}
              type="button"
              className="agent-next-step-btn"
              disabled={disabled}
              title={s.note_cn ?? s.draft_cn ?? s.label_cn}
              onClick={onClick}
            >
              {s.label_cn}
            </button>
          );
        })}
      </div>
    </div>
  );
}
