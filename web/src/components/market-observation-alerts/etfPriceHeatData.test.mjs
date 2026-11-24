import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";
import { readFile } from "node:fs/promises";

const result = await build({ entryPoints: [new URL("./etfPriceHeatData.ts", import.meta.url).pathname],
  bundle: true, platform: "node", format: "esm", write: false });
const { parseEtfPriceHeatSnapshot } = await import(`data:text/javascript;base64,${Buffer.from(result.outputFiles[0].text).toString("base64")}`);

function fixture() {
  const point = { date: "2026-11-06", price: 1.234, heat: 65, activity: 70,
    amountSharePct: 0.23, relativeTurnover: 1.2, turnoverSurge: 0.8,
    heatPeak20: 80, heatDrop20: 15, priceHigh20: true, divergence: true };
  return { schemaVersion: 1, generatedAt: "2026-11-08T20:00:00+08:00", snapshotAsOf: "2026-11-06",
    sourceLabel: "固定历史快照", sourceNote: "行情截至11月6日", priceNote: "价格复权待核",
    cards: ["512480", "515880", "159915", "510300"].map((symbol, i) => ({ symbol, name: `ETF ${symbol}`,
      kind: i < 2 ? "sector" : "index", turnoverComparison: i === 3 ? "自身换手" : "相对510300换手",
      points: [{ ...point }], research: { matureDays: 20, spacedEvents: 5, mean20: -5.77,
        otherHighMean20: 3.69, spacedMean20: -1.74 } })) };
}

test("accepts four dated cards and preserves last-day missing fields", () => {
  const x = fixture();
  x.cards[0].points[0].heat = null;
  x.cards[0].points[0].activity = null;
  const parsed = parseEtfPriceHeatSnapshot(x);
  assert.equal(parsed.cards[0].points[0].heat, null);
  assert.equal(parsed.cards[0].points[0].activity, null);
});

test("rejects duplicate or invalid point dates", () => {
  const x = fixture();
  x.cards[0].points.push({ ...x.cards[0].points[0] });
  assert.throws(() => parseEtfPriceHeatSnapshot(x));
  x.cards[0].points[1].date = "2026-02-30";
  assert.throws(() => parseEtfPriceHeatSnapshot(x));
});

test("rejects invalid or out-of-range readings and duplicate symbols", () => {
  for (const [field, value] of [["heat", 101], ["activity", -1], ["price", Infinity], ["relativeTurnover", NaN], ["divergence", "yes"]]) {
    const x = fixture(); x.cards[0].points[0][field] = value;
    assert.throws(() => parseEtfPriceHeatSnapshot(x), field);
  }
  const x = fixture(); x.cards[1].symbol = "512480";
  assert.throws(() => parseEtfPriceHeatSnapshot(x));
});

test("the shipped snapshot parses and retains its four distinct dates, scores and research counts", async () => {
  const source = JSON.parse(await readFile(new URL("../../../public/research/etf-price-heat-20261108/data.json", import.meta.url), "utf8"));
  const snapshot = parseEtfPriceHeatSnapshot(source);
  assert.equal(snapshot.snapshotAsOf, "2026-11-06");
  assert.deepEqual(snapshot.cards.map(c => c.research.spacedEvents), [5, 6, 5, 7]);
  assert.deepEqual(snapshot.cards.map(c => c.points.at(-1).heat.toFixed(1)), ["51.8", "46.5", "57.4", "56.0"]);
  assert.deepEqual(snapshot.cards.map(c => c.points.at(-1).divergence), [false, false, false, false]);
  assert.ok(snapshot.cards[0].points.some(p => p.heat === null), "pre-warmup heat stays missing");
});
