import { View } from '@tarojs/components'
import type { ReactNode } from 'react'

export type LoadStatus = 'loading' | 'empty' | 'error' | 'ok'

export default function LoadingState({
  status,
  emptyText = '暂无数据',
  errorText,
  onRetry,
  children,
}: {
  status: LoadStatus
  emptyText?: string
  errorText?: string
  onRetry?: () => void
  children?: ReactNode
}) {
  if (status === 'loading') {
    return (
      <View className="card tiny muted" style={{ textAlign: 'center', padding: '40px 0' }}>
        加载中…
      </View>
    )
  }
  if (status === 'error') {
    return (
      <View className="card" style={{ borderColor: '#5a2530' }}>
        <View className="up" style={{ fontWeight: 600 }}>
          加载失败
        </View>
        <View className="tiny muted" style={{ marginTop: 8 }}>
          {errorText || '请检查 BASE_URL 与服务是否存活（开发者工具可访问 127.0.0.1:8000）'}
        </View>
        {onRetry && (
          <View className="btn btn-ghost" style={{ marginTop: 16 }} onClick={onRetry}>
            重试
          </View>
        )}
      </View>
    )
  }
  if (status === 'empty') {
    return (
      <View className="card tiny muted" style={{ textAlign: 'center', padding: '40px 0' }}>
        {emptyText}
      </View>
    )
  }
  return <>{children}</>
}
