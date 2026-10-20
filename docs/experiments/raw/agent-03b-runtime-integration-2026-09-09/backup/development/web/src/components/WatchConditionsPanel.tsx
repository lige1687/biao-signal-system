/** 「到什么情况才算买点」面板 -- 在 BuyPointDrawer 底部渲染, 复用折叠 UI.
 *  每条 watch_condition 配一个 [设提醒] 按钮, 点完调 api.subscribeWatch
 *  并把该条标为已订阅 (本条变灰, 按钮变成 "已订阅").
 *
 *  设计: v1 简单按 watch_conditions[i] 索引作为订阅 key; 后端会按
 *  (symbol, level, source_rule_id, watch_kind) 去重, 重复订阅返回已有行.
 */
import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import type { SubscribeWatchRequest } from "../types";

interface Props {
  symbol: string;
  conditions: Array<{
    text_cn: string;
    kind: string;
    price: number | null;
    as_signal_rule_ids: string[];
  }>;
  candidateDirection: string;
  candidateModule: string;
  sourceRuleId: string | null;
  sourceCandidateId: string | null;
}

export default function WatchConditionsPanel({
  symbol,
  conditions,
  candidateDirection,
  candidateModule,
  sourceRuleId,
  sourceCandidateId,
}: Props) {
  const [expanded, setExpanded] = useState(false);
  const qc = useQueryClient();

  // 拉这个 symbol 的活跃 watch, 用来标 "已订阅" 状态
  const { data: watches } = useQuery({
    queryKey: ["watches", symbol],
    queryFn: () => api.listWatches({ symbol, state: "active,pending_confirmation" }),
    refetchInterval: 30_000,
  });

  const subscribe = useMutation({
    mutationFn: (body: SubscribeWatchRequest) => api.subscribeWatch(body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["watches", symbol] });
      qc.invalidateQueries({ queryKey: ["watches", "all"] });
    },
  });

  if (conditions.length === 0) return null;

  const isSubscribed = (cond: Props["conditions"][number]) => {
    if (!watches) return false;
    return watches.some(
      (w) =>
        w.watch_text_cn === cond.text_cn &&
        w.level === cond.price &&
        w.watch_kind === cond.kind,
    );
  };

  return (
    <div className="bp-watchconds">
      <div className="bp-watchconds-head" onClick={() => setExpanded((v) => !v)} role="button">
        <span>👀 未来买点 (watch_conditions) ({conditions.length})</span>
        <span className="bp-watchconds-toggle">{expanded ? "▼" : "▶"}</span>
      </div>
      {expanded && (
        <div className="bp-watchconds-detail">
          {conditions.map((c, i) => {
            const subscribed = isSubscribed(c);
            const pending = subscribe.isPending;
            return (
              <div
                key={i}
                className={`bp-watchconds-line${subscribed ? " subscribed" : ""}`}
              >
                <div className="bp-watchconds-text">
                  · {c.text_cn}
                  {c.kind === "price" && c.price != null && (
                    <span className="muted"> · 价位 {c.price}</span>
                  )}
                  <span className="muted"> · kind={c.kind}</span>
                </div>
                {subscribed ? (
                  <span className="bp-watchconds-tag">已订阅, 命中时推送</span>
                ) : (
                  <button
                    className="btn small"
                    disabled={pending}
                    onClick={() =>
                      subscribe.mutate({
                        symbol,
                        direction: candidateDirection,
                        module: candidateModule,
                        watch_kind: c.kind,
                        watch_text_cn: c.text_cn,
                        level: c.price,
                        source_candidate_id: sourceCandidateId,
                        source_rule_id: sourceRuleId,
                        as_signal_rule_ids: c.as_signal_rule_ids,
                      })
                    }
                  >
                    {pending ? "..." : "设提醒"}
                  </button>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
