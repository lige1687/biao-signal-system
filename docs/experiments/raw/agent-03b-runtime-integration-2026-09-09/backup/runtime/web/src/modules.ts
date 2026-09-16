/**
 * 交易模块与方向的中文标签（前端单一来源）。
 *
 * 模块中文名与后端 ``module_backtest.MODULE_MAP`` 的 module_cn 对齐，
 * 避免前端再造一套措辞。原值（A/B/C/D、long/short）仍是数据载体，
 * 仅在展示层翻译；表单 option 的 value 不变，保证与后端契约一致。
 */

export const MODULE_CN: Record<string, string> = {
  A: "A·稳定上升趋势回调",
  B: "B·均线密集区突破",
  C: "C·2B/破底翻",
  D: "D·假突破反向",
};

export const DIRECTION_CN: Record<string, string> = {
  long: "做多",
  short: "做空",
};

/** 模块字母 -> 中文标签；未知字母原样返回（不丢信息）。 */
export function moduleCn(letter: string | null | undefined): string {
  if (!letter) return "-";
  return MODULE_CN[letter] ?? letter;
}

/** 方向 -> 中文；未知原样返回。 */
export function directionCn(dir: string | null | undefined): string {
  if (!dir) return "-";
  return DIRECTION_CN[dir] ?? dir;
}
