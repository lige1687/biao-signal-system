import math,random,wave,struct,pathlib
root=pathlib.Path(__file__).parent
rate=24000; n=rate*60
signal=[0.0]*n
rng=random.Random(7)
# Original sound design: short filtered-noise sweeps and low impacts at six edits.
for sec in [3,11,20,29,38,47,56]:
    start=int((sec-.32)*rate)
    low=0
    for j in range(int(.70*rate)):
        t=j/rate;low=.88*low+.12*rng.uniform(-1,1)
        envelope=math.sin(min(1,t/.42)*math.pi/2)**3*math.exp(-max(0,t-.32)*14)
        signal[start+j]+=.24*low*envelope
    for j in range(int(.52*rate)):
        t=j/rate
        signal[int(sec*rate)+j]+=.15*math.sin(2*math.pi*(58*t-17*t*t))*math.exp(-t*12)
for sec in [4.2,5.9,7.6,13.4,15.0,16.6,22.6,25.3,32.3,33.6,35.0,41.7,43.2,44.5,49.0,49.8,50.6,51.4,56.9]:
    for j in range(int(.1*rate)):
        t=j/rate
        signal[int(sec*rate)+j]+=.07*math.sin(2*math.pi*820*t)*math.exp(-t*65)
with wave.open(str(root/'sfx.wav'),'wb') as w:
    w.setparams((1,2,rate,n,'NONE','not compressed'))
    w.writeframes(struct.pack('<%dh'%n,*[int(max(-1,min(1,v))*32767) for v in signal]))
