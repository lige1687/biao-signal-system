import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";

const bundle = await build({ entryPoints: [new URL("./breadthInterpretation.ts", import.meta.url).pathname],
  bundle: true, format: "esm", platform: "node", write: false });
const { breadthInterpretation, breadthChangeAnnotations } = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);

test("only known backend codes receive a specific reading", () => {
  const expected = { recovering: "supportive", expanding: "supportive", improving: "supportive",
    retreating: "caution", weakening: "caution", contracting: "caution", flat: "neutral", mixed: "neutral" };
  for (const [code, tone] of Object.entries(expected)) {
    const result = breadthInterpretation({ state: { code, label: "upstream", summary: "upstream", tone: "unknown" } });
    assert.equal(result.tone, tone, code);
    assert.ok(result.headline && result.meaning && result.watch);
    assert.doesNotMatch(`${result.headline}${result.meaning}${result.watch}`, /买入|卖出|见顶|见底/);
  }
});

test("missing and new codes stay unknown", () => {
  assert.equal(breadthInterpretation(null).tone, "unknown");
  assert.equal(breadthInterpretation({ state: { code: "new_code" } }).tone, "unknown");
});

test("a historical change mark does not depend on the length of its later run", () => {
  const point = (code) => ({ state: { code } });
  const dates = Array.from({ length: 100 }, (_, i) => `d${i}`);
  const base = new Map(dates.map((date, i) => [date, point(i < 10 ? "flat" : i < 20 ? "improving" : "flat")]));
  const short = breadthChangeAnnotations(dates.slice(0, 21), dates.map(() => 100), base);
  const long = breadthChangeAnnotations(dates, dates.map(() => 100), base);
  assert.deepEqual(short, long);
  assert.deepEqual(long.map((mark) => [mark.date, mark.label]), [["d10", "参与回升"]]);
});
