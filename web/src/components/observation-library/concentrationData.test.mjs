import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { build } from "esbuild";

const bundle = await build({ entryPoints: [new URL("./concentrationData.ts", import.meta.url).pathname],
  bundle: true, platform: "node", format: "esm", write: false });
const { parseConcentration, fromConcentration } = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);
const snapshot = JSON.parse(readFileSync(new URL("../../../public/research/turnover-concentration/observation.v1.json", import.meta.url)));

test("reviewed monthly snapshot keeps all unknown months and exposes only its dated historical reading", () => {
  const data = parseConcentration(snapshot);
  const reading = fromConcentration(data);
  assert.equal(data.points.length, 129);
  assert.equal(data.points.filter(p => p.value === null).length, 45);
  assert.equal(reading.date, "2026-09");
  assert.ok(Math.abs(reading.value - 42.15817807057034) < 1e-10);
  assert.equal(reading.points.filter(p => p.date >= "2023-01" && p.date < "2026-08").every(p => p.value === null), true);
  assert.equal(data.current, null);
  assert.match(reading.status, /不自动更新/);
});

test("an unavailable last month stays unavailable instead of borrowing an old value", () => {
  const data = structuredClone(snapshot);
  data.points.at(-1).value = null;
  data.points.at(-1).missingDays = 1;
  const reading = fromConcentration(parseConcentration(data));
  assert.equal(reading.date, "2026-09");
  assert.equal(reading.value, null);
  assert.equal(reading.change, null);
});

test("a finite share cannot conceal incomplete input, an invalid pool or missing calendar month", () => {
  for (const key of ["missingDays", "invalidRows", "amountConflicts", "extraCalendarDays", "sourceMissingDates"]) {
    const data = structuredClone(snapshot);
    data.points.at(-1)[key] = 1;
    assert.throws(() => parseConcentration(data), /覆盖/);
  }
  for (const mutate of [
    d => { d.points.at(-1).value = 1.01; },
    d => { d.points.at(-1).k += 1; },
    d => { d.points.splice(1, 1); },
    d => { d.asOf = "2026-10-23"; },
  ]) {
    const data = structuredClone(snapshot); mutate(data);
    assert.throws(() => parseConcentration(data));
  }
});
