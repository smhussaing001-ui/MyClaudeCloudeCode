# Turns the downloaded stills into soft-edged PNG cutouts, and generates the star field,
# the Malin 1 illustration and the music bed. Run from galaxy-scale-short/.
import numpy as np, wave
from PIL import Image, ImageFilter
SRC='assets/source/'; OUT='assets/cutouts/'
# name: file, centre x/y (fractions), radius x/y (fractions of width), angle deg, output px
SPEC={
 'mw' :('eso1339g.jpg',.50,.50,.47,.47,0,1100),
 'lmc':('eso1914a.jpg',.50,.47,.40,.26,-8,800),
 'smc':('eso1714a.jpg',.51,.50,.34,.24,-30,800),
 'm31':('heic2501a.jpg',.50,.50,.49,.082,0,1280),
 'm33':('heic1901f.jpg',.50,.50,.24,.17,25,800),
 'm64':('opo0404a.jpg',.53,.47,.44,.36,-55,800),
 'ant':('potw1345a.jpg',.50,.50,.48,.48,0,800),
 'm77':('heic1305a.jpg',.48,.47,.46,.44,0,800),
}
for n,(f,cx,cy,rx,ry,ang,px) in SPEC.items():
    im=Image.open(SRC+f).convert('RGB'); w,h=im.size
    Y,X=np.mgrid[0:h,0:w].astype(float); a=np.radians(ang)
    dx,dy=(X-cx*w),(Y-cy*h)
    u=( dx*np.cos(a)+dy*np.sin(a))/(rx*w); v=(-dx*np.sin(a)+dy*np.cos(a))/(ry*w)
    r=np.sqrt(u*u+v*v); t=np.clip((1-r)/.38,0,1); mask=t*t*(3-2*t)
    rgb=np.asarray(im).astype(float)/255
    lum=rgb.max(axis=2)
    alpha=mask*np.clip(lum*3.0+.05,0,1)
    out=np.dstack([rgb,alpha]); o=Image.fromarray((out*255+.5).astype('uint8'),'RGBA')
    bb=Image.fromarray((mask>0.002).astype('uint8')*255).getbbox(); o=o.crop(bb)
    o.thumbnail((px,px),Image.LANCZOS); o.save(OUT+n+'.png'); print(n,o.size)
rng=np.random.default_rng(7)
# Star field: transparent PNG, 1.5x frame so it can scale slowly.
W,H=1620,2880; S=np.zeros((H,W,4))
for i in range(5200):
    x,y=rng.integers(0,W),rng.integers(0,H); b=rng.power(5)*.95*rng.random()**1.5+.04
    tint=np.array([1,1,1])+rng.normal(0,.09,3)
    S[y,x,:3]=np.clip(tint,0,1); S[y,x,3]=b
stars=Image.fromarray((S*255).astype('uint8'),'RGBA')
glow=np.zeros((H,W,4))
for i in range(90):
    x,y=rng.integers(8,W-8),rng.integers(8,H-8); glow[y,x]=[1,1,1,1]
gl=Image.fromarray((glow*255).astype('uint8'),'RGBA').filter(ImageFilter.GaussianBlur(1.6))
g=np.asarray(gl).astype(float)/255; g[...,3]=np.clip(g[...,3]*6,0,1); g[...,:3]=1
s=np.asarray(stars).astype(float)/255; a=np.maximum(s[...,3],g[...,3])
Image.fromarray((np.dstack([np.where(g[...,3:]>s[...,3:],g[...,:3],s[...,:3]),a])*255).astype('uint8'),'RGBA').save(OUT+'stars.png')
# Malin 1 illustration: small bright core inside a huge, faint two-arm disc.
N=800; Y,X=np.mgrid[-1:1:N*1j,-1:1:N*1j]; Yt=Y/.72
r=np.hypot(X,Yt); th=np.arctan2(Yt,X)
arms=(np.cos(2*th-7.5*np.log(r+.04))*.5+.5)**2
n=np.asarray(Image.fromarray((rng.random((200,200))*255).astype('uint8')).resize((N,N),Image.BICUBIC)).astype(float)/255
disc=np.exp(-r*3.1)*(.45+.55*arms)*(.75+.5*n)
core=np.exp(-(r/.035)**2)*1.5+np.exp(-(r/.11)**2)*.45
lum=np.clip(disc*.9+core,0,1)
rgb=np.dstack([lum*.78+core.clip(0,1)*.22,lum*.87+core.clip(0,1)*.13,lum])
edge=np.clip((1-r)/.3,0,1); alpha=np.clip(lum*3,0,1)*edge
Image.fromarray((np.dstack([np.clip(rgb,0,1),alpha])*255).astype('uint8'),'RGBA').save(OUT+'malin1_illustration.png')
# Music bed: slow additive pad with a rising tension at the final zoom. 40 s, 48 kHz stereo.
sr=48000; T=40; t=np.arange(sr*T)/sr
chords=[(55,82.5,110,164.8,220),(49,73.4,98,146.8,196),(43.65,65.4,87.3,130.8,174.6),(55,82.5,110,164.8,247)]
L=np.zeros_like(t);R=np.zeros_like(t); seg=10.0
for c,ch in enumerate(chords):
    e=np.clip(1-np.abs((t-(c+.5)*seg)/(seg*.68)),0,1)**.8
    for k,f in enumerate(ch):
        p=rng.random(2)*6.28; a=.2/(1+.35*k)
        L+=e*a*(np.sin(2*np.pi*f*.998*t+p[0])+.3*np.sin(2*np.pi*f*2.003*t+p[1]))
        R+=e*a*(np.sin(2*np.pi*f*1.002*t+p[1])+.3*np.sin(2*np.pi*f*1.997*t+p[0]))
swell=np.clip((t-28)/7,0,1)**2*(1-np.clip((t-37)/3,0,1))
for f in (880,1318.5,1760):
    L+=swell*.03*np.sin(2*np.pi*f*t);R+=swell*.03*np.sin(2*np.pi*f*1.001*t)
fade=np.clip(t/2,0,1)*np.clip((T-t)/3,0,1)*(.7+.3*np.clip((t-20)/15,0,1))
L*=fade;R*=fade;m=max(abs(L).max(),abs(R).max());A=(np.dstack([L,R])[0]/m*.6*32767).astype('int16')
w=wave.open('assets/audio/ambient_pad_original.wav','wb');w.setnchannels(2);w.setsampwidth(2);w.setframerate(sr);w.writeframes(A.tobytes());w.close()
