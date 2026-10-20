// 通用格式化与小工具（仅展示，不做任何信号计算）。

export function fmtPct(v: number | null | undefined, digits = 2): string {
  if (v == null || Number.isNaN(v)) return '--'
  const s = v.toFixed(digits)
  return v > 0 ? `+${s}%` : `${s}%`
}

export function fmtNum(v: number | null | undefined, digits = 2): string {
  if (v == null || Number.isNaN(v)) return '--'
  return v.toFixed(digits)
}

export function fmtPrice(v: number | null | undefined): string {
  if (v == null || Number.isNaN(v)) return '--'
  return v.toFixed(2)
}

export function fmtDate(s: string | null | undefined): string {
  if (!s) return '--'
  return s.slice(0, 10)
}

export function fmtDateTime(s: string | null | undefined): string {
  if (!s) return '--'
  return s.replace('T', ' ').slice(0, 16)
}

// 涨跌 -> 红涨绿跌（A股惯例）
export function changeClass(v: number | null | undefined): 'up' | 'down' | 'flat' {
  if (v == null || Number.isNaN(v) || v === 0) return 'flat'
  return v > 0 ? 'up' : 'down'
}

// LEI 三色 -> 中文 + class
export function leiColorCn(c: string | null | undefined): string {
  switch (c) {
    case 'green':
      return '绿色'
    case 'gray':
      return '灰色'
    case 'black':
      return '黑色'
    default:
      return c || '--'
  }
}

export function leiColorClass(c: string | null | undefined): string {
  switch (c) {
    case 'green':
      return 'c-green'
    case 'gray':
      return 'c-gray'
    case 'black':
      return 'c-black'
    default:
      return 'muted'
  }
}

// verdict / state 中文 -> 徽标色调
export function toneFromText(t: string | null | undefined): 'red' | 'green' | 'gray' | 'warn' | 'default' {
  if (!t) return 'default'
  if (t.includes('行动') || t.includes('确认') || t.includes('已确认') || t.includes('有效')) return 'green'
  if (t.includes('阻断') || t.includes('风险') || t.includes('失效') || t.includes('弱势')) return 'red'
  if (t.includes('等待') || t.includes('观察') || t.includes('关注')) return 'warn'
  return 'gray'
}

export function isDataUnavailable(text: string | null | undefined): boolean {
  return !!text && (text.includes('DATA_UNAVAILABLE') || text.toUpperCase().includes('DATA UNAVAILABLE'))
}
