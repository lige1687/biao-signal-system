import { useEffect, useState } from 'react'
import { View } from '@tarojs/components'
import Taro from '@tarojs/taro'
import { api, ApiError } from '../../api/client'
import type { Plan, PlansSummary, PlanAlert, ActionItem } from '../../types'
import LoadingState, { type LoadStatus } from '../../components/LoadingState'
import Tag from '../../components/Tag'
import { fmtDate, fmtPrice } from '../../utils/format'

// 监督待办（只读）：活跃计划（armed 待入场 + entered 持仓中）+ 当日提醒 + 未处理待办。
// 提醒/待办的判定全部在后端（evaluate_plan / action items），这里只展示。
// 写操作（已执行/推迟/确认）请到 web 端完成。

interface PlanExtras {
  alerts: PlanAlert[]
  alertError: string | null
  actions: ActionItem[]
}

const SEVERITY_ORDER: Record<string, number> = { block: 0, remind: 1, hint: 2 }

function kindCn(kind: string): string {
  switch (kind) {
    case 'entry':
      return '入场计划'
    case 'holding_watch':
      return '持仓盯盘'
    default:
      return kind
  }
}

function stateTone(state: string): 'green' | 'warn' | 'gray' {
  if (state === 'entered') return 'green'
  if (state === 'armed') return 'warn'
  return 'gray'
}

function dirCn(d: string): string {
  return d === 'long' ? '做多' : d === 'short' ? '做空' : d
}

function actionKindCn(k: string): string {
  switch (k) {
    case 'ENTER':
      return '入场'
    case 'EXIT':
      return '退出'
    case 'REVIEW':
      return '复盘'
    default:
      return k
  }
}

function LabelValue({ label, value }: { label: string; value: string }) {
  if (!value || value === '--') return null
  return (
    <View className="tiny dim" style={{ marginTop: 4 }}>
      {label}：{value}
    </View>
  )
}

function PlanCard({ plan, extras }: { plan: Plan; extras?: PlanExtras }) {
  const goDetail = () =>
    Taro.navigateTo({ url: `/pages/detail/index?symbol=${encodeURIComponent(plan.symbol)}` })

  const alerts = [...(extras?.alerts || [])].sort(
    (a, b) => (SEVERITY_ORDER[a.severity] ?? 9) - (SEVERITY_ORDER[b.severity] ?? 9),
  )
  const isEntry = plan.plan_kind !== 'holding_watch'

  return (
    <View className="card" style={{ marginTop: 10 }}>
      {/* 头部 */}
      <View className="row between">
        <View onClick={goDetail} style={{ flex: 1, marginRight: 12 }}>
          <View style={{ fontWeight: 600, color: '#f2f4f7' }}>
            {plan.symbol}
            <View className="tiny muted" style={{ display: 'inline', marginLeft: 8 }}>
              点击看详情 ›
            </View>
          </View>
          <View className="tiny muted">
            {kindCn(plan.plan_kind)} · 模块{plan.module} · {dirCn(plan.direction)}
          </View>
        </View>
        <Tag text={plan.state === 'entered' ? '持仓中' : plan.state === 'armed' ? '待入场' : plan.state} tone={stateTone(plan.state)} />
      </View>

      {/* 关键日期 */}
      <View className="tiny muted" style={{ marginTop: 6 }}>
        有效期至 {fmtDate(plan.valid_until)}
        {plan.entered_on ? ` · 入场 ${fmtDate(plan.entered_on)}` : ''}
        {plan.exited_on ? ` · 退出 ${fmtDate(plan.exited_on)}` : ''}
        {` · 建于 ${fmtDate(plan.created_at)}`}
      </View>

      {/* 关键价位 */}
      {isEntry ? (
        <View className="row wrap" style={{ marginTop: 8 }}>
          {plan.entry_price_ref != null && <Tag text={`入场参考 ${fmtPrice(plan.entry_price_ref)}`} tone="gray" />}
          {plan.invalidation_price != null && <Tag text={`失效价 ${fmtPrice(plan.invalidation_price)}`} tone="red" />}
          {plan.target_b_price != null && <Tag text={`目标B ${fmtPrice(plan.target_b_price)}`} tone="green" />}
          {plan.reward_risk_at_plan != null && <Tag text={`R/R ${plan.reward_risk_at_plan.toFixed(2)}`} tone="warn" />}
        </View>
      ) : (
        <View className="row wrap" style={{ marginTop: 8 }}>
          {plan.take_profit_price != null && <Tag text={`止盈价 ${fmtPrice(plan.take_profit_price)}`} tone="green" />}
          {plan.stop_price != null && <Tag text={`止损价 ${fmtPrice(plan.stop_price)}`} tone="red" />}
          {plan.watch_signal_rule_ids?.length > 0 && (
            <Tag text={`盯盘信号 ${plan.watch_signal_rule_ids.length} 项`} tone="gray" />
          )}
        </View>
      )}
      {isEntry && plan.entry_trigger_cn && (
        <LabelValue label="入场触发" value={plan.entry_trigger_cn} />
      )}

      {/* 五项预案文本 */}
      <LabelValue label="交易假设" value={plan.thesis_cn} />
      <LabelValue label="失效标准" value={plan.invalidation_criteria_cn} />
      <LabelValue label="回撤预案" value={plan.drawdown_playbook_cn} />
      <LabelValue label="止盈预案" value={plan.take_profit_plan_cn} />
      <LabelValue label="止损预案" value={plan.stop_plan_cn} />

      {/* 当日提醒 */}
      {extras && (alerts.length > 0 || extras.alertError) && (
        <View style={{ marginTop: 10, borderTop: '1px solid #2a2e37', paddingTop: 8 }}>
          <View className="tiny muted" style={{ marginBottom: 4 }}>当日提醒</View>
          {extras.alertError && (
            <View className="tiny" style={{ color: '#ff8a93' }}>
              提醒获取失败：{extras.alertError}
            </View>
          )}
          {alerts.map((a, i) => (
            <View key={i} style={{ marginTop: 6 }}>
              <View className="row" style={{ alignItems: 'flex-start' }}>
                <View
                  style={{
                    flexShrink: 0,
                    width: 6,
                    height: 6,
                    borderRadius: 3,
                    marginTop: 6,
                    marginRight: 8,
                    background:
                      a.severity === 'block' ? '#ef4650' : a.severity === 'remind' ? '#f0cf6b' : '#8a8f98',
                  }}
                />
                <View style={{ flex: 1 }}>
                  <View className="tiny" style={{ color: '#dfe5ee' }}>
                    {a.next_step_cn || a.code}
                    {a.logic_provenance?.includes('research_proxy') && (
                      <View style={{ display: 'inline', marginLeft: 6 }}>
                        <Tag text="研究代理" tone="rp" />
                      </View>
                    )}
                  </View>
                  {a.caveat_cn && (
                    <View className="tiny muted" style={{ marginTop: 2 }}>{a.caveat_cn}</View>
                  )}
                </View>
              </View>
            </View>
          ))}
        </View>
      )}

      {/* 未处理待办（只读） */}
      {extras && extras.actions.length > 0 && (
        <View style={{ marginTop: 8 }}>
          <View className="tiny muted" style={{ marginBottom: 4 }}>未处理待办</View>
          {extras.actions.map((act) => (
            <View key={act.action_id} className="row between" style={{ marginTop: 4 }}>
              <View className="tiny dim">
                [{actionKindCn(act.kind)}] {act.source_alert_code}
              </View>
              <View className="tiny muted">
                {act.due_from ? `应办 ${fmtDate(act.due_from)}` : ''}
                {act.nag_count > 0 ? ` · 催办 ${act.nag_count} 次` : ''}
              </View>
            </View>
          ))}
        </View>
      )}
    </View>
  )
}

export default function PlansPage() {
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [errorText, setErrorText] = useState('')
  const [summary, setSummary] = useState<PlansSummary | null>(null)
  const [plans, setPlans] = useState<Plan[]>([])
  const [extras, setExtras] = useState<Record<string, PlanExtras>>({})
  const [refreshing, setRefreshing] = useState(false)

  const load = async () => {
    setStatus(plans.length > 0 ? 'ok' : 'loading')
    try {
      const [all, sum] = await Promise.all([
        api.plans(),
        api.plansSummary().catch(() => null),
      ])
      const active = all
        .filter((p) => p.state === 'armed' || p.state === 'entered')
        .sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''))
      setPlans(active)
      setSummary(sum)
      setErrorText('')
      setStatus(active.length > 0 ? 'ok' : 'empty')

      // 逐计划取提醒 + 未处理待办；提醒依赖分析服务，失败降级为卡内提示
      const entries = await Promise.all(
        active.map(async (p): Promise<[string, PlanExtras]> => {
          const [alertsRes, actionsRes] = await Promise.all([
            api.planAlerts(p.plan_id).then(
              (r): PlanExtras => ({ alerts: r, alertError: null, actions: [] }),
              (e): PlanExtras => ({
                alerts: [],
                alertError: e instanceof ApiError ? e.message : String(e),
                actions: [],
              }),
            ),
            api.planActions(p.plan_id, 'open').catch(() => [] as ActionItem[]),
          ])
          return [p.plan_id, { alerts: alertsRes.alerts, alertError: alertsRes.alertError, actions: actionsRes }]
        }),
      )
      setExtras(Object.fromEntries(entries))
    } catch (e) {
      setErrorText(e instanceof ApiError ? e.message : String(e))
      setStatus('error')
    }
  }

  useEffect(() => {
    void load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const openActions = summary?.open_actions ?? Object.values(extras).reduce((s, x) => s + x.actions.length, 0)

  return (
    <View className="page">
      <View className="row between" style={{ marginBottom: 10 }}>
        <View className="tiny muted">
          待办 {openActions} · 活跃计划 {summary?.active_plans ?? plans.length}
        </View>
        <View
          className="btn btn-ghost tiny"
          style={{ padding: '6px 16px' }}
          onClick={async () => {
            if (refreshing) return
            setRefreshing(true)
            await load()
            setRefreshing(false)
          }}
        >
          {refreshing ? '刷新中…' : '刷新'}
        </View>
      </View>

      <LoadingState status={status} emptyText="暂无活跃计划（armed / entered）" errorText={errorText} onRetry={load}>
        {plans.map((p) => (
          <PlanCard key={p.plan_id} plan={p} extras={extras[p.plan_id]} />
        ))}
        <View className="tiny muted" style={{ marginTop: 14 }}>
          只读视图：待办已执行 / 推迟、计划确认与编辑请到 web 端完成。提醒与待办判定均在后端，前端不计算。
        </View>
      </LoadingState>
    </View>
  )
}
