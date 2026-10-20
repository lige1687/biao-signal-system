import { useEffect, useRef, useState } from "react";
import { useMutation } from "@tanstack/react-query";
import { api } from "../api/client";

type Turn = { who: "you" | "agent"; text: string; grounded?: boolean };

/**
 * 监督员 agent 抽屉（表达层）。
 *
 * 打开即取当前 alert 的接地摘要（message 为空）；之后可自由提问。
 * grounded=false 表示 LLM 不可用或输出未过接地校验，已降级为判定层模板--
 * 判定权始终在 Python，抽屉只显示，不自行推断。
 */
export default function AgentDrawer({
  planId,
  onClose,
}: {
  planId: string;
  onClose: () => void;
}) {
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const bodyRef = useRef<HTMLDivElement | null>(null);

  const ask = useMutation({
    mutationFn: (message: string) => api.planChat(planId, message),
    onSuccess: (reply) =>
      setTurns((cur) => [
        ...cur,
        { who: "agent", text: reply.reply, grounded: reply.grounded },
      ]),
    onError: (e: unknown) =>
      setTurns((cur) => [
        ...cur,
        { who: "agent", text: `取回失败：${e instanceof Error ? e.message : String(e)}` },
      ]),
  });

  // 打开时取一次接地摘要（空 message）。
  useEffect(() => {
    ask.mutate("");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [planId]);

  useEffect(() => {
    bodyRef.current?.scrollTo({ top: bodyRef.current.scrollHeight });
  }, [turns, ask.isPending]);

  const send = () => {
    const message = input.trim();
    if (!message || ask.isPending) return;
    setTurns((cur) => [...cur, { who: "you", text: message }]);
    setInput("");
    ask.mutate(message);
  };

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <aside className="drawer-panel">
        <div className="drawer-head">
          <h2>监督员 · 讲解</h2>
          <button className="btn small" onClick={onClose}>
            关闭
          </button>
        </div>

        <div className="drawer-body" ref={bodyRef}>
          {turns.map((turn, i) => (
            <div className="turn" key={i}>
              <div className="who">{turn.who === "you" ? "你" : "监督员"}</div>
              <div className="msg">{turn.text}</div>
              {turn.who === "agent" && turn.grounded !== undefined && (
                <div className={`grounded-tag ${turn.grounded ? "" : "warn"}`}>
                  {turn.grounded
                    ? "已过接地校验（rule_id 白名单 + 禁用词）"
                    : "已降级为判定层模板（LLM 输出不可用：超时 / 被截断 / 未过接地校验）"}
                </div>
              )}
            </div>
          ))}
          {ask.isPending && <div className="muted">监督员正在整理…</div>}
        </div>

        <div className="drawer-input">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && send()}
            placeholder="就这个计划提问（判定不变，只讲解）"
            disabled={ask.isPending}
          />
          <button
            className="btn small primary"
            onClick={send}
            disabled={ask.isPending || !input.trim()}
          >
            发送
          </button>
        </div>
      </aside>
    </>
  );
}
