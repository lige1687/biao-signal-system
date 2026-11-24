import assert from "node:assert/strict";
import { test } from "node:test";
import {
  emptyPortfolioChat, isCurrentScope, loadPortfolioChat, portfolioScopeKey, savePortfolioChat,
} from "./portfolioAgentState.ts";

function storage() {
  const values = new Map();
  return {
    getItem: (key) => values.get(key) ?? null,
    setItem: (key, value) => values.set(key, value),
  };
}

test("A, B and all holdings retain separate session and draft", () => {
  const local = storage();
  savePortfolioChat(local, "A", { sessionId: "sess-a", draft: "甲的原计划", turns: [] });
  savePortfolioChat(local, "B", { sessionId: "sess-b", draft: "乙的缺口", turns: [] });
  savePortfolioChat(local, null, { sessionId: "sess-all", draft: "整体风险", turns: [] });
  assert.deepEqual(["A", "B", null].map((id) => loadPortfolioChat(local, id).sessionId),
    ["sess-a", "sess-b", "sess-all"]);
  assert.deepEqual(["A", "B", null].map((id) => loadPortfolioChat(local, id).draft),
    ["甲的原计划", "乙的缺口", "整体风险"]);
  assert.notEqual(portfolioScopeKey("A"), portfolioScopeKey(null));
});

test("late A response is rejected after switching to B", () => {
  const a = portfolioScopeKey("A");
  assert.equal(isCurrentScope(a, "A"), true);
  assert.equal(isCurrentScope(a, "B"), false);
  assert.equal(isCurrentScope(a, null), false);
});

test("corrupt browser state degrades to an empty draft", () => {
  const local = storage();
  local.setItem(portfolioScopeKey("A"), "{bad json");
  assert.deepEqual(loadPortfolioChat(local, "A"), emptyPortfolioChat());
});

test("interrupted local reply keeps verified retry identity on reopen", () => {
  const local = storage();
  savePortfolioChat(local, "A", { sessionId: "sess-a", draft: "继续问", turns: [
    { id: "assistant-cid", role: "assistant", text: "", status: "pending", cid: "cid",
      retry: { message: "原计划呢？", client_request_id: "cid", portfolio_holding_id: "A" } },
  ] });
  const restored = loadPortfolioChat(local, "A");
  assert.equal(restored.turns[0].status, "failed");
  assert.equal(restored.turns[0].retry.client_request_id, "cid");
  assert.equal(restored.draft, "继续问");
});

test("storage denial does not crash the chat", () => {
  assert.equal(savePortfolioChat({ setItem: () => { throw new Error("quota"); } },
    "A", emptyPortfolioChat()), false);
});
