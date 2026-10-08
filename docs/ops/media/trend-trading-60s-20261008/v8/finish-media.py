import subprocess,pathlib,json,hashlib
r=pathlib.Path(__file__).resolve().parent
ff='/Users/yongbiaoli/.local/bin/ffmpeg'
probe=str(r/'studio/node_modules/@remotion/compositor-darwin-arm64/ffprobe')
master=r/'trend-chronicle-v8-4k.mp4';preview=r/'trend-chronicle-v8-1080.mp4'
def run(args):subprocess.run(args,check=True)
def check(path):
 d=json.loads(subprocess.check_output([probe,'-v','error','-show_streams','-show_format','-of','json',str(path)],cwd=str(pathlib.Path(probe).parent)))
 with (r/(path.stem+'-decode.log')).open('w') as log:subprocess.run([ff,'-hide_banner','-v','error','-i',str(path),'-f','null','-'],stderr=log,check=True)
 v=next(x for x in d['streams'] if x['codec_type']=='video');a=next(x for x in d['streams'] if x['codec_type']=='audio');assert v['nb_frames']=='1800';assert abs(float(d['format']['duration'])-60)<.1
 return dict(path=path.name,width=v['width'],height=v['height'],frames=v['nb_frames'],fps=v['r_frame_rate'],audio=a['codec_name'],duration=d['format']['duration'],sha256=hashlib.sha256(path.read_bytes()).hexdigest(),full_decode=True)
mastercheck=check(master);assert mastercheck['width']==3840
run([ff,'-hide_banner','-v','error','-i',str(master),'-vf','scale=1920:1080','-c:v','libx264','-preset','fast','-crf','20','-c:a','copy','-movflags','+faststart',str(preview)])
previewcheck=check(preview)
run([ff,'-hide_banner','-v','error','-ss','18','-i',str(master),'-frames:v','1','-q:v','2',str(r/'poster.jpg')])
select='+'.join('eq(n\\,%s)'%x for x in [80,285,570,825,1095,1365,1635,1770])
run([ff,'-hide_banner','-v','error','-i',str(preview),'-vf',f'select={select},scale=640:-1,tile=4x2','-frames:v','1',str(r/'final-contact.jpg')])
(r/'validation.json').write_text(json.dumps({'master':mastercheck,'preview':previewcheck,'browser_playback':'pending','subjective_user_acceptance':'pending'},ensure_ascii=False,indent=2));print(json.dumps([mastercheck,previewcheck]))
