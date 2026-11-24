import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { build } from "esbuild";

const bundle = await build({ entryPoints: [new URL("./metricData.ts", import.meta.url).pathname],
  bundle: true, format: "esm", platform: "node", write: false });
const data = await import(`data:text/javascript;base64,${Buffer.from(bundle.outputFiles[0].text).toString("base64")}`);
const read = (file) => JSON.parse(readFileSync(new URL(`../../../public/research/observation-library-20261026/${file}`, import.meta.url), "utf8"));

test("FSI, FINRA and verified NFCI reuse preserve source identity, dates and units", () => {
  const saved = data.parseReused(read("reused-series.json"));
  const fsi = data.fromReused(saved, "ofr-fsi", false);
  const finra = data.fromReused(saved, "finra-margin", true);
  assert.equal(fsi.date, "2026-10-21");
  assert.equal(fsi.unit, "指数值");
  assert.equal(saved.series["ofr-fsi"].points.length, 276);
  assert.equal(finra.date, "2026-09");
  assert.equal(finra.dateLabel, "所属月");
  assert.equal(finra.value, 1480054);
  assert.equal(finra.points.length, 0);
  assert.deepEqual(finra.auxiliary.map((row) => row.value), [215328, 218581]);
  const nfci = data.fromReused(saved, "nfci", false);
  assert.equal(nfci.date, "2026-10-09");
  assert.equal(nfci.value, -0.499);
  assert.equal(nfci.points.length, 5);
  assert.equal(nfci.change, 0.03700000000000003);
  assert.equal(nfci.comparisonPeriod, "前4周");
  assert.match(nfci.status, /不自动更新/);
  assert.equal(data.formatValue(0, "%"), "0 %");
  assert.equal(data.formatValue(null, "%"), "暂无可核读数");
  assert.throws(() => data.parseReused({ ...saved, series: { ...saved.series, "ofr-fsi": { ...saved.series["ofr-fsi"], latest: { date: "2026-10-22", value: 0 } } } }), /不完整/);
  assert.throws(() => data.parseReused({ ...saved, series: { ...saved.series, nfci: { ...saved.series.nfci, points: saved.series.nfci.points.slice(1) } } }), /NFCI.*身份不符/);
});

test("Baker remains monthly historical levels, preserves absent orthogonal month and never reports monthly change", () => {
  const saved = data.parseBaker(read("baker.json"));
  const orth = data.fromBaker(saved, false);
  const raw = data.fromBaker(saved, false, "raw");
  assert.equal(orth.date, "2025-12");
  assert.equal(orth.change, null);
  assert.equal(orth.value, 0.06564764678478241);
  assert.equal(raw.value, 0.12571176886558533);
  assert.equal(orth.points.find((row) => row.date === "2025-10-31").value, null);
  assert.match(orth.status, /不能读作今日值/);
  assert.match(data.fromBaker(saved, true).status, /默认 SENT_ORTH 宏观调整后/);
  assert.throws(() => data.parseBaker({ ...saved, latest: { ...saved.latest, change: 1 } }), /版本或末值/);
});

test("missing live observations remain missing, while percent units and zero survive", () => {
  const sample = { value: 0, unit: "%", observation_date: "2026-10-20", change: 0,
    change_unit: "百分点", source_name: "source", source_url: null, definition_version: "v1",
    quality_status: "stale", quality_reason: "lag", limitations: [] };
  const reading = data.fromObservation(sample);
  assert.equal(reading.value, 0);
  assert.equal(reading.change, 0);
  assert.equal(reading.status, "资料已陈旧；不当作当前市场读数");
  assert.equal(data.fromObservation({ ...sample, quality_status: "time_unverified" }).status, "首次发布时间未核；按资料日期观察");
  assert.equal(data.fromObservation({ ...sample, value: null }).value, null);
  const missing = data.fromObservation({ ...sample, quality_status: "missing" }, [{ date: "2026-10-19", value: 1 }]);
  assert.equal(missing.value, null);
  assert.equal(missing.change, null);
  assert.deepEqual(missing.points, []);
  const undated = data.fromObservation({ ...sample, observation_date: "" }, [{ date: "2026-10-19", value: 1 }]);
  assert.equal(undated.value, null);
  assert.equal(undated.date, null);
  assert.deepEqual(undated.points, []);
  assert.equal(data.fromObservation(undefined), null);
});

test("valuation uses actual rates.valuation and distinct HS300/CAPE series", () => {
  const rates = { valuation: {
    cn_pe: { value: 12, as_of: "2026-10-20", percentile: 43, percentile_full: 47, calib_from: "2010", calib_n: 4000, full_from: "2005", full_n: 5000 },
    us_cape: { value: 39, as_of: "2026-09-01", percentile: 91, percentile_full: 94, calib_from: "1950", calib_n: 900, full_from: "1881", full_n: 1700 },
  } };
  assert.equal(data.fromValuation(rates, "hs300-pe").value, 12);
  assert.equal(data.fromValuation(rates, "sp500-cape").value, 39);
  assert.match(data.fromValuation(rates, "hs300-pe").sourceName, /乐咕乐股.*akshare/);
  assert.equal(data.fromValuation(rates, "sp500-cape").date, "2026-09");
  assert.equal(data.fromValuation(rates, "sp500-cape").dateLabel, "所属月");
  assert.match(data.fromValuation(rates, "sp500-cape").status, /发布日期未知/);
  assert.equal(data.fromValuation({ valuation: { cn_pe: null, us_cape: null } }, "hs300-pe"), null);
});

test("survey curve takes dated source fields without substituting percentiles", () => {
  const history = { observations: [{ survey_week: "2026-10-08", bull_bear: 0, exposure_index: null, percentile: 100 }] };
  assert.deepEqual(data.fromSurveyHistory(history, "aaii"), [{ date: "2026-10-08", value: 0 }]);
  assert.deepEqual(data.fromSurveyHistory(history, "naaim"), [{ date: "2026-10-08", value: null }]);
});

test("legacy OAS warning copy cannot reintroduce an unqualified threshold into the observation library", () => {
  const input = { items: [{ key: "hy_oas", value: 3.4, date: "2026-10-22", note_cn: ">6% 历史警戒" }],
    series: { hy_oas: { dates: ["2026-10-21", "2026-10-22"], values: [3.3, 3.4] } } };
  const reading = data.fromUsMacro(input, "hy_oas", true);
  assert.equal(reading.value, 3.4);
  assert.equal(reading.unit, "%");
  assert.equal(reading.date, "2026-10-22");
  assert.deepEqual(reading.points.map((p) => p.value), [3.3, 3.4]);
  assert.doesNotMatch(reading.note, />6|警戒/);
  assert.match(reading.note, /未建立固定顶底线/);
});
