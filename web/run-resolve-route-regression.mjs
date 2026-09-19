#!/usr/bin/env node

/**
 * resolveRoute 前端预路由回归
 *
 * 验证：
 * 1. 新叙事卡 topic 可进入 dispatch
 * 2. 非目标 discussion 不误放行
 * 3. 旧 dispatch/backtest 行为不变
 * 4. symbol 存在时不改变路由判断
 * 5. 源文件同步守卫：本脚本内嵌逻辑副本与 src 真文件关键行一致
 *
 * 不调用真实 API。
 */

import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, join } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));

// 源文件同步守卫：真文件若偏离本脚本测试的逻辑副本，在此直接失败。
const src = readFileSync(join(here, "src/utils/resolveRoute.ts"), "utf8");
assert.ok(
  src.includes('["dca", "sentiment", "mindset"].includes(resolve.topic)'),
  "source guard: resolveRoute.ts 未包含三类叙事 topic 放行，逻辑副本已漂移",
);
assert.ok(
  src.includes('resolve.intent === "discussion"'),
  "source guard: resolveRoute.ts 缺少 discussion 分支条件",
);
assert.ok(
  src.includes('action = "dispatch"; // 已有流水线：报单预览/机会卡/持仓复盘卡'),
  "source guard: 旧三类 dispatch 注释行漂移",
);

function resolveRoute(resolve) {
  let action = "chat";

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
    // resolve 话题词表覆盖范围大于 dispatch 出卡词表。
    // 前端仅放行已上线三类叙事卡 topic；
    // 后端 dispatch 未命中时仍允许 chat_fallback 优雅回落。
    action = "dispatch";
  } else if (resolve.intent === "backtest_request") {
    action = "backtest";
  }

  return { action, resolve };
}

const cases = [
  { name: "dca topic dispatch", resolve: { intent: "discussion", topic: "dca" }, expected: "dispatch" },
  { name: "sentiment topic dispatch", resolve: { intent: "discussion", topic: "sentiment" }, expected: "dispatch" },
  { name: "mindset topic dispatch", resolve: { intent: "discussion", topic: "mindset" }, expected: "dispatch" },
  { name: "discussion unknown topic stays chat", resolve: { intent: "discussion", topic: "general" }, expected: "chat" },
  { name: "discussion missing topic stays chat", resolve: { intent: "discussion", topic: "" }, expected: "chat" },
  { name: "trade_report keeps dispatch", resolve: { intent: "trade_report", topic: "anything" }, expected: "dispatch" },
  { name: "discovery keeps dispatch", resolve: { intent: "discovery", topic: "anything" }, expected: "dispatch" },
  { name: "existing_action keeps dispatch", resolve: { intent: "existing_action", topic: "anything" }, expected: "dispatch" },
  { name: "backtest keeps backtest", resolve: { intent: "backtest_request", topic: "anything" }, expected: "backtest" },
  { name: "symbol does not alter discussion routing", resolve: { intent: "discussion", topic: "sentiment", symbol: "510300" }, expected: "dispatch" },
];

let passed = 0;
for (const item of cases) {
  const result = resolveRoute(item.resolve);
  assert.equal(
    result.action,
    item.expected,
    `${item.name}: expected ${item.expected}, got ${result.action}`,
  );
  passed += 1;
}

console.log(`resolve-route regression passed: ${passed} assertions + 3 source guards`);
