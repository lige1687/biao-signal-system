interface Props {
  color: string | null; // green | gray | black | unknown
  colorCn: string | null;
  days?: number | null;
}

/**
 * LEI 信号颜色徽章。永远以「圆点 + 中文文字」呈现，绝不只靠颜色传达语义，
 * 与涨跌幅的红涨绿跌严格区分。
 */
export default function ColorBadge({ color, colorCn, days }: Props) {
  if (!color || !colorCn) return null;
  return (
    <span className={`color-badge ${color}`} title="LEI 信号颜色：绿=多头观察 / 灰=中性 / 黑=空头规避">
      <span className="dot" />
      <span>
        {colorCn}
        {days != null && days > 0 ? ` · 第${days}天` : ""}
      </span>
    </span>
  );
}
