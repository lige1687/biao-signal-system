import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { describe, it } from "node:test";
import { fileURLToPath } from "node:url";

const HERE = path.dirname(fileURLToPath(import.meta.url));

const GUARDED_UI_FILES = [
  "HomeEnvironmentStrip.tsx",
  "market-style/BreadthComparison.tsx",
  "market-style/breadthRegimeScreener.ts",
  "observation-library/ErpCrossChart.tsx",
  "observation-library/MetricComboWorkbench.tsx",
  "observation-library/metricCrossScreener.ts",
  "observation-library/projectionThresholds.ts",
];

// Confusing financial / quant jargon banned in user-facing UI strings (2026-11-23 user rule).
const BANNED_UI_JARGON = [
  "免疫",
  "走阔",
  "传染",
  "双低出清",
  "存量出清",
  "存量偏重",
  "高赔率",
  "无赔率垫",
  "弱势底座",
  "多头底座",
  "牛市底座",
  "Contango",
  "Vol Crush",
  "Washout",
  "W3 范式",
  "W3范式",
  "右偏脉冲",
  "右偏厚尾",
  "近正态对称",
  "因果计算",
  "单因子",
];

function stripCodeComments(source) {
  return source
    .replace(/\/\*[\s\S]*?\*\//g, (m) => m.replace(/[^\n]/g, " "))
    .replace(/(^|[^:])\/\/.*$/gm, "$1");
}

describe("plainLanguageGuard (前端界面禁用黑话检查)", () => {
  it("forbids confusing financial jargon across core dashboard and modal UI files", () => {
    const violations = [];
    for (const relPath of GUARDED_UI_FILES) {
      const fullPath = path.join(HERE, relPath);
      const cleanLines = stripCodeComments(fs.readFileSync(fullPath, "utf8")).split("\n");
      cleanLines.forEach((line, idx) => {
        for (const term of BANNED_UI_JARGON) {
          if (line.includes(term)) {
            violations.push(`${relPath}:${idx + 1} 含禁用黑话「${term}」 -> ${line.trim().slice(0, 80)}`);
          }
        }
      });
    }
    assert.deepEqual(
      violations,
      [],
      `发现令人迷惑的金融黑话，请改写成大白话（见 AGENTS.md / web/AGENTS.md）：\n${violations.join("\n")}`,
    );
  });
});
