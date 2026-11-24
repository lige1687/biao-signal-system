"""Descriptive increment conditional on current 2-sigma state and price baseline."""
import json, pathlib, statistics as st, random, collections, hashlib
P=pathlib.Path(__file__).resolve().parent
# Frozen clarification of the planned mild-event comparison, no future event grouping.
method={'question':'Do k crossings inside the existing2sigma envelope add information beyond B and current2sigma state?', 'k':[1.,1.5], 'h':63, 'events':'first k crossing whose contemporaneous abs(z)<2', 'controls':'same B cell, inside2sigma now, not a first k crossing now, >=5 controls', 'uncertainty':'2000 resamples of original two-year calendar blocks; common original-event cells; no future-window event exclusion', 'stage':'descriptive reused history; planned increment question made explicit after core statistics; no parameter selection'}
(P/'increment-method.json').write_text(json.dumps(method,indent=2))
def mean(xs):return st.fmean(xs) if xs else None
def q(xs,p):
 xs=sorted(xs);pos=(len(xs)-1)*p;a=int(pos);return xs[a]+(xs[min(a+1,len(xs)-1)]-xs[a])*(pos-a) if xs else None
def match(es,cs,minn=5):
 cells=collections.defaultdict(list)
 for r in cs:cells[r['B']].append(r['outcomes']['63']['returnPct'])
 valid={k:mean(v) for k,v in cells.items() if len(v)>=minn};events=[r for r in es if r['B'] in valid]
 if not events:return None
 sign=lambda r:1 if r['firstEntry']=='upper' else -1
 er=mean([sign(r)*r['outcomes']['63']['returnPct'] for r in events]);cr=mean([sign(r)*valid[r['B']] for r in events])
 return {'n':len(events),'event':er,'control':cr,'increment':er-cr,'dates':[r['date'] for r in events]}
out={}
for k in [1.,1.5]:
 rows=json.loads((P/f'sigma-{k}'/'eligible-weeks.json').read_text());rows=[r for r in rows if r['B'] and r['outcomes']['63']]
 mild=[r for r in rows if r['sigma'] and abs((r['erp']-r['middle'])/r['sigma'])<2]
 cs=[r for r in mild if r['firstEntry'] is None];blocks=sorted(set(r['block'] for r in rows));out[str(k)]={}
 for side in ['upper','lower']:
  es=[r for r in mild if r['firstEntry']==side];m=match(es,cs);common=set(m['dates'] if m else []);vals=[];rng=random.Random(20261101)
  for _ in range(2000):
   drawn=[rng.choice(blocks) for b in blocks];e=[r for b in drawn for r in es if r['block']==b and r['date'] in common];c=[r for b in drawn for r in cs if r['block']==b];v=match(e,c,1)
   if v and v['n']==len(e):vals.append(v['increment'])
  out[str(k)][side]={'candidateN':len(es),'matched':m,'interval':[q(vals,.025),q(vals,.975)],'validResamples':len(vals),'meanActualReturn':mean([r['outcomes']['63']['returnPct'] for r in es]),'positiveN':sum(r['outcomes']['63']['returnPct']>0 for r in es),'adverseMinMean':mean([r['outcomes']['63']['minMovePct'] for r in es]),'favorableMaxMean':mean([r['outcomes']['63']['maxMovePct'] for r in es])}
(P/'increment-results.json').write_text(json.dumps(out,ensure_ascii=False,indent=2))
print(json.dumps(out,ensure_ascii=False))
