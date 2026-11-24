import assert from "node:assert/strict";
import test from "node:test";
import { build } from "esbuild";

const bundle = await build({ entryPoints: ["src/components/market-observation-panel/diagnostics.ts"], bundle: true, platform: "node", format: "esm", write: false });
const { buildReminders } = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);
const date = "2026-11-06", now = new Date("2026-11-09T06:00:00Z");
function card(value, extra = {}) { return { frequency: "daily", unit: "%", sourceName: "fixture", points: [{ date, value }], window: 20, observations: 20, current_zscore: null, current_percentile: null, ...extra }; }
function packet() { return { schemaVersion: 1, generatedAt: "2026-11-09", cards: {
  "vix-term-structure": card(1.1), "hv-us": card(25, { lines: [{ id: "hv60", label: "60日", points: [{ date, value: 20 }] }] }),
  "ofr-fsi": card(-.2), "hy-oas": card(3.9),
  "cn-daily-amount-top5": card(40, { points: [{ date, value: 40, ma20: 36 }] }), "focus-momentum": card(-6),
  "cn-financing": card(7.9), "cn-index-futures-basis": card(-9, { lines: [{ id: "ih", label: "IH", points: [{ date, value: -9 }] }] }),
} }; }
test("all three exact reminder combinations and equality boundaries", () => {
  const input = packet();
  const on = buildReminders(input, now);
  assert.deepEqual(on.map(item => item.state), ["present", "present", "present"]);
  assert.match(on[0].title, /短期去杠杆恐慌/);
  assert.match(on[1].title, /局部抱团拥挤/);
  assert.match(on[2].title, /蓝筹对冲贴水深/);
  input.cards["vix-term-structure"].points[0].value = 1;
  input.cards["focus-momentum"].points[0].value = -5;
  input.cards["cn-financing"].points[0].value = 8;
  assert.deepEqual(buildReminders(input, now).map(item => item.state), ["absent", "absent", "absent"]);
});
test("old or nonaligned legs remain unavailable", () => {
  const input = packet();
  input.cards["ofr-fsi"].points[0].date = "2026-10-01";
  input.cards["focus-momentum"].points[0].date = "2026-11-05";
  input.cards["cn-index-futures-basis"].lines[0].points[0].date = "2026-11-05";
  assert.deepEqual(buildReminders(input, now).map(item => item.state), ["unavailable", "unavailable", "unavailable"]);
});
