import test from "node:test";
import assert from "node:assert/strict";
import { build } from "esbuild";

// Bundle the production TypeScript in memory, without creating files outside this task's paths.
const bundle = await build({ entryPoints: [new URL("./preferences.ts", import.meta.url).pathname], bundle: true,
  format: "esm", platform: "node", write: false });
const { normalizePins, parsePins, readPins, writePins, PINS_STORAGE_KEY } =
  await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);

test("catalogue preserves old families, adds three nonduplicate observations and refuses unavailable inputs", async () => {
  const catalogBundle = await build({ entryPoints: [new URL("./catalog.ts", import.meta.url).pathname], bundle: true,
    format: "esm", platform: "node", write: false });
  const catalog = await import(`data:text/javascript;base64,${Buffer.from(catalogBundle.outputFiles[0].text).toString("base64")}`);
  assert.equal(catalog.CANDIDATE_IDS.size, 27);
  assert.deepEqual([...catalog.CANDIDATE_IDS].sort(), Array.from({ length: 27 }, (_, index) => `C${String(index + 1).padStart(2, "0")}`));
  assert.equal(new Set(catalog.OBSERVATION_CATALOG.map((item) => item.id)).size, catalog.OBSERVATION_CATALOG.length);
  assert.equal(catalog.READABLE_IDS.size, 21);
  for (const id of ["earnings-breadth", "industry-relative-value", "equity-funding-cost"]) assert.equal(catalog.OBSERVATION_BY_ID.get(id).readable, false);
  assert.equal(catalog.OBSERVATION_BY_ID.get("chinext-pe").readable, false);
  assert.equal(catalog.OBSERVATION_BY_ID.get("star50-pe").readable, false);
  assert.equal(catalog.OBSERVATION_BY_ID.get("nasdaq100-pe").readable, false);
  assert.equal(catalog.OBSERVATION_BY_ID.get("pmi-us").readable, false);
  assert.ok(catalog.observationReadingRank(catalog.OBSERVATION_BY_ID.get("ofr-fsi"))
    < catalog.observationReadingRank(catalog.OBSERVATION_BY_ID.get("new-high-low")));
  assert.match(catalog.OBSERVATION_BY_ID.get("baker-wurgler").limitation, /2025-10该列缺失/);
});

test("new visitors get a small default set; an explicitly empty or saved selection is preserved", () => {
  assert.deepEqual(parsePins(null), { ids: ["cn-financing", "vix", "hy-oas", "turnover-concentration"], warning: null });
  assert.deepEqual(parsePins('[]'), { ids: [], warning: null });
  assert.deepEqual(normalizePins(["vix", "vix", "unknown", 2, "focus-momentum"]), ["vix", "focus-momentum"]);
  assert.deepEqual(parsePins('["vix","unknown","vix","hs300-pe"]').ids, ["vix", "hs300-pe"]);
  assert.deepEqual(parsePins('{"id":"vix"}').ids, []);
  assert.match(parsePins("[broken").warning, /损坏/);
});

test("storage failure leaves a usable in-memory choice and does not claim persistence", () => {
  const blocked = { getItem() { throw Error("blocked"); }, setItem() { throw Error("blocked"); } };
  assert.deepEqual(readPins(blocked).ids, []);
  assert.match(readPins(blocked).warning, /存储不可用/);
  assert.equal(writePins(blocked, ["vix"]), false);
  const saved = new Map();
  const storage = { getItem: (key) => saved.get(key) ?? null, setItem: (key, value) => saved.set(key, value) };
  assert.equal(writePins(storage, ["vix", "vix", "invalid"]), true);
  assert.equal(saved.get(PINS_STORAGE_KEY), '["vix"]');
  assert.deepEqual(readPins(storage).ids, ["vix"]);
});
