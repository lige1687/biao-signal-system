/**
 * 前向成绩页回归：断言两套成绩都渲染（展示模型层）+ 降级态也渲染。
 * 输入是后端 /api/fwd-ledger/scorecard 的形状（与 tests/unit/test_fwd_ledger_api.py
 * 的断言互为对照）。跑法：npm run test:fwd-ledger
 */
import assert from "node:assert/strict";
import { pctText, recommendationView, sentimentView } from "/tmp/lei-fwd-ledger-logic.mjs";

const okSentiment = {
  available: true, reason: "", records: 5, reviewedRecords: 2,
  buckets: [
    { key: "pick10", labelCn: "冰点机会·10日", horizonDays: 10, n: 2, winRatePct: 50.0, meanPct: 1.5 },
    { key: "pick20", labelCn: "冰点机会·20日", horizonDays: 20, n: 1, winRatePct: 100.0, meanPct: 10.0 },
    { key: "alarm10", labelCn: "强热警报·10日", horizonDays: 10, n: 1, winRatePct: 0.0, meanPct: -3.0 },
    { key: "alarm20", labelCn: "强热警报·20日", horizonDays: 20, n: 0 },
  ],
};
const okRec = {
  available: true, reason: "", scoredDates: 2, latestDate: "2026-08-02",
  bySymbol: [
    { symbol: "510300", nameCn: "沪深300ETF", samples: 4,
      t1: { n: 2, winRatePct: 50.0, meanPct: 0.5 }, t5: { n: 2, winRatePct: 100.0, meanPct: 2.0 }, t20: null },
    { symbol: "513100", nameCn: null, samples: 2,
      t1: { n: 2, winRatePct: 50.0, meanPct: -0.5 }, t5: null, t20: null },
  ],
};

// A 四桶全部渲染：key/标签/数值齐全，空桶 n=0 不编数
const s = sentimentView(okSentiment);
assert.equal(s.status, "ok");
assert.equal(s.data.cards.length, 4);
const byKey = Object.fromEntries(s.data.cards.map((c) => [c.key, c]));
assert.equal(byKey.pick10.labelCn, "冰点机会·10日");
assert.equal(byKey.pick10.meanPct, 1.5);
assert.equal(byKey.alarm10.meanPct, -3.0);
assert.equal(byKey.alarm20.n, 0);
assert.equal(byKey.alarm20.meanPct, null); // 空桶不给数
assert.equal(pctText(byKey.alarm10.meanPct), "-3.00%");
assert.equal(pctText(null), "—");

// B 按标的渲染：名称回退 symbol、空档位为 null
const r = recommendationView(okRec);
assert.equal(r.status, "ok");
assert.equal(r.data.rows.length, 2);
assert.equal(r.data.rows[0].name, "沪深300ETF");
assert.equal(r.data.rows[1].name, "513100"); // nameCn=null 回退代码
assert.equal(r.data.rows[0].horizons.t20, null);
assert.equal(r.data.rows[0].horizons.t1.meanPct, 0.5);

// 降级态：available=false 时输出原因，不给数据
const dS = sentimentView({ available: false, reason: "账本文件不存在（情绪信号尚未存证过）" });
assert.equal(dS.status, "degraded");
assert.match(dS.reason, /不存在/);
const dR = recommendationView({ available: false, reason: "推荐账本尚无任何到期对账结果" });
assert.equal(dR.status, "degraded");
assert.match(dR.reason, /尚无任何到期对账/);

// 加载态
assert.equal(sentimentView(undefined).status, "loading");
assert.equal(recommendationView(undefined).status, "loading");

console.log("✓ 前向成绩页回归通过：四桶渲染、按标的渲染、降级/加载态齐全");
