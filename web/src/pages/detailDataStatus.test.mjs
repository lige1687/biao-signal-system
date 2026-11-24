import assert from "node:assert/strict";
import { test } from "node:test";
import { readFile } from "node:fs/promises";
import { build } from "esbuild";
import { createRequire } from "node:module";

// Bundle the real component and renderer with one React identity. No temporary
// modules or API calls: a fresh node process reproduces these checks directly.
const source = await readFile(new URL("./DetailPage.tsx", import.meta.url), "utf8");
const built = await build({
  stdin: { contents: source + `
    import { createElement } from "react";
    import { renderToStaticMarkup } from "react-dom/server";
    export { createElement, renderToStaticMarkup };
  `, resolveDir: new URL(".", import.meta.url).pathname, loader: "tsx" },
  loader: { ".css": "empty" },
  bundle: true, write: false, platform: "node", format: "cjs", jsx: "automatic",
});
const mod = { exports: {} };
new Function("require", "module", "exports", built.outputFiles[0].text)(createRequire(import.meta.url), mod, mod.exports);
const { DetailDataStatus, createElement, renderToStaticMarkup } = mod.exports;
function render(data) { return renderToStaticMarkup(createElement(DetailDataStatus, { data })); }
test("fresh retrieval preserves older quote and signal dates and original warnings", () => {
  const html = render({meta:{data_time:"2026-10-01T09:30:00+08:00", last_bar_date:"2026-09-29", is_intraday_forming:true, cache_fallback_used:true, data_warnings:["服务端原文：行情存在缺失日", "原始警告：<请核对>"]}, assessment:{as_of:"2026-09-28"}});
  for (const expected of ["读取时间", "2026", "盘中", "缓存兜底", "行情日", "2026-09-29", "信号判定日", "2026-09-28", "服务端原文：行情存在缺失日", "原始警告：&lt;请核对&gt;"]) assert.ok(html.includes(expected),expected);
});
test("missing dates stay explicitly unknown and rendering performs no request", () => {
  const original = globalThis.fetch;
  let calls=0;
  globalThis.fetch=()=>{calls++;throw new Error("network forbidden");};
  try {
    const html=render({meta:{data_time:null,last_bar_date:null,data_warnings:[]},assessment:{as_of:null}});
    assert.equal((html.match(/未提供/g)??[]).length,3);
    assert.equal(calls,0);
  } finally { globalThis.fetch=original; }
});
