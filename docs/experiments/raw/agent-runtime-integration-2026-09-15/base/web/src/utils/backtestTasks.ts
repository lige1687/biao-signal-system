import { api } from "../api/client";
import type { BacktestRequestStatus } from "../types";

/** 03B-R2（契约4）：两个入口共用的补测任务控制。
 * - 提交时捕获 {sessionId, questionId, symbol, generation}；
 * - 轮询回来的每次更新都校验世代与归属，不匹配即丢弃（切对象/开新对话/
 *   卸载不串）；
 * - 五状态逐一处理：queued/running 只**更新当前任务卡**（不显示中断、不
 *   每轮追加新消息）；只有 completed/failed/interrupted 进入终态处理一次；
 * - 任务登记持久化在 localStorage（只是提示）；恢复以**服务端任务列表为
 *   权威**，刷新/历史重开后重新接线轮询；
 * - 终态只回填一次（服务端唯一约束兜底）。 */

export type BacktestPhase = BacktestRequestStatus["status"];

export const TERMINAL_PHASES: BacktestPhase[] = [
  "completed",
  "failed",
  "interrupted",
];

export function isTerminal(status: BacktestPhase): boolean {
  return TERMINAL_PHASES.includes(status);
}

export function phaseLabelCn(status: BacktestPhase): string {
  switch (status) {
    case "queued":
      return "排队中";
    case "running":
      return "运行中";
    case "completed":
      return "已完成";
    case "failed":
      return "失败";
    case "interrupted":
      return "已中断";
  }
}

/** 五状态逐一给任务卡文案：queued/running 是进行时（更新当前卡，不显示
 * 中断、不追加新消息）；completed/failed/interrupted 是终态（只处理一次）。 */
export function taskStatusTextCn(st: BacktestRequestStatus): string {
  const head = `${st.symbol} · 模块${st.method} · 退出 ${st.exit_variant}`;
  switch (st.status) {
    case "queued":
      return `补测任务 ${st.request_id}（${head}）排队中…完成后结果自动回到原问题。`;
    case "running":
      return `补测任务 ${st.request_id}（${head}）运行中…`;
    case "completed":
      return `补测完成（运行 ${st.run_id}）：${head}；结果已回填到原问题。`;
    case "failed":
      return `补测失败：${st.error ?? "未知原因"}（${head}）`;
    case "interrupted":
      return `补测中断：${st.error ?? "无法确认后台任务状态"}（${head}；可在原问题下重试）`;
  }
}

export interface TrackedTask {
  requestId: string;
  sessionId: string;
  questionId: number;
  symbol: string;
  generation: number;
  createdAt: string;
  terminal?: boolean;
}

const REG_KEY = "lei.btr.registry.v1";

function loadRegistry(): Record<string, TrackedTask> {
  try {
    return JSON.parse(localStorage.getItem(REG_KEY) || "{}");
  } catch {
    return {};
  }
}

function saveRegistry(reg: Record<string, TrackedTask>): void {
  try {
    localStorage.setItem(REG_KEY, JSON.stringify(reg));
  } catch {
    /* 隐私模式等：登记不可用只影响刷新恢复 */
  }
}

/** 页面世代（会话/对象切换时 +1）：过期世代的视图更新一律丢弃。 */
let generation = 0;
export function bumpGeneration(): number {
  generation += 1;
  return generation;
}
export function currentGeneration(): number {
  return generation;
}

export function trackTask(t: {
  requestId: string;
  sessionId: string;
  questionId: number;
  symbol: string;
}): TrackedTask {
  const task: TrackedTask = {
    ...t,
    generation: generation,
    createdAt: new Date().toISOString(),
  };
  const reg = loadRegistry();
  reg[task.requestId] = task;
  saveRegistry(reg);
  return task;
}

export function trackedTasks(): TrackedTask[] {
  return Object.values(loadRegistry()).sort((a, b) =>
    a.createdAt < b.createdAt ? 1 : -1);
}

export interface PollHandle {
  stop: () => void;
}

/** 轮询一个任务到终态；每次回调前校验世代守卫仍有效。
 * onUpdate 对五种状态都会调用——由页面决定「更新任务卡」还是「终态处理」。 */
export function pollTask(
  requestId: string,
  genGuard: () => boolean,
  onUpdate: (st: BacktestRequestStatus) => void,
  intervalMs = 2000,
): PollHandle {
  const timer = window.setInterval(async () => {
    try {
      const st = await api.copilotBacktestStatus(requestId);
      if (!genGuard()) return; // 世代过期：视图更新丢弃（任务照常在原问题下）
      onUpdate(st);
      if (isTerminal(st.status)) {
        window.clearInterval(timer);
        const reg = loadRegistry();
        if (reg[requestId]) {
          reg[requestId].terminal = true;
          saveRegistry(reg);
        }
      }
    } catch {
      /* 单次查询失败忽略，下轮再试 */
    }
  }, intervalMs);
  return { stop: () => window.clearInterval(timer) };
}

/** 恢复（03B-R2 契约4）：服务端任务列表为权威，localStorage 只是提示——
 * 未终态任务（含本浏览器没登记过的）重新接线轮询；本浏览器登记过、服务端
 * 已终态的，回调一次终态让页面收口显示。 */
export async function recoverActiveTasks(
  genGuard: () => boolean,
  onUpdate: (st: BacktestRequestStatus) => void,
  sessionId?: string | null,
): Promise<PollHandle[]> {
  const handles: PollHandle[] = [];
  let serverTasks: BacktestRequestStatus[] = [];
  try {
    serverTasks = (await api.copilotBacktestList(sessionId ?? null)).requests ?? [];
  } catch {
    serverTasks = [];
  }
  const reg = loadRegistry();
  const seen = new Set<string>();
  for (const st of serverTasks.slice(0, 10)) {
    seen.add(st.request_id);
    if (isTerminal(st.status)) {
      if (!genGuard()) continue;
      if (reg[st.request_id] && !reg[st.request_id].terminal) {
        reg[st.request_id].terminal = true;
        onUpdate(st);
      }
      continue;
    }
    handles.push(pollTask(st.request_id, genGuard, onUpdate));
  }
  // localStorage 里有、服务端列表没返回（列表窗口外）的非终态任务也补查
  for (const t of trackedTasks()) {
    if (t.terminal || seen.has(t.requestId)) continue;
    if (sessionId && t.sessionId !== sessionId) continue;
    handles.push(pollTask(t.requestId, genGuard, onUpdate));
  }
  saveRegistry(reg);
  return handles;
}

/** 稳定请求编号（跨刷新一致）：sha-256 不可用时的确定性降级哈希。 */
export function stableClientId(parts: (string | number | null | undefined)[]): string {
  const raw = parts.join("|");
  let h1 = 0x811c9dc5;
  let h2 = 0x01000193;
  for (let i = 0; i < raw.length; i += 1) {
    h1 = ((h1 ^ raw.charCodeAt(i)) * 0x01000193) >>> 0;
    h2 = ((h2 + raw.charCodeAt(i) * (i + 7)) * 0x85ebca6b) >>> 0;
  }
  return `cli_${h1.toString(16)}${h2.toString(16)}_${raw.length}`;
}
