"""Read-only account summarizer and self-contained visual report. No simulation."""
from pathlib import Path
import hashlib
import json
import math
import statistics

D = Path(__file__).parent
W = D.parents[3]
OUT = Path(json.loads((D/'storage-plan.json').read_text())['output'])
WEB = W/'web/public/research/factor-group-curves-20261021'
NAMES = {'momentum':'中期动量','cool':'短期反转','lowvol':'低波动','high52':'接近一年高点'}
COLORS = ['#b34a39','#c88836','#a6a285','#41988d','#264ed0','#182a38']
PERIODS = {'all':('2015-01','2025-12'),'early':('2015-01','2018-12'),
           'middle':('2019-01','2021-12'),'late':('2022-01','2025-12')}


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def metrics(daily, start, end):
    prior = next((r for r in reversed(daily) if r['date'][:7] < start), None)
    rows = [r for r in daily if start <= r['date'][:7] <= end]
    if not prior or not rows: raise ValueError('missing continuous period')
    values = [prior['nav_quote_proxy']] + [r['nav_quote_proxy'] for r in rows]
    ret = [b/a-1 for a,b in zip(values,values[1:])]
    peak = values[0]; dd=[]
    for v in values:
        peak=max(peak,v);dd.append(v/peak-1)
    monthends={r['date'][:7]:r for r in rows}
    mvalues=[values[0]]+[r['nav_quote_proxy'] for r in monthends.values()]
    monthly=[b/a-1 for a,b in zip(mvalues,mvalues[1:])]
    return {'return':values[-1]/values[0]-1,'cagr':(values[-1]/values[0])**(12/len(monthly))-1,
        'max_drawdown':min(dd),'volatility':statistics.stdev(ret)*math.sqrt(252),
        'months':len(monthly),'loss_month_fraction':sum(x<0 for x in monthly)/len(monthly),
        'fee_currency':rows[-1]['fees_cumulative']-prior['fees_cumulative'],
        'gross_turnover_monthly':sum(r['gross_traded_today']/r['nav_before_trade'] for r in rows)/len(monthly),
        'unknown_mean':statistics.mean(r['unknown_fraction'] for r in rows),
        'unknown_max':max(r['unknown_fraction'] for r in rows),
        'unknown_days':sum(r['unknown_fraction']>1e-12 for r in rows),
        'cash_mean':statistics.mean(r['cash_fraction'] for r in rows),
        'final_unknown':rows[-1]['unknown_fraction'],'final_cash':rows[-1]['cash_fraction'],
        'monthly':dict(zip(monthends,monthly)),'days':len(rows)}


def mean_range(values):
    n=len(values);mean=sum(values)/n
    v=sum((x-mean)**2 for x in values)/n
    for lag in range(1,min(3,n-1)+1):
        cov=sum((values[i]-mean)*(values[i-lag]-mean) for i in range(lag,n))/n
        v+=2*(1-lag/4)*cov
    se=math.sqrt(max(0,v)/n)
    return {'mean':mean,'descriptive95':[mean-1.96*se,mean+1.96*se],'months':n}


def main():
    WEB.mkdir(parents=True,exist_ok=True)
    manifest=json.loads((OUT/'manifest.json').read_text())['files']
    streams={};reconcile={'streams':0,'daily':0,'trades':0,'month_end_positions':0,'maximum_cash_error':0.0,'maximum_identity_error':0.0}
    for p in sorted(OUT.glob('*__fee*.json')):
        if p.name.startswith('._'):continue
        assert sha(p)==manifest[p.name]['sha256']
        d=json.loads(p.read_text());daily=d['daily'];assert len({r['date'] for r in daily})==len(daily)
        trades=d['trades'];cash=100000;fees=0;byday={};units={}
        for t in trades:
            delta=t['gross']*(1 if t['side']=='sell' else -1)-t['fee']
            cash+=delta;fees+=t['fee']
            reconcile['maximum_cash_error']=max(reconcile['maximum_cash_error'],abs(cash-t['cash_after']))
            assert abs(cash-t['cash_after'])<1e-5 and cash>-1e-5
            sign=1 if t['side']=='buy' else -1
            units[t['code']]=units.get(t['code'],0)+sign*t['qty']
            assert abs(units[t['code']]-t['units_after'])<1e-5
            assert t['decision_date']<t['date']
            byday.setdefault(t['date'],[]).append(t)
        cash=100000;fees=0;position_units={};holdings_bydate={}
        for h in d['month_end_holdings']:holdings_bydate.setdefault(h['date'],[]).append(h)
        for r in daily:
            for t in byday.get(r['date'],[]):
                cash+=t['gross']*(1 if t['side']=='sell' else -1)-t['fee'];fees+=t['fee']
                position_units[t['code']]=position_units.get(t['code'],0)+(1 if t['side']=='buy' else -1)*t['qty']
            assert abs(cash-r['cash'])<1e-5 and abs(fees-r['fees_cumulative'])<1e-5
            err=abs(r['nav_quote_proxy']-r['cash']-r['market_value'])
            reconcile['maximum_identity_error']=max(reconcile['maximum_identity_error'],err);assert err<1e-5
            assert abs(r['stress_zero_unknown_nav']+r['unknown_value']-r['nav_quote_proxy'])<1e-5
            if r['date'] in holdings_bydate:
                hs=holdings_bydate[r['date']]
                assert abs(sum(h['units']*h['mark'] for h in hs)-r['market_value'])<1e-5
                assert all(abs(position_units[h['code']]-h['units'])<1e-6 for h in hs)
        reconcile['streams']+=1;reconcile['daily']+=len(daily);reconcile['trades']+=len(trades);reconcile['month_end_positions']+=len(d['month_end_holdings'])
        period={k:metrics(daily,*bounds) for k,bounds in PERIODS.items()}
        bymonth={};peak=daily[0]['nav_quote_proxy']
        for r in daily:
            peak=max(peak,r['nav_quote_proxy']);m=r['date'][:7]
            old=bymonth.get(m)
            bymonth[m]=[r['date'],r['nav_quote_proxy']/100000,r['unknown_fraction'],r['cash_fraction'],
                        min(old[4] if old else 0,r['nav_quote_proxy']/peak-1),
                        max(old[5] if old else 0,r['unknown_fraction'])]
        streams[p.stem]={'points':list(bymonth.values()),'period':period,
            'orders':len(d['orders']),'filled':len(trades),'blocked':len(d['orders'])-len(trades)}
    assert len(streams)==84
    increments={}
    for universe in ('all_qualified','green_only'):
      for factor in NAMES:
       for period in PERIODS:
        a=streams[f'{universe}__{factor}__G5__fee25']['period'][period]
        for label,base in [('pool',f'{universe}__pool__fee25'),('momentum',f'{universe}__momentum__G5__fee25')]:
            b=streams[base]['period'][period];months=list(a['monthly'])
            diff=[a['monthly'][m]-b['monthly'][m] for m in months]
            up=[a['monthly'][m]-b['monthly'][m] for m in months if b['monthly'][m]>0]
            down=[a['monthly'][m]-b['monthly'][m] for m in months if b['monthly'][m]<0]
            increments[f'{universe}__{factor}__{period}__vs_{label}']={
              **mean_range(diff),'cagr_difference':a['cagr']-b['cagr'],
              'drawdown_difference':a['max_drawdown']-b['max_drawdown'],
              'up_month_difference':statistics.mean(up) if up else None,
              'down_month_difference':statistics.mean(down) if down else None,
              'up_month_n':len(up),'down_month_n':len(down),
              'cash_difference':a['cash_mean']-b['cash_mean'],'unknown_difference':a['unknown_mean']-b['unknown_mean']}
    payload={'streams':streams,'increments':increments,'labels':NAMES,'periods':PERIODS,
        'source_manifest_sha256':sha(OUT/'manifest.json'),'method':'固定300股，2015—2025已看历史；日度报价记账，月末曲线展示。非实盘成交/独立验证。'}
    (D/'summary.json').write_text(json.dumps(payload,ensure_ascii=False,separators=(',',':')))
    (D/'account-reconciliation.json').write_text(json.dumps(reconcile,indent=2)+'\n')
    template=(D/'viewer-template.html').read_text()
    (WEB/'index.html').write_text(template.replace('__DATA__',json.dumps(payload,ensure_ascii=False,separators=(',',':'))))
    for factor in NAMES:
        (WEB/f'{factor}.svg').write_text(static_svg(streams,factor))
    print(json.dumps(reconcile));print('ARTIFACT',WEB/'index.html')


def static_svg(streams,factor):
    keys=[f'all_qualified__{factor}__G{g}__fee25' for g in range(1,6)]+['all_qualified__pool__fee25']
    ymax=max(p[1] for k in keys for p in streams[k]['points'])*1.07
    parts=['<svg xmlns="http://www.w3.org/2000/svg" width="1100" height="700" viewBox="0 0 1100 700">',
      '<rect width="1100" height="700" fill="#f7f5ef"/>',
      '<g font-family="Arial, PingFang SC, sans-serif" fill="#182a38">',
      f'<text x="55" y="45" font-size="25" font-weight="bold">{NAMES[factor]} · 五组连续资金示意</text>',
      '<text x="55" y="76" font-size="15">固定300只A股来源样本 · 全体合格股票 · 月调仓 · 单边费用0.25% · 初始=1</text>',
      '<text x="55" y="100" font-size="14" fill="#8e4535">2015—2025已看历史；日线约束报价模拟，虚线含缺价估值，不能当作可兑现净值。</text>']
    x=lambda i:70+i/132*970
    y=lambda v:440-v/ymax*300
    for j in range(5):
        v=ymax*j/4;yy=y(v)
        parts.extend([f'<path d="M70 {yy}H1040" stroke="#d9ddd8"/>',f'<text x="28" y="{yy+5}" font-size="12">{v:.1f}</text>'])
    for n,key in enumerate(keys):
        pts=streams[key]['points'];color=COLORS[n]
        for i in range(1,len(pts)):
            dashed=' stroke-dasharray="5 4"' if pts[i][5]>1e-12 or pts[i-1][5]>1e-12 else ''
            parts.append(f'<path d="M{x(i-1):.2f} {y(pts[i-1][1]):.2f}L{x(i):.2f} {y(pts[i][1]):.2f}" stroke="{color}" fill="none" stroke-width="2"{dashed}/>')
        label=f'G{n+1}' if n<5 else '共同池'
        parts.append(f'<text x="{70+n*160}" y="125" font-size="14" fill="{color}">{label} · 期末 {pts[-1][1]:.2f}</text>')
        path=' '.join(('M' if i==0 else 'L')+f'{x(i):.2f} {605-p[5]*95:.2f}' for i,p in enumerate(pts))
        parts.append(f'<path d="{path}" stroke="{color}" fill="none" stroke-width="1.4"/>')
    for i,label in [(1,'2015'),(49,'2019'),(85,'2022'),(132,'2025年末')]:
        parts.append(f'<text x="{x(i)-15}" y="465" font-size="13">{label}</text>')
    parts.extend(['<text x="55" y="500" font-size="16">缺价持仓占比（每月最高值；越高，资金线越依赖旧报价）</text>',
      '<text x="28" y="515" font-size="12">100%</text><text x="40" y="610" font-size="12">0%</text>',
      '<text x="55" y="650" font-size="14">G1→G5 按事先约定偏好排序；反转G5为上月较弱，低波动G5为波动较小。</text>',
      '<text x="55" y="675" font-size="14">完整页面可切换四因子、趋势绿池、费用及历史分期，并查看回撤、现金与对照差额。</text></g></svg>'])
    return ''.join(parts)


if __name__=='__main__':main()
