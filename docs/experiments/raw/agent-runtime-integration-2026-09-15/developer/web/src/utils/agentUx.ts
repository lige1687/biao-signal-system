/**
 * UX 第一期（2026-09-13）+ 返修 U4（2026-09-13 主控复核）：标的讨论展示层的
 * 中文映射与不支持项检测。全部是纯展示转换：中文名只维护显示，不创造引擎
 * 能力、不决定参数；数值与合法性仍以服务端/引擎为准（A/B/C/D 与退出代码
 * 是既有引擎选项）。
 *
 * U4 修正：退出方式的名称与解释按引擎实际规则改写
 * （引擎 EXIT_VARIANT_CN：A6① 抵扣价退出 / A6② 顶部构造+关键性波动 /
 *  A6③ 仅初始结构止损 / B3 双条件退出（跌回密集区上沿+破20组下弯；
 *  底线=排列破坏）），不承诺相对结果（如"落袋更早"），不把"或"写成
 * "且"、反之亦然。
 */

/** 交易模块（入场打法）的中文显示名——准确映射引擎模块 A/B/C/D。 */
export const MODULE_CN_SIMPLE: Record<string, string> = {
  A: "上升趋势中的回调打法（A）",
  B: "横盘整理后突破密集区的打法（B）",
  C: "跌破前低后又收回的 2B 反转打法（C）",
  D: "假跌破后的反转打法（D）",
};

/** 模块的一句话解释（给中文选择面板用）。 */
export const MODULE_HINT_CN: Record<string, string> = {
  A: "趋势已经走稳，等价格回调到均线附近再入场",
  B: "均线粘在一起横盘，等有效突破密集区再入场",
  C: "价格创了新低又快速收回，做破底翻",
  D: "向下假摔跌破支撑又收回来，做反转",
};

/** 退出方式的中文显示名——名称按引擎实际条件表述（U4；R1 二轮复核修正：
 * 退出1 引擎条件为收盘价**同时**低于 EMA20 与 20 个交易日前收盘价
 * （engine.py::prepare_frame：(close<ema20)&(close<close_lag20)），
 * 不是"任一跌破"。） */
export const EXIT_CN_SIMPLE: Record<string, string> = {
  a6_1_costbasis: "收盘同时跌破20日指数均线与抵扣价时退出（退出1）",
  a6_2_top_plus_keywave: "先出现顶部构造，再按关键性波动条件退出（退出2）",
  a6_3_structure_stop: "只按初始结构止损退出（退出3）",
  b3_dual: "B 专用双条件退出（跌回密集区上沿＋20日线组下弯）（退出B）",
};

/** 退出方式的一句话解释——只描述既有条件，不承诺相对结果（U4/R1）。 */
export const EXIT_HINT_CN_SIMPLE: Record<string, string> = {
  a6_1_costbasis: "收盘价同时低于20日指数均线（EMA20）和20个交易日前的收盘价，按既有规则在下一交易日开盘退出；初始结构止损仍独立生效",
  a6_2_top_plus_keywave: "顶部构造成立是前提，之后按关键性波动的既有条件执行退出",
  a6_3_structure_stop: "进场后只认初始止损，其余一律持有",
  b3_dual: "两个条件同时满足才离场：跌回密集区上沿、20日线组下弯；均线排列被破坏是另一个独立的底线条件",
};

/** 引擎当前支持的补测退出方式清单（拦截文案与面板共用同一来源，
 * 与 /backtest/options 的 exit_variants 对应；B 专用项单独说明）。 */
export const SUPPORTED_EXITS_CN =
  "收盘同时跌破20日指数均线与抵扣价时退出（退出1）、先出现顶部构造再按"
  + "关键性波动条件退出（退出2）、只按初始结构止损退出（退出3），B 打法另有"
  + "专用双条件退出";

export function moduleCn(m: string | null | undefined): string {
  if (!m) return "未指定";
  return MODULE_CN_SIMPLE[m] ?? `模块${m}`;
}

export function exitCn(v: string | null | undefined): string {
  if (!v) return "未指定";
  return EXIT_CN_SIMPLE[v] ?? v;
}

/** 历史测试与本次问题的匹配程度（exact/unknown → 中文，不输出英文枚举）。 */
export const COMPAT_CN: Record<string, string> = {
  exact: "适用于这次问题",
  incompatible: "与这次问题不一致（仅作参考）",
  unknown: "暂不能确定是否适用",
  reference: "仅供参考",
};

export function compatCn(c: string | null | undefined): string {
  if (!c) return "暂不能确定是否适用";
  return COMPAT_CN[c] ?? c;
}

/** 后端 note 文案里的英文枚举做显示层映射（只改显示，不改存储/判定）。 */
export function noteCn(t: string | null | undefined): string {
  if (!t) return "";
  return t
    .replace(/只有\s*exact\s*支持本问题/g, "只有与这次问题完全一致的结果才支持本问题")
    .replace(/[（(]兼容性\s*unknown[)）]/g, "")
    .replace(/[（(]兼容性\s*exact[)）]/g, "")
    .replace(/兼容性\s*unknown/g, "暂不能确定是否适用")
    .replace(/兼容性\s*exact/g, "适用于这次问题")
    .replace(/\bexact\b/g, "完全一致")
    .replace(/\bunknown\b/g, "暂不能确定");
}

/** R 的一次性解释（第一次出现 R 的地方必须带，不写成收益率）。 */
export const R_EXPLAIN_CN = "R＝每笔预定风险金额的倍数，不是收益率";

/** 期望 R 的中文展示（数值原样保留，只换说法）。 */
export function expectancyCn(r: number | null | undefined): string {
  return r != null
    ? `每笔平均 ${r.toFixed(2)} 倍风险金额（R）`
    : "每笔平均 -";
}

/**
 * 检测补测请求里**当前引擎不支持**的退出方式说法。
 * 命中时如实告知"暂未支持"，不用普通结构止损静默替代（任务书场景 5）。
 * 注意：引擎有 ATR 缓冲过滤参数，但补测入口不暴露它，也不构成
 * "ATR 止损退出方式"——所以这里判为不支持是准确的。
 */
export function detectUnsupportedExitRequest(message: string): string | null {
  const t = (message || "").replace(/\s+/g, "");
  if (/atr止损|atr缓冲止损|atr止损方式/i.test(t)) return "ATR 止损";
  if (/atr.*(退出|止损)/i.test(t) || /(退出|止损).*atr/i.test(t)) return "ATR 止损";
  return null;
}

/**
 * U1 返修：ATR 拦截后提供给用户修改后发送的**讨论**草稿。
 * 措辞必须避开后端 parse_request 的补测触发词
 * （src/lei_signal/copilot/resolve.py::_BACKTEST_RE：
 *   补测｜回测｜测一下｜复跑｜重新测｜再测｜跑一次回测），
 * 否则用户点"继续讨论"发送后会被再次拦截，讨论入口是假的。
 */
export function atrDiscussionDraft(symbol: string | null | undefined): string {
  return `我想先聊聊思路：${symbol || "这个标的"} 参照 ATR 距离来设想止损位置，`
    + "在当前系统状态下合不合适？（只讨论思路，不做数值比较）";
}

/** U2 返修：某打法下合法的退出方式清单（b3_dual 仅 B 可用）。
 * 只做可见性过滤，能力清单本身以服务端 /backtest/options 为准。 */
export function validExitsFor(module: string | null, exits: string[]): string[] {
  return exits.filter(v => module === "B" || v !== "b3_dual");
}

/** U2 返修：切换打法后核对当前退出是否仍合法；失效即回落到该打法下的
 * 合法默认（调用方保证 defaultExit 本身合法），绝不发送隐藏的旧选项。 */
export function resolveExitAfterModuleChange(
  prevExit: string | null, module: string | null, exits: string[], defaultExit: string | null,
): string | null {
  const valid = validExitsFor(module, exits);
  if (prevExit && valid.includes(prevExit)) return prevExit;
  return defaultExit != null && valid.includes(defaultExit) ? defaultExit : (valid[0] ?? null);
}

/**
 * U2 返修：从原问题冻结的比较配置里如实读窗口；读不到就区分说明，
 * 不统一称"未指定"。comparison_config 来自服务端 evidence_card
 * （history_and_scope.comparison_config.window = {start,end,...}）。
 */
export function windowLabelFromComparisonConfig(
  comparisonConfig: Record<string, unknown> | null | undefined,
): string | null {
  if (!comparisonConfig || typeof comparisonConfig !== "object") return null;
  const win = comparisonConfig.window as Record<string, unknown> | null | undefined;
  if (win && typeof win === "object" && win.start && win.end) {
    return `沿用原问题窗口 ${String(win.start)} ~ ${String(win.end)}`;
  }
  const state = comparisonConfig.window_state;
  if (state === "unverified" || win == null) {
    return "原问题没有可核实的窗口选择（按系统默认处理，可在对话中说明起止日期）";
  }
  return null;
}
