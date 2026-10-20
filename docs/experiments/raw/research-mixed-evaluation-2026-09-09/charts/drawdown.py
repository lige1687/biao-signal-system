from pathlib import Path
import json,hashlib
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import font_manager
from matplotlib.ticker import PercentFormatter
B=Path(__file__).resolve().parent;S=B.parent.parent/'research-mixed-pool-audit-2026-09-09/dedup-execution'
font_manager.fontManager.addfont('/System/Library/Fonts/Supplemental/Arial Unicode.ttf')
plt.rcParams.update({'font.family':'Arial Unicode MS','axes.unicode_minus':False,'svg.fonttype':'path','font.size':11,'axes.spines.top':False,'axes.spines.right':False})
e=pd.read_csv(S/'equity.csv',parse_dates=['date']);names={'equal':'普通平均配置','no_exit_100':'满额选强、不退出','no_exit_75':'75%选强、不退出','fast_reentry_exit':'退出＋快速回补'}
colors={'equal':'#7c8490','no_exit_100':'#c76727','no_exit_75':'#337aa0','fast_reentry_exit':'#168365'}
fig,axes=plt.subplots(2,1,figsize=(12,7.8),sharex=True,sharey=True);out=[]
for ax,fee in zip(axes,[.001,.002]):
 for method in names:
  aid=f'{method}-fee{fee:.3f}';g=e[e.account_id==aid].sort_values('date');peak=np.maximum.accumulate(np.r_[1e6,g.equity.to_numpy()])[1:];dd=g.equity.to_numpy()/peak-1
  ax.plot(g.date,dd,color=colors[method],label=names[method],lw=1.9 if method=='fast_reentry_exit' else 1.2,alpha=.98)
  out.extend({'account_id':aid,'date':d.strftime('%Y-%m-%d'),'drawdown':float(x)} for d,x in zip(g.date,dd))
 ax.axhline(0,color='#5f6872',lw=.6);ax.axvline(pd.Timestamp('2025-01-01'),color='#a4a9b0',ls='--',lw=1)
 ax.grid(axis='y',color='#e2e6e9',lw=.6);ax.set_ylim(-.38,.015);ax.yaxis.set_major_formatter(PercentFormatter(1,decimals=0));ax.set_ylabel('距此前账户高点的跌幅')
 ax.set_title(f'买卖每边费用 {fee:.1%}',loc='left',fontweight='bold');ax.set_xlim(pd.Timestamp('2020-12-01'),pd.Timestamp('2026-06-30'))
axes[0].legend(loc='lower left',ncol=2,frameon=True,facecolor='white',edgecolor='#e2e6e9',fontsize=10)
axes[1].xaxis.set_major_locator(mdates.YearLocator());axes[1].xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
fig.suptitle('11只固定代表产品：四种方案的完整回撤路径',x=.085,ha='left',fontsize=18,fontweight='bold')
fig.text(.085,.92,'2020-12-01—2026-06-30  ·  初始100万元、无追加  ·  每日账户含现金、分红权益和费用',fontsize=11,color='#58626c')
fig.text(.085,.025,'0%表示回到此前高点；虚线划分2025年前后。两图使用相同刻度，曲线未按时期重置。',fontsize=10,color='#58626c')
fig.subplots_adjust(top=.86,bottom=.09,left=.085,right=.97,hspace=.25)
for ext in ['png','svg','pdf']:fig.savefig(B/f'four-way-drawdown.{ext}',dpi=180,facecolor='white')
pd.DataFrame(out).to_csv(B/'drawdown-data.csv',index=False)
# Cross-check each curve's minimum with independently saved account summary.
a=pd.read_csv(S/'accounts.csv');d=pd.DataFrame(out);checks=[]
for row in a.itertuples():
 value=d[d.account_id==row.account_id].drawdown.min();assert abs(value-row.max_drawdown)<1e-12
 checks.append({'account_id':row.account_id,'max_drawdown':float(value)})
(B/'chart-checks.json').write_text(json.dumps({'passed':True,'principles':'v1.0','source_sha256':hashlib.sha256((S/'equity.csv').read_bytes()).hexdigest(),'checks':checks},ensure_ascii=False,indent=2)+'\n')
print('Saved PNG/SVG/PDF and 16,304 curve rows; all 8 minima match.')
