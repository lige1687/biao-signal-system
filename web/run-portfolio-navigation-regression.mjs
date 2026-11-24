import assert from "node:assert/strict";
import { patchPortfolioParams } from "./src/pages/portfolioUrl.ts";
import { groupPortfolioGaps } from "./src/components/portfolio/portfolioGapGroups.ts";

const original = new URLSearchParams("tab=holdings&group=overseas&q=ETF&sort=return&holding=old&todayFilter=incomplete&todayQ=A&todayHolding=h1");
const selected = patchPortfolioParams(original, { holding: "new" });
assert.equal(selected.get("holding"), "new");
assert.equal(selected.get("group"), "overseas");
assert.equal(selected.get("todayHolding"), "h1");
const today = patchPortfolioParams(selected, { tab: null, todayFilter: null, todayQ: null, todayHolding: "h2" });
assert.equal(today.get("tab"), null);
assert.equal(today.get("todayHolding"), "h2");
assert.equal(today.get("todayQ"), null);
assert.equal(original.get("holding"), "old", "current URL must remain untouched");

const groups = groupPortfolioGaps([
  { holding_id: "h1", name: "甲", code: "1", gaps: ["缺技术行情", "缺计划", "缺计划"] },
  { holding_id: "h2", name: "乙", code: "2", gaps: ["缺技术行情"] },
  { holding_id: "h3", name: "丙", code: null, gaps: [] },
]);
assert.deepEqual(groups.map(g => [g.gap, g.affected.length]), [["缺技术行情", 2], ["缺计划", 1]]);
assert.deepEqual(groups[0].affected.map(h => h.holding_id), ["h1", "h2"]);
console.log("portfolio URL and exact gap grouping regression passed");
