import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { RESEARCH_EXTENSIONS, normalizeSelectedDocumentId } from "/tmp/lei-strategy-system-logic.mjs";

const logic = readFileSync(new URL("./src/pages/strategySystemLogic.ts", import.meta.url), "utf8");
assert.ok(logic.includes("normalizeSelectedDocumentId"));
assert.equal(normalizeSelectedDocumentId("invalid", ["technical-system", "technical-implementation"]), "technical-system");
assert.equal(normalizeSelectedDocumentId(null, []), null);
assert.equal(normalizeSelectedDocumentId("technical-implementation", ["technical-system", "technical-implementation"]), "technical-implementation");
assert.deepEqual(RESEARCH_EXTENSIONS.map((item) => item.id), ["breadth", "institutional", "retail", "a-share-sentiment"]);
assert.equal(RESEARCH_EXTENSIONS[3].sourceClass, "体系外研究扩展");
assert.ok(RESEARCH_EXTENSIONS.slice(0, 3).every((item) => item.sourceClass === "原文与实现已有"));
assert.ok(RESEARCH_EXTENSIONS.every((item) => item.plainDefinition && item.status && item.to.startsWith("/")));
console.log("strategy-system regression passed");
