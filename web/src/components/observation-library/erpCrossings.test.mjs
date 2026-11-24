import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";

const bundle = await build({ entryPoints: [new URL("./erpCrossings.ts", import.meta.url).pathname], bundle: true,
  platform: "node", format: "esm", write: false });
const { erpCrossings } = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);
const row = (date, value, upper = 2, lower = -2) => ({ date, value, upper, lower, middle: 0, sigma: 1, z: value, n: 100 });

test("first usable row and persistent excursions are not repeated events", () => {
  assert.deepEqual(erpCrossings([row("2025-01-03", 3), row("2025-01-10", 4), row("2025-01-17", 1),
    row("2025-01-24", 3), row("2025-01-31", 4)]).map(p => p.date), ["2025-01-24"]);
});
test("strict edge, missing data, and historical prefix", () => {
  const rows = [row("2025-01-03", 2), row("2025-01-10", 3), row("2025-01-17", 2),
    row("2025-01-24", null), row("2025-01-31", 3), row("2025-02-07", -2), row("2025-02-14", -3)];
  assert.deepEqual(erpCrossings(rows).map(p => [p.date, p.kind]), [["2025-01-10", "upper"], ["2025-02-14", "lower"]]);
  assert.deepEqual(erpCrossings(rows.slice(0, 3)), erpCrossings(rows).slice(0, 1));
  assert.deepEqual(erpCrossings([row("2025-01-03", 0, null), row("2025-01-10", 3)]), []);
});
test("a missing week does not create a crossing across a 14-day gap", () => {
  assert.deepEqual(erpCrossings([row("2025-01-03", 1), row("2025-01-17", 3)]), []);
  assert.deepEqual(erpCrossings([row("2025-01-03", 1), row("2025-01-10", 3)]).map(p => p.date), ["2025-01-10"]);
});
