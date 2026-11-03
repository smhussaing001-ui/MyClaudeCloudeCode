# Original reveal sound design, generated with numpy and synced to the animation in build_comps.py.
# Per galaxy at line start t: whoosh over the camera move (t-0.5 to t+2.2), neon zap while the line
# draws (t to t+1.5), soft tick when the name appears, impact + chime when the line lands (t+1.5).
import numpy as np, wave, json
SR=48000; DUR=40; N=SR*DUR; rng=np.random.default_rng(11)
TIMES=[1.5,5.5,9.5,13.5,18,22,26.5,31]
NAME_DELAY=[.33]*5+[1.92,1.67,.33]
# A minor pentatonic rising with distance, so each reveal lands higher than the last.
CHIME=[440,523.25,587.33,659.25,783.99,880,1046.5,1174.66]
L=np.zeros(N); R=np.zeros(N); events=[]
def put(sig,t,gain=1,pan=0):
    """pan may be a scalar or an array the same length as sig (-1 left .. 1 right)."""
    i=int(t*SR); sig=sig[:max(0,N-i)]
    p=(np.asarray(pan)[:len(sig)] if np.ndim(pan) else pan)
    L[i:i+len(sig)]+=sig*gain*np.cos((p+1)*np.pi/4); R[i:i+len(sig)]+=sig*gain*np.sin((p+1)*np.pi/4)
def lin(n): return np.linspace(0,1,n,endpoint=False)
def band_noise(n,lo,hi):
    F=np.fft.rfft(rng.standard_normal(n)); f=np.fft.rfftfreq(n,1/SR)
    F*=np.exp(-.5*(np.log(np.maximum(f,1)/np.sqrt(lo*hi))/(np.log(hi/lo)/2))**2)
    x=np.fft.irfft(F,n); return x/(np.abs(x).max()+1e-9)
def whoosh(d,lo=180,hi=3200,dirn=1):
    """Noise whose brightness rises then falls, crossfaded across 8 bands, sweeping across the stereo field."""
    n=int(d*SR); x=lin(n); out=np.zeros(n)
    centres=np.geomspace(lo,hi,8); pos=np.sin(np.pi*x**.8)    # 0 -> 1 -> 0 through the band stack
    for k,c in enumerate(centres):
        e=np.exp(-.5*((pos*7-k)/1.2)**2); out+=band_noise(n,c/1.5,c*1.5)*e
    env=np.sin(np.pi*x**.75)**1.6
    return out*env/np.abs(out*env).max(), dirn*(2*x-1)*.75
def zap(d,base=100):
    """Mains-hum neon tube: harmonic buzz with a rising pitch, flicker and sparse crackle."""
    n=int(d*SR); x=lin(n); f=base*(1+.5*x**2); ph=2*np.pi*np.cumsum(f)/SR
    buzz=sum(np.sin(h*ph)/h**.8 for h in (1,2,3,4,5,7,9,11,13))
    flick=.72+.28*np.sign(np.sin(2*np.pi*(13+22*x)*x*d))*rng.random()
    tone=buzz/np.abs(buzz).max()*flick
    crack=(rng.random(n)<.0009+.0018*x).astype(float)
    k=np.exp(-np.arange(int(.004*SR))/(.0007*SR))
    crack=np.convolve(crack*rng.standard_normal(n),k,'same')
    env=np.minimum(x/.05,1)*np.minimum((1-x)/.035,1)
    return (tone*.65+crack*.4)*env
def impact(weight=1.0):
    n=int(1.6*SR); t=np.arange(n)/SR
    sub=np.sin(2*np.pi*np.cumsum(38+70*np.exp(-t/.07))/SR)*np.exp(-t/(.42*weight))
    body=band_noise(n,90,500)*np.exp(-t/.11)*.5
    click=band_noise(n,1500,7000)*np.exp(-t/.012)*.45
    return sub+body+click
def chime(f):
    n=int(2.4*SR); t=np.arange(n)/SR; o=np.zeros(n)
    for r,a,dc in ((1,1,.9),(2.0,.5,.6),(3.01,.28,.4),(4.2,.14,.25),(6.27,.07,.12)):
        o+=a*np.sin(2*np.pi*f*r*t+rng.random()*6)*np.exp(-t/dc)
    return o*np.minimum(t/.002,1)/1.8
def tick():
    n=int(.09*SR); t=np.arange(n)/SR
    return band_noise(n,2500,8000)*np.exp(-t/.009)
def riser(d):
    n=int(d*SR); x=lin(n); ph=2*np.pi*np.cumsum(55*2**(2.5*x))/SR
    return (np.sin(ph)+.5*np.sin(2*ph)+.25*band_noise(n,800,6000)*x)*x**2.2
# Opening: the Milky Way settles in.
s,p=whoosh(1.6,120,1400); put(s,0,.22,p); put(chime(220),.05,.2,0); events.append(('open',0))
for i,t in enumerate(TIMES):
    last=i==7; g=1+.06*i; side=1 if i%2==0 else -1
    d=6 if last else 2.7
    s,p=whoosh(d,120 if last else 200,3600 if last else 3000+200*i,side); put(s,t-.5,(.5 if last else .42)*g,p)
    put(zap(1.5,92+7*i),t,.16*g,side*.25)
    put(tick(),t+NAME_DELAY[i],.17,side*.35)
    put(impact(1+.1*i),t+1.5,.8*g,0)
    put(chime(CHIME[i]),t+1.5,.3,side*.3)
    events+= [('whoosh',t-.5),('zap',t),('name',t+NAME_DELAY[i]),('impact',t+1.5)]
# Finale: long riser into the punch line at 35 s.
put(riser(3.4),31.6,.2,0); put(impact(2.4),35,1.0,0); put(chime(1318.51),35,.26,0); put(chime(220),35,.3,0); events.append(('punch',35))
# Light room reverb so nothing sounds dry and synthetic.
m=int(1.5*SR); tt=np.arange(m)/SR
for ch,name in ((L,'L'),(R,'R')):
    ir=rng.standard_normal(m)*np.exp(-tt/.42)*np.minimum(tt/.008,1); ir/=np.sqrt((ir**2).sum())
    wet=np.fft.irfft(np.fft.rfft(ch,N+m)*np.fft.rfft(ir,N+m),N+m)[:N]
    ch+=wet*.33
fade=np.clip((DUR-np.arange(N)/SR)/1.2,0,1)
L*=fade;R*=fade
def save(path,a,b):
    w=wave.open(path,'wb');w.setnchannels(2);w.setsampwidth(2);w.setframerate(SR)
    w.writeframes((np.dstack([a,b])[0]*32767).astype('int16').tobytes());w.close()
pk=max(abs(L).max(),abs(R).max()); L=np.tanh(L/pk*1.25)*.78; R=np.tanh(R/pk*1.25)*.78
save('assets/audio/sfx_reveals.wav',L,R)
# Music bed: the existing pad, lowered 10 dB and ducked under each impact.
w=wave.open('assets/audio/ambient_pad_original.wav','rb'); P=np.frombuffer(w.readframes(w.getnframes()),'int16').reshape(-1,2)/32767; w.close()
t=np.arange(len(P))/SR; duck=np.ones(len(P))
for x in [v+1.5 for v in TIMES]+[35]:
    duck=np.minimum(duck,1-.5*np.exp(-np.maximum(t-x,0)/.7)*(t>=x-.02))
P=P[:,:]*.316*duck[:,None]
save('assets/audio/pad_ducked.wav',P[:,0],P[:,1])
json.dump(events,open('assets/audio/sfx_events.json','w'))
print('ok',round(pk,2),len(events))
