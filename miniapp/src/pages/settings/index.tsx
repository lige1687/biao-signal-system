import { useEffect, useState } from 'react'
import { View, Input } from '@tarojs/components'
import Taro from '@tarojs/taro'
import {
  getBaseUrlSync,
  setBaseUrl,
  BASE_URL_PRESETS,
} from '../../store/settings'

export default function SettingsPage() {
  const [url, setUrl] = useState('')
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    setUrl(getBaseUrlSync())
  }, [])

  const save = async () => {
    const v = (url || '').trim()
    if (!v) {
      Taro.showToast({ title: '地址不能为空', icon: 'none' })
      return
    }
    await setBaseUrl(v)
    setSaved(true)
    Taro.showToast({ title: '已保存', icon: 'success' })
    setTimeout(() => setSaved(false), 1500)
  }

  return (
    <View className="page">
      <View className="tiny muted" style={{ marginBottom: 12 }}>
        后端地址存于本机 storage。体验版手机上常需切换地址，改完即生效，无需重编译。
      </View>

      <View className="card">
        <View className="tiny muted" style={{ marginBottom: 8 }}>BASE_URL（含 http/https，端口 8000）</View>
        <Input
          value={url}
          onInput={(e) => setUrl(e.detail.value)}
          placeholder="http://127.0.0.1:8000"
          style={{
            background: '#0f1115',
            border: '1px solid #2c3038',
            borderRadius: 10,
            padding: '16px 14px',
            color: '#e6e8eb',
            fontSize: 26,
          }}
        />
      </View>

      <View className="tiny muted" style={{ margin: '16px 0 8px' }}>快捷预设</View>
      {BASE_URL_PRESETS.map((p) => (
        <View
          key={p.key}
          className="card"
          onClick={() => setUrl(p.url)}
          style={{ borderColor: '#2c3038' }}
        >
          <View className="row between">
            <View style={{ fontWeight: 600, color: '#f2f4f7' }}>{p.label}</View>
            <View className="tiny muted">{p.url}</View>
          </View>
          {p.note && <View className="tiny muted" style={{ marginTop: 6 }}>{p.note}</View>}
        </View>
      ))}

      <View
        className="btn"
        style={{ marginTop: 24 }}
        onClick={save}
      >
        保存
      </View>

      <View className="tiny muted" style={{ marginTop: 18, whiteSpace: 'pre-wrap' }}>
        说明：后端 launchd 监听 127.0.0.1，故「开发者工具」能直连本机；手机真机若用局域网 IP 需先把
        start_backend.sh 的 host 改为 0.0.0.0（由你决定，本小程序不改后端）。最稳的真机方式是用
        scripts/start_feishu_tunnel.sh 起的 Cloudflare 隧道域名（https）。
        {'\n'}体验版需在微信开发者工具「详情 → 本地设置」勾选「不校验合法域名」。
      </View>
    </View>
  )
}
