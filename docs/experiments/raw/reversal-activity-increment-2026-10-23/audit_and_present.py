"""Independent arithmetic checks and predeclared diagnostics, no new accounts."""
from pathlib import Path
import json, csv, gzip, hashlib, math, os
from collections import Counter
import numpy as np
import pandas as pd

D = Path(__file__).resolve().parent
PLAN = json.loads((D/'storage-plan-v2.json').read_text())
O = Path(PLAN['output'])
REFS = json.loads((D/'input-refs.json').read_text())

def readj(p): return json.loads(Path(p).read_text())
def gz(p): return pd.read_csv(p)
def sha(p): return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def save(name, obj):
    (D/name).write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False)+'\n')
def near(a,b,tol=1e-8):
    assert abs(float(a)-float(b)) <= tol*max(1,abs(float(b))), (a,b)

def uncertainty(values):
    a=np.array([np.nan if v is None else v for v in values],dtype=float)
    n=int(np.isfinite(a).sum())
    if not n:return {'n':0,'mean':None,'ci_low':None,'ci_high':None}
    mean=float(np.nanmean(a)); e=a-mean
    total=float(np.nansum(e*e))
    for k in range(1,min(3,len(a)-1)+1):total += 2*(1-k/4)*float(np.nansum(e[k:]*e[:-k]))
    se=max(total,0)**.5/n
    return {'n':n,'mean':mean,'ci_low':mean-1.96*se,'ci_high':mean+1.96*se}

def main():
    manifest=readj(O/'manifest.json')
    for name,ref in manifest['files'].items():assert sha(O/name)==ref['sha256'], name
    forms=readj(O/'formations.json'); months=readj(O/'account-months.json')
    summary=gz(O/'account-summary.csv.gz')
    comparisons=readj(O/'monthly-comparisons.json')
    counters=Counter(); daily={}; extra=[]
    for key in sorted(months):
        f=gz(O/f'{key}__daily.csv.gz'); t=gz(O/f'{key}__trades.csv.gz'); orders=gz(O/f'{key}__orders.csv.gz')
        daily[key]=f
        assert f.date.is_unique and f.date.is_monotonic_increasing
        assert (f.cash>=-1e-7).all()
        assert np.allclose(f.nav_quote_proxy, f.cash+f.market_value,rtol=1e-12,atol=1e-8)
        fee=int(key.split('fee')[-1])/10000
        assert np.allclose(t.fee,t.gross*fee,rtol=1e-12,atol=1e-8)
        near(t.fee.sum(), f.fees_cumulative.iloc[-1])
        cash=100000+float(t.loc[t.side=='sell','gross'].sum())-float(t.loc[t.side=='buy','gross'].sum())-float(t.fee.sum())
        near(cash,f.cash.iloc[-1])
        ends=f.groupby(f.date.str[:7],sort=True).last()
        last=100000
        for month,row in ends.iterrows():
            near(row.nav_quote_proxy/last-1, months[key][month]['return']);last=row.nav_quote_proxy
        for _,r in summary[summary.account==key].iterrows():
            dates={'full':('2015-01','2025-12'),'early':('2015-01','2018-12'),'middle':('2019-01','2021-12'),'late':('2022-01','2025-12')}[r.period]
            z=f[(f.date.str[:7]>=dates[0])&(f.date.str[:7]<=dates[1])]
            start=100000 if z.index[0]==0 else f.loc[z.index[0]-1,'nav_quote_proxy']
            nav=np.r_[start,z.nav_quote_proxy.to_numpy()]
            near(float(np.min(nav/np.maximum.accumulate(nav)-1)),r.max_daily_drawdown)
            near((nav[-1]/nav[0])**(12/r.calendar_months)-1,r.annualized_return)
        peaks=np.maximum.accumulate(np.r_[100000,f.nav_quote_proxy.to_numpy()])[1:]
        underwater=(f.nav_quote_proxy.to_numpy()<peaks-1e-7)
        longest=cur=0
        for flag in underwater:cur=cur+1 if flag else 0;longest=max(longest,cur)
        last_hold=gz(O/f'{key}__month_end_holdings.csv.gz')
        last_hold=last_hold[last_hold.date==f.date.iloc[-1]]
        near(float((last_hold.units*last_hold.mark).sum()),f.market_value.iloc[-1])
        extra.append({'account':key,'cash_end':float(f.cash.iloc[-1]),'value_end':float(f.nav_quote_proxy.iloc[-1]),
          'unknown_end':float(f.unknown_fraction.iloc[-1]),'unknown_max':float(f.unknown_fraction.max()),
          'zero_unknown_end_value':float(f.stress_zero_unknown_nav.iloc[-1]),
          'longest_below_prior_peak_trading_days':longest,'blocked_orders':int((orders.status=='blocked').sum()),
          'traded_value_per_year_over_daily_nav':float((f.gross_traded_today/f.nav_before_trade).sum()/11),
          'known_valuation_days':int((f.unknown_fraction==0).sum()),'daily_records':len(f)})
        counters['accounts']+=1;counters['daily_rows']+=len(f);counters['trades']+=len(t)
    for c in comparisons:
        key=f"s{c['stratum']}__{c['candidate']}__fee{c['fee_bps']}"; base=f"s{c['stratum']}__{c['baseline']}__fee{c['fee_bps']}"
        period={'full':('2015-01','2025-12'),'early':('2015-01','2018-12'),'middle':('2019-01','2021-12'),'late':('2022-01','2025-12')}[c['period']]
        vals=[months[key][m]['return']-months[base][m]['return'] for m in months[key] if period[0]<=m<=period[1]]
        u=uncertainty(vals)
        for k in ('mean','ci_low','ci_high'):near(u[k],c['hac3'][k],1e-11)
        counters['comparisons']+=1
    for f in forms:
        features={r['code']:r for r in f['features']}
        ordered=sorted(features,key=lambda c:(features[c]['amount60'],c)); n=len(ordered)
        cuts=np.array_split(np.array(ordered),3)
        for s,cut in zip(f['strata'],cuts):
            assert list(cut)==s['codes']
            order=sorted(cut,key=lambda c:(-features[c]['hot'],c))
            for i,g in enumerate(np.array_split(np.array(order),5),1):assert list(g)==s['groups'][f'G{i}']
            for weights in s['weights'].values():near(sum(weights.values()),1)
            counters['strata']+=1
    old=readj(REFS['original_input_rows']['path']); labels={(r['month'],r['code']):r for r in old}
    core_ic=gz(O/'old-label-rankic.csv.gz'); more=[]; anchors=[]
    raw_manifest=readj(REFS['source_manifest']['path']); cal=readj(REFS['calendar']['path']); days=[r[0] for r in cal['data'] if r[1]=='1']
    for fi,f in enumerate(forms):
        m=f['month_end'][:7]; feat={r['code']:r for r in f['features']}
        for s in f['strata']:
            known={c:labels[m,c]['return'] for c in s['codes'] if labels[m,c].get('return') is not None and math.isfinite(float(labels[m,c]['return']))}
            if len(known)>=3:
                scores=pd.Series({c:-feat[c]['hot'] for c in known});returns=pd.Series(known)
                ic=float(scores.rank().corr(returns.rank()))
                row=core_ic[(core_ic.month==m)&(core_ic.stratum==s['stratum'])].iloc[0]
                near(ic,row.rankic,1e-10)
            winners={c for c,v in known.items() if v>=.2}
            for name,w in s['weights'].items():
                selected=set(w);good=selected & set(known)
                more.append({'month':m,'holding_month':labels[m,next(iter(feat))]['holding_month'],'stratum':s['stratum'],'portfolio':name,
                  'pool_n':s['n'],'selected_n':len(w),'known_n':len(good),'known_pool_winners':len(winners),
                  'retained_known_winners':len(selected&winners),'selected_known_losers':sum(known[c]<0 for c in good),
                  'selected_known_deep_losses':sum(known[c]<=-.2 for c in good),
                  'known_unknown_weight':sum(w[c] for c in selected-set(known))})
            if fi in (0,24,48,72,96,131) and s['codes']:
                c=s['codes'][len(s['codes'])//2]; p=readj(raw_manifest['asset_sources'][c]['daily']['path']); rows={r[0]:dict(zip(p['fields'],r)) for r in p['data']}
                end=days.index(f['month_end']);window=days[end-59:end+1]; amount=sum(float(rows[d]['amount']) for d in window)/60
                near(amount,feat[c]['amount60'],1e-12);anchors.append({'month':m,'code':c,'n_days':60,'amount60':amount})
    diag=gz(O/'old-label-diagnostics.csv.gz'); selections=[]
    for s in (1,2,3):
        sub=diag[diag.stratum==s]; pivot=sub.pivot(index='month',columns='portfolio',values='complete_return')
        shared=pivot[[f'G{i}' for i in range(1,6)]].dropna()
        broad=pivot.dropna()
        pairs={}
        for a,b in [('G5','pool'),('G5','lowvol'),('rev_volbalanced','pool')]:
            v=pivot[a]-pivot[b];pairs[a+'-'+b]=uncertainty([None if pd.isna(x) else float(x) for x in v])
        ic=core_ic[core_ic.stratum==s]
        selections.append({'stratum':s,'rankic':uncertainty(list(ic.rankic)),
          'rankic_known_pairs':int(ic.known_pairs.sum()),'five_groups_shared_months':len(shared),
          'five_groups_mean':{c:float(shared[c].mean()) if len(shared) else None for c in shared},
          'all_eight_shared_months':len(broad),'paired_complete_month_comparisons':pairs,
          'average_unknown_weight_by_portfolio':sub.groupby('portfolio').unknown_weight.mean().to_dict(),
          'mean_vol60':sub.groupby('portfolio').selected_vol60.mean().to_dict(),
          'mean_momentum':sub.groupby('portfolio').selected_momentum.mean().to_dict()})
    more=pd.DataFrame(more); capture=[]
    for (s,p),g in more.groupby(['stratum','portfolio']):
        capture.append({'stratum':int(s),'portfolio':p,'known_winners_available':int(g.known_pool_winners.sum()),
          'known_winners_retained':int(g.retained_known_winners.sum()),'known_winner_capture':float(g.retained_known_winners.sum()/g.known_pool_winners.sum()),
          'known_selected_count':int(g.known_n.sum()),'loss_fraction_known':float(g.selected_known_losers.sum()/g.known_n.sum()),
          'deep_loss_fraction_known':float(g.selected_known_deep_losses.sum()/g.known_n.sum())})
    leave=[]
    for s in (1,2,3):
        for a,b in [('G5','pool'),('G5','lowvol'),('rev_volbalanced','pool')]:
            values={m:months[f's{s}__{a}__fee25'][m]['return']-months[f's{s}__{b}__fee25'][m]['return'] for m in months[f's{s}__{a}__fee25']}
            leave.append({'stratum':s,'comparison':a+'-'+b,'leave_one_year_out_means':{str(y):float(np.mean([v for m,v in values.items() if not m.startswith(str(y))])) for y in range(2015,2026)}})
    for c in readj(O/'cross-stratum-increments.json'):
        lo,hi,fee=c['lower_activity_stratum'],c['higher_activity_stratum'],c['fee_bps']
        for m,v in c['monthly_differences'].items():
            expected=(months[f's{lo}__G5__fee{fee}'][m]['return']-months[f's{lo}__pool__fee{fee}'][m]['return'])-(months[f's{hi}__G5__fee{fee}'][m]['return']-months[f's{hi}__pool__fee{fee}'][m]['return'])
            near(expected,v,1e-12)
        u=uncertainty(list(c['monthly_differences'].values()))
        for k in ('mean','ci_low','ci_high'):near(u[k],c['hac3'][k],1e-11)
    save('independent-audit.json',{'status':'passed','checks':dict(counters),'amount_anchors':anchors,'source_manifest_sha256':sha(O/'manifest.json'),'no_account_rerun':True,'scope':'arithmetic, memberships, source anchors, time-series paired comparisons; not complete independent data certification'})
    save('supplement-summary.json',{'account_extra':extra,'selection':selections,'opportunities':capture,'leave_one_year':leave,
      'formation_eligible_min':min(f['eligible_n'] for f in forms),'formation_eligible_max':max(f['eligible_n'] for f in forms),
      'formation_eligible_total':sum(f['eligible_n'] for f in forms),'rejected_reasons':dict(Counter(r['reason'].split(':')[0] for f in forms for r in f['rejected']))})
    os.environ['MPLCONFIGDIR']=str(O/'matplotlib-cache')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams.update({'font.family':'Arial Unicode MS','axes.unicode_minus':False,'svg.fonttype':'none'})
    names=['G1','G2','G3','G4','G5','lowvol','rev_volbalanced']
    labels_cn={'G1':'G1 前月最强','G2':'G2','G3':'G3','G4':'G4','G5':'G5 前月最弱','lowvol':'同数量低波动','rev_volbalanced':'波动分层后反转'}
    colors=['#bf5252','#cb8b53','#a8a293','#7c9c9d','#146c94','#7c54a1','#228652']
    for kind in ('excess','absolute'):
        fig,axes=plt.subplots(3,1,figsize=(12,11),sharex=True,layout='constrained')
        for s,ax in enumerate(axes,1):
            base=daily[f's{s}__pool__fee25'].groupby(daily[f's{s}__pool__fee25'].date.str[:7],sort=True).last().reset_index(drop=True);x=pd.to_datetime(base.date)
            # Explicit 100000 initial point at last pre-holding month end.
            xx=pd.DatetimeIndex([pd.Timestamp('2014-12-31')]).append(pd.DatetimeIndex(x))
            for name,color in zip(names,colors):
                source=daily[f's{s}__{name}__fee25'];f=source.groupby(source.date.str[:7],sort=True).last().reset_index(drop=True);assert list(f.date)==list(base.date)
                y=(f.nav_quote_proxy-base.nav_quote_proxy)/100000*100 if kind=='excess' else f.nav_quote_proxy/100000*100
                ax.plot(xx,np.r_[0 if kind=='excess' else 100,y],label=labels_cn[name],color=color,linewidth=1.0 if name.startswith('G') and name!='G5' else 1.7,alpha=.9)
            if kind=='absolute':ax.plot(xx,np.r_[100,base.nav_quote_proxy/100000*100],label='同档全体',color='#202832',linewidth=1.7)
            else:ax.axhline(0,color='#202832',linewidth=.8)
            for date in ['2019-01-01','2022-01-01']:ax.axvline(pd.Timestamp(date),color='#bfc6cd',linestyle='--',linewidth=.8)
            ax.set_title(['成交金额较低的一档','成交金额中间的一档','成交金额较高的一档'][s-1],loc='left',fontsize=12)
            ax.set_ylabel('累计收益差（百分点）' if kind=='excess' else '资产指数（起点100）');ax.grid(alpha=.18)
        handles,labels=axes[0].get_legend_handles_labels();fig.legend(handles,labels,loc='outside lower center',ncol=4,frameon=False)
        fig.suptitle(('相对同档全体的累计收益差' if kind=='excess' else '固定资金账户绝对曲线')+'｜单边25基点费用假设\n固定300股；2015—2025年已见历史，月末绘图；报价情景，未知按最后可信报价列示',fontsize=14)
        fig.savefig(D/f'{kind}-curves.svg');svg=D/f'{kind}-curves.svg';svg.write_text('\n'.join(line.rstrip() for line in svg.read_text().splitlines())+'\n');fig.savefig(D/f'{kind}-curves.png',dpi=115);plt.close(fig)
    print(json.dumps({'audit':'passed','counts':dict(counters),'eligible':sum(f['eligible_n'] for f in forms),'summary':'supplement-summary.json'},ensure_ascii=False))

if __name__=='__main__':main()
