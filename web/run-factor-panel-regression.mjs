import {
  buildRiskChips,
  groupFactorCards,
  marketRegimePhrase,
  WEAK_COLUMN_KEYS,
} from "file:///tmp/biao-factor-panel-logic.mjs";

// ---- buildRiskChips：chips 文案必须携带 2026-09-05 复核边界，不得暗示否决信号 ----

const highRv = buildRiskChips({ rv_pct: 0.9, mom_20_group_pct: null, ivol_pct: null, notes: [] });
if (highRv.length !== 1 || highRv[0].text !== "高波·仅读数") {
  throw new Error(`高波 chip 文案错误：${JSON.stringify(highRv)}`);
}
if (highRv[0].text.includes("打折")) {
  throw new Error("高波 chip 文案仍在宣称「信号打折」（2026-09-05 复核未复现）");
}
if (!highRv[0].title.includes("复核") || !highRv[0].title.includes("不挡信号")) {
  throw new Error("高波 chip 缺复核溯源或「不挡信号」边界说明");
}

const overbought = buildRiskChips({ rv_pct: null, mom_20_group_pct: 0.9, ivol_pct: null, notes: [] });
if (overbought.length !== 1 || !overbought[0].text.startsWith("短线超买")) {
  throw new Error(`超买 chip 文案错误：${JSON.stringify(overbought)}`);
}
if (!overbought[0].title.includes("无预测力")) {
  throw new Error("超买 chip 缺「对已确认信号无预测力」边界");
}

const ivol = buildRiskChips({ rv_pct: null, mom_20_group_pct: null, ivol_pct: 0.9, notes: [] });
if (ivol.length !== 1 || ivol[0].text !== "IVOL高·入口排雷") {
  throw new Error(`IVOL chip 文案错误：${JSON.stringify(ivol)}`);
}
if (!ivol[0].title.includes("入口") || !ivol[0].title.includes("不否决")) {
  throw new Error("IVOL chip 缺「入口排雷/不否决已确认信号」边界");
}

const stale = buildRiskChips({ rv_pct: null, mom_20_group_pct: null, ivol_pct: null, notes: ["数据较旧(12天)"] });
if (stale.length !== 1 || stale[0].text !== "数据较旧") {
  throw new Error(`数据较旧 chip 错误：${JSON.stringify(stale)}`);
}

const none = buildRiskChips({ rv_pct: null, mom_20_group_pct: null, ivol_pct: null, notes: [] });
if (none.length !== 0) {
  throw new Error(`空读数不应出 chip：${JSON.stringify(none)}`);
}

const all = buildRiskChips({ rv_pct: 0.95, mom_20_group_pct: 0.95, ivol_pct: 0.95, notes: ["数据较旧(12天)"] });
if (all.length !== 4) {
  throw new Error(`四类 chip 应同时出现：实际 ${all.length}`);
}

// ---- groupFactorCards：pass 展开、weak/inverse/fail 折叠，保持原序 ----

const meta = (level) => ({ verdict_level: level });
const groups = groupFactorCards({
  rv_pct: meta("pass"),
  mom_121: meta("pass"),
  mom_20: meta("inverse"),
  vol_up: meta("weak"),
  adx14: meta("fail"),
  idio_vol: meta("pass"),
});
if (groups.primary.map(([k]) => k).join(",") !== "rv_pct,mom_121,idio_vol") {
  throw new Error(`pass 分组错误：${groups.primary.map(([k]) => k).join(",")}`);
}
if (groups.weak.map(([k]) => k).join(",") !== "mom_20,vol_up,adx14") {
  throw new Error(`弱卡分组错误：${groups.weak.map(([k]) => k).join(",")}`);
}

// ---- marketRegimePhrase：模块分层口径，不再宣称「高波整体打折」 ----

const high = marketRegimePhrase(0.85);
if (!high.includes("C") || !high.includes("主场")) {
  throw new Error(`高波短语应指向 C 模块主场：${high}`);
}
const low = marketRegimePhrase(0.1);
if (!low.includes("不占优")) {
  throw new Error(`低波短语应说明 C 不占优：${low}`);
}
const mid = marketRegimePhrase(0.42);
if (!mid.startsWith("中波")) {
  throw new Error(`中波短语错误：${mid}`);
}
if (marketRegimePhrase(null) !== "" || marketRegimePhrase(undefined) !== "") {
  throw new Error("缺读数应返回空串");
}

// ---- 弱列清单（页面默认折叠的列）----

if (WEAK_COLUMN_KEYS.join(",") !== "mom_20,mom_20_group_pct,vol_ok,adx14") {
  throw new Error(`弱列清单变动需同步页面与测试：${WEAK_COLUMN_KEYS.join(",")}`);
}

console.log("因子观测台展示层回归通过：chips边界/评级分组/体制短语/弱列清单 均符合 2026-09-05 复核口径");
