import type { MarkLine, ZoneLevel } from "./zones";
import { zoneToneColor } from "./zones";
import TrendChart, { type LineSeries } from "./TrendChart";

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
            />
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
