import { useEffect, useMemo, useRef, useState } from 'react'
import { Canvas, View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import type { ChartPayload, StructureMark } from '../../types'
import { fmtPrice } from '../../utils/format'
import {
  DEFAULT_DISPLAY,
  MA_DEFS,
  canvasHeight,
  computeLayout,
  drawKline,
  hitTestX,
  markHit,
  type Ctx2D,
  type KlineDisplay,
  type MaKey,
} from './draw'

const ZOOMS = [60, 120, 250]

function fmtVol(v: number | null | undefined): string {
  if (v == null || !isFinite(v)) return '--'
  if (v >= 1e8) return `${(v / 1e8).toFixed(2)}亿`
  if (v >= 1e4) return `${(v / 1e4).toFixed(1)}万`
  return v.toFixed(0)
}

function Chip({
  label,
  active,
  color,
  onClick,
}: {
  label: string
  active: boolean
  color?: string
  onClick: () => void
}) {
  return (
    <View
      onClick={onClick}
      style={{
        padding: '3px 10px',
        borderRadius: 6,
        fontSize: 10,
        lineHeight: '14px',
        marginRight: 6,
        marginBottom: 6,
        background: '#1d2026',
        border: `1px solid ${active ? color || '#5a636e' : '#2a2e37'}`,
        color: active ? color || '#dfe5ee' : '#8a8f98',
      }}
    >
      {label}
    </View>
  )
}

interface CanvasInfo {
  ctx: Ctx2D
  width: number
  height: number
  left: number
}

export default function KLineView({
  chart,
  leiMode,
}: {
  chart: ChartPayload
  leiMode?: boolean
}) {
  const canvasId = useMemo(() => `klc-${Math.random().toString(36).slice(2, 9)}`, [])
  const [display, setDisplay] = useState<KlineDisplay>(DEFAULT_DISPLAY)
  const [zoom, setZoom] = useState(120)
  const [selected, setSelected] = useState<number | null>(null)
  const [ready, setReady] = useState(0)
  const canvasInfo = useRef<CanvasInfo | null>(null)
  const touchStart = useRef<{ x: number; y: number } | null>(null)

  const n = chart?.ohlc?.length || 0
  const totalH = canvasHeight(display)

  // canvas 节点初始化 / css 高度变化（MACD 开关）时重取尺寸；重设 width 会清空变换，需重新 scale
  useEffect(() => {
    let cancelled = false
    Taro.nextTick(() => {
      const q = Taro.createSelectorQuery()
      q.select(`#${canvasId}`)
        .fields({ node: true, size: true, rect: true })
        .exec((res: any) => {
          if (cancelled) return
          const r = res && res[0]
          if (!r || !r.node || !r.width) return
          const dpr = Taro.getSystemInfoSync().pixelRatio || 2
          const node = r.node
          node.width = r.width * dpr
          node.height = r.height * dpr
          const ctx = node.getContext('2d') as Ctx2D
          ctx.scale(dpr, dpr)
          canvasInfo.current = { ctx, width: r.width, height: r.height, left: r.left || 0 }
          setReady((v) => v + 1)
        })
    })
    return () => {
      cancelled = true
    }
  }, [canvasId, totalH])

  useEffect(() => {
    const info = canvasInfo.current
    if (!info || n === 0) return
    drawKline(info.ctx, {
      chart,
      leiMode: !!leiMode,
      visibleCount: zoom,
      display,
      selected,
      width: info.width,
      height: info.height,
    })
  }, [ready, chart, leiMode, display, zoom, selected, n])

  // 换标的后旧选中下标失效，清掉十字线
  useEffect(() => {
    setSelected(null)
  }, [chart])

  if (n === 0) {
    return (
      <View className="card tiny muted" style={{ textAlign: 'center' }}>
        无 K 线数据
      </View>
    )
  }

  const localX = (t: { x?: number; clientX?: number }): number => {
    if (typeof t.x === 'number') return t.x
    if (t.clientX != null && canvasInfo.current) return t.clientX - canvasInfo.current.left
    return NaN
  }

  const onTouchStart = (e: any) => {
    const t = e.touches && e.touches[0]
    if (t) touchStart.current = { x: localX(t), y: t.clientY ?? t.y ?? 0 }
  }

  const onTouchEnd = (e: any) => {
    const info = canvasInfo.current
    if (!info) return
    const t = (e.changedTouches && e.changedTouches[0]) || (e.touches && e.touches[0])
    if (!t) return
    const x = localX(t)
    if (!isFinite(x)) return
    // 滑动手势（滚动页面）不当作点按
    if (touchStart.current) {
      const dx = x - touchStart.current.x
      const dy = (t.clientY ?? t.y ?? 0) - touchStart.current.y
      if (Math.abs(dx) > 10 || Math.abs(dy) > 10) return
    }
    const idx = hitTestX(x, computeLayout(chart, Math.min(zoom, n), info.width, display))
    setSelected((prev) => (idx != null && prev !== idx ? idx : null))
  }

  const toggle = (patch: Partial<KlineDisplay>) =>
    setDisplay((d) => ({ ...d, ...patch }))
  const toggleMa = (key: MaKey) =>
    setDisplay((d) => ({ ...d, ma: { ...d.ma, [key]: !d.ma[key] } }))

  // 选中读出：OHLC / 涨跌 / 量 / 启用均线值 / 命中结构标记
  const selBar = selected != null && selected < n ? chart.ohlc[selected] : null
  const selDate = selected != null ? (chart.dates || [])[selected] : undefined
  const selPrevClose =
    selected != null && selected > 0 ? chart.ohlc[selected - 1][1] : selBar ? selBar[0] : null
  const selPct =
    selBar && selPrevClose ? ((selBar[1] - selPrevClose) / selPrevClose) * 100 : null
  const selMark: StructureMark | null =
    (markHit(chart.bottomMarks, selDate) ||
      markHit(chart.topMarks, selDate) ||
      markHit(chart.invalidatedMarks, selDate))

  return (
    <View>
      {/* 工具行：缩放 + 显示开关 */}
      <View className="row wrap" style={{ marginBottom: 8 }}>
        {ZOOMS.filter((z) => z <= Math.max(60, n)).map((z) => (
          <Chip
            key={z}
            label={`${z}根`}
            active={zoom === z}
            onClick={() => {
              setZoom(z)
              setSelected(null)
            }}
          />
        ))}
        <Chip
          label="MACD"
          active={display.macd}
          color="#8b5cf6"
          onClick={() => toggle({ macd: !display.macd })}
        />
        {MA_DEFS.map((def) => (
          <Chip
            key={def.key}
            label={def.label}
            active={display.ma[def.key]}
            color={def.color}
            onClick={() => toggleMa(def.key)}
          />
        ))}
        <Chip
          label="底/顶标记"
          active={display.bottomMarks || display.topMarks}
          color="#0b9b64"
          onClick={() =>
            toggle({
              bottomMarks: !(display.bottomMarks || display.topMarks),
              topMarks: !(display.bottomMarks || display.topMarks),
            })
          }
        />
        <Chip
          label="失效✕"
          active={display.invalidatedMarks}
          color="#98a2b3"
          onClick={() => toggle({ invalidatedMarks: !display.invalidatedMarks })}
        />
        <Chip
          label="关键波动"
          active={display.keyVolatility}
          color="#f0cf6b"
          onClick={() => toggle({ keyVolatility: !display.keyVolatility })}
        />
        <Chip
          label="参考线"
          active={display.levels}
          color="#9aa3af"
          onClick={() => toggle({ levels: !display.levels })}
        />
      </View>

      {/* 选中读出面板 */}
      {selBar && (
        <View
          style={{
            background: '#1d2026',
            borderRadius: 8,
            padding: '8px 10px',
            marginBottom: 8,
          }}
        >
          <View className="row between">
            <View className="tiny" style={{ color: '#dfe5ee' }}>
              {(chart.dates || [])[selected!] || ''}
            </View>
            <View
              className="tiny"
              style={{ color: selPct != null && selPct >= 0 ? '#ef4650' : '#12b375' }}
            >
              {selPct != null ? `${selPct >= 0 ? '+' : ''}${selPct.toFixed(2)}%` : ''}
            </View>
          </View>
          <View className="tiny dim" style={{ marginTop: 4 }}>
            开 {fmtPrice(selBar[0])} · 高 {fmtPrice(selBar[3])} · 低 {fmtPrice(selBar[2])} · 收{' '}
            {fmtPrice(selBar[1])} · 量 {fmtVol((chart.volumes || [])[selected!])}
          </View>
          {MA_DEFS.filter((d) => display.ma[d.key]).length > 0 && (
            <View className="row wrap" style={{ marginTop: 4 }}>
              {MA_DEFS.filter((d) => display.ma[d.key]).map((d) => (
                <View
                  key={d.key}
                  className="tiny"
                  style={{ color: d.color, marginRight: 10 }}
                >
                  {d.label}{' '}
                  {fmtPrice(((chart[d.key] || []) as (number | null)[])[selected!])}
                </View>
              ))}
            </View>
          )}
          {selMark && (
            <View className="tiny" style={{ marginTop: 4, color: '#f0cf6b' }}>
              {selMark.label}
              {selMark.info?.confirmed_date ? ` · 确认 ${selMark.info.confirmed_date}` : ''}
              {selMark.info?.invalidated_date ? ` · 失效 ${selMark.info.invalidated_date}` : ''}
            </View>
          )}
        </View>
      )}

      <Canvas
        type="2d"
        id={canvasId}
        canvasId={canvasId}
        style={{ width: '100%', height: `${totalH}px` }}
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
      />

      {/* 图例 */}
      <View className="tiny muted" style={{ marginTop: 8, lineHeight: '18px' }}>
        ◆ 底部确认 · ◆ 顶部确认 · ✕ 结构失效 · ▍关键性波动 · 虚线 B1/C/颈线
        {display.levels && chart.b1Line?.yAxis != null ? ` · B1 ${fmtPrice(chart.b1Line.yAxis)}` : ''}
        {display.macd ? ' · MACD 副图为研究代理（强度描述，不构成买卖点）' : ''}
        {' '}· 点按 K 线查看当日数值
      </View>
    </View>
  )
}
