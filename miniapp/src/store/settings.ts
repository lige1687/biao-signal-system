import Taro from '@tarojs/taro'

export const BASE_URL_KEY = 'lei_base_url'
export const DEFAULT_BASE_URL = 'http://127.0.0.1:8000'

export interface UrlPreset {
  key: string
  label: string
  url: string
  note?: string
}

// 三种常用地址；用户也可直接输入自定义（如 Mac 局域网 IP、cloudflare 隧道域名）。
// 注意：后端 launchd 监听 127.0.0.1，故「局域网 IP」需后端 host 改为 0.0.0.0 才能被手机访问；
// 手机真机最稳的是 cloudflare 隧道（见 README）。
export const BASE_URL_PRESETS: UrlPreset[] = [
  {
    key: 'local',
    label: '开发者工具（本机）',
    url: 'http://127.0.0.1:8000',
    note: '微信开发者工具 / 模拟器里运行，或手机扫码但同本机',
  },
  {
    key: 'lan',
    label: 'Mac 局域网 IP',
    url: 'http://192.168.1.x:8000',
    note: '需把 start_backend.sh 的 host 改为 0.0.0.0（由你决定，本小程序不改后端）',
  },
  {
    key: 'tunnel',
    label: 'Cloudflare 隧道',
    url: 'https://xxxx.trycloudflare.com',
    note: '运行 scripts/start_feishu_tunnel.sh 获得临时域名（每次重启会变）',
  },
]

let cache: string | null = null

export function getBaseUrlSync(): string {
  if (cache !== null) return cache || DEFAULT_BASE_URL
  try {
    const v = Taro.getStorageSync(BASE_URL_KEY)
    cache = v || ''
  } catch {
    cache = ''
  }
  return cache || DEFAULT_BASE_URL
}

export async function getBaseUrl(): Promise<string> {
  try {
    const res = await Taro.getStorage({ key: BASE_URL_KEY })
    cache = (res.data as string) || ''
  } catch {
    cache = ''
  }
  return cache || DEFAULT_BASE_URL
}

export async function setBaseUrl(url: string): Promise<void> {
  const trimmed = (url || '').trim()
  cache = trimmed
  try {
    await Taro.setStorage({ key: BASE_URL_KEY, data: trimmed })
  } catch {
    /* ignore */
  }
}
