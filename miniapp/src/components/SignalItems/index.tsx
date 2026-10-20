import { View } from '@tarojs/components'
import type { ScanItem, SignalAlert, UnavailableItem } from '../../types'
import Tag from '../Tag'
import { fmtDate } from '../../utils/format'

// 买点（来自 daily_opportunity_scan）：actionable / waiting / blocked
export function BuySignalCard({ item, onOpen }: { item: ScanItem; onOpen?: () => void }) {
  const tone = item.verdict === 'actionable' ? 'green' : item.verdict === 'blocked' ? 'red' : 'warn'
  return (
    <View className="card" onClick={onOpen}>
      <View className="row between">
        <View style={{ flex: 1, marginRight: 12 }}>
          <View style={{ fontWeight: 600, color: '#f2f4f7' }}>{item.display_name || item.symbol}</View>
          <View className="tiny muted">{item.symbol}</View>
        </View>
        <Tag text={item.verdict_cn} tone={tone} />
      </View>
      {item.best_scenario_cn && (
        <View className="tiny dim" style={{ marginTop: 8 }}>
          场景：{item.best_scenario_cn}
          {item.best_state ? `（${item.best_state}）` : ''}
        </View>
      )}
      {item.reward_risk_computable && item.reward_risk_ratio != null && (
        <View className="tiny muted" style={{ marginTop: 2 }}>
          盈亏比 {item.reward_risk_ratio.toFixed(2)}
        </View>
      )}
      {item.blocking_reasons && item.blocking_reasons.length > 0 && (
        <View className="tiny" style={{ color: '#ff8a93', marginTop: 6 }}>
          阻断：{item.blocking_reasons.join('；')}
        </View>
      )}
      {item.missing_summary_cn && (
        <View className="tiny muted" style={{ marginTop: 4 }}>
          {item.missing_summary_cn}
        </View>
      )}
      {item.has_active_plan && (
        <View style={{ marginTop: 8 }}>
          <Tag text="已有计划" tone="gray" />
        </View>
      )}
      {item.error && (
        <View className="tiny" style={{ color: '#ff8a93', marginTop: 6 }}>
          错误：{item.error}
        </View>
      )}
    </View>
  )
}

// 卖点（来自 signal_alerts）：hard / warn / soft
export function SellSignalCard({ item }: { item: SignalAlert }) {
  const tierTone = item.tier === 'hard' ? 'red' : item.tier === 'warn' ? 'warn' : 'gray'
  const tierCn = item.tier === 'hard' ? '硬' : item.tier === 'warn' ? '警' : '软'
  return (
    <View className="card" style={{ borderColor: '#3a2630' }}>
      <View className="row between">
        <View style={{ flex: 1, marginRight: 12 }}>
          <View style={{ fontWeight: 600, color: '#f2f4f7' }}>{item.display_name || item.symbol}</View>
          <View className="tiny muted">{item.symbol}</View>
        </View>
        <View className="row">
          {item.is_new && <Tag text="新" tone="red" />}
          <Tag text={tierCn} tone={tierTone} />
        </View>
      </View>
      <View className="tiny dim" style={{ marginTop: 6 }}>
        {item.kind_cn}
        {item.title ? ` · ${item.title}` : ''}
      </View>
      <View className="tiny" style={{ marginTop: 4 }}>
        {item.reason_cn}
      </View>
      {item.provenance === 'research_proxy' && (
        <View style={{ marginTop: 8 }}>
          <Tag text="研究代理" tone="rp" />
        </View>
      )}
      {item.available_date && (
        <View className="tiny muted" style={{ marginTop: 4 }}>
          可用日：{fmtDate(item.available_date)}
        </View>
      )}
    </View>
  )
}

// 数据不可用：必须显式展示 DATA_UNAVAILABLE，不得静默当成无信号。
export function UnavailableCard({ item }: { item: UnavailableItem }) {
  return (
    <View className="card" style={{ borderColor: '#6b5a1f', background: '#2a2410' }}>
      <View className="row between">
        <View style={{ flex: 1, marginRight: 12 }}>
          <View style={{ fontWeight: 600, color: '#f0cf6b' }}>{item.symbol}</View>
        </View>
        <Tag text="DATA_UNAVAILABLE" tone="warn" />
      </View>
      <View className="tiny" style={{ marginTop: 6, color: '#f0cf6b' }}>
        {item.error || '该标的分析失败，数据不可用'}
      </View>
    </View>
  )
}
