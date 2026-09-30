import assert from "node:assert/strict";
import { test } from "node:test";
import { build } from "esbuild";

const built = await build({ entryPoints: [new URL("./overviewModel.ts", import.meta.url).pathname], bundle: true, write: false, platform: "node", format: "esm" });
const model = await import(`data:text/javascript;base64,${Buffer.from(built.outputFiles[0].contents).toString("base64")}`);

test("overview preserves existing deep links and filters", () => {
  for (const [query, expected] of [
    ["", "overview"], ["tab=overview", "overview"], ["tab=legacy", "legacy"],
    ["factor=a%401.0.0", "catalog"], ["experiment=e1", "experiments"],
    ["project=p1", "experiments"], ["category=宽度", "catalog"],
    ["q=均线", "catalog"], ["tab=unknown", "overview"],
  ]) assert.equal(model.factorView(new URLSearchParams(query)), expected, query);
});

test("catalog action follows only completed experiments linked to the exact version", () => {
  const item = (reference, stage = "historical") => ({ reference, experiment_ids: ["e1"], research: { stage } });
  const completed = [{ id: "e1", references: ["a@1.0.0"], run_status: "completed" }];
  assert.equal(model.catalogAction(item("a@1.0.0"), completed), "查看证据");
  assert.equal(model.catalogAction(item("a@2.0.0"), completed), "查看定义");
  assert.equal(model.catalogAction(item("a@1.0.0", "calculation_only"), []), "查看定义");
  assert.equal(model.catalogAction(item("a@1.0.0", "in_progress"), []), "查看进展");
  assert.equal(model.catalogAction(item("a@1.0.0", "unbound"), []), "查看定义");
});
