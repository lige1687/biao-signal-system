"""Check a shared audiovisual cue plan. Standard library only."""
import argparse, json, math
from pathlib import Path

def validate(plan):
    errors=[]
    fps=plan.get('fps',0);duration=plan.get('duration',0)
    if not isinstance(fps,(int,float)) or not math.isfinite(fps) or fps<=0:
        errors.append('fps must be positive and finite');fps=0
    if not isinstance(duration,(int,float)) or not math.isfinite(duration) or duration<=0:
        errors.append('duration must be positive and finite');duration=0
    scenes=plan.get('scenes',[]);ids={};previous=0
    if not scenes:errors.append('no scenes')
    for scene in scenes:
        ident=scene.get('id');start=scene.get('start');end=scene.get('end')
        if not ident or ident in ids:errors.append('missing or duplicate scene id')
        ids[ident]=scene
        if not all(isinstance(x,(int,float)) and math.isfinite(x) for x in (start,end)):
            errors.append(f'{ident}: invalid interval');continue
        if abs(start-previous)>1e-6:errors.append(f'{ident}: gap or overlap at {start}, expected {previous}')
        if end<=start or end>duration+1e-6:errors.append(f'{ident}: invalid scene duration')
        previous=end
        if not scene.get('claim') or not scene.get('action'):errors.append(f'{ident}: missing evidence or action')
    if abs(previous-duration)>1e-6:errors.append('scene coverage does not reach duration')
    for cue in plan.get('cues',[]):
        t=cue.get('time');s=ids.get(cue.get('scene'))
        if not isinstance(t,(int,float)) or not math.isfinite(t) or not 0<=t<duration:errors.append('cue outside video');continue
        if not s or not s['start']<=t<s['end']:errors.append(f'cue {t}: outside referenced scene')
        if not cue.get('purpose'):errors.append(f'cue {t}: missing purpose')
    if fps>0 and duration>0 and abs(round(fps*duration)-fps*duration)>1e-6:errors.append('duration is not whole frames')
    return errors

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('plan',type=Path);args=parser.parse_args()
    data=json.loads(args.plan.read_text());errors=validate(data)
    print(json.dumps({'passed':not errors,'errors':errors,'frames':round(data.get('fps',0)*data.get('duration',0))},ensure_ascii=False))
    raise SystemExit(bool(errors))
