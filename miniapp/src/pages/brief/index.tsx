import { useEffect, useState } from 'react'
import { View } from '@tarojs/components'
import { api, ApiError } from '../../api/client'
import type { DailyBriefResponse, BriefAnomaly, BriefWatchItem, BriefPoolItem } from '../../types'
import LoadingState, { type LoadStatus } from '../../components/LoadingState'
import SectionTitle from '../../components/SectionTitle'
import Tag from '../../components/Tag'
import { fmtDate, fmtNum, toneFromText } from '../../utils/format'

function slotLabel(slot: string | undefined): { text: string; tone: 'intraday' | 'green' } {
  if (slot === '1445') return { text: '盘中预判 14:45', tone: 'intraday' }
  if (slot === '1645') return { text: '收盘复核 16:45', tone: 'green' }
  return { text: slot || '未知槽位', tone: 'intraday' }
}

export default function BriefPage() {
  const [data, setData] = useState<DailyBriefResponse | null>(null)
  const [status, setStatus] = useState<LoadStatus>('loading')
  const [errorText, setErrorText] = useState<string>('')

  const load = async () => {
    try {
      const d = await api.dailyBrief()
      setData(d)
      setStatus(d?.brief ? 'ok' : 'empty')
      setErrorText('')
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : String(e)
      setErrorText(msg)
      setStatus('error')
    }
  }

  useEffect(() => {
    void load()
  }, [])

  const brief = data?.brief
  const sl = slotLabel(data?.slot)

  return (
    <View className="page">
      <View className="row between" style={{ marginBottom: 8 }}>
        <View className="row">
          <Tag text={sl.text} tone={sl.tone} />
          {data?.date && <View className="tiny muted" style={{ marginLeft: 8 }}>{fmtDate(data.date)}</View>}
        </View>
        {brief?.summary && (
          <Tag text={brief.summary.generated_by === 'llm' ? 'LLM 表达' : '模板表达'} tone="rp" />
        )}
      </View>
      <View className="tiny muted" style={{ marginBottom: 10 }}>
        研究代理简报（不冒充 LEI 原始规则，不出买卖点）；盘中预判与收盘复核为两槽位，以收盘为准。
      </View>

      <LoadingState status={status} emptyText="尚未生成简报（可运行 scripts/precompute_daily_brief.py）" errorText={errorText} onRetry={load}>
        {brief && (
          <>
            {/* 环境异常 */}
            {brief.env?.anomalies && brief.env.anomalies.length > 0 && (
              <>
                <SectionTitle>环境异常</SectionTitle>
                {brief.env.anomalies.map((a: BriefAnomaly, i: number) => (
                  <View key={i} className="card" style={{ borderColor: '#3a2630' }}>
                    <View className="tiny" style={{ color: '#ff8a93' }}>{a.note_cn}</View>
                    <View className="tiny muted" style={{ marginTop: 4 }}>
                      {a.market} · {a.metric} = {fmtNum(a.value)} · 250日分位 {fmtNum(a.pctile_250d)}%
                    </View>
                  </View>
                ))}
              </>
            )}

            {/* 宽度背景 + 宏观 */}
            {brief.env?.breadth_context && brief.env.breadth_context.length > 0 && (
              <>
                <SectionTitle>宽度背景</SectionTitle>
                <View className="card">
                  {brief.env.breadth_context.map((b, i: number) => (
                    <View key={i} className="row between tiny" style={{ padding: '4px 0' }}>
                      <View className="dim">{b.market} · {b.metric}</View>
                      <View className="muted">{fmtNum(b.value)}（{fmtDate(b.date)}）· 分位 {fmtNum(b.pctile_250d)}%</View>
                    </View>
                  ))}
                </View>
              </>
            )}
            {brief.env?.macro?.line_cn && (
              <View className="card tiny dim" style={{ marginTop: 12 }}>{brief.env.macro.line_cn}</View>
            )}

            {/* 自选重点变化 */}
            {brief.watchlist?.items && brief.watchlist.items.length > 0 && (
              <>
                <SectionTitle>自选重点变化</SectionTitle>
                {brief.watchlist.items.map((w: BriefWatchItem) => (
                  <View key={w.symbol} className="card">
                    <View className="row between">
                      <View style={{ flex: 1 }}>
                        <View style={{ fontWeight: 600, color: '#f2f4f7' }}>{w.display_name || w.symbol}</View>
                        <View className="tiny muted">{w.symbol}</View>
                      </View>
                      <View className="row">
                        {w.is_new && <Tag text="新纳入" tone="green" />}
                        {w.verdict_cn && <Tag text={w.verdict_cn} tone={toneFromText(w.verdict_cn)} />}
                      </View>
                    </View>
                    {w.changes && w.changes.length > 0 && (
                      <View className="tiny" style={{ marginTop: 6, color: '#f0cf6b' }}>
                        {w.changes.join('；')}
                      </View>
                    )}
                  </View>
                ))}
                <View className="tiny muted" style={{ marginTop: 8 }}>
                  未变化 {brief.watchlist.unchanged_count ?? 0} 项 · 板块观察 {brief.watchlist.sector_watch_count ?? 0} 项
                </View>
              </>
            )}

            {/* 板块观察池 */}
            {brief.pool?.items && brief.pool.items.length > 0 && (
              <>
                <SectionTitle>板块观察池</SectionTitle>
                {brief.pool.items.map((p: BriefPoolItem) => (
                  <View key={p.code} className="card">
                    <View className="row between">
                      <View style={{ fontWeight: 600, color: '#f2f4f7' }}>{p.name || p.code}</View>
                      <View className="row">
                        {p.stage && <Tag text={String(p.stage)} tone="gray" />}
                        {p.streak ? <Tag text={`连续${p.streak}天`} tone="warn" /> : null}
                      </View>
                    </View>
                    <View className="tiny muted" style={{ marginTop: 6 }}>
                      RS分位 {fmtNum(p.rs_pctile)}% · 20日主力 {fmtNum(p.flow_20d_main_yi)}亿
                      {p.flow_vs_stage_cn ? ` · ${p.flow_vs_stage_cn}` : ''}
                    </View>
                    {p.next_watch && (
                      <View className="tiny dim" style={{ marginTop: 4 }}>下一观察：{p.next_watch}</View>
                    )}
                    {p.tags && p.tags.length > 0 && (
                      <View className="row wrap" style={{ marginTop: 6 }}>
                        {p.tags.map((t, i) => (
                          <Tag key={i} text={t} tone="gray" />
                        ))}
                      </View>
                    )}
                  </View>
                ))}
              </>
            )}

            {/* 简报摘要 */}
            {brief.summary?.text && (
              <>
                <SectionTitle>简报摘要</SectionTitle>
                <View className="card tiny dim" style={{ whiteSpace: 'pre-wrap' }}>
                  {brief.summary.text}
                </View>
              </>
            )}
          </>
        )}
      </LoadingState>
    </View>
  )
}
