import { View } from '@tarojs/components'
import { useMemo } from 'react'
import { fmtPrice } from '../../utils/format'

// 极简迷你走势：用 view 柱状近似，红线=涨绿线=跌（A股惯例）。无缩放平移。
export default function Sparkline({
  points,
  width = 160,
  height = 48,
}: {
  points: { date: string; close: number }[] | null | undefined
  width?: number
  height?: number
}) {
  const bars = useMemo(() => {
    if (!points || points.length === 0) return []
    const closes = points.map((p) => p.close)
    const min = Math.min(...closes)
    const max = Math.max(...closes)
    const range = max - min || 1
    const n = closes.length
    const bw = width / Math.max(1, n)
    return closes.map((c, i) => {
      const prev = i > 0 ? closes[i - 1] : c
      const up = c >= prev
      const h = Math.max(2, ((c - min) / range) * (height - 4))
      return { i, up, h, left: i * bw, bw, c }
    })
  }, [points, width, height])

  if (!bars.length) return null

  return (
    <View style={{ position: 'relative', width, height, overflow: 'hidden' }}>
      {bars.map((b) => (
        <View
          key={b.i}
          style={{
            position: 'absolute',
            left: b.left,
            bottom: 0,
            width: Math.max(1, b.bw - 1),
            height: b.h,
            background: b.up ? '#e33d47' : '#0b9b64',
            opacity: 0.85,
          }}
        />
      ))}
      <View className="tiny muted" style={{ position: 'absolute', top: 0, right: 0 }}>
        {fmtPrice(bars[bars.length - 1]?.c)}
      </View>
    </View>
  )
}
