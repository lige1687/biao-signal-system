import assert from "node:assert/strict";
import { patchReportLibraryParams, reportLibrarySearch } from "./src/pages/reportLibraryUrl.ts";

const current = new URLSearchParams("cat=%E5%AE%BD%E5%BA%A6%E6%8B%A9%E6%97%B6&verdict=falsified&q=RS26&prompts=show&report=old.md");
const href = reportLibrarySearch(current, "docs/experiments/RS26 背离度.md");
const selected = new URL(`https://example.test/library${href}`);
assert.equal(selected.pathname, "/library");
assert.equal(selected.searchParams.get("report"), "docs/experiments/RS26 背离度.md");
assert.equal(selected.searchParams.get("q"), "RS26");
assert.equal(selected.searchParams.get("cat"), "宽度择时");
assert.equal(selected.searchParams.get("verdict"), "falsified");
assert.equal(selected.searchParams.get("prompts"), "show");

const filtered = patchReportLibraryParams(current, "q", "新词");
assert.equal(filtered.get("report"), "old.md");
assert.equal(filtered.get("q"), "新词");
const backToList = patchReportLibraryParams(filtered, "report", null);
assert.equal(backToList.get("report"), null);
assert.equal(backToList.get("q"), "新词");
assert.equal(current.get("report"), "old.md", "URL edits must not mutate the current location");
console.log("report library URL regression passed");
