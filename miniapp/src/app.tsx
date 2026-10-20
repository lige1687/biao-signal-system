import { PropsWithChildren } from 'react'
import { useLaunch } from '@tarojs/taro'

import './app.scss'

function App({ children }: PropsWithChildren) {
  useLaunch(() => {
    // 小程序只读看板：无登录、无支付、无订阅消息。仅做必要初始化。
  })

  return children
}

export default App
