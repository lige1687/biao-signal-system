from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.ticker import PercentFormatter
W=Path(__file__).resolve().parents[1];D=W/'comparison';F=font_manager.FontProperties(fname='/System/Library/Fonts/Supplemental/Arial Unicode.ttf');plt.rcParams['font.family']=F.get_name();plt.rcParams['axes.unicode_minus']=False
x=pd.read_csv(D/'relative-daily.csv',parse_dates=['date'])
fig,axes=plt.subplots(2,2,figsize=(14,8),sharex=True)
for i,fee in enumerate(['10bp','20bp']):
 for aid,name,color in [(f'159915-all_a-W3-{fee}','创业板：全A宽度＋价格确认','#13836f'),(f'510300-csi300-W0-{fee}','沪深300：自身宽度原规则','#da7b23'),(f'510300-all_a-W3-{fee}','沪深300：全A宽度＋价格确认','#5277ba')]:
  z=x[(x.candidate==aid)&x.benchmark.str.contains('-B1-')]
  axes[0,i].plot(z.date,z.relative_nav,label=name,color=color,lw=1.3)
  axes[1,i].plot(z.date,z.relative_drawdown,label=name,color=color,lw=1.2)
 axes[0,i].axhline(1,color='gray',ls='--',lw=.7);axes[0,i].set_title('每边费用 '+('0.1%' if i==0 else '0.2%'));axes[0,i].set_ylim(.65,2.4);axes[1,i].set_ylim(-.48,.02);axes[1,i].yaxis.set_major_formatter(PercentFormatter(1))
 for ax in axes[:,i]:ax.grid(alpha=.2);ax.axvline(pd.Timestamp('2025-01-01'),color='gray',ls=':',lw=.8)
axes[0,0].set_ylabel('相对净值：1表示与同ETF纯200日趋势持平');axes[1,0].set_ylabel('相对此前最高优势的回落（非账户亏损）');axes[0,0].legend(fontsize=9,loc='upper left')
fig.suptitle('账户少跌，也可能长期跑输：优势何时积累、何时回吐',fontsize=16)
fig.text(.5,.015,'2018-07-05—2026-06-30；各自同ETF、同费用基准；已知历史补充评价，不是新行情验证。虚线标出2025年。',ha='center',fontsize=10)
fig.tight_layout(rect=(0,.04,1,.95))
for ext in ['png','svg','pdf']:fig.savefig(D/f'relative-performance.{ext}',dpi=160)
print('charts saved')
