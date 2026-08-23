import { useEffect, useState } from 'react'
import { View, Switch } from '@tarojs/components'
import Taro, { useRouter } from '@tarojs/taro'
import { api, ApiError } from '../../api/client'
import type {
  SymbolDetail,
  Metric,
  Factor,
  RiskAlert,
  TradeOpportunity,
  PullbackOpportunity,
  ConditionalScenario,
  ExitSignal,
  Tradability,
  StructureBrief,
  EventItem,
} from '../../types'
import LoadingState, { type LoadStatus } from '../../components/LoadingState'
import SectionTitle from '../../components/SectionTitle'
import Tag from '../../components/Tag'
import KLineView from '../../components/KLineView'
import { fmtPrice, fmtNum, fmtDate, fmtDateTime, leiColorCn, leiColorClass, isDataUnavailable } from '../../utils/format'

function metricClass(tone?: string): string {
  switch (tone) {
    case 'up':
      return 'up'
    case 'down':
      return 'down'
    case 'warn':
      return 'flat'
    default:
      return 'dim'
  }
}

function MetricGrid({ title, metrics }: { title: string; metrics: Metric[] | undefined }) {
  if (!metrics || metrics.length === 0) return null
  return (
    <View style={{ marginTop: 10 }}>
      <View className="tiny muted" style={{ marginBottom: 6 }}>{title}</View>
      <View className="row wrap">
        {metrics.map((m, i) => (
          <View
            key={m.key || i}
            style={{
              width: '48%',
              background: '#1d2026',
              borderRadius: 10,
              padding: '10px 12px',
              marginBottom: 8,
              marginRight: '4%',
            }}
          >
            <View className="tiny muted">{m.label_cn}</View>
            <View className={metricClass(m.tone)} style={{ fontSize: 28, fontWeight: 600 }}>
              {m.text ?? (m.value != null ? `${fmtNum(m.value)}${m.unit || ''}` : '--')}
            </View>
            {m.hint_cn && <View className="tiny muted">{m.hint_cn}</View>}
          </View>
        ))}
      </View>
    </View>
  )
}

function CondList({ items, label, tone }: { items: string[] | undefined; label: string; tone: 'green' | 'gray' }) {
  if (!items || items.length === 0) return null
  return (
    <View style={{ marginTop: 6 }}>
      <View className="tiny muted">{label}：</View>
      <View className="row wrap" style={{ marginTop: 4 }}>
        {items.map((s, i) => (
          <Tag key={i} text={s} tone={tone} />
        ))}
      </View>
    </View>
  )
}

function StructureCard({ s }: { s: StructureBrief }) {
  return (
    <View className="card" style={{ marginTop: 10 }}>
      <View className="row between">
        <View style={{ fontWeight: 600, color: '#f2f4f7' }}>{s.structure_type_cn}</View>
        <Tag text={s.status_cn} tone={s.status === 'confirmed' ? 'green' : 'gray'} />
      </View>
      <View className="tiny muted" style={{ marginTop: 4 }}>
        {s.side === 'bottom' ? '底部' : '顶部'} · 检测 {fmtDate(s.detected_date)}
        {s.confirmed_date ? ` · 确认 ${fmtDate(s.confirmed_date)}` : ''}
      </View>
      {s.c_price != null && (
        <View className="tiny dim" style={{ marginTop: 4 }}>C点 {fmtPrice(s.c_price)}{s.neckline != null ? ` · 颈线 ${fmtPrice(s.neckline)}` : ''}</View>
      )}
      {s.distance_to_c_pct != null && (
        <View className="tiny" style={{ marginTop: 2, color: '#f0cf6b' }}>距 C 点 {s.distance_to_c_pct.toFixed(2)}%</View>
      )}
    </View>
  )
}

function TradeOppCard({ o }: { o: TradeOpportunity }) {
  return (
    <View className="card" style={{ marginTop: 10 }}>
      <View className="row between">
        <View style={{ flex: 1, fontWeight: 600, color: '#f2f4f7' }}>
          {o.structure?.structure_type_cn || '机会'}
        </View>
        <View className="row">
          <Tag text={o.state_cn} tone={o.state === 'confirmed' ? 'green' : 'warn'} />
        </View>
      </View>
      <View className="tiny muted" style={{ marginTop: 4 }}>
        {o.direction_cn} · 档位 {o.reached_tier_cn}
        {o.is_buy_reference ? ' · 买点参考' : ''}
      </View>
      <CondList items={o.satisfied_conditions} label="已满足条件" tone="green" />
      <CondList items={o.missing_conditions} label="还缺条件" tone="gray" />
      {o.next_step_cn && <View className="tiny dim" style={{ marginTop: 6 }}>下一步：{o.next_step_cn}</View>}
      {o.invalidation_cn && <View className="tiny" style={{ marginTop: 2, color: '#ff8a93' }}>失效位：{o.invalidation_cn}</View>}
      {o.b1_price != null && (
        <View className="tiny muted" style={{ marginTop: 2 }}>B1 {fmtPrice(o.b1_price)}{o.distance_to_b1_pct != null ? `（距 ${o.distance_to_b1_pct.toFixed(2)}%）` : ''}</View>
      )}
    </View>
  )
}

function CondScenarioCard({ s }: { s: ConditionalScenario }) {
  return (
    <View className="card" style={{ marginTop: 10 }}>
      <View className="row between">
        <View style={{ flex: 1, fontWeight: 600, color: '#f2f4f7' }}>{s.scenario_cn}</View>
        <View className="row">
          {s.research_proxy && <Tag text="研究代理" tone="rp" />}
          <Tag text={s.state_cn} tone={s.state === 'confirmed' ? 'green' : 'warn'} />
        </View>
      </View>
      <View className="tiny muted" style={{ marginTop: 4 }}>
        {s.direction_cn} · 锚定 {fmtDate(s.anchor_date)}
        {s.key_price != null ? ` · 关键价 ${fmtPrice(s.key_price)}` : ''}
        {s.distance_pct != null ? ` · 距 ${s.distance_pct.toFixed(2)}%` : ''}
      </View>
      <CondList items={s.satisfied_conditions} label="已满足条件" tone="green" />
      <CondList items={s.missing_conditions} label="还缺条件" tone="gray" />
      {s.next_step_cn && <View className="tiny dim" style={{ marginTop: 6 }}>下一步：{s.next_step_cn}</View>}
      {s.invalidation_cn && <View className="tiny" style={{ marginTop: 2, color: '#ff8a93' }}>失效位：{s.invalidation_cn}</View>}
      {s.reward_risk_computable && s.reward_risk_ratio != null && (
        <View className="tiny muted" style={{ marginTop: 2 }}>盈亏比 {s.reward_risk_ratio.toFixed(2)}（研究代理，只算不强制）</View>
      )}
    </View>
  )
}

function PullbackCard({ p }: { p: PullbackOpportunity }) {
  return (
    <View className="card" style={{ marginTop: 10 }}>
      <View className="row between">
        <View style={{ flex: 1, fontWeight: 600, color: '#f2f4f7' }}>
          模块B · {p.ma_name}
        </View>
        <View className="row">
          {p.research_proxy && <Tag text="研究代理" tone="rp" />}
          <Tag text={p.state_cn} tone={p.state === 'confirmed' ? 'green' : 'warn'} />
        </View>
      </View>
      <View className="tiny muted" style={{ marginTop: 4 }}>
        MA{p.ma_period} = {fmtPrice(p.ma_value)} · 收盘 {fmtPrice(p.close)}
        {p.distance_to_ma_pct != null ? ` · 距 ${p.distance_to_ma_pct.toFixed(2)}%` : ''}
      </View>
      <CondList items={p.satisfied_conditions} label="已满足条件" tone="green" />
      <CondList items={p.missing_conditions} label="还缺条件" tone="gray" />
      {p.next_step_cn && <View className="tiny dim" style={{ marginTop: 6 }}>下一步：{p.next_step_cn}</View>}
      {p.invalidation_cn && <View className="tiny" style={{ marginTop: 2, color: '#ff8a93' }}>失效位：{p.invalidation_cn}</View>}
    </View>
  )
}

function ExitCard({ e }: { e: ExitSignal }) {
  return (
    <View className="card" style={{ marginTop: 10, borderColor: '#3a2630' }}>
      <View className="row between">
        <View style={{ flex: 1, fontWeight: 600, color: '#f2f4f7' }}>{e.rule_cn}</View>
        <View className="row">
          {e.research_proxy && <Tag text="研究代理" tone="rp" />}
          <Tag text={e.state_cn} tone={e.state === 'active' ? 'red' : 'gray'} />
        </View>
      </View>
      <View className="tiny muted" style={{ marginTop: 4 }}>{e.direction_cn}{e.sub_rule_cn ? ` · ${e.sub_rule_cn}` : ''}</View>
      <View className="tiny dim" style={{ marginTop: 4 }}>{e.reason_cn}</View>
      {e.invalidation_cn && <View className="tiny" style={{ marginTop: 2, color: '#ff8a93' }}>失效位：{e.invalidation_cn}</View>}
    </View>
  )
}

function FactorListView({ title, factors, tone }: { title: string; factors: Factor[] | undefined; tone: 'green' | 'gray' }) {
  if (!factors || factors.length === 0) return null
  return (
    <View style={{ marginTop: 8 }}>
      <View className="tiny" style={{ color: tone === 'green' ? '#4fd6a0' : '#aeb6c2' }}>{title}</View>
      {factors.map((f, i) => (
        <View key={i} className="tiny dim" style={{ marginTop: 4 }}>· {f.label_cn}：{f.detail_cn}</View>
      ))}
    </View>
  )
}

function RiskListView({ risks }: { risks: RiskAlert[] | undefined }) {
  if (!risks || risks.length === 0) return null
  return (
    <View style={{ marginTop: 8 }}>
      {risks.map((r, i) => (
        <View key={i} className="tiny" style={{ color: '#ff8a93', marginTop: 4 }}>
          · {r.label_cn}：{r.detail_cn}
        </View>
      ))}
    </View>
  )
}

export default function DetailPage() {
  const router = useRouter()
  const symbol = router.params.symbol || ''
  const [data, setData] = useState<SymbolDetail | null>(null)
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [errorText, setErrorText] = useState<string>('')
  const [leiMode, setLeiMode] = useState(false)

  const load = async () => {
    if (!symbol) {
      setErrorText('缺少 symbol 参数')
      setStatus('error')
      return
    }
    try {
      const d = await api.symbolDetail(symbol)
      setData(d)
      setStatus('ok')
      setErrorText('')
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : String(e)
      setErrorText(msg)
      setStatus('error')
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const a = data?.assessment
  const meta = data?.meta
  const dataUnavailable = isDataUnavailable(errorText) || (meta?.data_warnings && meta.data_warnings.length > 0)

  return (
    <View className="page">
      <LoadingState status={status} emptyText="暂无数据" errorText={errorText} onRetry={load}>
        {data && (
          <>
            {/* 头部 */}
            <View className="card">
              <View style={{ fontSize: 34, fontWeight: 700, color: '#f2f4f7' }}>
                {data.display_name || data.symbol}
              </View>
              <View className="tiny muted" style={{ marginTop: 2 }}>
                {data.symbol} · {data.market_cn}
              </View>
              <View className="row wrap" style={{ marginTop: 12 }}>
                {a?.color_cn && <Tag text={leiColorCn(a.color)} tone={a.color === 'green' ? 'green' : a.color === 'black' ? 'default' : 'gray'} style={a.color === 'black' ? { background: '#1f2937', color: '#d7dbe0', borderColor: '#1f2937' } : undefined} />}
                {a?.stage_cn && <Tag text={a.stage_cn} tone="gray" />}
                {a?.risk_state_cn && <Tag text={a.risk_state_cn} tone="red" />}
                {a?.opportunity_stage_cn && <Tag text={a.opportunity_stage_cn} tone="green" />}
              </View>
              {(data.chart?.lastClose != null || meta?.last_bar_date) && (
                <View className="tiny muted" style={{ marginTop: 10 }}>
                  最新 {data.chart?.lastClose != null ? fmtPrice(data.chart.lastClose) : '--'}
                  {meta?.last_bar_date ? ` · 末根 ${fmtDate(meta.last_bar_date)}` : ''}
                  {meta?.data_time ? ` · 数据 ${fmtDateTime(meta.data_time)}` : ''}
                </View>
              )}
            </View>

            {/* DATA_UNAVAILABLE 显式展示，不静默 */}
            {dataUnavailable && (
              <View className="card" style={{ borderColor: '#6b5a1f', background: '#2a2410' }}>
                <Tag text="DATA_UNAVAILABLE" tone="warn" />
                <View className="tiny" style={{ color: '#f0cf6b', marginTop: 6 }}>
                  {errorText && isDataUnavailable(errorText) ? errorText : (meta?.data_warnings || []).join('；') || '该标的分析失败，数据不可用'}
                </View>
              </View>
            )}

            {/* K 线 + 三色切换 */}
            <SectionTitle>K 线</SectionTitle>
            <View className="card">
              <View className="row between" style={{ marginBottom: 8 }}>
                <View className="tiny muted">红涨绿跌（默认） / LEI 三色</View>
                <View className="row">
                  <View className="tiny dim" style={{ marginRight: 10 }}>{leiMode ? 'LEI 三色' : '红涨绿跌'}</View>
                  <Switch checked={leiMode} onChange={(e) => setLeiMode(e.detail.value)} color="#e33d47" />
                </View>
              </View>
              <KLineView chart={data.chart} leiMode={leiMode} />
            </View>

            {/* 三色判断依据 */}
            <SectionTitle>三色状态与判断依据</SectionTitle>
            <View className="card">
              {a?.stage_change_reason_cn && (
                <View className="tiny dim" style={{ marginBottom: 8 }}>{a.stage_change_reason_cn}</View>
              )}
              {a?.dimensions && Object.keys(a.dimensions).length > 0 && (
                <View className="row wrap">
                  {Object.entries(a.dimensions).map(([k, v]) => (
                    <Tag key={k} text={`${k}: ${v}`} tone="gray" />
                  ))}
                </View>
              )}
              <FactorListView title="支持维度" factors={a?.supports} tone="green" />
              <FactorListView title="冲突维度" factors={a?.conflicts} tone="gray" />
              <RiskListView risks={a?.risks} />
            </View>

            {/* 指标 */}
            {data.today && (
              <>
                <SectionTitle>指标</SectionTitle>
                <View className="card">
                  <MetricGrid title="价格" metrics={data.today.price} />
                  <MetricGrid title="技术" metrics={data.today.technical} />
                  <MetricGrid title="量能" metrics={data.today.volume} />
                  <MetricGrid title="资金" metrics={data.today.capital} />
                  <MetricGrid title="信号" metrics={data.today.signal} />
                </View>
              </>
            )}

            {/* 结构 / B1 */}
            {(data.live_structures?.length || data.chart?.b1Line) && (
              <>
                <SectionTitle>结构 / B1</SectionTitle>
                {(() => {
                  const b1 = data.chart?.b1Line
                  if (!b1) return null
                  return (
                    <View className="card" style={{ marginTop: 10 }}>
                      <View className="row between">
                        <View style={{ fontWeight: 600, color: '#f2f4f7' }}>{b1.label_cn || 'B1 第一阻力'}</View>
                        <Tag text={fmtPrice(b1.yAxis)} tone="warn" />
                      </View>
                      {b1.distance_pct != null && (
                        <View className="tiny muted" style={{ marginTop: 4 }}>距离 {b1.distance_pct.toFixed(2)}%</View>
                      )}
                    </View>
                  )
                })()}
                {data.live_structures?.map((s) => (
                  <StructureCard key={s.structure_id} s={s} />
                ))}
              </>
            )}

            {/* 机会与风险 */}
            {(a?.trade_opportunities?.length || a?.conditional_scenarios?.length || a?.pullback_opportunities?.length || a?.exit_signals?.length) && (
              <>
                <SectionTitle>机会与风险</SectionTitle>
                {a?.trade_opportunities?.map((o, i) => (
                  <TradeOppCard key={`t${i}`} o={o} />
                ))}
                {a?.conditional_scenarios?.map((s, i) => (
                  <CondScenarioCard key={`c${i}`} s={s} />
                ))}
                {a?.pullback_opportunities?.map((p, i) => (
                  <PullbackCard key={`p${i}`} p={p} />
                ))}
                {a?.exit_signals?.map((e, i) => (
                  <ExitCard key={`e${i}`} e={e} />
                ))}
              </>
            )}

            {/* 可交易性门禁 */}
            {a?.tradability && (
              <>
                <SectionTitle>可交易性门禁（研究代理）</SectionTitle>
                <View className="card">
                  <View className="row between">
                    <View className="tiny dim">趋势类型：{a.tradability.trend_type_cn || '--'}</View>
                    <Tag text={a.tradability.tradable ? '可交易' : '受限'} tone={a.tradability.tradable ? 'green' : 'red'} />
                  </View>
                  {a.tradability.blocking_reasons?.length > 0 && (
                    <View className="tiny" style={{ color: '#ff8a93', marginTop: 6 }}>
                      阻断：{a.tradability.blocking_reasons.join('；')}
                    </View>
                  )}
                  {a.tradability.caveat_cn && (
                    <View className="tiny muted" style={{ marginTop: 4 }}>{a.tradability.caveat_cn}</View>
                  )}
                </View>
              </>
            )}

            {/* 市场环境徽标 */}
            {data.market_badge && (
              <>
                <SectionTitle>市场环境</SectionTitle>
                <View className="card">
                  <View className="tiny dim">{data.market_badge.summary_cn}</View>
                  {data.market_badge.reasons_cn?.map((r, i) => (
                    <View key={i} className="tiny muted" style={{ marginTop: 4 }}>· {r}</View>
                  ))}
                </View>
              </>
            )}

            {/* 今日新事件 */}
            {data.new_events?.length > 0 && (
              <>
                <SectionTitle>今日新事件</SectionTitle>
                {data.new_events.slice(0, 8).map((ev: EventItem) => (
                  <View key={ev.event_id} className="card" style={{ marginTop: 10 }}>
                    <View className="row between">
                      <View style={{ fontWeight: 600, color: '#f2f4f7' }}>{ev.rule_cn}</View>
                      <Tag text={ev.severity_cn} tone={ev.severity === 'important' ? 'red' : 'gray'} />
                    </View>
                    <View className="tiny dim" style={{ marginTop: 4 }}>{ev.reason_cn}</View>
                  </View>
                ))}
              </>
            )}

            {data.disclaimer_cn && (
              <View className="tiny muted" style={{ marginTop: 18 }}>
                {data.disclaimer_cn}
              </View>
            )}
          </>
        )}
      </LoadingState>
    </View>
  )
}
