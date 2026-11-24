"""Prepare a reviewable, separate reconstruction; never writes a live cache."""
from pathlib import Path
import csv
import hashlib
import json
import os

ROOT = Path(__file__).resolve().parents[3]
OUT = Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR'] = str(ROOT / '.codex/breadth-reading-coordination-20261101/mpl-config')
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.font_manager import FontProperties

live = Path('/Users/yongbiaoli/.lei_signal_lab/cache/a_share_ma_breadth_history.json')
before = live.read_bytes()
old = json.loads(before)
by_date = {r['date']: r for r in old}
source = OUT / 'cn-reconstructed-window-v4.json'
reconstruction = json.loads(source.read_text())
dates = reconstruction['target_dates']
assert len(dates) == 47 and dates[0] == '2026-08-19' and dates[-1] == '2026-10-30'
rows = []
replacements = []
additions = []
for day in dates:
    counts = reconstruction['days'][day]['all']
    row = {'date': day, **{f'ma{n}_pct': counts[f'B{n}_pct'] for n in (20, 50, 200)}}
    rows.append(row)
    if day in by_date:
        replacements.append({'date': day, 'before': by_date[day], 'candidate': row})
    else:
        additions.append(row)
assert len(replacements) == 33 and len(additions) == 14
candidate = {**by_date, **{r['date']: r for r in rows}}
payload = [candidate[d] for d in sorted(candidate)]
assert len(payload) == 1302
assert all(candidate[d] == r for d, r in by_date.items() if d not in dates)
candidate_path = OUT / 'cn-history-replacement-preview-v4.json'
candidate_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + '\n')
with (OUT / 'cn-reconstructed-window-v4.csv').open('w', newline='') as f:
    w = csv.writer(f)
    w.writerow(['date', 'was_missing', *[f'old_B{n}' for n in (20, 50, 200)], *[f'new_B{n}' for n in (20, 50, 200)], *[f'E{n}' for n in (20, 50, 200)], 'same_day_available', 'listed_current_codes'])
    for day, row in zip(dates, rows):
        c = reconstruction['days'][day]['all']
        w.writerow([day, day not in by_date, *[by_date.get(day, {}).get(f'ma{n}_pct') for n in (20, 50, 200)], *[row[f'ma{n}_pct'] for n in (20, 50, 200)], *[c[f'E{n}'] for n in (20, 50, 200)], c['same_day_valid_quote'], c['listed_current_code']])

plan = {
    'status': 'review_only_not_installed',
    'target': str(live),
    'before_sha256': hashlib.sha256(before).hexdigest(),
    'candidate_file': candidate_path.name,
    'candidate_sha256': hashlib.sha256(candidate_path.read_bytes()).hexdigest(),
    'source_file': source.name,
    'source_sha256': hashlib.sha256(source.read_bytes()).hexdigest(),
    'existing_records': len(old), 'candidate_records': len(payload),
    'missing_dates_added': additions, 'existing_dates_changed': replacements,
    'other_existing_dates_preserved': len(old) - len(replacements),
    'authorization_boundary': 'Prior approval explicitly retained every existing record. This preview would change 33 existing dates and is not installed under that approval.',
    'qualification': 'Current-list, per-window valid-observation reconstruction; not historical PIT universe or strict-all verified. Missing per-symbol dates are excluded, not filled.',
}
(OUT / 'cn-history-change-plan-v4.json').write_text(json.dumps(plan, ensure_ascii=False, indent=2) + '\n')

font = FontProperties(fname='/System/Library/Fonts/STHeiti Medium.ttc')
plt.rcParams.update({'font.family': font.get_name(), 'axes.unicode_minus': False, 'font.size': 10})
fig, axes = plt.subplots(3, 1, figsize=(12, 8.2), sharex=True)
fig.patch.set_facecolor('#f8fafc')
fig.suptitle('A股宽度：旧记录与同源重建对照', fontproperties=font, fontsize=20, x=.08, ha='left', y=.98, color='#183153')
fig.text(.08, .923, '2026-08-19 — 2026-10-30 · 47个交易日 · 橙点为原图缺测的14日', fontproperties=font, fontsize=11, color='#46576d')
fig.text(.08, .892, '独立候选，尚未替换线上历史；按当前股票名单回看，逐窗口排除新股暖身不足及当日无报价。', fontproperties=font, fontsize=10, color='#68778c')
for ax, n in zip(axes, (20, 50, 200)):
    ax.set_facecolor('white')
    old_y = [by_date.get(d, {}).get(f'ma{n}_pct', float('nan')) for d in dates]
    new_y = [r[f'ma{n}_pct'] for r in rows]
    missing = [i for i, d in enumerate(dates) if d not in by_date]
    ax.plot(range(len(dates)), old_y, color='#9ba6b5', linewidth=2, linestyle='--', label='旧记录（缺日断开）')
    ax.plot(range(len(dates)), new_y, color='#2563eb', linewidth=2.2, label='同源重建候选')
    ax.scatter(missing, [new_y[i] for i in missing], color='#d97706', s=22, zorder=5, label='原缺测日')
    for i in missing:
        ax.axvspan(i-.45, i+.45, color='#f59e0b', alpha=.045, linewidth=0)
    ax.set_ylim(0, 100 if n != 200 else 40)
    ax.set_yticks([0, 20, 40, 60, 80, 100] if n != 200 else [0, 10, 20, 30, 40])
    ax.set_yticklabels([f'{int(t)}%' for t in ax.get_yticks()])
    ax.set_ylabel(f'{n}日宽度', fontproperties=font, color='#183153', labelpad=15)
    ax.grid(axis='y', color='#e4e9f0')
    ax.spines[['top', 'right']].set_visible(False)
    ax.spines[['left', 'bottom']].set_color('#ccd5e0')
    ax.tick_params(colors='#516178', length=0, pad=6)
    ax.set_xlim(-.5, len(dates)+1)
    ax.annotate(f'{new_y[-1]:.2f}%', (len(dates)-1, new_y[-1]), xytext=(8, 4), textcoords='offset points', color='#2563eb', fontsize=10)
axes[0].legend(loc='upper left', ncol=3, frameon=False, prop=font)
ticks = [0, 9, 18, 27, 36, 46]
axes[-1].set_xticks(ticks, [dates[i][5:] for i in ticks])
fig.text(.08, .027, '此图用于核对数据与读图，不表示准确顶底。旧记录保留原件；新候选不与旧值拼接成一条假连续曲线。', fontproperties=font, color='#68778c', fontsize=9)
fig.subplots_adjust(left=.10, right=.94, top=.85, bottom=.09, hspace=.23)
fig.savefig(OUT / 'cn-reconstruction-comparison-v4.png', dpi=170, facecolor=fig.get_facecolor())
fig.savefig(OUT / 'cn-reconstruction-comparison-v4.svg', facecolor=fig.get_facecolor())
print(json.dumps({'preview': str(candidate_path), 'changes': 33, 'added': 14, 'preserved': 1255, 'plot': str(OUT / 'cn-reconstruction-comparison-v4.png')}))
