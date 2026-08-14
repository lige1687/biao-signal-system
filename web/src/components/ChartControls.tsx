import { MA_META, type ChartDisplay, type ColorMode, type MaKey } from "./KlineChart";

interface Props {
  display: ChartDisplay;
  onChange: (next: ChartDisplay) => void;
  counts: {
    bottomMarks: number;
    topMarks: number;
    invalidatedMarks: number;
    keyVolatility: number;
    levels: number;
  };
  /** 导出当前 K 线为 PNG（由父组件从 KlineChart 拿到的回调） */
  onDownloadPng?: () => void;
}

/**
 * K 线显示控制条：标记开关（默认全关）、着色模式、均线开关。
 *
 * 为什么标记默认关闭：一只标的历史上可能有数百个结构确认/失效标记，
 * 全部铺在图上会严重干扰看盘。需要研究某段行情时再按需打开。
 *
 * 「结构标记」拆为三个按钮（底部确认 / 顶部确认 / 结构失效）——分类
 * 显示比一个总开关有用：用户经常只想看一种，不想被另两种标记干扰。
 */
export default function ChartControls({
  display,
  onChange,
  counts,
  onDownloadPng,
}: Props) {
  const toggle = (key: "keyVolatility" | "levels") =>
    onChange({ ...display, [key]: !display[key] });

  const toggleStruct = (key: "bottomMarks" | "topMarks" | "invalidatedMarks") =>
    onChange({ ...display, [key]: !display[key] });

  const toggleMa = (key: MaKey) =>
    onChange({ ...display, ma: { ...display.ma, [key]: !display.ma[key] } });

  const setMode = (mode: ColorMode) => onChange({ ...display, colorMode: mode });

  const anyMark =
    display.bottomMarks ||
    display.topMarks ||
    display.invalidatedMarks ||
    display.keyVolatility ||
    display.levels;

  return (
    <div className="chart-controls">
      <div className="ctl-group">
        <span className="ctl-label">K线着色</span>
        <div className="seg">
          <button
            className={`seg-btn ${display.colorMode === "red_green" ? "on" : ""}`}
            onClick={() => setMode("red_green")}
            title="中国惯例：红涨绿跌"
          >
            红涨绿跌
          </button>
          <button
            className={`seg-btn ${display.colorMode === "lei_state" ? "on" : ""}`}
            onClick={() => setMode("lei_state")}
            title="按当日 LEI 三色着色（颜色只表达状态，涨跌看今日概述）"
          >
            LEI 绿灰黑
          </button>
        </div>
      </div>

      <div className="ctl-group">
        <span className="ctl-label">均线</span>
        {MA_META.map((m) => (
          <button
            key={m.key}
            className={`chip ${display.ma[m.key] ? "on" : ""}`}
            style={
              display.ma[m.key]
                ? {
                    borderColor: m.color,
                    color: m.color,
                    // 虚线均线的开关也用虚线边框，和图上线型对应
                    borderStyle: m.dashed ? "dashed" : "solid",
                  }
                : undefined
            }
            onClick={() => toggleMa(m.key)}
          >
            {m.label}
          </button>
        ))}
      </div>

      <div className="ctl-group">
        <span className="ctl-label">结构</span>
        <button
          className={`chip ${display.bottomMarks ? "on" : ""}`}
          style={display.bottomMarks ? { borderColor: "#0b9b64", color: "#0b9b64" } : undefined}
          onClick={() => toggleStruct("bottomMarks")}
          title="底部结构确认（绿色菱形 = 存活，灰色 = 已失效）"
        >
          <span className="mk mk-bottom" style={{ marginRight: 2 }}>◆</span> 底部确认{" "}
          {counts.bottomMarks > 0 && <em>{counts.bottomMarks}</em>}
        </button>
        <button
          className={`chip ${display.topMarks ? "on" : ""}`}
          style={display.topMarks ? { borderColor: "#dc2626", color: "#dc2626" } : undefined}
          onClick={() => toggleStruct("topMarks")}
          title="顶部结构确认（红色菱形 = 存活，灰色 = 已失效）"
        >
          <span className="mk mk-top" style={{ marginRight: 2 }}>◆</span> 顶部确认{" "}
          {counts.topMarks > 0 && <em>{counts.topMarks}</em>}
        </button>
        <button
          className={`chip ${display.invalidatedMarks ? "on" : ""}`}
          style={
            display.invalidatedMarks
              ? { borderColor: "#9ca3af", color: "#5b6473" }
              : undefined
          }
          onClick={() => toggleStruct("invalidatedMarks")}
          title="结构失效日（触及 C 点永久失效时的标记）"
        >
          <span className="mk mk-dead" style={{ marginRight: 2 }}>✕</span> 结构失效{" "}
          {counts.invalidatedMarks > 0 && <em>{counts.invalidatedMarks}</em>}
        </button>
      </div>

      <div className="ctl-group">
        <span className="ctl-label">参考</span>
        <button
          className={`chip ${display.levels ? "on" : ""}`}
          onClick={() => toggle("levels")}
          title="B1 第一阻力 / C 点失效线 / 顶部颈线"
        >
          <span className="mk mk-b1" style={{ marginRight: 2 }}>●</span> 参考线{" "}
          {counts.levels > 0 && <em>{counts.levels}</em>}
        </button>
        <button
          className={`chip ${display.keyVolatility ? "on" : ""}`}
          onClick={() => toggle("keyVolatility")}
          title="颜色转绿/转黑的关键性波动日"
        >
          <span className="mk mk-kv" style={{ marginRight: 2 }}>▲</span> 关键性波动{" "}
          {counts.keyVolatility > 0 && <em>{counts.keyVolatility}</em>}
        </button>
        <button
          className={`chip ${display.chipDist ? "on" : ""}`}
          style={display.chipDist ? { borderColor: "#f59e0b", color: "#f59e0b" } : undefined}
          onClick={() => onChange({ ...display, chipDist: !display.chipDist })}
          title="筹码分布（CYQ）：把成交量按价格纵向铺开，看筹码密集的支撑/阻力区"
        >
          ▤ 筹码峰
        </button>
        <button
          className={`chip ${display.macd ? "on" : ""}`}
          style={display.macd ? { borderColor: "#8b5cf6", color: "#8b5cf6" } : undefined}
          onClick={() => onChange({ ...display, macd: !display.macd })}
          title="MACD 副图（研究代理）：DIF/DEA + 红绿柱。表达均线扩散/密集=乖离率=强度，不是转折节点；破线看 LEI 颜色，均线拐头看均线斜率"
        >
          ⑃ MACD
        </button>
        {anyMark && (
          <button
            className="chip clear"
            onClick={() =>
              onChange({
                ...display,
                bottomMarks: false,
                topMarks: false,
                invalidatedMarks: false,
                keyVolatility: false,
                levels: false,
              })
            }
            title="清空所有信号标记，回到干净的看盘视图"
          >
            全部隐藏
          </button>
        )}
        {onDownloadPng && (
          <button
            className="chip export"
            onClick={onDownloadPng}
            title="把当前 K 线图导出为 PNG（包含你打开的标记、参考线、均线）"
          >
            ⤓ 导出 PNG
          </button>
        )}
      </div>
    </div>
  );
}
