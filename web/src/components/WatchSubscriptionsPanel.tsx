/** 全局「我的提醒」面板 -- 展示用户所有 active + pending_confirmation 订阅.
 *  设计: 30s 轮询, 让 pending_confirmation 状态快速反映.
 *
 *  - 每行: 标的 / 价位 / 方向 / 状态 / 创建时间 / [取消] / [据此建计划]
 *  - [据此建计划] 在 Step 2 暂为 placeholder (Step 3 接入 plan 创建流程).
 *  - [取消] 调 dismissWatch, 状态 → dismissed.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { WatchSubscription } from "../types";
import PromotePlanDialog from "./PromotePlanDialog";

const STATE_CN: Record<string, string> = {
  active: "盯盘中",
  pending_confirmation: "已命中, 待确认",
  promoted: "已落计划",
  dismissed: "已取消",
};

const STATE_TONE: Record<string, string> = {
  active: "var(--text-faint)",
  pending_confirmation: "var(--warn)",
  promoted: "var(--lei-green)",
  dismissed: "var(--text-faint)",
};

export default function WatchSubscriptionsPanel() {
  const qc = useQueryClient();
  const { data: watches, isLoading } = useQuery({
    queryKey: ["watches", "all"],
    queryFn: () => api.listWatches({ state: "active,pending_confirmation" }),
    refetchInterval: 30_000,
  });

  const [dismissReasonFor, setDismissReasonFor] = useState<string | null>(null);
  const [dismissReason, setDismissReason] = useState("");
  const [promoteFor, setPromoteFor] = useState<WatchSubscription | null>(null);

  const dismiss = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.dismissWatch(id, reason),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["watches", "all"] });
      setDismissReasonFor(null);
      setDismissReason("");
    },
  });

  return (
    <div className="watch-panel">
      <div className="watch-panel-head">
        <b>🔔 我的提醒</b>
        <span className="muted">
          {isLoading ? "加载中..." : `${watches?.length ?? 0} 条 live`}
        </span>
      </div>
      {!watches || watches.length === 0 ? (
        <div className="muted watch-empty">
          还没有订阅. 标的详情页的「未来买点」处可 [设提醒].
        </div>
      ) : (
        <ul className="watch-list">
          {watches.map((w) => (
            <WatchRow
              key={w.watch_id}
              w={w}
              dismissing={dismissReasonFor === w.watch_id}
              dismissReason={dismissReason}
              onStartDismiss={() => {
                setDismissReasonFor(w.watch_id);
                setDismissReason("");
              }}
              onChangeReason={setDismissReason}
              onCancelDismiss={() => {
                setDismissReasonFor(null);
                setDismissReason("");
              }}
              onConfirmDismiss={() =>
                dismiss.mutate({ id: w.watch_id, reason: dismissReason || "用户取消" })
              }
              onPromote={setPromoteFor}
              pending={dismiss.isPending}
            />
          ))}
        </ul>
      )}
      {promoteFor && (
        <PromotePlanDialog
          watch={promoteFor}
          onClose={() => setPromoteFor(null)}
        />
      )}
    </div>
  );
}

function WatchRow({
  w,
  dismissing,
  dismissReason,
  onStartDismiss,
  onChangeReason,
  onCancelDismiss,
  onConfirmDismiss,
  onPromote,
  pending,
}: {
  w: WatchSubscription;
  dismissing: boolean;
  dismissReason: string;
  onStartDismiss: () => void;
  onChangeReason: (s: string) => void;
  onCancelDismiss: () => void;
  onConfirmDismiss: () => void;
  onPromote: (w: WatchSubscription) => void;
  pending: boolean;
}) {
  const stateCn = STATE_CN[w.state] ?? w.state;
  const tone = STATE_TONE[w.state] ?? "var(--text-faint)";
  return (
    <li className="watch-row">
      <div className="watch-row-head">
        <span className="watch-symbol">{w.symbol}</span>
        <span className="watch-direction">
          {w.direction === "long" ? "多" : "空"} · {w.module}
        </span>
        <span className="watch-state" style={{ color: tone }}>
          [{stateCn}]
        </span>
        {w.level != null && (
          <span className="watch-level">价位 {w.level}</span>
        )}
      </div>
      <div className="watch-text">{w.watch_text_cn}</div>
      {w.state === "pending_confirmation" && w.triggered_price != null && (
        <div className="watch-triggered">
          14:45 价 <b>{w.triggered_price.toFixed(2)}</b>
          {w.triggered_at && ` · ${w.triggered_at.slice(0, 16).replace("T", " ")}`}
          <br />
          <span className="muted">{w.triggered_reason_cn}</span>
        </div>
      )}
      <div className="watch-actions">
        {w.state === "pending_confirmation" && (
          <button
            className="btn small primary"
            onClick={() => onPromote(w)}
          >
            据此建计划
          </button>
        )}
        {!dismissing ? (
          <button className="btn small" onClick={onStartDismiss}>
            取消
          </button>
        ) : (
          <>
            <input
              className="watch-dismiss-input"
              placeholder="原因 (可选)"
              value={dismissReason}
              onChange={(e) => onChangeReason(e.target.value)}
            />
            <button
              className="btn small"
              disabled={pending}
              onClick={onConfirmDismiss}
            >
              {pending ? "..." : "确认取消"}
            </button>
            <button className="btn small" onClick={onCancelDismiss}>
              算了
            </button>
          </>
        )}
      </div>
    </li>
  );
}
