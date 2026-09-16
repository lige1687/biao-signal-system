import { useEffect, useRef, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { directionCn, moduleCn } from "../modules";
import type { PlanAlert } from "../types";
import CreatePlanDialog from "./CreatePlanDialog";
import ProvenanceBadge from "./ProvenanceBadge";

type Turn = { who: "you" | "agent"; text: string; grounded?: boolean };

/**
 * 监督员 · 计划核对抽屉（表达层）。
 *
 * 提交草案后打开：取草稿符合性核对（evaluate_draft_conformance，判定权在 Python），
 * 列硬阻断项（红，须修正才能确认）+ 软建议项（黄）。可「编辑计划」改 draft 后重取，
 * 或就符合性疑问向 agent 提问（planChat，只讲解不判定）。can_confirm 时「确认生效」
 * 走 confirm：entry->armed / holding_watch->entered。
 */
export default function ReviewDrawer({
  planId,
  onClose,
}: {
  planId: string;
  onClose: () => void;
}) {
  const queryClient = useQueryClient();
  const [turns, setTurns] = useState<Turn[]>([]);
  const [input, setInput] = useState("");
  const [error, setError] = useState("");
  const [editing, setEditing] = useState(false);
  const bodyRef = useRef<HTMLDivElement | null>(null);

  const { data: report, refetch } = useQuery({
    queryKey: ["conformance", planId],
    queryFn: () => api.conformance(planId),
  });

  const confirm = useMutation({
    mutationFn: () => api.confirmPlan(planId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["plans"] });
      queryClient.invalidateQueries({ queryKey: ["plansSummary"] });
      queryClient.invalidateQueries({ queryKey: ["plan", planId] });
      onClose();
    },
    onError: (e: unknown) => {
      // 422 硬阻断：body.detail.hard_issues 为结构化报告；刷新面板以同步。
      const body = (e as Error & { body?: unknown }).body as
        | { detail?: { message?: string } }
        | undefined;
      const msg = body?.detail?.message;
      setError(msg ?? (e instanceof Error ? e.message : String(e)));
      refetch();
    },
  });

  // 协商问答：复用 planChat（agent 只讲解，判定不变）。
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

  const hard = report?.hard_issues ?? [];
  const soft = report?.soft_issues ?? [];
  const canConfirm = report?.can_confirm ?? false;
  const detected = report?.system_detected ?? {};
  const detModule = (detected.module as string | null | undefined) ?? null;
  const detDir = (detected.direction as string | null | undefined) ?? null;
  const detScenarios =
    (detected.scenarios as
      | { rule_id: string | null; module: string | null; direction: string | null; state: string }[]
      | undefined) ?? [];
  const hasDetected = detModule != null || detDir != null || detScenarios.length > 0;

  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <aside className="drawer-panel rv-panel">
        <div className="drawer-head">
          <h2>监督员 · 计划核对</h2>
          <button className="btn small" onClick={onClose}>关闭</button>
        </div>

        <div className="drawer-body" ref={bodyRef}>
          <div className="rv-conformance">
            {!report && <div className="muted">核对中…</div>}
            {report && hard.length === 0 && soft.length === 0 && (
              <div className="rv-ok">
                ✓ 入场/退出逻辑符合系统，可直接确认生效。
              </div>
            )}
            {hard.length > 0 && (
              <div className="rv-block">
                <div className="rv-title">硬阻断项 · 须修正才能确认</div>
                {hard.map((a) => <IssueRow key={a.code} a={a} />)}
              </div>
            )}
            {soft.length > 0 && (
              <div className="rv-soft">
                <div className="rv-title">建议项 · 不阻断，自行斟酌</div>
                {soft.map((a) => <IssueRow key={a.code} a={a} />)}
              </div>
            )}
            {report && hasDetected && (
              <div className="rv-detected">
                <div className="rv-title">系统检测对照</div>
                <ul>
                  {detModule != null && (
                    <li><code>模块</code> = {moduleCn(detModule)}</li>
                  )}
                  {detDir != null && (
                    <li><code>方向</code> = {directionCn(detDir)}</li>
                  )}
                  {detScenarios.length > 0 && (
                    <li>
                      <code>已确认场景</code>
                      <ul>
                        {detScenarios.map((s, i) => (
                          <li key={i}>
                            {moduleCn(s.module)} · {directionCn(s.direction)} · {s.state}
                            {s.rule_id && (
                              <ProvenanceBadge
                                items={[
                                  {
                                    label: `${moduleCn(s.module)} ${directionCn(s.direction)}`,
                                    rule_id: s.rule_id,
                                    evidence_cn: "",
                                    research_proxy: false,
                                    principle_source: null,
                                  },
                                ]}
                              />
                            )}
                          </li>
                        ))}
                      </ul>
                    </li>
                  )}
                </ul>
              </div>
            )}
          </div>

          <div className="rv-chat">
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
        </div>

        {error && <div className="cp-error">{error}</div>}

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

        <div className="rv-actions">
          <button
            className="btn"
            onClick={() => { setError(""); setEditing(true); }}
            disabled={confirm.isPending}
          >
            编辑计划
          </button>
          <button
            className="btn primary"
            onClick={() => { setError(""); confirm.mutate(); }}
            disabled={!canConfirm || confirm.isPending}
            title={canConfirm ? "确认生效：entry->armed / 持仓->entered" : "存在硬阻断项，先修正再确认"}
          >
            {confirm.isPending ? "确认中…" : "确认生效"}
          </button>
        </div>
      </aside>

      {editing && (
        <CreatePlanDialog
          editPlanId={planId}
          onClose={() => setEditing(false)}
          onSaved={() => { setEditing(false); refetch(); }}
        />
      )}
    </>
  );
}

function IssueRow({ a }: { a: PlanAlert }) {
  return (
    <div className="rv-issue">
      <div className="rv-issue-head">
        <code>{a.code}</code>
        <ProvenanceBadge
          items={[
            {
              label: a.next_step_cn || a.code,
              rule_id: a.rule_id ?? null,
              evidence_cn: Object.entries(a.evidence ?? {})
                .map(([k, v]) => `${k}=${v}`)
                .join("；"),
              research_proxy: a.logic_provenance === "research_proxy",
              principle_source: a.principle_source ?? null,
            },
          ]}
        />
      </div>
      <div className="rv-issue-step">{a.next_step_cn || a.caveat_cn || "—"}</div>
    </div>
  );
}
