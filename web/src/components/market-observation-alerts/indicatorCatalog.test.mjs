import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";
import { readFileSync } from "node:fs";

async function load(file) {
  const result = await build({
    entryPoints: [new URL(file, import.meta.url).pathname],
    bundle: true,
    platform: "node",
    format: "esm",
    write: false,
  });
  return import(`data:text/javascript;base64,${Buffer.from(result.outputFiles[0].text).toString("base64")}`);
}

const { OBSERVATION_CATALOG } = await load("../observation-library/catalog.ts");
const { INDICATOR_CATALOG, INDICATOR_BY_ID, INDICATOR_CATEGORIES, filterIndicators } = await load("./indicatorCatalog.ts");

const extras = [
  ["breadth-cn", "cn", "participation"],
  ["breadth-us", "us", "participation"],
  ["hv-cn", "cn", "risk"],
  ["hv-us", "us", "risk"],
  ["dr007", "cn", "funding"],
  ["cn-session", "cn", "participation"],
  ["cn-institution", "cn", "funding"],
  ["cn-style-relative", "cn", "style"],
  ["us-semiconductor-relative", "us", "style"],
  ["us-equal-weight-relative", "us", "style"],
  ["vix-term-structure", "us", "risk"],
  ["industry-structure-cn", "cn", "style"],
];

test("catalog has unique IDs, all legacy indicators and all six categories", () => {
  assert.equal(new Set(INDICATOR_CATALOG.map(({ id }) => id)).size, INDICATOR_CATALOG.length);
  assert.equal(INDICATOR_BY_ID.size, INDICATOR_CATALOG.length);
  for (const { id } of OBSERVATION_CATALOG) assert.ok(INDICATOR_BY_ID.has(id), id);
  assert.deepEqual(INDICATOR_CATEGORIES.map(({ id, label }) => [id, label]), [
    ["valuation", "估值与股债"],
    ["participation", "市场参与"],
    ["risk", "波动与信用"],
    ["funding", "资金与情绪"],
    ["style", "风格与行业"],
    ["economy", "盈利与经济"],
  ]);
});

test("existing groups and additional cards use the agreed categories and markets", () => {
  const byGroup = {
    valuation: "valuation", participation: "participation", credit: "risk",
    positioning: "funding", earnings: "economy", cycle: "economy",
  };
  for (const { id, group, market } of OBSERVATION_CATALOG) {
    const item = INDICATOR_BY_ID.get(id);
    const category = ["equal-weight-spread", "industry-diffusion"].includes(id) ? "style" : byGroup[group];
    assert.equal(item.category, category, id);
    assert.equal(item.market, market, id);
  }
  for (const [id, market, category] of extras) {
    const item = INDICATOR_BY_ID.get(id);
    assert.ok(item, id);
    assert.equal(item.market, market, id);
    assert.equal(item.category, category, id);
    assert.equal(item.readable, true, id);
  }
});

test("pending entries preserve the missing-data explanation and require opt-in", () => {
  const pending = OBSERVATION_CATALOG.filter(({ readable }) => !readable);
  assert.ok(pending.length);
  const defaultIds = new Set(filterIndicators({}).map(({ id }) => id));
  const allIds = new Set(filterIndicators({ includePending: true }).map(({ id }) => id));
  for (const { id, limitation } of pending) {
    assert.equal(INDICATOR_BY_ID.get(id).readable, false, id);
    assert.equal(INDICATOR_BY_ID.get(id).limitation, limitation, id);
    assert.ok(!defaultIds.has(id), id);
    assert.ok(allIds.has(id), id);
  }
});

test("search finds both market breadth cards by either Chinese name and matches ETF symbols", () => {
  for (const query of ["广度", "宽度"]) {
    assert.deepEqual(filterIndicators({ query, category: "participation" }).map(({ id }) => id).sort(),
      ["breadth-cn", "breadth-us"]);
  }
  for (const [query, id] of [["512100", "cn-style-relative"], [" smh ", "us-semiconductor-relative"], ["RSP", "us-equal-weight-relative"]]) {
    assert.ok(filterIndicators({ query }).some((item) => item.id === id));
  }
});

test("cross-market filter selects only catalog entries scoped to cross-market observation", () => {
  for (const market of ["cn", "us", "global"]) {
    assert.deepEqual(filterIndicators({ market, includePending: true }), INDICATOR_CATALOG.filter((item) => item.market === market));
  }
  assert.ok(filterIndicators({ market: "global" }).some(({ id }) => id === "ofr-fsi"));
});

test("filter accepts a supplied indicator collection", () => {
  const base = INDICATOR_BY_ID.get("breadth-cn");
  const extra = { ...base, id: "fixture", label: "新增指标", keywords: "样例" };
  assert.deepEqual(filterIndicators({ market: "cn", query: "样例" }, [extra]), [extra]);
  assert.deepEqual(filterIndicators({}, []), []);
});

test("concentration has one browse entry with daily and monthly search aliases", () => {
  assert.ok(INDICATOR_BY_ID.has("turnover-concentration"));
  assert.ok(!INDICATOR_BY_ID.has("cn-daily-amount-top5"));
  assert.ok(!INDICATOR_BY_ID.has("cn-daily-amount-top10"));
  assert.ok(!INDICATOR_BY_ID.has("cn-monthly-amount-top5"));
  for (const query of ["成交额集中度","每日 前5%","月度","top10"]) {
    assert.ok(filterIndicators({ query }).some(({id}) => id === "turnover-concentration"),query);
  }
});

test("industry turnover exposes one searchable entry backed by the six chosen series", async () => {
  const { INDUSTRY_TURNOVER_OPTIONS } = await load("./industryTurnoverOptions.ts");
  const packet = JSON.parse(readFileSync(new URL("../../../public/research/microstructure-observations-20261108/equity.json", import.meta.url)));
  assert.deepEqual(INDUSTRY_TURNOVER_OPTIONS.map(({ label }) => label),
    ["通信设备", "半导体设备", "半导体材料", "有色金属", "电力", "电网设备"]);
  assert.deepEqual(INDICATOR_CATALOG.filter(({ id }) => id.startsWith("cn-industry-turnover")).map(({ id }) => id),
    ["cn-industry-turnover"]);
  assert.equal(INDICATOR_BY_ID.has("cn-all-industry-independent-float-turnover"), false);
  for (const { id, label } of INDUSTRY_TURNOVER_OPTIONS) {
    assert.deepEqual(filterIndicators({ query: `换手率 ${label}` }).map(item => item.id), ["cn-industry-turnover"]);
    assert.equal(packet.cards.find(card => card.id === id)?.title, `${label}日换手率`);
  }
  assert.deepEqual(filterIndicators({ query: "换手率 石油" }), []);
});
