import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";
import { readFile } from "node:fs/promises";

async function load(file) {
  const result = await build({ entryPoints: [new URL(file, import.meta.url).pathname],
    bundle: true, platform: "node", format: "esm", write: false });
  return import(`data:text/javascript;base64,${Buffer.from(result.outputFiles[0].text).toString("base64")}`);
}
const { thumbnailWindow, historyState, microThumbnailId, microThumbnail, breadthThumbnail } = await load("./indicatorThumbnailData.ts");
const { parseMicrostructure } = await load("./microstructureData.ts");
const { MICRO_INDICATORS } = await load("./indicatorCatalog.ts");

test("thumbnail history keeps the current missing reading and the gaps in each series", () => {
  const dates = ["2026-11-02", "2026-11-03", "2026-11-04", "2026-11-05"];
  const values = [2, 3, 4, null];
  const window = thumbnailWindow({ dates, lines: [{ name: "走势", color: "#123456", values }],
    references: [{ name: "参照", color: "#987654", values: [1, 1, null, 1] }] }, 3);
  assert.deepEqual(window.dates, dates.slice(-3));
  assert.deepEqual(window.lines[0].values, [3, 4, null]);
  assert.deepEqual(window.references[0].values, [1, null, 1]);
  assert.equal(historyState(window.lines), "chart");
});

test("a snapshot or a run of isolated readings never becomes a fake trend", () => {
  const line = values => [{ name: "走势", color: "#123456", values }];
  assert.equal(historyState(line([null, null])), "empty");
  assert.equal(historyState(line([null, 4, null])), "snapshot");
  assert.equal(historyState(line([2, null, 4])), "disconnected");
  assert.equal(historyState(line([2, 3, null, 4])), "chart");
});

test("concentration thumbnail uses the actual daily top-five series and its original readout", async () => {
  const source = new URL("../../../public/research/microstructure-observations-20261108/equity.json", import.meta.url);
  const packet = parseMicrostructure(JSON.parse(await readFile(source, "utf8")));
  const id = microThumbnailId("turnover-concentration");
  assert.equal(id, "cn-daily-amount-top5");
  const card = packet.cards.find(entry => entry.id === id);
  assert.ok(card);
  const thumb = microThumbnail(card);
  const latest = card.points.at(-1);
  assert.equal(thumb.date, latest.date);
  assert.equal(thumb.value, latest.value === null ? "待补" : `${latest.value.toFixed(2)}%`);
  assert.deepEqual(thumb.chart.lines[0].values, card.points.map(p => p.value));
  for (const [mode, frequency] of [["cn-daily-amount-top5", "daily"], ["cn-daily-amount-top10", "daily"], ["cn-monthly-amount-top5", "monthly"]]) {
    assert.equal(packet.cards.find(entry => entry.id === mode)?.frequency, frequency, mode);
  }
});

test("breadth uses matched, validated dynamic reference rails and keeps missing values", () => {
  const history = [
    { date: "2026-11-02", breadth_50: 40 },
    { date: "2026-11-03", breadth_50: 45 },
    { date: "2026-11-04", breadth_50: null },
  ];
  const observations = history.map(({ date }, index) => ({ date, horizons: {
    50: { status: "ready", sample_count: index === 0 ? 200 : 252, lower: 20, upper: 80 },
  } }));
  const result = breadthThumbnail("CN_ALL_A", { history, observation: { history: observations } });
  assert.equal(result.date, "2026-11-04");
  assert.equal(result.value, "待补");
  assert.deepEqual(result.chart.lines[0].values, [40, 45, null]);
  assert.deepEqual(result.chart.lower, [null, 20, null]);
  assert.deepEqual(result.chart.upper, [null, 80, null]);
});

test("every readable microstructure entry has a real source packet with an aligned thumbnail", async () => {
  const packets = await Promise.all(["funding", "equity", "derivatives"].map(async (branch) => {
    const source = new URL(`../../../public/research/microstructure-observations-20261108/${branch}.json`, import.meta.url);
    return parseMicrostructure(JSON.parse(await readFile(source, "utf8")));
  }));
  const byId = new Map(packets.flatMap((packet) => packet.cards).map((card) => [card.id, card]));
  for (const entry of MICRO_INDICATORS.filter(({ readable }) => readable)) {
    const card = byId.get(entry.id);
    assert.ok(card, entry.id);
    assert.equal(card.market, entry.market, entry.id);
    const { chart, date } = microThumbnail(card);
    assert.equal(chart.dates.at(-1), date, entry.id);
    assert.equal(chart.lines[0].values.length, chart.dates.length, entry.id);
  }
});
