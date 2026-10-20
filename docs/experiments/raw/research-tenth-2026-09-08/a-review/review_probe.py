"""Review a-contract evidential strength without changing sealed artifacts."""
from pathlib import Path
import sys, json, hashlib
from unittest.mock import patch
from dataclasses import asdict
import pandas as pd
import numpy as np
ROOT=Path(__file__).resolve().parents[5]
OUT=Path(__file__).resolve().parent
PKG=ROOT/'docs/experiments/raw/research-eighth-2026-09-08/b-research-fix/research-package'
sys.path.insert(0,str(PKG/'src'))
from lei_signal.rules import first_ma_pullback as a
from lei_signal.rules.strict_structure import detect_strict_structures

def enc(obj):
    if hasattr(obj,'isoformat'): return obj.isoformat()
    if hasattr(obj,'value'): return obj.value
    if isinstance(obj,np.generic): return obj.item()
    raise TypeError(type(obj).__name__)

# Exactly the original fixture source confirms the given Structure was injected.
old=ROOT/'docs/experiments/raw/research-tenth-2026-09-08/a-contract/probe.py'
# Three monotonically rising, non-contained final ranges create a true bottom.
# After confirmation a later low genuinely breaks its reference low, but the
# closing price stays above the current pullback's previous minimum.
rows=[(9.,10.,8.,9.)]*20+[(9.2,9.8,9.,9.4),(9.9,10.3,9.3,10.2),(10.2,10.8,9.7,10.6),(10.1,10.7,7.5,10.4)]
f=pd.DataFrame(rows,columns=['open','high','low','close'],index=pd.bdate_range('2024-01-01',periods=len(rows)))
f['volume']=1000.
f['signal_color']='green'
for n,sm,em in [(20,9.2,8.9),(60,8.,8.),(120,7.,7.)]:
    f[f'sma{n}']=sm;f[f'ema{n}']=em+np.arange(len(f))*.001;f[f'close_lag{n}']=8.5
clock=[2]*len(f);clock[22]=3
structures=detect_strict_structures(f)
with patch.object(a,'clock_series',lambda frame:pd.Series(clock[:len(frame)],index=frame.index)),patch.object(a,'weekly_env_series',lambda frame:pd.Series(True,index=frame.index)):
    events=a.detect_first_ma_pullback_events(f,'SYNTHETIC')
confirmed=[e for e in events if e.evidence['sub_rule']==a.SUB_RULE_CONFIRMED]
byid={s.structure_id:s for s in structures}
stale=[]
for e in confirmed:
    s=byid.get(e.evidence.get('a3_structure_id'))
    if s is not None and s.invalidated_date is not None and s.invalidated_date<=e.available_date:
        stale.append({'event':asdict(e),'structure':asdict(s)})
assert stale
# No close<=EMA20 to >EMA20 crossings; an alternative EMA reclaim cannot explain entries.
reclaims=(f.close.shift(1)<=f.ema20.shift(1))&(f.close>f.ema20)
assert not reclaims.any()
for pair in stale:
    s=pair['structure']
    assert f.loc[pd.Timestamp(s['invalidated_date']),'low']<s['reference_price']
    assert pair['event']['available_date']==f.index[23].date()
report={
 'original_fixture_review':{
  'source_sha256':hashlib.sha256(old.read_bytes()).hexdigest(),
  'invalidation_predicate_compatible':True,
  'reason':'原夹具指定reference_price=9.0、失效日low=8.8，因此符合确认后low<reference_price的失效判据。',
  'full_structure_trajectory_compatible':False,
  'limitation':'原夹具reference_date=第18日，但该日真实low=8.0，不是指定9.0；结构对象和确认轨迹由夹具直接指定，不能单独证明真实strict输出可达。原案例只证明A信任已标失效对象。'},
 'new_actual_strict_reachability':{
  'patches':['clock_series固定环境序列，第22日暂离二类、第23日回二类','weekly_env_series固定True'],
  'not_patched':['detect_strict_structures','detect_first_ma_pullback_events','ATR','规则参数'],
  'limitations':'OHLC有效，strict输出完全由这些OHLC生成；SMA/EMA/抵扣价为手工给定的上游派生列，时钟和周线为隔离依赖。因此证明strict→A状态可达，不宣称完整compute_features/weekly/clock自然生成链已复现。',
  'input':f.reset_index(names='date').to_dict('records'),
  'clock':clock,'actual_structures':[asdict(s) for s in structures],
  'stale_confirmed':stale,
  'ema_reclaim_count':int(reclaims.sum()),
  'state_explanation':['2024-01-29触及SMA20，记录回撤最低9.0。','2024-01-31真实strict底部确认，reference_price=8.0；当日時钟不满足，A仍缓存底部ID但不确认入场。','2024-02-01最低7.5跌破底部参考8.0，真实strict标底部失效；收盘10.4没有跌破此前回撤最低9.0，故A5收盘失效未触发。','时钟恢复后A不重新检查缓存ID，仍以该失效底部作为唯一A3来源，确认两种入场；失效价写入7.5。']},
 'weekly_false_touch_interpretation':{
  'direct_observation':'原例产生weekly_bull_env=false的触碰，confirmed_count=0。',
  'established_effect':'触碰观察记录与文案不一致；可记录本不应开始的回撤周期。',
  'not_established':'未证明周线不满足时直接入场；代码确认分支明确要求weekly_ok。也未在原例证明随后实际入场日期/首次标签变化。',
  'potential_only':'若该触碰后来失败，可能消耗首次标记；若以后周线恢复，已开启周期可能继续走入场分支；需另例才能当作实测结论。'},
 'verdict':'原stale夹具证据降级为缓存信任检查；新增真实strict→A依赖隔离反例补足结构对象可达性，但不越界宣称完整真实指标链。A的未来K线历史改写阻断结论不依赖此补充。'}
(OUT/'review-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,default=enc)+'\n')
print(json.dumps({'stale_confirmed_count':len(stale),'strict_bottom':[(s.structure_id,str(s.confirmed_date),s.reference_price,str(s.invalidated_date)) for s in structures if s.side=='bottom'],'ema_reclaim_count':int(reclaims.sum())},ensure_ascii=False,indent=2))
