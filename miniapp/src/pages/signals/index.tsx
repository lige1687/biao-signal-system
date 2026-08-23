import { useEffect, useRef, useState } from 'react'
import { View, Text } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { api, ApiError } from '../../api/client'
import type { SignalsToday, ScanItem, SignalAlert, UnavailableItem } from '../../types'
import { BuySignalCard, SellSignalCard, UnavailableCard } from '../../components/SignalItems'
import LoadingState, { type LoadStatus } from '../../components/LoadingState'
import SectionTitle from '../../components/SectionTitle'
import Tag from '../../components/Tag'
import { fmtDate } from '../../utils/format'

// 下拉刷新回调需在模块作用域暴露给 Taro 框架
let pullRefreshHandler: (() => void) | null = null
export function onPullDownRefresh() {
  pullRefreshHandler?.()
}

function asOfBadge(asOf: string | null | undefined): { text: string; tone: 'intraday' | 'green' } {
  if (asOf === 'intraday') return { text: '盘中临时', tone: 'intraday' }
  if (asOf === 'close') return { text: '收盘权威', tone: 'green' }
  return { text: '口径未知', tone: 'intraday' }
}

export default function SignalsPage() {
  const [data, setData] = useState<SignalsToday | null>(null)
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [errorText, setErrorText] = useState<string>('')
  const [rescanning, setRescanning] = useState(false)

  const load = async (fromPull = false) => {
    try {
      const d = await api.signalsToday()
      setData(d)
      const empty =
        !d ||
        (d.available === false) ||
        (!d.actionable.length &&
          !d.waiting.length &&
          !d.blocked.length &&
          !d.sell_hard.length &&
          !d.sell_warn.length &&
          !d.sell_soft.length &&
          !d.unavailable.length)
      setStatus(empty ? 'empty' : 'ok')
      setErrorText('')
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : String(e)
      setErrorText(msg)
      setStatus('error')
    } finally {
      if (fromPull) Taro.stopPullDownRefresh()
    }
  }

  const rescan = async () => {
    if (rescanning) return
    setRescanning(true)
    try {
      const d = await api.refreshSignals('close')
      setData(d)
      setStatus('ok')
      setErrorText('')
      Taro.showToast({ title: '已重扫（收盘口径）', icon: 'none' })
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : String(e)
      Taro.showToast({ title: '重扫失败', icon: 'none' })
      setErrorText(msg)
    } finally {
      setRescanning(false)
    }
  }

  useEffect(() => {
    pullRefreshHandler = () => {
      void load(true)
    }
    void load(false)
  }, [])

  const ab = asOfBadge(data?.as_of)

  return (
    <View className="page">
      <View className="row between" style={{ marginBottom: 6 }}>
        <View className="row">
          <Tag text={ab.text} tone={ab.tone} />
          {data?.scan_date && <Text className="tiny muted" style={{ marginLeft: 8 }}>{fmtDate(data.scan_date)}</Text>}
        </View>
        <View
          className={rescanning ? 'btn btn-ghost tiny' : 'btn tiny'}
          style={{ width: 200, padding: '10px 0' }}
          onClick={rescan}
        >
          {rescanning ? '重扫中…' : '重扫(收盘)'}
        </View>
      </View>
      <View className="tiny muted" style={{ marginBottom: 10 }}>
        买点来自 daily_opportunity_scan，卖点来自 signal_alerts；收盘口径为权威，盘中临时仅当日参考。
      </View>

      <LoadingState status={status} emptyText="今日尚未扫描或暂无信号（可点右上「重扫」）" errorText={errorText} onRetry={() => load(false)}>
        {data && (
          <>
            {(data.actionable.length > 0 || data.waiting.length > 0 || data.blocked.length > 0) && (
              <>
                <SectionTitle>买点（机会扫描）</SectionTitle>
                {data.actionable.map((it: ScanItem) => (
                  <BuySignalCard key={it.symbol + 'a'} item={it} />
                ))}
                {data.waiting.map((it: ScanItem) => (
                  <BuySignalCard key={it.symbol + 'w'} item={it} />
                ))}
                {data.blocked.map((it: ScanItem) => (
                  <BuySignalCard key={it.symbol + 'b'} item={it} />
                ))}
              </>
            )}

            {(data.sell_hard.length > 0 || data.sell_warn.length > 0 || data.sell_soft.length > 0) && (
              <>
                <SectionTitle>卖点（信号警示）</SectionTitle>
                {data.sell_hard.map((it: SignalAlert) => (
                  <SellSignalCard key={it.symbol + 'h'} item={it} />
                ))}
                {data.sell_warn.map((it: SignalAlert) => (
                  <SellSignalCard key={it.symbol + 'w'} item={it} />
                ))}
                {data.sell_soft.map((it: SignalAlert) => (
                  <SellSignalCard key={it.symbol + 's'} item={it} />
                ))}
              </>
            )}

            {data.unavailable.length > 0 && (
              <>
                <SectionTitle>数据不可用</SectionTitle>
                {data.unavailable.map((it: UnavailableItem) => (
                  <UnavailableCard key={it.symbol} item={it} />
                ))}
              </>
            )}
          </>
        )}
      </LoadingState>
    </View>
  )
}
