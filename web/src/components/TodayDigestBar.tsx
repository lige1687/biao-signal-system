import type { Tradability } from "../types";

export type DigestKey = "events" | "buys" | "exits" | "tradability";

interface Props {
  /** 今日新事件数 N = data.new_events.length */
  events: number;
  /** 活跃买点数 M = trade_opportunities 中 is_active 的数量 */
  activeBuys: number;
  /** 退出信号数 K = assessment.exit_signals.length */
  exitSignals: number;
  /** 可交易性门禁（来自 assessment.tradability，可能为 null） */
  tradability: Tradability | null;
  /** 点击某段 → 滚动到对应面板并展开 */
  onJump: (key: DigestKey) => void;
}

/**
 * 今日摘要条：把中栏 9+ 张折叠面板的「今天有几件事」压成一行横向摘要，
 * 各段可点击跳转到对应面板并展开。只读既有数据、不做任何新增判定
 * （零噪音原则：四项全空时整条不渲染）。
 */
export default function TodayDigestBar({
  events,
  activeBuys,
  exitSignals,
  tradability,
  onJump,
}: Props) {
  // 零噪音：四项全空则不显示。
  if (
    events === 0 &&
    activeBuys === 0 &&
    exitSignals === 0 &&
    tradability == null
  ) {
    return null;
  }

  const tradable = tradability?.tradable ?? false;
  const tradFirstReason = tradability?.blocking_reasons[0];

  return (
    <div className="today-digest" role="list">
      <span className="td-label">今日</span>

      <button
        type="button"
        className="td-seg"
        role="listitem"
        onClick={() => onJump("events")}
        title="点击展开「今日新事件」面板"
      >
        新事件 <b>{events}</b>
      </button>

      <span className="td-sep">·</span>

      <button
        type="button"
        className="td-seg"
        role="listitem"
        onClick={() => onJump("buys")}
        title="点击展开「潜在买点」面板"
      >
        活跃买点 <b>{activeBuys}</b>
      </button>

      <span className="td-sep">·</span>

      <button
        type="button"
        className="td-seg"
        role="listitem"
        onClick={() => onJump("exits")}
        title="点击展开「持仓退出」面板"
      >
        退出信号 <b>{exitSignals}</b>
      </button>

      <span className="td-sep">·</span>

      {tradability == null ? (
        <span className="td-seg td-muted" role="listitem">
          可交易性 <b>—</b>
        </span>
      ) : (
        <button
          type="button"
          className={`td-seg ${tradable ? "ok" : "blocked"}`}
          role="listitem"
          onClick={() => onJump("tradability")}
          title={
            tradable
              ? "点击展开「可交易性门禁」面板"
              : `门禁：${tradFirstReason ?? "未知原因"}（点击展开）`
          }
        >
          可交易性{" "}
          <b>
            {tradable ? "✓" : `✗ ${tradFirstReason ?? "门禁"}`}
          </b>
        </button>
      )}
    </div>
  );
}
