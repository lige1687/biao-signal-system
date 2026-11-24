import assert from "node:assert/strict";
import { test } from "node:test";
import { createElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { build } from "esbuild";
const built = await build({ entryPoints: [new URL("./ReportReader.tsx", import.meta.url).pathname], bundle:true, write:false, platform:"node", format:"esm", jsx:"automatic" });
const { default: Reader } = await import(`data:text/javascript;base64,${Buffer.from(built.outputFiles[0].contents).toString("base64")}`);
const path = "docs/experiments/ma-cluster-information-mae-artifact-2026-09-30.md";
const render = changes => renderToStaticMarkup(createElement(Reader, {selected:path, loading:false, error:null, onBack(){}, ...changes}, createElement("h1",null,"M01限定范围正文")));
test("deep link shows its exact report and provides a return to the unchanged list",()=>{
  const html = render({report:{name:path}});
  assert.ok(html.includes("M01限定范围正文") && html.includes("返回报告列表"));
  assert.ok(!html.includes("点左侧任意报告"));
});
test("loading and failures cannot masquerade as unselected reports",()=>{
  const pending = render({loading:true}); const failed=render({error:new Error("报告不存在")});
  assert.ok(pending.includes('role="status"') && pending.includes("正在加载所选报告正文"));
  assert.ok(failed.includes('role="alert"') && failed.includes("报告不存在"));
  for (const html of [pending,failed]) assert.ok(!html.includes("M01限定范围正文") && !html.includes("点左侧任意报告"));
});
test("a different returned report cannot supply the selected report's conclusion",()=>{
  const html = render({report:{name:"docs/experiments/other.md"}});
  assert.ok(html.includes('role="alert"') && !html.includes("M01限定范围正文"));
});
test("returning to no selection retains list guidance without old report content",()=>{
  const html = render({selected:null,report:{name:path}});
  assert.ok(html.includes("点左侧任意报告") && !html.includes("M01限定范围正文"));
});
