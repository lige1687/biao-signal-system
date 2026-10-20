interface Props {
  color: string | null; // green | gray | black | unknown
  colorCn: string | null;
  days?: number | null;
  descriptive?: boolean;
}

/**
 * BIAO 信号颜色徽章。永远以「圆点 + 中文文字」呈现，绝不只靠颜色传达语义，
 * 与涨跌幅的红涨绿跌严格区分。
 */
export default function ColorBadge({ color, colorCn, days, descriptive = false }: Props) {
  if (!color || !colorCn) return null;
  const meaning = ({ green: "多头观察", gray: "中性", black: "空头规避" } as Record<string, string>)[color];
  return (
    <span className={`color-badge ${color}`} title="BIAO 信号颜色：绿=多头观察 / 灰=中性 / 黑=空头规避">
      <span className="dot" />
      <span>
        {colorCn}
        {descriptive && meaning ? ` · ${meaning}` : ""}
        {days != null && days > 0 ? ` · 第${days}天` : ""}
      </span>
    </span>
  );
}
