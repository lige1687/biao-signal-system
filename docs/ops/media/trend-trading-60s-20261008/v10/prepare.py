from pathlib import Path
import json,shutil,random,math,wave,struct
r=Path(__file__).resolve().parent;o=Path(json.loads((r/'storage-plan.json').read_text())['output'])
shutil.copy2(r.parent/'v7/studio/public/oxygen-garden.m4a',o/'assets/music.m4a')
rate=48000;n=rate*15;signal=[0.0]*n;rng=random.Random(17)
for sec in [3.66,6.9,8.9,10.9,12.53]:
 for j in range(int(.46*rate)):
  t=j/rate;k=int(sec*rate)+j
  signal[k]+=.22*math.sin(2*math.pi*(66*t-24*t*t))*math.exp(-t*15)
 low=0
 for j in range(int(.5*rate)):
  t=j/rate;low=.91*low+.09*rng.uniform(-1,1);k=int((sec-.35)*rate)+j
  signal[k]+=.35*low*math.sin(math.pi*j/(.5*rate))**2
for sec in [.3,1.0,1.47,7.6,9.33,11.3]:
 for j in range(int(.11*rate)):
  t=j/rate;signal[int(sec*rate)+j]+=.065*math.sin(2*math.pi*880*t)*math.exp(-t*65)
with wave.open(str(o/'assets/sfx.wav'),'wb') as w:
 w.setparams((1,2,rate,n,'NONE','not compressed'));w.writeframes(struct.pack('<%dh'%n,*[int(v*32767) for v in signal]))
(r/'cues.json').write_text(json.dumps({'duration_seconds':15,'fps':30,'cuts':[{'at':0,'action':'报价机缓推、标题错峰出现'},{'at':3.66,'action':'水平推移转入道氏思想'},{'at':4.67,'action':'价格轨迹从左向右画出'},{'at':6.9,'action':'金色主要趋势生长'},{'at':8.9,'action':'珊瑚色次级回调'},{'at':10.9,'action':'青色日常波动'},{'at':12.53,'action':'总结句，停留到15秒'}],'music':'Oxygen Garden — Chris Zabriskie, CC BY 4.0, source segment 42–57 seconds; volume envelope','sfx':'Original synthesized sweep, low impact, soft ticks; fixed seed 17'},ensure_ascii=False,indent=2))
print(o)
