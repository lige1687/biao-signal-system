import { View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import type { Card } from '../../types'
import Tag from '../Tag'
import Sparkline from '../Sparkline'
import { fmtPrice, fmtPct, changeClass, leiColorCn } from '../../utils/format'

function colorTone(c: string | null | undefined): { tone: Parameters<typeof Tag>[0]['tone']; style?: Record<string, string> } {
  switch (c) {
    case 'green':
      return { tone: 'green' }
    case 'gray':
      return { tone: 'gray' }
    case 'black':
      return { tone: 'default', style: { background: '#1f2937', color: '#d7dbe0', borderColor: '#1f2937' } }
    default:
      return { tone: 'default' }
  }
}

export default function CardItem({ card }: { card: Card }) {
  const go = () => {
    Taro.navigateTo({ url: `/pages/detail/index?symbol=${encodeURIComponent(card.symbol)}` })
  }
  const chg = card.change_pct
  const chgCls = changeClass(chg)
  const ct = colorTone(card.color)

  return (
    <View className="card" onClick={go} style={{ opacity: card.stale ? 0.62 : 1 }}>
      <View className="row between">
        <View style={{ flex: 1, minWidth: 0, marginRight: 12 }}>
          <View style={{ fontSize: 30, fontWeight: 600, color: '#f2f4f7' }}>
            {card.display_name || card.symbol}
          </View>
          <View className="tiny muted">
            {card.symbol} · {card.market_cn}
          </View>
        </View>
        <View style={{ textAlign: 'right' }}>
          <View className={chgCls} style={{ fontSize: 32, fontWeight: 600 }}>
            {fmtPrice(card.price)}
          </View>
          <View className={`tiny ${chgCls}`}>{fmtPct(chg)}</View>
        </View>
      </View>

      <View className="row wrap" style={{ marginTop: 12 }}>
        <Tag text={leiColorCn(card.color)} tone={ct.tone} style={ct.style} />
        {card.stage_cn && <Tag text={card.stage_cn} tone="gray" />}
        {card.risk_state_cn && <Tag text={card.risk_state_cn} tone="red" />}
        {card.is_intraday_forming && <Tag text="盘中成形" tone="intraday" />}
      </View>

      {card.key_change_cn && (
        <View className="tiny dim" style={{ marginTop: 8 }}>
          关键变化：{card.key_change_cn}
        </View>
      )}

      {card.sparkline && card.sparkline.length > 1 && (
        <View style={{ marginTop: 10 }}>
          <Sparkline points={card.sparkline} width={300} height={44} />
        </View>
      )}

      {card.error && (
        <View className="tiny" style={{ color: '#ff8a93', marginTop: 8 }}>
          数据异常：{card.error}
        </View>
      )}
      {card.stale && !card.error && (
        <View className="tiny muted" style={{ marginTop: 4 }}>
          数据较旧（stale）
        </View>
      )}
    </View>
  )
}
