import { View } from '@tarojs/components'
import type { ReactNode } from 'react'

export default function SectionTitle({ children }: { children: ReactNode }) {
  return <View className="section-title">{children}</View>
}
