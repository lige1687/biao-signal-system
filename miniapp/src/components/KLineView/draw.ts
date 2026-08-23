// K 线 canvas 绘图（纯函数，不依赖 Taro，可脱离小程序环境单测）。
// 均线数值、结构标记、参考线、量能色全部来自后端 ChartPayload，这里只画不算——
// 不在前端计算任何信号（项目硬红线）。

import type { ChartPayload, LevelLine, StructureMark } from '../../types'
import { fmtPrice } from '../../utils/format'

export type MaKey = 'ema20' | 'sma20' | 'ema60' | 'sma60' | 'ema120' | 'sma120'

/** 均线定义：同周期同色、EMA 实线 SMA 虚线（与 web KlineChart 约定一致）。 */
export const MA_DEFS: { key: MaKey; label: string; color: string; dashed: boolean }[] = [
  { key: 'ema20', label: 'EMA20', color: '#3b76e8', dashed: false },
  { key: 'sma20', label: 'SMA20', color: '#3b76e8', dashed: true },
  { key: 'ema60', label: 'EMA60', color: '#12b375', dashed: false },
  { key: 'sma60', label: 'SMA60', color: '#12b375', dashed: true },
  { key: 'ema120', label: 'EMA120', color: '#ef4650', dashed: false },
  { key: 'sma120', label: 'SMA120', color: '#ef4650', dashed: true },
]

export interface KlineDisplay {
  ma: Record<MaKey, boolean>
  bottomMarks: boolean // 底部确认菱形
  topMarks: boolean // 顶部确认菱形
  invalidatedMarks: boolean // 结构失效 ✕
  keyVolatility: boolean // 关键性波动竖线
  levels: boolean // B1 / C 点 / 颈线参考线
  macd: boolean // MACD 副图（研究代理强度指标）
}

/** 手机屏默认三条线：EMA20（蓝实）/ SMA60（绿虚）/ EMA120（红实），其余可点开。 */
export const DEFAULT_DISPLAY: KlineDisplay = {
  ma: { ema20: true, sma20: false, ema60: false, sma60: true, ema120: true, sma120: false },
  bottomMarks: true,
  topMarks: true,
  invalidatedMarks: true,
  keyVolatility: true,
  levels: true,
  macd: false,
}

/** 画布总高（css px），主图 240 + 量能 50 + MACD 56（可选）+ 轴 18 + 间距。 */
export function canvasHeight(display: KlineDisplay): number {
  return 10 + 240 + 6 + 50 + 6 + 18 + (display.macd ? 6 + 56 : 0)
}

// 微信 canvas 2d context 的最小结构类型（避免引 DOM lib）。
export interface Ctx2D {
  fillStyle: string
  strokeStyle: string
  lineWidth: number
  globalAlpha: number
  font: string
  textAlign: 'left' | 'right' | 'center'
  textBaseline: 'top' | 'middle' | 'bottom'
  clearRect(x: number, y: number, w: number, h: number): void
  fillRect(x: number, y: number, w: number, h: number): void
  beginPath(): void
  closePath(): void
  moveTo(x: number, y: number): void
  lineTo(x: number, y: number): void
  arc(x: number, y: number, r: number, start: number, end: number): void
  stroke(): void
  fill(): void
  fillText(text: string, x: number, y: number): void
  measureText(text: string): { width: number }
  setLineDash(segments: number[]): void
  scale(x: number, y: number): void
  save(): void
  restore(): void
}

export interface KlineLayout {
  start: number // 可见区间起始下标（全局）
  count: number // 可见根数
  barW: number // 每根 K 的像素宽
  padL: number
  plotW: number
  plotRight: number
  mainTop: number
  mainH: number
  volTop: number
  volH: number
  macdTop: number
  macdH: number
}

const PAD_L = 6
const PAD_R = 52
const PAD_T = 10
const AXIS_H = 18
const VOL_H = 50
const MACD_H = 56
const GAP = 6

export function computeLayout(
  chart: ChartPayload,
  visibleCount: number,
  width: number,
  display: KlineDisplay,
): KlineLayout {
  const n = chart.ohlc.length
  const count = Math.max(1, Math.min(visibleCount, n))
  const start = n - count
  const plotW = Math.max(10, width - PAD_L - PAD_R)
  const macdH = display.macd ? MACD_H : 0
  const mainH = 240
  const mainTop = PAD_T
  const volTop = mainTop + mainH + GAP
  const macdTop = volTop + VOL_H + GAP
  return {
    start,
    count,
    barW: plotW / count,
    padL: PAD_L,
    plotW,
    plotRight: PAD_L + plotW,
    mainTop,
    mainH,
    volTop,
    volH: VOL_H,
    macdTop,
    macdH,
  }
}

/** 触摸 x（相对画布）→ 全局 K 线下标；不在绘图区返回 null。 */
export function hitTestX(x: number, layout: KlineLayout): number | null {
  const rel = Math.floor((x - layout.padL) / layout.barW)
  const idx = layout.start + rel
  if (rel < 0 || idx >= layout.start + layout.count) return null
  return idx
}

export interface DrawParams {
  chart: ChartPayload
  leiMode: boolean
  visibleCount: number
  display: KlineDisplay
  selected: number | null // 全局下标，画十字线
  width: number
  height: number
}

function diamond(ctx: Ctx2D, x: number, y: number, r: number, color: string, ring: boolean): void {
  ctx.beginPath()
  ctx.moveTo(x, y - r)
  ctx.lineTo(x + r, y)
  ctx.lineTo(x, y + r)
  ctx.lineTo(x - r, y)
  ctx.closePath()
  ctx.fillStyle = color
  ctx.fill()
  if (ring) {
    ctx.beginPath()
    ctx.arc(x, y, r + 2.5, 0, Math.PI * 2)
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 1
    ctx.stroke()
  }
}

function crossMark(ctx: Ctx2D, x: number, y: number, r: number, color: string, ring: boolean): void {
  ctx.beginPath()
  ctx.moveTo(x - r, y - r)
  ctx.lineTo(x + r, y + r)
  ctx.moveTo(x + r, y - r)
  ctx.lineTo(x - r, y + r)
  ctx.strokeStyle = color
  ctx.lineWidth = 1.6
  ctx.stroke()
  if (ring) {
    ctx.beginPath()
    ctx.arc(x, y, r + 2.5, 0, Math.PI * 2)
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 1
    ctx.stroke()
  }
}

function clamp(v: number, lo: number, hi: number): number {
  return v < lo ? lo : v > hi ? hi : v
}

/** 选中日命中的结构标记（供读出面板显示确认/失效信息）。 */
export function markHit(
  marks: StructureMark[] | undefined,
  date: string | undefined,
): StructureMark | null {
  if (!marks || !date) return null
  for (const m of marks) if (m.date === date) return m
  return null
}

export function drawKline(ctx: Ctx2D, p: DrawParams): void {
  const { chart, leiMode, display } = p
  const n = chart.ohlc.length
  if (n === 0) return
  const L = computeLayout(chart, p.visibleCount, p.width, display)
  const { start, count } = L

  ctx.clearRect(0, 0, p.width, p.height)

  const ohlc = chart.ohlc
  const dates = chart.dates || []
  const volumes = chart.volumes || []
  const states = chart.states || []
  const volColors = chart.volColors || []
  const priceUp = chart.priceUp || '#e33d47'
  const priceDown = chart.priceDown || '#0b9b64'
  const stateColors = chart.stateColors || {}

  const candleColor = (i: number): string => {
    const bar = ohlc[i]
    const up = bar[1] >= bar[0]
    if (leiMode) return stateColors[states[i]] || (up ? priceUp : priceDown)
    return up ? priceUp : priceDown
  }

  // ---- 比例尺：可见高低点 + 启用均线 + 参考线（远离盘面的参考线不参与，只钉边显示）----
  let minLow = Infinity
  let maxHigh = -Infinity
  let volMax = 0
  for (let i = start; i < n; i++) {
    const bar = ohlc[i]
    if (bar[2] < minLow) minLow = bar[2]
    if (bar[3] > maxHigh) maxHigh = bar[3]
    const v = volumes[i] || 0
    if (v > volMax) volMax = v
  }
  for (const def of MA_DEFS) {
    if (!display.ma[def.key]) continue
    const series = (chart[def.key] || []) as (number | null)[]
    for (let i = start; i < n; i++) {
      const v = series[i]
      if (v == null) continue
      if (v < minLow) minLow = v
      if (v > maxHigh) maxHigh = v
    }
  }
  const allLevels: LevelLine[] = []
  if (display.levels) {
    if (chart.b1Line) allLevels.push(chart.b1Line)
    allLevels.push(...(chart.bottomLines || []), ...(chart.topLines || []))
  }
  for (const lv of allLevels) {
    if (lv.yAxis == null) continue
    const span = maxHigh - minLow || 1
    if (lv.yAxis >= minLow - span * 0.35 && lv.yAxis <= maxHigh + span * 0.35) {
      if (lv.yAxis < minLow) minLow = lv.yAxis
      if (lv.yAxis > maxHigh) maxHigh = lv.yAxis
    }
  }
  const pad = (maxHigh - minLow) * 0.06 || 1
  minLow -= pad
  maxHigh += pad
  const range = maxHigh - minLow || 1

  const toY = (price: number): number => L.mainTop + L.mainH - ((price - minLow) / range) * L.mainH
  const xOf = (i: number): number => L.padL + (i - start) * L.barW + L.barW / 2

  // ---- 网格 + 价格刻度（右轴）----
  ctx.font = '10px sans-serif'
  ctx.textAlign = 'left'
  ctx.textBaseline = 'middle'
  for (let k = 0; k <= 4; k++) {
    const y = L.mainTop + (L.mainH * k) / 4
    const price = maxHigh - (range * k) / 4
    ctx.strokeStyle = 'rgba(255,255,255,0.06)'
    ctx.lineWidth = 1
    ctx.setLineDash([])
    ctx.beginPath()
    ctx.moveTo(L.padL, y)
    ctx.lineTo(L.plotRight, y)
    ctx.stroke()
    ctx.fillStyle = '#7b8494'
    ctx.fillText(fmtPrice(price), L.plotRight + 4, y)
  }

  // ---- 量能（后端 4 档量能色优先）----
  const bodyW = Math.min(13, Math.max(1, L.barW * 0.62))
  const volBase = L.volTop + L.volH
  for (let i = start; i < n; i++) {
    const v = volumes[i] || 0
    if (v <= 0) continue
    const h = volMax > 0 ? (v / volMax) * (L.volH - 4) : 0
    if (h <= 0) continue
    ctx.fillStyle = volColors[i] || candleColor(i)
    ctx.globalAlpha = 0.8
    ctx.fillRect(xOf(i) - bodyW / 2, volBase - h, bodyW, h)
    ctx.globalAlpha = 1
  }

  // ---- 均线（同周期同色，EMA 实线 / SMA 虚线）----
  ctx.lineWidth = 1.2
  for (const def of MA_DEFS) {
    if (!display.ma[def.key]) continue
    const series = (chart[def.key] || []) as (number | null)[]
    ctx.strokeStyle = def.color
    ctx.setLineDash(def.dashed ? [4, 3] : [])
    ctx.beginPath()
    let drawing = false
    for (let i = start; i < n; i++) {
      const v = series[i]
      if (v == null) {
        drawing = false
        continue
      }
      const x = xOf(i)
      const y = toY(v)
      if (drawing) ctx.lineTo(x, y)
      else {
        ctx.moveTo(x, y)
        drawing = true
      }
    }
    ctx.stroke()
  }
  ctx.setLineDash([])

  // ---- 关键性波动竖线（含顶部把手）----
  if (display.keyVolatility && chart.keyVolatility) {
    for (const kv of chart.keyVolatility) {
      const idx = dates.indexOf(kv.date)
      if (idx < start) continue
      const x = xOf(idx)
      ctx.strokeStyle = 'rgba(240,207,107,0.5)'
      ctx.lineWidth = 1
      ctx.setLineDash([3, 3])
      ctx.beginPath()
      ctx.moveTo(x, L.mainTop)
      ctx.lineTo(x, L.mainTop + L.mainH)
      ctx.stroke()
      ctx.setLineDash([])
      ctx.beginPath()
      ctx.arc(x, L.mainTop + 3, 2.5, 0, Math.PI * 2)
      ctx.fillStyle = '#f0cf6b'
      ctx.fill()
    }
  }

  // ---- 蜡烛 ----
  for (let i = start; i < n; i++) {
    const [o, c, l, h] = ohlc[i]
    const color = candleColor(i)
    const x = xOf(i)
    ctx.strokeStyle = color
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(x, toY(h))
    ctx.lineTo(x, toY(l))
    ctx.stroke()
    const top = toY(Math.max(o, c))
    const hgt = Math.max(1, Math.abs(toY(c) - toY(o)))
    ctx.fillStyle = color
    ctx.fillRect(x - bodyW / 2, top, bodyW, hgt)
  }

  // ---- 参考线（B1 / C 点 / 颈线），右端小标签，超界钉边 ----
  if (display.levels) {
    ctx.font = '9px sans-serif'
    ctx.textAlign = 'right'
    ctx.textBaseline = 'bottom'
    for (const lv of allLevels) {
      if (lv.yAxis == null) continue
      const y = clamp(toY(lv.yAxis), L.mainTop + 8, L.mainTop + L.mainH - 2)
      ctx.strokeStyle = lv.color || '#9aa3af'
      ctx.lineWidth = 1.1
      ctx.setLineDash(lv.dash === 'dash' ? [5, 4] : [])
      ctx.globalAlpha = 0.85
      ctx.beginPath()
      ctx.moveTo(L.padL, y)
      ctx.lineTo(L.plotRight, y)
      ctx.stroke()
      ctx.globalAlpha = 1
      ctx.setLineDash([])
      const text = `${lv.label_cn || '参考位'} ${fmtPrice(lv.yAxis)}`
      const w = ctx.measureText(text).width + 8
      ctx.fillStyle = 'rgba(15,17,21,0.88)'
      ctx.fillRect(L.plotRight - w - 2, y - 13, w, 12)
      ctx.fillStyle = lv.color || '#9aa3af'
      ctx.fillText(text, L.plotRight - 6, y - 2)
    }
  }

  // ---- 结构标记：底部确认 ◆ / 顶部确认 ◆ / 失效 ✕（选中日白圈点亮）----
  const selDate = p.selected != null ? dates[p.selected] : undefined
  const drawMarks = (
    marks: StructureMark[] | undefined,
    enabled: boolean,
    kind: 'bottom' | 'top' | 'invalidated',
  ) => {
    if (!enabled || !marks) return
    for (const m of marks) {
      const idx = dates.indexOf(m.date)
      if (idx < start) continue
      const x = xOf(idx)
      const y = clamp(toY(m.price), L.mainTop + 6, L.mainTop + L.mainH - 6)
      const ring = selDate === m.date
      const r = ring ? 5.5 : 4.5
      if (kind === 'invalidated') {
        crossMark(ctx, x, y, r, '#98a2b3', ring)
      } else {
        const live = m.live !== false
        const color =
          kind === 'bottom' ? (live ? '#0b9b64' : '#98a2b3') : live ? '#dc2626' : '#98a2b3'
        diamond(ctx, x, y, r, color, ring)
      }
    }
  }
  drawMarks(chart.bottomMarks, display.bottomMarks, 'bottom')
  drawMarks(chart.topMarks, display.topMarks, 'top')
  drawMarks(chart.invalidatedMarks, display.invalidatedMarks, 'invalidated')

  // ---- MACD 副图（DIF 橙 / DEA 紫 / 红绿柱，研究代理强度指标）----
  if (display.macd && L.macdH > 0) {
    const dif = chart.macdDif || []
    const dea = chart.macdDea || []
    const hist = chart.macdHist || []
    let m = 0
    for (let i = start; i < n; i++) {
      for (const arr of [dif, dea, hist]) {
        const v = Math.abs(arr[i] || 0)
        if (v > m) m = v
      }
    }
    m = m || 1
    const y0 = L.macdTop + L.macdH / 2
    ctx.strokeStyle = 'rgba(255,255,255,0.08)'
    ctx.lineWidth = 1
    ctx.beginPath()
    ctx.moveTo(L.padL, y0)
    ctx.lineTo(L.plotRight, y0)
    ctx.stroke()
    const amp = L.macdH / 2 - 3
    const hw = Math.max(1, bodyW * 0.7)
    for (let i = start; i < n; i++) {
      const v = hist[i] || 0
      const h = (Math.abs(v) / m) * amp
      if (h <= 0) continue
      ctx.fillStyle = v >= 0 ? '#e33d47' : '#0b9b64'
      ctx.globalAlpha = 0.75
      ctx.fillRect(xOf(i) - hw / 2, v >= 0 ? y0 - h : y0, hw, h)
      ctx.globalAlpha = 1
    }
    const drawLine = (arr: (number | null)[], color: string) => {
      ctx.strokeStyle = color
      ctx.lineWidth = 1.1
      ctx.beginPath()
      let drawing = false
      for (let i = start; i < n; i++) {
        const v = arr[i]
        if (v == null) {
          drawing = false
          continue
        }
        const y = y0 - (v / m) * amp
        if (drawing) ctx.lineTo(xOf(i), y)
        else {
          ctx.moveTo(xOf(i), y)
          drawing = true
        }
      }
      ctx.stroke()
    }
    drawLine(dif, '#e36b1c')
    drawLine(dea, '#8b5cf6')
  }

  // ---- 最新价标签（右轴色块）----
  const lastIdx = n - 1
  const lastClose = chart.lastClose != null ? chart.lastClose : ohlc[lastIdx][1]
  const tagY = clamp(toY(lastClose), L.mainTop + 7, L.mainTop + L.mainH - 7)
  ctx.fillStyle = candleColor(lastIdx)
  ctx.fillRect(L.plotRight + 2, tagY - 7, PAD_R - 6, 14)
  ctx.font = '9px sans-serif'
  ctx.textAlign = 'center'
  ctx.textBaseline = 'middle'
  ctx.fillStyle = '#ffffff'
  ctx.fillText(fmtPrice(lastClose), L.plotRight + 2 + (PAD_R - 6) / 2, tagY)

  // ---- 日期轴 ----
  ctx.font = '9px sans-serif'
  ctx.fillStyle = '#7b8494'
  ctx.textBaseline = 'top'
  ctx.textAlign = 'center'
  const spots = [start, start + Math.floor(count / 3), start + Math.floor((count * 2) / 3), n - 1]
  const seen = new Set<number>()
  for (const idx of spots) {
    if (idx < start || idx >= n || seen.has(idx) || !dates[idx]) continue
    seen.add(idx)
    ctx.fillText(dates[idx].slice(5), clamp(xOf(idx), L.padL + 14, L.plotRight - 14), p.height - AXIS_H + 5)
  }

  // ---- 十字线（选中根）----
  if (p.selected != null && p.selected >= start && p.selected < n) {
    const x = xOf(p.selected)
    const close = ohlc[p.selected][1]
    const bottomY = L.macdH > 0 ? L.macdTop + L.macdH : L.volTop + L.volH
    ctx.strokeStyle = 'rgba(255,255,255,0.45)'
    ctx.lineWidth = 1
    ctx.setLineDash([3, 3])
    ctx.beginPath()
    ctx.moveTo(x, L.mainTop)
    ctx.lineTo(x, bottomY)
    ctx.moveTo(L.padL, toY(close))
    ctx.lineTo(L.plotRight, toY(close))
    ctx.stroke()
    ctx.setLineDash([])
    ctx.beginPath()
    ctx.arc(x, toY(close), 2.5, 0, Math.PI * 2)
    ctx.strokeStyle = '#ffffff'
    ctx.lineWidth = 1.2
    ctx.stroke()
  }
}
