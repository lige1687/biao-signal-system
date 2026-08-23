import { useEffect, useState } from 'react'
import { ScrollView, View } from '@tarojs/components'
import { api, ApiError } from '../../api/client'
import type { GlobalPanel, GlobalStripResponse, BreadthAlert } from '../../types'
import Tag from '../Tag'
import { fmtDateTime } from '../../utils/format'

// 顶部宽度条：横向市场面板 + 三个「阶段坑位」+ 点按展开详情。
// 口径与 web MarketBreadthStrip 一致（B50≥80 阶段顶 / ≤20 短期底，B50+B200 共振反转），
// 判定全部沿用后端 global-strip 数据，这里只做展示。

const HOT = 80
const COLD = 20

interface SlotState {
  active: boolean
  text: string
  color: string
}

function deriveStageSlots(panel: GlobalPanel): { base: SlotState; stage: SlotState; reversal: SlotState } {
  const b50 = panel.breadth_50
  const b20 = panel.breadth_20
  const b200 = panel.breadth_200
  // 中周期取 B50，缺失时回退 B20（与后端一致）
  const medium = b50 != null ? b50 : b20

  let base: SlotState
  if (b200 == null) base = { active: false, text: '无宽度', color: '#8a8f98' }
  else if (b200 > 50) base = { active: true, text: '🐂 牛市底色', color: '#ef4650' }
  else if (b200 < 50) base = { active: true, text: '🐻 熊市底色', color: '#12b375' }
  else base = { active: false, text: '中性', color: '#8a8f98' }

  let stage: SlotState
  if (medium == null) stage = { active: false, text: '—', color: '#8a8f98' }
  else if (medium >= HOT) stage = { active: true, text: '阶段性顶部', color: '#f0cf6b' }
  else if (medium <= COLD) stage = { active: true, text: '短期底部', color: '#12b375' }
  else stage = { active: false, text: '—', color: '#8a8f98' }

  let reversal: SlotState
  if (medium != null && b200 != null && medium >= HOT && b200 >= HOT)
    reversal = { active: true, text: '⚠️ 反转顶部', color: '#ef4650' }
  else if (medium != null && b200 != null && medium <= COLD && b200 <= COLD)
    reversal = { active: true, text: '⚠️ 反转底部', color: '#12b375' }
  else reversal = { active: false, text: '—', color: '#8a8f98' }

  return { base, stage, reversal }
}

function fmtPct1(v: number | null | undefined): string {
  return v == null ? '--' : `${v.toFixed(1)}%`
}

function fmtSigned(v: number | null | undefined): string {
  if (v == null) return ''
  return `${v > 0 ? '+' : ''}${v.toFixed(1)}`
}

function deltaColor(v: number | null | undefined): string {
  if (v == null || v === 0) return '#8a8f98'
  return v > 0 ? '#ef4650' : '#12b375'
}

function deltaArrow(v: number | null | undefined): string {
  if (v == null) return ''
  return v > 0 ? '↑' : v < 0 ? '↓' : '→'
}

function BreadthCell({
  label,
  value,
  delta,
  pctile,
}: {
  label: string
  value: number | null | undefined
  delta?: number | null
  pctile?: number | null
}) {
  return (
    <View style={{ flex: 1, minWidth: '31%', background: '#1d2026', borderRadius: 8, padding: '8px 10px', marginRight: '2%', marginBottom: 8 }}>
      <View className="tiny muted">
        {label}
        {pctile != null ? `（5年分位 ${pctile.toFixed(0)}）` : ''}
      </View>
      <View className="row" style={{ alignItems: 'baseline', marginTop: 2 }}>
        <View style={{ fontSize: 22, fontWeight: 600, color: '#f2f4f7' }}>{fmtPct1(value)}</View>
        {delta != null && (
          <View className="tiny" style={{ marginLeft: 8, color: deltaColor(delta) }}>
            {deltaArrow(delta)} {fmtSigned(delta)}
          </View>
        )}
      </View>
    </View>
  )
}

export default function MarketBreadthStrip() {
  const [data, setData] = useState<GlobalStripResponse | null>(null)
  const [errorText, setErrorText] = useState('')
  const [loading, setLoading] = useState(true)
  const [openId, setOpenId] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const d = await api.globalStrip()
      setData(d)
      setErrorText('')
    } catch (e) {
      setErrorText(e instanceof ApiError ? e.message : String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void load()
  }, [])

  if (loading && !data) {
    return (
      <View className="tiny muted" style={{ marginBottom: 10 }}>
        市场宽度加载中…
      </View>
    )
  }
  if (errorText && !data) {
    return (
      <View className="card tiny" style={{ borderColor: '#3a2630', marginBottom: 10, color: '#ff8a93' }}>
        市场宽度加载失败：{errorText}
        <View className="btn btn-ghost tiny" style={{ marginTop: 8, display: 'inline-block', padding: '6px 16px' }} onClick={() => void load()}>
          重试
        </View>
      </View>
    )
  }

  const panels = data?.panels || []
  if (panels.length === 0) return null
  const open = openId ? panels.find((p) => p.market_id === openId) : null
  const sentiment = data?.sentiment

  return (
    <View style={{ marginBottom: 12 }}>
      <ScrollView scrollX style={{ whiteSpace: 'nowrap' }}>
        <View className="row" style={{ display: 'inline-flex' }}>
          {panels.map((p) => {
            const slots = deriveStageSlots(p)
            const anyAlert = !!p.alerts && p.alerts.length > 0
            const reversal = !!p.alerts?.some((a: BreadthAlert) => a.level === 'reversal')
            return (
              <View
                key={p.market_id}
                onClick={() => setOpenId(openId === p.market_id ? null : p.market_id)}
                style={{
                  flexShrink: 0,
                  width: 152,
                  marginRight: 8,
                  borderRadius: 10,
                  padding: '8px 10px',
                  background: openId === p.market_id ? '#242830' : '#1d2026',
                  border: `1px solid ${reversal ? '#5a2a30' : anyAlert ? '#4a4630' : '#2a2e37'}`,
                }}
              >
                <View className="row between">
                  <View className="tiny" style={{ color: '#dfe5ee', fontWeight: 600 }}>
                    {p.display_name}
                  </View>
                  {anyAlert && <View className="tiny" style={{ color: '#f0cf6b' }}>⚠</View>}
                </View>
                <View className="row" style={{ marginTop: 4 }}>
                  {[slots.base, slots.stage, slots.reversal].map((s, i) => (
                    <View
                      key={i}
                      style={{
                        width: 8,
                        height: 8,
                        borderRadius: 4,
                        marginRight: 5,
                        background: s.active ? s.color : '#2a2e37',
                      }}
                    />
                  ))}
                  <View style={{ fontSize: 20, fontWeight: 600, color: '#f2f4f7', marginLeft: 'auto' }}>
                    {fmtPct1(p.breadth_20)}
                  </View>
                  <View className="tiny" style={{ marginLeft: 6, color: deltaColor(p.breadth_20_delta_5) }}>
                    {deltaArrow(p.breadth_20_delta_5)}
                  </View>
                </View>
              </View>
            )
          })}
        </View>
      </ScrollView>

      {open && (
        <View className="card" style={{ marginTop: 10 }}>
          <View className="row between">
            <View style={{ fontWeight: 600, color: '#f2f4f7' }}>{open.display_name}</View>
            {open.data_status && open.data_status !== 'ok' && <Tag text={open.data_status} tone="warn" />}
          </View>
          <View className="row wrap" style={{ marginTop: 6 }}>
            {[
              { t: '底色', s: deriveStageSlots(open).base },
              { t: '阶段', s: deriveStageSlots(open).stage },
              { t: '反转', s: deriveStageSlots(open).reversal },
            ].map(({ t, s }) => (
              <View
                key={t}
                className="tiny"
                style={{
                  marginRight: 8,
                  marginBottom: 4,
                  padding: '2px 8px',
                  borderRadius: 4,
                  background: s.active ? `${s.color}22` : '#1d2026',
                  color: s.active ? s.color : '#8a8f98',
                  border: `1px solid ${s.active ? `${s.color}55` : '#2a2e37'}`,
                }}
              >
                {t}：{s.text}
              </View>
            ))}
          </View>
          <View className="row wrap" style={{ marginTop: 8 }}>
            <BreadthCell label="B20" value={open.breadth_20} delta={open.breadth_20_delta_5} pctile={open.percentile_20} />
            <BreadthCell label="B50" value={open.breadth_50} delta={open.breadth_50_delta_5} pctile={open.percentile_50} />
            <BreadthCell label="B200" value={open.breadth_200} />
          </View>
          {open.is_real_a_share && open.total != null && (
            <View className="tiny dim" style={{ marginTop: 2 }}>
              全A 涨跌家数：涨 {open.up ?? '--'} / 跌 {open.down ?? '--'} / 平 {open.flat ?? '--'}（共 {open.total}）
              {open.limit_up != null ? ` · 涨停 ${open.limit_up}` : ''}
              {open.limit_down != null ? ` / 跌停 ${open.limit_down}` : ''}
              {open.adv_dec_ratio != null ? ` · 涨跌比 ${open.adv_dec_ratio.toFixed(2)}` : ''}
              {open.breadth_trading_day ? `（${open.breadth_trading_day} 收盘快照）` : ''}
            </View>
          )}
          {open.drawdown_from_ath != null && (
            <View className="tiny muted" style={{ marginTop: 4 }}>
              距历史高点回撤 {open.drawdown_from_ath.toFixed(1)}%
            </View>
          )}
          {open.alerts && open.alerts.length > 0 && (
            <View style={{ marginTop: 6 }}>
              {open.alerts.map((a, i) => (
                <View key={i} className="tiny" style={{ marginTop: 4, color: a.level === 'reversal' ? '#ef4650' : '#f0cf6b' }}>
                  ⚠ {a.title}：{a.desc}
                </View>
              ))}
            </View>
          )}
          {open.summary_cn && (
            <View className="tiny dim" style={{ marginTop: 6 }}>
              {open.summary_cn}
            </View>
          )}
          {open.updated_at && (
            <View className="tiny muted" style={{ marginTop: 4 }}>
              更新 {fmtDateTime(open.updated_at)}
            </View>
          )}

          {sentiment && (
            <View style={{ marginTop: 8, borderTop: '1px solid #2a2e37', paddingTop: 8 }}>
              <View className="tiny muted" style={{ marginBottom: 4 }}>
                投资者情绪{sentiment.root_set ? '' : '（未配置 LEI_SENTIMENT_ROOT）'}
              </View>
              <View className="row wrap">
                {sentiment.naaim && (
                  <Tag
                    text={`NAAIM ${sentiment.naaim.label_cn}${sentiment.naaim.survey_week ? ` · ${sentiment.naaim.survey_week}` : ''}`}
                    tone="gray"
                  />
                )}
                {sentiment.aaii && (
                  <Tag
                    text={`AAII ${sentiment.aaii.label_cn}${sentiment.aaii.survey_week ? ` · ${sentiment.aaii.survey_week}` : ''}`}
                    tone="gray"
                  />
                )}
              </View>
            </View>
          )}
        </View>
      )}
    </View>
  )
}
