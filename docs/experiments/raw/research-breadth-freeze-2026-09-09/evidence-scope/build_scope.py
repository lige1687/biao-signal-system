from pathlib import Path
import pandas as pd, json, hashlib

ROOT=Path(__file__).resolve().parents[5]
OLD=ROOT/'docs/experiments/raw/research-etf-breadth-confirmation-2026-09-09'
OUT=Path(__file__).resolve().parent
START,END=pd.Timestamp('2018-07-05'),pd.Timestamp('2026-06-30')
THRESHOLDS=(43.3,56.7)

def weekly(width, dates):
    work=width.reindex(dates); iso=work.index.isocalendar(); rows=[]
    for _,g in work.groupby([iso.year,iso.week]):
        g=g[g.index.to_series().between(START,END)]
        if g.empty or g.index.max()+pd.Timedelta(days=7-g.index.max().weekday())>END: continue
        v=g[g.valid.fillna(False)]
        if v.empty: continue
        x=v.iloc[-1]; b=float(x.b200); target=1.0 if b<43.3 else (0.5 if b<56.7 else 0.0)
        rows.append({'signal_date':g.index.max(),'width_date':v.index[-1],'b200':b,'target':target})
    return pd.DataFrame(rows)

bars={}
for sym,prefix in [('510300','sh'),('159915','sz')]:
    d=pd.read_csv(ROOT/f'docs/experiments/raw/research-broad-etf-cash-2026-09-08/first12/inputs/bars/{prefix}{sym}-nominal.csv',parse_dates=['date'])
    bars[sym]=pd.DatetimeIndex(d.loc[d.date.between(START,END),'date'])
width={s:pd.read_parquet(OLD/f'prepared/breadth_{s}.parquet').loc[START:END] for s in ['all_a','csi300']}
probe=json.loads((OLD/'prepared/csi300_membership_probe_audit.json').read_text())
effective=pd.to_datetime(probe['detected_effective_dates'])

all_candidates=[]
weekly_frames={}
for source,symbol in [('all_a','510300'),('csi300','510300')]:
    d=width[source]
    q=d[d.valid].copy(); q['distance']=abs(q.coverage-.90)
    for day,x in q[q.distance<=.005].iterrows():
        all_candidates.append({'source':source,'kind':'coverage_boundary','observation_date':day,'signal_date':pd.NaT,'distance':x.distance,'coverage':x.coverage,'b200':x.b200,'current_target':''})
    w=weekly(d,bars[symbol]); weekly_frames[source]=w
    w['distance']=w.b200.map(lambda x:min(abs(x-t) for t in THRESHOLDS))
    for x in w[w.distance<=1.0].itertuples():
        all_candidates.append({'source':source,'kind':'weekly_band_boundary','observation_date':x.width_date,'signal_date':x.signal_date,'distance':x.distance,'coverage':d.loc[x.width_date,'coverage'],'b200':x.b200,'current_target':x.target})

# Membership-change candidates: a weekly observation within five CSI300 quote rows of an
# effective change, ranked only by calendar proximity and date.
w=weekly_frames['csi300']; dates=bars['510300']; pos={d:i for i,d in enumerate(dates)}
for x in w.itertuples():
    near=[]
    for e in effective:
        if e in pos and x.width_date in pos and abs(pos[x.width_date]-pos[e])<=5: near.append(e)
    if near:
        e=min(near,key=lambda z:(abs(pos[x.width_date]-pos[z]),z))
        all_candidates.append({'source':'csi300','kind':'membership_change_near_week','observation_date':x.width_date,'signal_date':x.signal_date,'distance':abs(pos[x.width_date]-pos[e]),'coverage':width['csi300'].loc[x.width_date,'coverage'],'b200':x.b200,'current_target':x.target,'effective_date':e})

cand=pd.DataFrame(all_candidates)
for c in ['observation_date','signal_date','effective_date']:
    if c in cand: cand[c]=pd.to_datetime(cand[c]).dt.strftime('%Y-%m-%d')
cand.sort_values(['source','kind','distance','observation_date']).to_csv(OUT/'all-candidates.csv',index=False)

# Frozen allocation: 2 per source for coverage, 2 per source for band boundary,
# and 2 CSI300 membership-change cases. Rank by distance then earliest date; no P&L read.
parts=[]
for source in ['all_a','csi300']:
    for kind in ['coverage_boundary','weekly_band_boundary']:
        parts.append(cand[(cand.source==source)&(cand.kind==kind)].sort_values(['distance','observation_date']).head(2))
parts.append(cand[(cand.source=='csi300')&(cand.kind=='membership_change_near_week')].sort_values(['distance','observation_date']).head(2))
sel=pd.concat(parts,ignore_index=True)
def need(r):
    if r.kind=='coverage_boundary' and r.source=='all_a': return '历史时点上市/退市/暂停上市全A名单；逐股当日原始报价与此前200条有效收盘；源available_at'
    if r.kind=='coverage_boundary': return '该日沪深300官方生效成分；300只逐股当日原始报价与此前200条有效收盘；源available_at'
    if r.kind=='weekly_band_boundary' and r.source=='all_a': return '同周最后有效日的历史全A成员与逐股连续价格；逐股复算B200及覆盖率'
    if r.kind=='weekly_band_boundary': return '同周最后有效日官方沪深300成员与逐股连续价格；逐股复算B200及覆盖率'
    return '相邻两次20交易日查询之间的每日官方成分变更公告、生效日及完整进出名单；核是否有离开后返回'
def affected(r):
    if r.source=='all_a': return '510300-all_a-W0..W3与159915-all_a-W0..W3（两费率）；同周信号及其后待买/下一可成交开盘'
    return '510300-csi300-W0..W3（两费率）；同周信号及其后待买/下一可成交开盘'
sel['source_to_add']=sel.apply(need,axis=1);sel['jointly_affected_comparisons']=sel.apply(affected,axis=1)
sel['status']='sensitivity_evidence_candidate_not_known_error'
def archived_crosscheck(r):
    if pd.isna(r.signal_date): return pd.Series({'saved_signal_rows_matching':0,'saved_trade_events_next_10d':''})
    day=pd.Timestamp(r.signal_date); symbols=['510300','159915'] if r.source=='all_a' else ['510300']; sm=0; seen=[]
    for fee in ['10bp','20bp']:
        folder=OLD/'results'/f'fee-{fee}'
        for symbol in symbols:
            for variant in ['W0','W1','W2','W3']:
                stem=f'{symbol}-{r.source}-{variant}-{fee}'
                sig=pd.read_csv(folder/f'{stem}-signals.csv',parse_dates=['date'])
                sm += int(((sig.date==day)&(sig.kind=='weekly_target')&(abs(sig.b200-float(r.b200))<1e-9)).sum())
                tr=pd.read_csv(folder/f'{stem}-trades.csv',parse_dates=['date'])
                q=tr[tr.date.between(day+pd.Timedelta(days=1),day+pd.Timedelta(days=10))]
                seen += [f'{stem}:{x.date.date()}:{x.side}:{x.reason}' for x in q.itertuples()]
    return pd.Series({'saved_signal_rows_matching':sm,'saved_trade_events_next_10d':' | '.join(sorted(set(seen)))})
sel=pd.concat([sel,sel.apply(archived_crosscheck,axis=1)],axis=1)
sel.to_csv(OUT/'selected-events.csv',index=False)
counts=cand.groupby(['source','kind']).size().rename('candidate_count').reset_index()
counts.to_csv(OUT/'candidate-counts.csv',index=False)
print(counts.to_string(index=False));print(sel[['source','kind','observation_date','signal_date','distance']].to_string(index=False))
