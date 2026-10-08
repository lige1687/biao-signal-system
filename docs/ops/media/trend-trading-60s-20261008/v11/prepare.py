from pathlib import Path
import json,shutil,random,math,wave,struct
r=Path(__file__).resolve().parent;o=Path(json.loads((r/'storage-plan.json').read_text())['output'])
shutil.copy2(r.parent/'v7/studio/public/oxygen-garden.m4a',o/'assets/music.m4a')
rate=48000;n=rate*60;signal=[0.0]*n;rng=random.Random(17)
for sec in [3.66,6.9,8.9,10.9,12.53,15,24,32,40,48,56]:
 for j in range(int(.46*rate)):
  t=j/rate;k=int(sec*rate)+j
  signal[k]+=.22*math.sin(2*math.pi*(66*t-24*t*t))*math.exp(-t*15)
 low=0
 for j in range(int(.5*rate)):
  t=j/rate;low=.91*low+.09*rng.uniform(-1,1);k=int((sec-.35)*rate)+j
  signal[k]+=.35*low*math.sin(math.pi*j/(.5*rate))**2
for sec in [.3,1.0,1.47,7.6,9.33,11.3,17.83,19.1,20.37,27.77,29.27,33,34,35,36.67,41.5,42.23,42.97,43.7,45.4,49,49.83,50.67,51.5,53.2,57.13]:
 for j in range(int(.11*rate)):
  t=j/rate;signal[int(sec*rate)+j]+=.065*math.sin(2*math.pi*880*t)*math.exp(-t*65)
with wave.open(str(o/'assets/sfx.wav'),'wb') as w:
 w.setparams((1,2,rate,n,'NONE','not compressed'));w.writeframes(struct.pack('<%dh'%n,*[int(v*32767) for v in signal]))
