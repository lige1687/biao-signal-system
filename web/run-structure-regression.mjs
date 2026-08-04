import { buildStructureMarkPoints } from "file:///tmp/lei-kline-structure-marks.mjs";

function mark(kind) {
  return {
    date: "2026-07-31",
    price: kind === "top" ? 1.25 : 0.95,
    label: kind,
    live: kind !== "invalidated",
    info: {
      structure_id: `S-${kind}`,
      structure_type: kind === "top" ? "top_structure" : "double_bottom",
      source_rule: "",
      detected_date: "2026-07-28",
      confirmed_date: "2026-07-31",
      invalidated_date: kind === "invalidated" ? "2026-08-01" : null,
    },
  };
}

const payload = {
  bottomMarks: [mark("bottom")],
  topMarks: [mark("top")],
  invalidatedMarks: [mark("invalidated")],
};
const allOff = { bottomMarks: false, topMarks: false, invalidatedMarks: false };
const cases = [
  ["bottomMarks", "bottom_mark"],
  ["topMarks", "top_mark"],
  ["invalidatedMarks", "invalidated_mark"],
];

for (const [key, expected] of cases) {
  const points = buildStructureMarkPoints(payload, { ...allOff, [key]: true });
  const kinds = points.map((point) => point.pick.kind);
  if (kinds.length !== 1 || kinds[0] !== expected) {
    throw new Error(`${key} 单独开启失败：${kinds.join(",") || "无标记"}`);
  }
}

console.log("结构开关回归通过：底部、顶部、失效可独立显示");
