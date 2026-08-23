import { useEffect, useState } from 'react'
import { View } from '@tarojs/components'
import Taro, { useDidShow } from '@tarojs/taro'
import { api, ApiError } from '../../api/client'
import type { DashboardResponse, Card, PlansSummary } from '../../types'
import CardItem from '../../components/CardItem'
import LoadingState, { type LoadStatus } from '../../components/LoadingState'
import SectionTitle from '../../components/SectionTitle'
import MarketBreadthStrip from '../../components/MarketBreadthStrip'
import OpportunityPanel from '../../components/OpportunityPanel'

export default function DashboardPage() {
  const [data, setData] = useState<DashboardResponse | null>(null)
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [errorText, setErrorText] = useState<string>('')
  const [todoCount, setTodoCount] = useState<number | null>(null)

  const load = async () => {
    try {
      const d = await api.dashboardCards()
      setData(d)
      setStatus((d.cards && d.cards.length) ? 'ok' : 'empty')
      setErrorText('')
    } catch (e) {
      let msg: string
      if (e instanceof ApiError) {
        msg = e.message
      } else {
        const anyE = e as { errMsg?: string; message?: string } | null
        msg = anyE?.errMsg || anyE?.message || '加载失败，请检查后端地址或网络'
      }
      setErrorText(msg)
      setStatus('error')
    }
  }

  const loadTodo = async () => {
    try {
      const s = await api.plansSummary()
      setTodoCount(s.open_actions)
    } catch {
      // 红点计数失败不打扰主看板，下次 onShow 再试
      setTodoCount(null)
    }
  }

  useEffect(() => {
    void load()
    void loadTodo()
  }, [])

  // 从监督待办/详情页返回时刷新红点（待办可能已在别处处理）
  useDidShow(() => {
    void loadTodo()
  })

  const indexCards: Card[] = (data?.cards || []).filter((c) => c.group === 'index')
  const watchCards: Card[] = (data?.cards || []).filter((c) => c.group === 'watchlist')

  const goSettings = () => Taro.navigateTo({ url: '/pages/settings/index' })
  const goPlans = () => Taro.navigateTo({ url: '/pages/plans/index' })

  return (
    <View className="page">
      <View className="row between" style={{ marginBottom: 10 }}>
        <View className="tiny muted">点击卡片查看标的详情</View>
        <View className="row">
          <View className="btn btn-ghost tiny" style={{ padding: '8px 18px', marginRight: 8, position: 'relative' }} onClick={goPlans}>
            📋 监督待办
            {todoCount != null && todoCount > 0 && (
              <View
                style={{
                  position: 'absolute',
                  top: -5,
                  right: -5,
                  minWidth: 16,
                  height: 16,
                  borderRadius: 8,
                  background: '#e33d47',
                  color: '#ffffff',
                  fontSize: 10,
                  lineHeight: '16px',
                  textAlign: 'center',
                  padding: '0 4px',
                }}
              >
                {todoCount > 99 ? '99+' : todoCount}
              </View>
            )}
          </View>
          <View className="btn btn-ghost tiny" style={{ padding: '8px 18px' }} onClick={goSettings}>
            ⚙ 设置地址
          </View>
        </View>
      </View>

      {/* 市场宽度条（自加载，失败不影响卡片） */}
      <MarketBreadthStrip />

      {/* 今日机会雷达（读库快照，可重扫） */}
      <OpportunityPanel />

      <LoadingState
        status={status}
        emptyText="自选看板暂无卡片"
        errorText={errorText}
        onRetry={load}
      >
        {data && (
          <>
            {indexCards.length > 0 && (
              <>
                <SectionTitle>大盘指数</SectionTitle>
                {indexCards.map((c) => (
                  <CardItem key={c.symbol} card={c} />
                ))}
              </>
            )}
            {watchCards.length > 0 && (
              <>
                <SectionTitle>自选</SectionTitle>
                {watchCards.map((c) => (
                  <CardItem key={c.symbol} card={c} />
                ))}
              </>
            )}
            {data.disclaimer_cn && (
              <View className="tiny muted" style={{ marginTop: 16 }}>
                {data.disclaimer_cn}
              </View>
            )}
          </>
        )}
      </LoadingState>
    </View>
  )
}
