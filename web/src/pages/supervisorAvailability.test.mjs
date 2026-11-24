import assert from "node:assert/strict";
import { test } from "node:test";
import { createRequire } from "node:module";
import { build } from "esbuild";
import React from "react";
import { renderToStaticMarkup } from "react-dom/server";

// Actual component + real React Query seeded with synthetic states. API doubles
// forbid unspecified reads and all mutations. No browser, server or network.
const key = "__leiSupervisorAvailabilityTest";
const source = new URL("./SupervisorPage.tsx", import.meta.url).pathname;
const runtime = () => globalThis[key];
const built = await build({
  entryPoints: [source], bundle: true, write: false, platform: "node", format: "cjs",
  packages: "external", jsx: "automatic",
  plugins: [{ name: "offline-supervisor-boundaries", setup(b) {
    b.onResolve({ filter: /^(react|react\/jsx-runtime)$/ }, args => {
      if (args.namespace === "test-boundary") return { path: args.path, external: true };
      if (args.importer === source) return { path: args.path, namespace: "test-boundary" };
    });
    b.onResolve({ filter: /(^|\/)api\/client$|(^|\/)App$|BuyPointDrawer$/ }, args => {
      if (args.importer === source) return { path: args.path, namespace: "test-boundary" };
    });
    b.onLoad({ filter: /.*/, namespace: "test-boundary" }, args => {
      const state = `globalThis[${JSON.stringify(key)}]`;
      if (args.path === "react") return { contents: `
        import * as real from "react";
        export const useRef = real.useRef;
        export const useEffect = real.useEffect;
        export const useState = initial => {
          const result = real.useState(initial), state = ${state};
          if (initial === false && state.falseHooks++ === 0)
            return [state.scanOpen, value => { state.scanOpen = typeof value === "function" ? value(state.scanOpen) : value; }];
          return result;
        };`, loader: "js" };
      if (args.path === "react/jsx-runtime") return { contents: `
        import * as real from "react/jsx-runtime";
        const capture = (kind, type, props, key) => {
          if (type === "button") ${state}.buttons.push(props);
          return real[kind](type, props, key);
        };
        export const jsx = (...args) => capture("jsx", ...args);
        export const jsxs = (...args) => capture("jsxs", ...args);
        export const Fragment = real.Fragment;`, loader: "js" };
      if (args.path.endsWith("App")) return { contents: "export const agentConsoleStore = { openConsole() { throw new Error('Assistant side effect forbidden'); } };", loader: "js" };
      if (args.path.endsWith("BuyPointDrawer")) return { contents: "export default function Drawer() { return null; }", loader: "js" };
      return { contents: `
        const state = () => ${state};
        const read = key => { state().reads.push(key); if (!(key in state().responses)) throw new Error("Unspecified offline read " + key); return Promise.resolve(state().responses[key]); };
        const forbidden = () => { throw new Error("Mutation forbidden in availability tests"); };
        export const api = {
          listPlans: ({state}) => read("plans:" + state), planAlerts: id => read("alerts:" + id),
          planActions: id => read("actions:" + id), opportunityScan: () => read("scan"),
          doneAction: forbidden, deferAction: forbidden,
        };`, loader: "js" };
    });
  } }],
});
const require = createRequire(import.meta.url);
// Use the same CJS module identity as the compiled page for shared contexts.
const { StaticRouter } = require("react-router-dom/server.js");
const { QueryClient, QueryClientProvider } = require("@tanstack/react-query");
const Module = require("node:module"), compiled = new Module(source);
compiled.filename = source;
compiled.paths = Module._nodeModulePaths(new URL("../../", import.meta.url).pathname);
compiled._compile(built.outputFiles[0].text, source);
const Page = compiled.exports.default;
const plan = { plan_id: "synthetic-plan", symbol: "510300.SS", plan_kind: "entry", direction: "long",
  module: "A", state: "armed", entry_rule_id: "synthetic_rule", valid_until: "2026-10-08",
  thesis_cn: "合成计划原假设", invalidation_criteria_cn: "合成失效标准", invalidation_price: 90,
  target_b_price: 130, reward_risk_at_plan: 3 };
const block = { code: "ENTRY_SYNTHETIC", severity: "block", next_step_cn: "合成已保存阻断",
  rule_id: "synthetic_rule", evidence: {}, logic_provenance: "research_proxy" };
const action = { action_id: "synthetic-action", kind: "EXIT", state: "open", source_alert_code: "EXIT_TEST", nag_count: 2, due_from: "2026-10-01" };
const scanItem = { symbol: "510300.SS", display_name: "合成ETF", verdict: "waiting", verdict_cn: "合成待确认",
  best_scenario_cn: "合成条件", reward_risk_computable: false, missing_summary_cn: "尚缺确认",
  blocking_reasons: [], has_active_plan: true };
const success = data => ({ status: "success", data, dataUpdatedAt: 1_700_000_000_000 });
const failure = data => ({ status: "error", data, error: new Error("离线合成503"), dataUpdatedAt: data === undefined ? 0 : 1_700_000_000_000 });
const pending = () => ({ status: "pending", data: undefined, dataUpdatedAt: 0 });
function harness(states = {}, scanOpen = false) {
  globalThis[key] = { scanOpen, falseHooks: 0, buttons: [], reads: [], responses: {} };
  const client = new QueryClient({ defaultOptions: { queries: {
    retry: false, retryOnMount: false, refetchOnMount: false, refetchOnWindowFocus: false,
    refetchOnReconnect: false, staleTime: Infinity, gcTime: Infinity,
  } } });
  const defaults = { armed: success([]), entered: success([]), alerts: success([]), actions: success([]), scan: success({ items: [] }) };
  const keys = { armed: ["plans", "armed"], entered: ["plans", "entered"], alerts: ["planAlerts", plan.plan_id], actions: ["planActions", plan.plan_id], scan: ["opportunityScan"] };
  for (const [name, queryKey] of Object.entries(keys))
    client.getQueryCache().build(client, { queryKey }).setState({ fetchStatus: "idle", ...defaults[name], ...states[name] });
  return { client, render() {
    runtime().buttons = []; runtime().falseHooks = 0;
    return renderToStaticMarkup(React.createElement(QueryClientProvider, { client },
      React.createElement(StaticRouter, { location: "/plans" }, React.createElement(Page)))).replace(/<!-- -->/g, "");
  } };
}
const text = children => Array.isArray(children) ? children.map(text).join("") : typeof children === "string" || typeof children === "number" ? String(children) : "";
const button = name => runtime().buttons.find(p => text(p.children) === name);
function noReads() { assert.deepEqual(runtime().reads, [], "rendering must not execute API reads"); }

test("failed lists cannot become zero or no plans", () => {
  const h = harness({ armed: failure(), entered: failure() }), html = h.render();
  assert.match(html, /活跃计划<\/span><b>未知/);
  assert.match(html, /待入场计划读取失败/); assert.match(html, /持仓中计划读取失败/);
  assert.doesNotMatch(html, /还没有活跃计划/); assert.ok(button("重新读取待入场计划")); noReads(); h.client.clear();
});
test("loading differs from an empty list", () => {
  const h = harness({ armed: pending(), entered: pending() }), html = h.render();
  assert.match(html, /待入场计划加载中/); assert.match(html, /持仓中计划加载中/);
  assert.doesNotMatch(html, /还没有活跃计划/); noReads(); h.client.clear();
});
test("only successful empty lists show no active plans", () => {
  const h = harness(), html = h.render();
  assert.match(html, /活跃计划<\/span><b>0/); assert.match(html, /还没有活跃计划/);
  assert.doesNotMatch(html, /读取失败/); noReads(); h.client.clear();
});
test("partial failure preserves successful plans without claiming complete count", () => {
  const h = harness({ armed: success([plan]), entered: failure() }), html = h.render();
  assert.match(html, /合成计划原假设/); assert.match(html, /持仓中计划读取失败/);
  assert.match(html, /活跃计划<\/span><b>未知/); assert.doesNotMatch(html, /还没有活跃计划/); noReads(); h.client.clear();
});
test("failed refresh marks retained plans as old with read time", () => {
  const h = harness({ armed: failure([plan]) }), html = h.render();
  assert.match(html, /合成计划原假设/); assert.match(html, /显示上次成功读取的记录（读取于/);
  assert.match(html, /当前资料尚未更新/); assert.match(html, /活跃计划<\/span><b>未知/); noReads(); h.client.clear();
});
test("cached plans being refreshed are explicitly still old", () => {
  const h = harness({ armed: { ...success([plan]), fetchStatus: "fetching" } }), html = h.render();
  assert.match(html, /待入场计划正在更新/); assert.match(html, /显示上次成功读取/);
  assert.match(html, /活跃计划<\/span><b>未知/); noReads(); h.client.clear();
});
test("alerts and actions independently display failure and retry", () => {
  const h = harness({ armed: success([plan]), alerts: failure(), actions: failure() }), html = h.render();
  assert.match(html, /计划提醒读取失败/); assert.match(html, /不能据此认为没有风险/);
  assert.match(html, /计划待办读取失败/); assert.ok(button("重新读取计划提醒")); assert.ok(button("重新读取计划待办")); noReads(); h.client.clear();
});
test("pending alerts and actions visibly await evidence", () => {
  const h = harness({ armed: success([plan]), alerts: pending(), actions: pending() }), html = h.render();
  assert.match(html, /计划提醒加载中/); assert.match(html, /不能据此认为没有风险/);
  assert.match(html, /计划待办加载中/); noReads(); h.client.clear();
});
test("cached block and action survive failure with historical wording and existing controls", () => {
  const h = harness({ armed: success([plan]), alerts: failure([block]), actions: failure([action]) }), html = h.render();
  assert.match(html, /合成已保存阻断/); assert.match(html, /上次记录存在入场阻断提示/);
  assert.doesNotMatch(html, /本轮存在入场阻断条件/); assert.match(html, /EXIT_TEST/);
  assert.ok(button("已执行")); assert.ok(button("推迟")); noReads(); h.client.clear();
});
test("current successful block and action retain original decisions and controls", () => {
  const h = harness({ armed: success([plan]), alerts: success([block]), actions: success([action]) }), html = h.render();
  assert.match(html, /本轮存在入场阻断条件/); assert.match(html, /合成已保存阻断/);
  assert.ok(button("已执行")); assert.ok(button("推迟")); noReads(); h.client.clear();
});
test("optional scan failure differs from success with zero matching items", () => {
  const failed = harness({ scan: failure() }, true), html = failed.render();
  assert.match(html, /买点扫描读取失败/); assert.doesNotMatch(html, /当前自选无系统定义的买点/);
  assert.ok(button("重新读取买点扫描")); noReads(); failed.client.clear();
  const empty = harness({}, true); assert.match(empty.render(), /当前自选无系统定义的买点/); noReads(); empty.client.clear();
});
test("pending, refreshing or failed empty scan cannot claim no opportunities", () => {
  for (const scan of [pending(), { ...success({ items: [] }), fetchStatus: "fetching" }, failure({ items: [] })]) {
    const h = harness({ scan }, true), html = h.render();
    assert.doesNotMatch(html, /当前自选无系统定义的买点/); noReads(); h.client.clear();
  }
});
test("failed cached scan retains rows explicitly as old", () => {
  const h = harness({ scan: failure({ items: [scanItem] }) }, true), html = h.render();
  assert.match(html, /合成ETF/); assert.match(html, /买点扫描读取失败/); assert.match(html, /显示上次成功读取/);
  assert.ok(button("分析")); noReads(); h.client.clear();
});
test("actual retry handlers target existing reads and recover query state", async () => {
  const h = harness({ armed: failure([plan]), entered: failure(), alerts: failure(), actions: failure(), scan: failure() }, true);
  runtime().responses = { "plans:armed": [], "plans:entered": [], "alerts:synthetic-plan": [], "actions:synthetic-plan": [], scan: { items: [] } };
  h.render();
  for (const label of ["重新读取计划提醒", "重新读取计划待办", "重新读取买点扫描", "重新读取待入场计划", "重新读取持仓中计划"]) {
    button(label).onClick(); await new Promise(resolve => setImmediate(resolve));
  }
  assert.deepEqual(runtime().reads, ["alerts:synthetic-plan", "actions:synthetic-plan", "scan", "plans:armed", "plans:entered"]);
  const html = h.render(); assert.doesNotMatch(html, /读取失败/); assert.match(html, /还没有活跃计划/); h.client.clear();
});
