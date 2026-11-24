import assert from "node:assert/strict";
import { test } from "node:test";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { build } from "esbuild";

// Compile the actual page and its private slot component together with one React
// instance. No production exports or API changes are needed for the SSR checks.
const source = await readFile(process.env.DAILY_BRIEF_SOURCE ?? new URL("./DailyBriefPage.tsx", import.meta.url), "utf8");
const built = await build({
  stdin: {
    contents: source + `
      import { createElement } from "react";
      import { renderToStaticMarkup } from "react-dom/server";
      import { StaticRouter } from "react-router-dom/server";
      import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
      export { createElement, renderToStaticMarkup, StaticRouter, QueryClient, QueryClientProvider, SlotView };
    `,
    resolveDir: new URL(".", import.meta.url).pathname,
    loader: "tsx",
  },
  bundle: true, write: false, platform: "node", format: "cjs", jsx: "automatic",
});
const mod = { exports: {} };
new Function("require", "module", "exports", built.outputFiles[0].text)(createRequire(import.meta.url), mod, mod.exports);
const { default: Page, SlotView, createElement: el, renderToStaticMarkup, StaticRouter, QueryClient, QueryClientProvider } = mod.exports;
const date = "2026-09-01";
const summary = "今日原始摘要：旧记录正文不得重写";
const brief = slot => ({
  generated_at: `${date}T${slot === "1445" ? "14:45" : "16:45"}:00`,
  summary: { generated_by: "template", text: summary },
  env: { anomalies: [], breadth_context: [], macro: { raw: {}, line_cn: "保存的背景参考" } },
  watchlist: { sector_watch_count: 1, items: [{
    symbol: "sh510300", display_name: "保存的ETF", verdict: "waiting", verdict_cn: "等待条件",
    n_changes: 1, is_new: false, changes: ["保存的变化"],
    state: { color: "green", color_cn: "绿", stage_cn: "保存的上升阶段", dimensions: { 长周期: "支持" } },
  }] },
  pool: { items: [{ code: "BK001", name: "保存的板块", stage: "accumulation", streak: 4,
    tags: ["保存的理由"], rs_pctile: 41, rs_pctile_delta_20: 3, flow_20d_main_yi: 5,
    pe_ttm: 19, next_watch: "保存的SMA60观察点" }] },
});
const response = slot => ({ date, slot, slots_available: ["1445", "1645"], brief: brief(slot) });
function render(slot, selectedSlot = false, mutate = () => {}) {
  const client = new QueryClient({ defaultOptions: { queries: { staleTime: Infinity, retry: false } } });
  const saved = response(slot);
  mutate(saved.brief);
  client.setQueryData(["dailyBriefLatest"], saved);
  client.setQueryData(["dailyBrief", date, slot], saved);
  // Latest values deliberately contradict the stored state. Before the fix these
  // cached current queries were silently joined into the stored brief's tables.
  client.setQueryData(["cards", "watchlist"], { cards: [{ symbol: "sh510300", price: 9876.54, change_pct: -88.88, stage_cn: "最新下降阶段" }] });
  client.setQueryData(["sectorsTrend"], { boards: [{ code: "BK001", pct_change: 77.77, up_count: 909, down_count: 808, dist_to_sma60_pct: -66.66, stage: "decline" }] });
  const component = selectedSlot
    ? el(SlotView, { date, slot, buttons: el("button", null, "已选保存版本") })
    : el(Page);
  const html = renderToStaticMarkup(el(QueryClientProvider, { client }, el(StaticRouter, { location: "/daily-brief" }, component)));
  const keys = client.getQueryCache().getAll().map(q => q.queryKey);
  client.clear();
  return { html, keys };
}

test("both saved versions render stored states and never join contradictory current quotes", () => {
  for (const slot of ["1445", "1645"]) {
    const { html } = render(slot);
    for (const saved of [date, "保存的上升阶段", "筑底", "保存的变化", "保存的理由", "保存的60日线观察点", summary]) assert.ok(html.includes(saved), saved);
    for (const current of ["9876.54", "-88.88", "77.77", "909", "808", "-66.7", "最新下降阶段"]) assert.ok(!html.includes(current), current);
    assert.ok(html.includes(slot === "1445" ? "盘中预判 · 14:45" : "收盘复核 · 16:45"));
    assert.ok(html.includes("14:45 预判") && html.includes("16:45 收盘"));
    assert.ok(!html.includes("今日变化") && !html.includes("和昨天一样") && !html.includes("判定的当前阶段"));
    assert.ok(html.includes("本次简报要点") && html.includes("与前一份简报对比"));
  }
});

test("selected saved slot uses its record, explains missing quotes, and links to latest information", () => {
  for (const slot of ["1445", "1645"]) {
    const { html } = render(slot, true);
    assert.ok(html.includes("已选保存版本"));
    assert.ok(html.includes("简报未保存当时行情（价格、涨跌、涨跌家数、距60日线）"));
    assert.ok(html.includes("可从标的或板块入口查看最新资料"));
    assert.ok(html.includes('href="/symbol/sh510300"') && html.includes('href="/sectors"'));
    for (const column of [">现价<", ">当日<", ">当日涨跌<", ">涨/跌家数<", ">距60日线<"]) assert.ok(!html.includes(column));
    assert.ok(html.includes(summary));
  }
});

test("unavailable stored values stay missing and empty pool uses recording-time language", () => {
  const { html } = render("1645", false, saved => {
    saved.watchlist.items[0].state = null;
    saved.pool.items[0].rs_pctile = null;
    saved.pool.items[0].flow_20d_main_yi = null;
    saved.pool.items[0].pe_ttm = null;
  });
  assert.ok(html.includes("—") && !html.includes("9876.54") && !html.includes("保存的上升阶段"));
  const empty = render("1645", false, saved => { saved.pool.items = []; saved.watchlist.items = []; }).html;
  assert.ok(empty.includes("记录时无持续上榜板块") && empty.includes("记录时全部为低档位"));
});

test("page contains no current quote/sector queries and SSR never requests an API", () => {
  assert.ok(!source.includes("api.dashboard") && !source.includes("sectorsApi.trend"));
  assert.deepEqual([...source.matchAll(/queryKey:\s*\["([^"]+)"/g)].map(m => m[1]), ["dailyBriefLatest", "dailyBrief"]);
  const originalFetch = globalThis.fetch;
  let requests = 0;
  globalThis.fetch = () => { requests++; throw new Error("No network allowed in brief regression"); };
  try { render("1445"); render("1645", true); assert.equal(requests, 0); }
  finally { globalThis.fetch = originalFetch; }
});
