import { useState } from "react";
import {
  MA_META,
  effectiveDisplay,
  type ChartDisplay,
  type ChipMode,
  type ColorMode,
  type MaKey,
} from "./KlineChart";
import { TIMEFRAME_META, saveTimeframe, type Timeframe } from "./klineTimeframe";
import type { MarksScope } from "./klineStructureMarks";

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
  /** 标记总数（不过滤口径），与 counts 搭配显示「存活 n / 全部 total」。 */
  markTotals?: {
    bottomMarks: number;
    topMarks: number;
    invalidatedMarks: number;
  };
  /** 导出当前 K 线为 PNG（由父组件从 KlineChart 拿到的回调） */
  onDownloadPng?: () => void;
}

/** 徽章文本：口径过滤后数量小于总数时显示「n/total」，提示还有被口径隐藏的标记。 */
function markBadge(shown: number, total: number | undefined): string {
  if (total != null && shown < total) return `${shown}/${total}`;
  return String(shown);
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
  markTotals,
  onDownloadPng,
}: Props) {
  const toggle = (key: "keyVolatility" | "levels") =>
    onChange({ ...display, [key]: !display[key] });

  const toggleStruct = (key: "bottomMarks" | "topMarks" | "invalidatedMarks") =>
    onChange({ ...display, [key]: !display[key] });

  const toggleMa = (key: MaKey) =>
    onChange({ ...display, ma: { ...display.ma, [key]: !display.ma[key] } });

  const setMode = (mode: ColorMode) => onChange({ ...display, colorMode: mode });

  // 周期切换：写 localStorage 持久化，下次打开沿用。display 里其余开关保持
  // 用户原意图不动——周/月线下的隐藏由 effectiveDisplay 派生，切回日线即复原。
  const setTimeframe = (tf: Timeframe) => {
    if (tf === display.timeframe) return;
    saveTimeframe(tf);
    onChange({ ...display, timeframe: tf });
  };

  // 日线专属开关在周/月线下禁用：聚合视图不提供 LEI 判定与结构标记，
  // 留着能点但没效果比直接禁掉更让人困惑。
  const isDaily = display.timeframe === "D";
  const eff = effectiveDisplay(display);
  const dailyOnlyTitle = "仅日线可用：周/月线是日线聚合的展示视图，不提供 LEI 信号与结构标记";

  const anyMark =
    display.bottomMarks ||
    display.topMarks ||
    display.invalidatedMarks ||
    display.keyVolatility ||
    display.levels;

  // 筹码峰口径下拉（全历史 / 衰减）的展开态
  const [modeOpen, setModeOpen] = useState(false);

  const setChipMode = (mode: ChipMode) => {
    onChange({ ...display, chipMode: mode, chipDist: true });
    setModeOpen(false);
  };

  // 结构标记口径：alive 只画存活结构的确认（看盘默认，数百个历史标记全画
  // 会遮挡 K 线）；all 全量铺开（研究视角）。仅日线有意义（周/月线无标记）。
  const setMarksScope = (scope: MarksScope) =>
    onChange({ ...display, marksScope: scope });
  const aliveOnly = display.marksScope === "alive";
  const scopeTitle = aliveOnly
    ? "当前仅显示存活结构；历史确认/失效标记切「全部」查看"
    : "全量显示历史确认与失效标记；密度大时图例会提示降密";

  return (
    <div className="chart-controls">
      <div className="ctl-group">
        <span className="ctl-label">周期</span>
        <div className="seg">
          {TIMEFRAME_META.map((t) => (
            <button
              key={t.key}
              className={`seg-btn ${display.timeframe === t.key ? "on" : ""}`}
              onClick={() => setTimeframe(t.key)}
              title={t.title}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>

      <div className="ctl-group">
        <span className="ctl-label">K线着色</span>
        <div className="seg">
          <button
            className={`seg-btn ${eff.colorMode === "red_green" ? "on" : ""}`}
            onClick={() => setMode("red_green")}
            title="中国惯例：红涨绿跌"
          >
            红涨绿跌
          </button>
          <button
            className={`seg-btn ${eff.colorMode === "lei_state" ? "on" : ""}`}
            onClick={() => setMode("lei_state")}
            disabled={!isDaily}
            title={isDaily ? "按当日 LEI 三色着色（颜色只表达状态，涨跌看今日概述）" : dailyOnlyTitle}
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
        <div className="seg seg-scope" title={scopeTitle}>
          <button
            type="button"
            className={`seg-btn ${aliveOnly ? "on" : ""}`}
            onClick={() => setMarksScope("alive")}
            disabled={!isDaily}
            title="只画存活结构的确认标记（看盘默认，失效标记是噪音）"
          >
            仅存活
          </button>
          <button
            type="button"
            className={`seg-btn ${!aliveOnly ? "on" : ""}`}
            onClick={() => setMarksScope("all")}
            disabled={!isDaily}
            title="全量显示历史确认/失效标记（研究视角，注意遮挡）"
          >
            全部
          </button>
        </div>
        <button
          className={`chip ${eff.bottomMarks ? "on" : ""}`}
          style={eff.bottomMarks ? { borderColor: "#0b9b64", color: "#0b9b64" } : undefined}
          onClick={() => toggleStruct("bottomMarks")}
          disabled={!isDaily}
          title={
            isDaily
              ? aliveOnly
                ? "底部结构确认（仅存活结构；灰色失效标记切「全部」口径查看）"
                : "底部结构确认（绿色菱形 = 存活，灰色 = 已失效）"
              : dailyOnlyTitle
          }
        >
          <span className="mk mk-bottom" style={{ marginRight: 2 }}>◆</span> 底部确认{" "}
          {counts.bottomMarks > 0 && (
            <em>{markBadge(counts.bottomMarks, markTotals?.bottomMarks)}</em>
          )}
        </button>
        <button
          className={`chip ${eff.topMarks ? "on" : ""}`}
          style={eff.topMarks ? { borderColor: "#dc2626", color: "#dc2626" } : undefined}
          onClick={() => toggleStruct("topMarks")}
          disabled={!isDaily}
          title={
            isDaily
              ? aliveOnly
                ? "顶部结构确认（仅存活结构；灰色失效标记切「全部」口径查看）"
                : "顶部结构确认（红色菱形 = 存活，灰色 = 已失效）"
              : dailyOnlyTitle
          }
        >
          <span className="mk mk-top" style={{ marginRight: 2 }}>◆</span> 顶部确认{" "}
          {counts.topMarks > 0 && (
            <em>{markBadge(counts.topMarks, markTotals?.topMarks)}</em>
          )}
        </button>
        <button
          className={`chip ${eff.invalidatedMarks ? "on" : ""}`}
          style={
            eff.invalidatedMarks
              ? { borderColor: "#9ca3af", color: "#5b6473" }
              : undefined
          }
          onClick={() => toggleStruct("invalidatedMarks")}
          disabled={!isDaily || aliveOnly}
          title={
            !isDaily
              ? dailyOnlyTitle
              : aliveOnly
                ? "结构失效标记属于已失效结构，「仅存活」口径下不显示；切「全部」口径后可用"
                : "结构失效日（触及 C 点永久失效时的标记；同结构已有确认标记时让位不画）"
          }
        >
          <span className="mk mk-dead" style={{ marginRight: 2 }}>✕</span> 结构失效{" "}
          {counts.invalidatedMarks > 0 && (
            <em>{markBadge(counts.invalidatedMarks, markTotals?.invalidatedMarks)}</em>
          )}
        </button>
      </div>

      <div className="ctl-group">
        <span className="ctl-label">参考</span>
        <button
          className={`chip ${eff.levels ? "on" : ""}`}
          onClick={() => toggle("levels")}
          disabled={!isDaily}
          title={isDaily ? "B1 第一阻力 / C 点失效线 / 顶部颈线" : dailyOnlyTitle}
        >
          <span className="mk mk-b1" style={{ marginRight: 2 }}>●</span> 参考线{" "}
          {counts.levels > 0 && <em>{counts.levels}</em>}
        </button>
        <button
          className={`chip ${eff.keyVolatility ? "on" : ""}`}
          onClick={() => toggle("keyVolatility")}
          disabled={!isDaily}
          title={isDaily ? "颜色转绿/转黑的关键性波动日" : dailyOnlyTitle}
        >
          <span className="mk mk-kv" style={{ marginRight: 2 }}>▲</span> 关键性波动{" "}
          {counts.keyVolatility > 0 && <em>{counts.keyVolatility}</em>}
        </button>
        <div className="chip-mode-group">
          <button
            className={`chip ${display.chipDist ? "on" : ""}`}
            style={display.chipDist ? { borderColor: "#f59e0b", color: "#f59e0b" } : undefined}
            onClick={() => onChange({ ...display, chipDist: !display.chipDist })}
            title="筹码分布（CYQ）：把成交量按价格纵向铺开，看筹码密集的支撑/阻力区"
          >
            ▤ 筹码峰
            {display.chipDist && (
              <em className="chip-mode-tag">
                {display.chipMode === "decay" ? "衰减" : "全历史"}
              </em>
            )}
          </button>
          {display.chipDist && (
            <div className="chip-mode-wrap">
              <button
                type="button"
                className="chip-mode-btn"
                onClick={() => setModeOpen((v) => !v)}
                title="切换筹码峰计算口径"
                aria-expanded={modeOpen}
              >
                {display.chipMode === "decay" ? "衰减" : "全历史"} ▾
              </button>
              {modeOpen && (
                <>
                  <div className="chip-mode-backdrop" onClick={() => setModeOpen(false)} />
                  <div className="chip-mode-menu" role="menu">
                    <button
                      type="button"
                      role="menuitemradio"
                      aria-checked={display.chipMode === "full"}
                      className={`chip-mode-item ${display.chipMode === "full" ? "on" : ""}`}
                      onClick={() => setChipMode("full")}
                    >
                      全历史（默认）
                    </button>
                    <button
                      type="button"
                      role="menuitemradio"
                      aria-checked={display.chipMode === "decay"}
                      className={`chip-mode-item ${display.chipMode === "decay" ? "on" : ""}`}
                      onClick={() => setChipMode("decay")}
                    >
                      衰减模式
                    </button>
                  </div>
                </>
              )}
            </div>
          )}
        </div>
        <button
          className={`chip ${eff.macd ? "on" : ""}`}
          style={eff.macd ? { borderColor: "#8b5cf6", color: "#8b5cf6" } : undefined}
          onClick={() => onChange({ ...display, macd: !display.macd })}
          disabled={!isDaily}
          title={
            isDaily
              ? "MACD 副图（研究代理）：DIF/DEA + 红绿柱。表达均线扩散/密集=乖离率=强度，不是转折节点；破线看 LEI 颜色，均线拐头看均线斜率"
              : "仅日线可用：MACD 判定口径在后端规则层，聚合视图不前端重算，避免两套口径分叉"
          }
        >
          ⑃ MACD
        </button>
        {isDaily && anyMark && (
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
