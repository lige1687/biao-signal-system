import { View } from '@tarojs/components'

export type Tone = 'default' | 'red' | 'green' | 'gray' | 'warn' | 'rp' | 'intraday'

const toneClass: Record<Tone, string> = {
  default: 'badge',
  red: 'badge badge-red',
  green: 'badge badge-green',
  gray: 'badge badge-gray',
  warn: 'badge badge-warn',
  rp: 'badge badge-rp',
  intraday: 'badge badge-intraday',
}

export default function Tag({
  text,
  tone = 'default',
  style,
}: {
  text: string | null | undefined
  tone?: Tone
  style?: Record<string, string | number>
}) {
  if (!text) return null
  return (
    <View className={toneClass[tone]} style={style}>
      {text}
    </View>
  )
}
