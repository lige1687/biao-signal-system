import assert from "node:assert/strict";
import { test } from "node:test";
import { readFile } from "node:fs/promises";
import { createRequire } from "node:module";
import { build } from "esbuild";

// Render the actual private card with its production JSX and one React instance.
const source = await readFile(new URL("./FundamentalsPage.tsx", import.meta.url), "utf8");
const built = await build({
  stdin: {
    contents: source + `
      import { createElement } from "react";
      import { renderToStaticMarkup } from "react-dom/server";
      export { CommodityCard, createElement, renderToStaticMarkup };
    `,
    resolveDir: new URL(".", import.meta.url).pathname,
    loader: "tsx",
  },
  bundle: true, write: false, platform: "node", format: "cjs", jsx: "automatic", loader: { ".css": "empty" },
});
const mod = { exports: {} };
new Function("require", "module", "exports", built.outputFiles[0].text)(createRequire(import.meta.url), mod, mod.exports);
const { CommodityCard, createElement, renderToStaticMarkup } = mod.exports;
const oldCache = { copper_gold: 0.00190005, crude_gold: 0.035, copper: 3.8001, gold: 2000, crude: 70 };
const meta = {
  quote_date: "2026-09-29", retrieved_at_utc: "2026-10-01T08:00:00+00:00", provider: "Yahoo Finance via yfinance",
  latest_dates: { "HG=F": "2026-09-30", "GC=F": "2026-09-29", "CL=F": "2026-09-30" },
  tickers: { copper: "HG=F", gold: "GC=F", crude: "CL=F" }, publication_time: "unknown", quote_units: "unknown", roll_contract_identity: "unknown", data_usage_license: "unknown",
};
const render = data => renderToStaticMarkup(createElement(CommodityCard, { data }));

test("card distinguishes common quote day, individual latest days, and UTC read time", () => {
  const html = render({ ...oldCache, meta });
  for (const text of ["共同报价日：2026-09-29", "读取时间（UTC）：2026-10-01T08:00:00+00:00", "读取时间不等于行情日期或首次发布时间", "三项报价取同一共同日期", "HG=F", "GC=F", "CL=F", "各源最新报价日：铜 2026-09-30", "3.800100", "2000.000000", "70.000000", "0.001900", "0.035000"]) assert.ok(html.includes(text), text);
  for (const text of ["报价单位：未提供或未核实", "首次发布时间：未提供或未核实", "合约换月身份：未提供或未核实"]) assert.ok(html.includes(text), text);
});

test("old five-field cache still displays values without inventing date, ticker or units", () => {
  const html = render(oldCache);
  for (const text of ["0.001900", "0.035000", "共同报价日：未提供或未核实", "旧缓存未提供日期信息，无法确认三项报价是否同日", "来源：未提供或未核实"]) assert.ok(html.includes(text), text);
  assert.ok(!html.includes("三项报价取同一共同日期") && !html.includes("HG=F") && !html.includes("2026-09-29"));
});

test("meaning stays narrative, explains both sides, and supplies no universal trading threshold", () => {
  for (const data of [oldCache, { ...oldCache, meta }, null]) {
    const html = render(data);
    for (const text of ["铜价、油价或作为分母的金价变动都会影响比值", "铜价不动、金价下降，铜金比也会上升", "单个数值不能判断趋势", "不能直接断言需求回暖或通胀上升", "无通用买卖阈值", "不参与技术判定"]) assert.ok(html.includes(text), text);
    for (const text of ["铜金比升=工业需求回暖", "油金比升=通胀预期升", "无量纲", "分位"]) assert.ok(!html.includes(text), text);
  }
});

test("unavailable and nonfinite values never appear as a valid numeric reading; negative crude stays visible", () => {
  assert.ok(render(null).includes("暂不可用") && render(undefined).includes("暂不可用"));
  const invalid = render({ ...oldCache, copper_gold: NaN, crude_gold: Infinity });
  assert.ok(invalid.includes("暂不可用") && !invalid.includes("NaN") && !invalid.includes("Infinity"));
  const negative = render({ ...oldCache, crude: -37, crude_gold: -37 / 2000, meta });
  assert.ok(negative.includes("-37.000000") && negative.includes("-0.018500"));
});

test("render never requests external data", () => {
  const originalFetch = globalThis.fetch;
  let requests = 0;
  globalThis.fetch = () => { requests++; throw new Error("No network allowed"); };
  try { render({ ...oldCache, meta }); render(oldCache); assert.equal(requests, 0); }
  finally { globalThis.fetch = originalFetch; }
});


test("compact reading stays visible while detailed source limits are expandable", () => {
  for (const data of [{ ...oldCache, meta }, oldCache]) {
    const html = render(data);
    const visible = html.slice(0, html.indexOf("<details"));
    assert.ok(visible.includes("共同报价日：") && visible.includes("报价单位：未提供或未核实") && visible.includes("无通用买卖阈值"));
    assert.ok(!visible.includes("原始报价") && !visible.includes("读取时间（UTC）"));
    assert.ok(html.includes("<summary>资料口径与限制</summary>") && !html.includes("<details open"));
    assert.ok(html.includes("数据使用许可：未提供或未核实") && html.includes("软件包许可不代表行情数据使用许可"));
  }
  assert.ok(render({ ...oldCache, meta }).includes('href="https://finance.yahoo.com/"'));
  assert.ok(!render(oldCache).includes('href="https://finance.yahoo.com/"'));
});
