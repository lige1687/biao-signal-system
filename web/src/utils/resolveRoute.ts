import { api } from "../api/client";
import type { CopilotResolveReply } from "../types";

/** 03B（2026-09-08）：统一解析后的路由动作。
 * 服务端 resolve 决定意图；两个入口（工作台/控制台）不再各自用
 * 前端关键词或「有 symbol 就一概 chat」的旁路决定行为。 */
export type RouteAction = "dispatch" | "chat" | "backtest";

export async function resolveRoute(opts: {
  message: string;
  sessionId: string | null;
  symbol: string | null;
}): Promise<{ action: RouteAction; resolve: CopilotResolveReply }> {
  const resolve = await api.copilotResolve({
    message: opts.message,
    client_request_id:
      typeof crypto !== "undefined" && "randomUUID" in crypto
        ? crypto.randomUUID()
        : `cr_${Date.now()}_${Math.random().toString(36).slice(2)}`,
    session_id: opts.sessionId,
    selected_symbol: opts.symbol,
  });
  let action: RouteAction = "chat";

  if (
    resolve.intent === "trade_report" ||
    resolve.intent === "discovery" ||
    resolve.intent === "existing_action"
  ) {
    action = "dispatch"; // 已有流水线：报单预览/机会卡/持仓复盘卡
  } else if (
    resolve.intent === "discussion" &&
    ["dca", "sentiment", "mindset"].includes(resolve.topic)
  ) {
    // discussion 统一由 resolve 层识别叙事主题。
    // resolve 话题词表覆盖范围大于 dispatch 出卡词表，
    // 因此前端只放行已上线的三类 topic；若后端 dispatch 未命中，
    // 仍会按 chat_fallback 优雅回落，不改变安全边界。
    action = "dispatch";
  } else if (resolve.intent === "backtest_request") {
    action = "backtest";
  }
  return { action, resolve };
}

/** 从一句话里解析用户明确选择的补测模块（不默认 A）。 */
export function parseBacktestModule(message: string): string | null {
  const m = /模块\s*([A-Da-d])/.exec(message);
  return m ? m[1].toUpperCase() : null;
}

/** 03B-R2 契约2：退出方式必须由用户明确选择（两前端不再统一固定
 * a6_1_costbasis）。识别口语：退出①/1、抵扣价、关键波动、初始止损、a6_x。 */
export function parseBacktestExit(message: string): string | null {
  const t = (message || "").toLowerCase();
  if (/a6[_\s]?1|成本|抵扣价|退出\s*[①1一]/.test(t)) return "a6_1_costbasis";
  if (/a6[_\s]?2|关键波|顶部构造.*退出|退出\s*[②2二]/.test(t))
    return "a6_2_top_plus_keywave";
  if (/a6[_\s]?3|初始止损|只.*止损|退出\s*[③3三]/.test(t))
    return "a6_3_structure_stop";
  return null;
}

/** 退出方式的人话清单（追问用语，与引擎 EXIT_VARIANT_CN 对应）。 */
export const EXIT_HINT_CN =
  "请说明退出方式：退出1（收盘跌破EMA20+抵扣价）/ 退出2（顶部构造后关键波动）/ 退出3（只按初始止损）。";
