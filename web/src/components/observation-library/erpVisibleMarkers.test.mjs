import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";

const bundle = await build({ entryPoints: [new URL("./erpVisibleMarkers.ts", import.meta.url).pathname],
  bundle: true, platform: "node", format: "esm", write: false });
const { erpEventsForZoom } = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);

test("zoom restores a crossing hidden behind an earlier group representative", () => {
  const before = { id: "early", date: "2020-01-03", kind: "upper", sigma: 1.5 };
  const visible = { id: "visible", date: "2020-03-06", kind: "upper", sigma: 2 };
  const events = [before, visible];
  const groups = [{ representative: before, members: events, count: 2, endDate: visible.date }];
  assert.deepEqual(erpEventsForZoom(events, groups, true), [before]);
  assert.deepEqual(erpEventsForZoom(events, groups, true, 20, 60), events);
  assert.deepEqual(erpEventsForZoom(events, groups, false), events);
  assert.equal(events[1], visible);
});
