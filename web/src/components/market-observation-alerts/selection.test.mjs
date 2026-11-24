import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";
const result = await build({ entryPoints: [new URL("./selection.ts", import.meta.url).pathname], bundle: true,
  platform: "node", format: "esm", write: false });
const { CORE_IDS, LEGACY_DEFAULT_IDS, parseSelection, normalizeSelection, migrateSelection } = await import(`data:text/javascript;base64,${Buffer.from(result.outputFiles[0].contents).toString("base64")}`);
const json = JSON.stringify;
test("fresh homepage contains exactly the four requested ERP and breadth cards", () => {
  assert.deepEqual(parseSelection(null, null), ["erp-cn", "breadth-cn", "erp-us", "breadth-us"]);
});
test("old complete automatic sets shrink and explicitly added cards survive", () => {
  for (const defaults of [LEGACY_DEFAULT_IDS, LEGACY_DEFAULT_IDS.slice(0,15), LEGACY_DEFAULT_IDS.slice(0,15).filter(id => !["cn-session","cn-institution"].includes(id))]) {
    assert.deepEqual(migrateSelection(null,json(defaults),null,null), CORE_IDS);
    assert.deepEqual(migrateSelection(null,json([...defaults,"aaii"]),null,null), [...CORE_IDS,"aaii"]);
  }
});
test("explicit old pins inside defaults are retained only if still selected", () => {
  assert.deepEqual(migrateSelection(null,json(LEGACY_DEFAULT_IDS),json(["vix","aaii"]),null), [...CORE_IDS,"vix"]);
});
test("custom subset and intentionally empty preferences are not reset", () => {
  for (const ids of [["breadth-cn","hv-us"],[]]) assert.deepEqual(migrateSelection(null,json(ids),json(["vix"]),null),ids);
  assert.deepEqual(migrateSelection(null,json(["erp-cn","cn-style-relative"]),null,null),["erp-cn","cn-style-relative"]);
});
test("hidden old cards stay off the homepage, including core and explicit pins", () => {
  assert.deepEqual(migrateSelection(null,json(LEGACY_DEFAULT_IDS),json(["vix"]),json(["breadth-us","vix"])),["erp-cn","breadth-cn","erp-us"]);
});
test("v2 is canonical and old keys cannot restore removed cards", () => {
  for (const ids of [["breadth-cn"],[],["us-semiconductor-relative","cn-300etf-pcr-volume"]])
    assert.deepEqual(migrateSelection(json(ids),json(LEGACY_DEFAULT_IDS),json(["vix"]),json(["breadth-cn"])),ids);
});
test("malformed preferences fall back safely; duplicates and unknown ids are rejected", () => {
  for (const malformed of ["{bad", "null", "{}", '"erp-cn"']) assert.deepEqual(migrateSelection(malformed,null,null,null),CORE_IDS);
  assert.deepEqual(normalizeSelection(["vix","vix","unknown",42,"industry-structure-cn","cn-300etf-pcr-volume"]),["vix","industry-structure-cn","cn-300etf-pcr-volume"]);
  assert.deepEqual(migrateSelection(null,"{bad",json(["aaii"]),null),[...CORE_IDS,"aaii"]);
});

test("daily and monthly concentration pins migrate to one canonical card", () => {
  assert.deepEqual(normalizeSelection(["cn-daily-amount-top5","vix","cn-daily-amount-top10","turnover-concentration"]), ["turnover-concentration","vix"]);
  assert.deepEqual(migrateSelection('["cn-daily-amount-top5","cn-daily-amount-top10"]',null,null,null),["turnover-concentration"]);
});

test("industry turnover pins coalesce and old per-industry hides do not hide the group", () => {
  const oldPins = ["vix", "cn-industry-turnover-bk0448", "cn-industry-turnover-bk0428", "cn-industry-turnover-above-own-p95", "breadth-cn"];
  const expected = ["vix", "cn-industry-turnover", "breadth-cn"];
  assert.deepEqual(migrateSelection(json(oldPins), null, null, null), expected);
  assert.deepEqual(migrateSelection(null, json(oldPins), null, json(["cn-industry-turnover-bk0448"])), expected);
  assert.deepEqual(migrateSelection(null, json(oldPins), null, json(["cn-industry-turnover"])), ["vix", "breadth-cn"]);
});
