import type { MarkLine, ZoneLevel } from "./zones";
import { zoneToneColor } from "./zones";
import TrendChart, { type LineSeries } from "./TrendChart";

/** 趋势抽屉配置（与 TrendDrawerProps 同构，仅可空）。抽自 FundamentalsPage，纯重构。 */
export type DrawerState = {
  title: string;
  subtitle?: string;
  dates: string[];
  series: LineSeries[];
  unit: string;
  markLines?: MarkLine[];
  yRange?: [number, number];
  zones?: readonly ZoneLevel[];
  footnote?: string;
  /** 默认可见窗口（最近多少个交易日）；不传则 TrendChart 全展。 */
  defaultWindowDays?: number;
} | null;

interface TrendDrawerProps {
  title: string;
  /** 副标题，如「当前 4.68% · 压力区（近 730 日）」。 */
  subtitle?: string;
  dates: string[];
  series: LineSeries[];
  unit: string;
  markLines?: MarkLine[];
  yRange?: [number, number];
  /** 区间图例（机会/风险各档带出处）。 */
  zones?: readonly ZoneLevel[];
  footnote?: string;
  /** 默认可见窗口（最近多少个交易日）；不传则 TrendChart 全展。 */
  defaultWindowDays?: number;
  /** 周期切换（3/5/10/20 年）：传入即渲染 chips，切换时父层重拉对应跨度数据。 */
  periodOptions?: readonly { label: string; days: number }[];
  activeDays?: number;
  onPeriodChange?: (days: number) => void;
  /** 周期数据加载中：chips 置灰防抖动。 */
  periodLoading?: boolean;
  onClose: () => void;
}

/** 趋势大图抽屉：点击小图后展开，含分界线大图 + 区间判断依据。 */
export default function TrendDrawer({
  title,
  subtitle,
  dates,
  series,
  unit,
  markLines,
  yRange,
  zones,
  footnote,
  defaultWindowDays,
  periodOptions,
  activeDays,
  onPeriodChange,
  periodLoading,
  onClose,
}: TrendDrawerProps) {
  return (
    <div className="drawer-overlay" onClick={onClose}>
      <div
        className="drawer-panel trend-drawer-panel"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="drawer-head">
          <h2>
            {title}
            {subtitle && <span className="trend-subtitle">{subtitle}</span>}
          </h2>
          {periodOptions && periodOptions.length > 0 && onPeriodChange && (
            <div className="overlay-market-controls" style={{ gap: 4 }}>
              {periodOptions.map((p) => (
                <button
                  key={p.days}
                  type="button"
                  disabled={periodLoading}
                  className={`ma-toggle${activeDays === p.days ? " on" : ""}`}
                  onClick={() => onPeriodChange(p.days)}
                >
                  {p.label}
                </button>
              ))}
            </div>
          )}
          <button className="btn" onClick={onClose}>
            关闭
          </button>
        </div>
        <div className="drawer-body trend-drawer-body">
          {dates.length < 2 ? (
            <div className="muted">暂无历史序列</div>
          ) : (
            <TrendChart
              dates={dates}
              series={series}
              unit={unit}
              markLines={markLines}
              zones={zones}
              yRange={yRange}
              height={340}
              draggableMarkLines={(markLines?.length ?? 0) > 0}
              defaultWindowDays={defaultWindowDays}
            />
          )}
          {(markLines?.length ?? 0) > 0 && (
            <div style={{ fontSize: 11, color: "#6b7280", marginTop: -12, marginBottom: 8 }}>
              图中虚线分界线可上下拖动，标签实时显示当前阈值（仅本地探索，不改变判断依据）。
            </div>
          )}
          {zones && zones.length > 0 && (
            <div className="trend-zones">
              <h5>区间与判断依据</h5>
              <ol className="zone-levels">
                {zones.map((z) => (
                  <li key={z.label} style={{ color: zoneToneColor(z.tone) }}>
                    {z.label}
                    {z.max !== Infinity ? `（≤ ${z.max}）` : ""}：{z.note}
                  </li>
                ))}
              </ol>
              {footnote && (
                <div className="trend-source">
                  <h5>数据与分界线来源</h5>
                  {footnote}
                </div>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
