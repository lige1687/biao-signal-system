import type { GlobalPanel } from "../types";

/* 涨跌配色（A股惯例：涨红 / 跌绿） */
export const UP_COLOR = "#e23d3d";
export const DOWN_COLOR = "#1a9e5f";
export const FLAT_COLOR = "#9ca3af";

/** 判断一个 GlobalPanel 是否走真全A涨跌家数源（而非旧 B 系列）。 */
export function isRealAShare(p: GlobalPanel | null | undefined): boolean {
  return !!p && (p.is_real_a_share === true || p.up != null);
}

export function fmtPct(v: number | null | undefined, d = 1): string {
  return v == null ? "—" : `${v.toFixed(d)}%`;
}
export function fmtNum(v: number | null | undefined): string {
  if (v == null) return "—";
  return v.toLocaleString("zh-CN");
}
export function fmtRatio(v: number | null | undefined): string {
  return v == null ? "—" : v.toFixed(2);
}

/* 涨跌占比条 */
export function AShareBar({ p }: { p: GlobalPanel }) {
  const total = p.total ?? 0;
  const upW = total ? ((p.up ?? 0) / total) * 100 : 0;
  const flatW = total ? ((p.flat ?? 0) / total) * 100 : 0;
  const downW = total ? ((p.down ?? 0) / total) * 100 : 0;
  return (
    <div className="ab-bar" title={`涨 ${p.up} · 平 ${p.flat} · 跌 ${p.down}`}>
      <div className="ab-seg up" style={{ width: `${upW}%` }} />
      <div className="ab-seg flat" style={{ width: `${flatW}%` }} />
      <div className="ab-seg down" style={{ width: `${downW}%` }} />
    </div>
  );
}

/* 核心数字网格 */
export function AShareGrid({ p, small = false }: { p: GlobalPanel; small?: boolean }) {
  return (
    <div className={`ab-grid${small ? " small" : ""}`}>
      <Stat label="上涨" value={fmtNum(p.up)} color={UP_COLOR} />
      <Stat label="下跌" value={fmtNum(p.down)} color={DOWN_COLOR} />
      <Stat label="平盘" value={fmtNum(p.flat)} color={FLAT_COLOR} />
      <Stat label="总数" value={fmtNum(p.total)} color="#374151" />
      <Stat label="上涨占比" value={fmtPct(p.up_pct)} color={UP_COLOR} />
      <Stat
        label="涨跌比"
        value={fmtRatio(p.adv_dec_ratio)}
        color={
          p.adv_dec_ratio == null
            ? FLAT_COLOR
            : p.adv_dec_ratio >= 1
            ? UP_COLOR
            : DOWN_COLOR
        }
      />
      <Stat label="涨停≈" value={fmtNum(p.limit_up)} color={UP_COLOR} />
      <Stat label="跌停≈" value={fmtNum(p.limit_down)} color={DOWN_COLOR} />
    </div>
  );
}

export function AShareSourceLine({ p }: { p: GlobalPanel }) {
  return (
    <div className="ab-source">
      <span className="ab-source-label">数据来源</span>
      <span className="ab-source-text">{p.source_detail || "—"}</span>
    </div>
  );
}

function Stat({
  label,
  value,
  color,
}: {
  label: string;
  value: string;
  color: string;
}) {
  return (
    <div className="ab-stat">
      <span className="ab-stat-label">{label}</span>
      <span className="ab-stat-value" style={{ color }}>
        {value}
      </span>
    </div>
  );
}
