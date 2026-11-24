import assert from "node:assert/strict";
import test from "node:test";
import { crossingMarkerSeries, filterCrossings } from "./crossing-markers.ts";

const events = Array.from({ length: 240 }, (_, i) => ({
  date: new Date(Date.UTC(2015, 0, 1 + i * 10)).toISOString().slice(0, 10),
  price: 3000 + i, focusPercent: i % 2 ? -0.1 : 0.2,
  direction: i % 2 ? "down" : "up",
}));

test("eleven-year view retains every raw event on both price and momentum axes", () => {
  const [price, focus] = crossingMarkerSeries(events, 2673);
  assert.equal(price.xAxisIndex, 0); assert.equal(price.yAxisIndex, 0);
  assert.equal(focus.xAxisIndex, 1); assert.equal(focus.yAxisIndex, 1);
  assert.equal(price.data.length, 240); assert.equal(focus.data.length, 240);
  for (let i = 0; i < events.length; i++) {
    assert.deepEqual(price.data[i].value, [events[i].date, events[i].price]);
    assert.deepEqual(focus.data[i].value, [events[i].date, events[i].focusPercent]);
    assert.equal(price.data[i].date, focus.data[i].date);
    assert.ok(price.data[i].symbolSize > 0);
  }
});

test("zoom changes size rather than dropping or changing events", () => {
  const long = crossingMarkerSeries(events, 2673), short = crossingMarkerSeries(events, 60);
  for (let i = 0; i < 2; i++) {
    assert.deepEqual(long[i].data.map(x => x.value), short[i].data.map(x => x.value));
    assert.ok(short[i].data[0].symbolSize > long[i].data[0].symbolSize);
  }
});

test("direction filters partition the original events without using future prices", () => {
  const before = structuredClone(events);
  const up = filterCrossings(events, "up"), down = filterCrossings(events, "down");
  assert.equal(up.length + down.length, events.length);
  assert.deepEqual(filterCrossings(events, "all"), before);
  assert.ok(up.every(x => x.direction === "up")); assert.ok(down.every(x => x.direction === "down"));
  assert.equal(crossingMarkerSeries(up, 2673)[0].data[0].symbolRotate, 0);
  assert.equal(crossingMarkerSeries(down, 2673)[0].data[0].symbolRotate, 180);
  assert.deepEqual(events, before);
});

test("empty or hidden markers clear both panels", () => {
  assert.ok(crossingMarkerSeries([], 2673).every(series => series.data.length === 0));
});
