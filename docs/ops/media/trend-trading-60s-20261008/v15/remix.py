from pathlib import Path
import json,subprocess,os
v=Path(__file__).resolve().parent
p=json.loads((v/'storage-plan.json').read_text());o=Path(p['out']);r=v.parents[4]
b=v.parent/'v7/studio/node_modules/@remotion/compositor-darwin-arm64'
e=os.environ.copy();e['PATH']=str(Path.home()/'.local/bin')+':'+str(b)+':'+e['PATH'];e['TMPDIR']=str(o/'tmp')
ff=str(Path.home()/'.local/bin/ffmpeg');skill=Path.home()/'.codex/skills/ffmpeg-skill/scripts'
def run(args,name):
 assert o.stat().st_dev==p['external_device']
 q=subprocess.run(args,cwd=b,env=e,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
 (o/'logs'/name).write_bytes(q.stdout+b'\n'+q.stderr)
 assert q.returncode==0,(name,q.stderr[-700:])
 return q
# One deterministic audio graph; the old mixed track is never added.
f="[0:a]aresample=48000,aformat=channel_layouts=stereo[a];[1:a]aresample=48000,aformat=channel_layouts=stereo[b];[a][b]acrossfade=d=8:c1=tri:c2=tri,atrim=duration=240,asetpts=PTS-STARTPTS,volume=0.6,afade=t=in:d=0.8,afade=t=out:st=236:d=4[m];[2:a]aformat=channel_layouts=stereo,volume=0.85[s];[m][s]amix=inputs=2:duration=longest:normalize=0,loudnorm=I=-18:TP=-1.5:LRA=14,aresample=48000[out]"
cmd=[ff,'-nostdin','-v','info','-i',p['source_music'],'-i',p['source_music'],'-i',p['source_sfx'],'-filter_complex',f,'-map','[out]','-t','240','-c:a','flac',str(o/'new-mix.flac')]
(o/'制作记录/audio-command.json').write_text(json.dumps(cmd,ensure_ascii=False,indent=2))
run(cmd,'mix.log')
args=['python3',str(skill/'audio.py'),p['source_video'],'--replace',str(o/'new-mix.flac'),'-o',str(o/'trend-history-v15.mp4'),'--json']
run(args+['--dry-run'],'replace-plan.json')
run(args,'replace-result.json')
run([ff,'-v','error','-i',str(o/'trend-history-v15.mp4'),'-f','null','-'],'full-decode.log')
run(['python3',str(skill/'check.py'),str(o/'trend-history-v15.mp4'),'--platform','custom','--max-duration','240.1','--aspect','16:9','--lufs','-18','--content','--json'],'check.json')
for key,path in [('original',p['source_video']),('new',str(o/'trend-history-v15.mp4'))]:
 q=run([ff,'-v','error','-i',path,'-map','0:v:0','-c','copy','-f','hash','-hash','sha256','-'],key+'-video-hash.txt')
 if key=='original':before=q.stdout
 else:assert before==q.stdout,'video elementary stream changed'
print(json.dumps({'output':str(o/'trend-history-v15.mp4'),'full_decode':True,'video_bitstream_unchanged':True},ensure_ascii=False))
