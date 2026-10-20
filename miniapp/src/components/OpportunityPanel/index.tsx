import { useEffect, useState } from 'react'
import { View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { api, ApiError } from '../../api/client'
import type { TodayOpportunityResponse, ScanItem } from '../../types'
import { BuySignalCard } from '../SignalItems'
import SectionTitle from '../SectionTitle'
import { fmtDateTime } from '../../utils/format'

// 今日机会雷达：读库快照（GET /opportunities/today，launchd 15:00 写入）。
// - actionable 条件已成立（绿）
// - waiting   等待条件成立（灰，展示缺的条件）
// - blocked   环境阻断（黄，展示阻断原因）
// [重扫] 调 POST /opportunities/today/refresh；当日未扫描（scanned=0）显示空态。

function Group({
  title,
  items,
  tone,
}: {
  title: string
  items: ScanItem[]
  tone: string
}) {
  if (items.length === 0) return null
  return (
    <View style={{ marginTop: 8 }}>
      <View className="tiny" style={{ color: tone, fontWeight: 600 }}>
        {title}（{items.length}）
      </View>
      {items.map((it) => (
        <View key={it.symbol} style={{ marginTop: 8 }}>
          <BuySignalCard
            item={it}
            onOpen={() =>
              Taro.navigateTo({ url: `/pages/detail/index?symbol=${encodeURIComponent(it.symbol)}` })
            }
          />
        </View>
      ))}
    </View>
  )
}

export default function OpportunityPanel() {
  const [data, setData] = useState<TodayOpportunityResponse | null>(null)
  const [errorText, setErrorText] = useState('')
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const d = await api.opportunitiesToday()
      setData(d)
      setErrorText('')
    } catch (e) {
      setErrorText(e instanceof ApiError ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  const rescan = async () => {
    if (refreshing) return
    setRefreshing(true)
    try {
      const d = await api.refreshOpportunities()
      setData(d)
      setErrorText('')
      Taro.showToast({ title: '已重扫', icon: 'none' })
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : String(e)
      Taro.showToast({ title: '重扫失败', icon: 'none' })
      setErrorText(msg)
    } finally {
      setRefreshing(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const scanned = data?.scanned ?? 0
  const actionable = data?.actionable || []
  const waiting = data?.waiting || []
  const blocked = data?.blocked || []

  return (
    <View style={{ marginBottom: 14 }}>
      <View className="row between" style={{ alignItems: 'center' }}>
        <View className="row" style={{ alignItems: 'center' }}>
          <SectionTitle>今日机会雷达</SectionTitle>
        </View>
        <View
          className="btn btn-ghost tiny"
          style={{ padding: '6px 16px' }}
          onClick={() => void rescan()}
        >
          {refreshing ? '重扫中…' : '重扫'}
        </View>
      </View>
      <View className="tiny muted" style={{ marginBottom: 4 }}>
        {loading && !data
          ? '加载中…'
          : scanned > 0
            ? `${actionable.length + waiting.length} 个机会 · ${actionable.length} 可操作 / ${waiting.length} 待确认 / ${blocked.length} 阻断${data?.generated_at ? ` · ${fmtDateTime(data.generated_at)}` : ''}`
            : '今日尚未扫描，点「重扫」立即扫描自选'}
      </View>

      {errorText && (
        <View className="tiny" style={{ color: '#ff8a93', marginTop: 4 }}>
          {errorText}
        </View>
      )}

      <Group title="✅ 条件已成立" items={actionable} tone="#12b375" />
      <Group title="🚫 环境阻断" items={blocked} tone="#f0cf6b" />
      <Group title="⏳ 等待条件成立" items={waiting} tone="#8a8f98" />
    </View>
  )
}
