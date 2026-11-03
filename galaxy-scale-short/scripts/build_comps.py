# Writes 8 consecutive 300-frame Fusion .comp files (5 s each, 60 fps, 1080x1920).
# Resolve's scripting API can't extend a Fusion comp clip beyond 300 frames, so the film is
# split; every comp evaluates the same camera at global time (time+T0), so joins are continuous.
import math, os, json
from PIL import Image, ImageFont
ROOT=os.path.abspath('.').replace('\\','/')
W,H,FPS=1080,1920,60; SEG=300; NSEG=8; TOTAL=SEG*NSEG
GOLD=(1.0,.88,.42)
NEON=(1.0,.16,.12); ACCENT=(1.0,.32,.27)
DISPLAY='Milker'; BODY='Bebas Neue'
# Galaxy motion: spin deg/s, float px at arrival, phase. Edge-on Andromeda barely turns.
MOVE={'lmc':(3,10,0),'smc':(-3,10,1.3),'m31':(.8,10,2.1),'m33':(9,8,.7),'m64':(5,7,3.1),'ant':(3,8,4.4),'m77':(8,7,5.2),'malin1_illustration':(10,8,2.8)}
MW_SPIN=10
# file, label, distance, t(s), zoom, MW screen pos, polar angle, screen radius, screen size
ST=[
 ('lmc','Large Magellanic Cloud','163,000 light-years',1.5,.62,(300,900),32,640,380),
 ('smc','Small Magellanic Cloud','200,000 light-years',5.5,.42,(210,950),-24,650,300),
 ('m31','Andromeda Galaxy','2,500,000 light-years',9.5,.22,(160,1000),-42,800,470),
 ('m33','Triangulum Galaxy','2,700,000 light-years',13.5,.16,(150,1000),8,800,270),
 ('m64','Black Eye Galaxy','17,000,000 light-years',18,.055,(130,1000),52,600,180),
 ('ant','Antennae Galaxies','45,000,000 light-years',22,.03,(120,1000),-58,730,180),
 ('m77','Messier 77','47,000,000 light-years',26.5,.02,(120,960),66,560,170),
 ('malin1_illustration','Malin 1 (illustration)','1,190,000,000 light-years',31,.0035,(110,960),-4,850,240),
]
MW_PX=860; IMG={}
for n in ['mw','stars']+[s[0] for s in ST]: IMG[n]=Image.open(f'assets/cutouts/{n}.png').size
FW=lambda t,px,f:ImageFont.truetype(os.environ['LOCALAPPDATA']+'/Microsoft/Windows/Fonts/'+f,px).getlength(t)
# Camera states: (time s, log zoom, mx, my). Each stage eases from t-0.5 to t+2.2 (final: t+5).
KEYS=[(0,0.0,540,960)]
for i,s in enumerate(ST):
    KEYS.append((s[3]-.5,KEYS[-1][1],KEYS[-1][2],KEYS[-1][3]))
    KEYS.append((s[3]+(5.5 if i==7 else 2.2),math.log(s[4]),s[5][0],s[5][1]))
def cam(f):
    t=f/FPS
    if t<=KEYS[0][0]: return KEYS[0][1:]
    for a,b in zip(KEYS,KEYS[1:]):
        if t<=b[0]:
            x=(t-a[0])/(b[0]-a[0]) if b[0]>a[0] else 1; x=x*x*(3-2*x)
            return tuple(a[j]+(b[j]-a[j])*x for j in (1,2,3))
    return KEYS[-1][1:]
KEYS.append((40,KEYS[-1][1]-.14,KEYS[-1][2],KEYS[-1][3]))  # keep drifting out through the ending
def num(v): return ('%.6f'%v).rstrip('0').rstrip('.')
def expr(e): return 'Input { Expression = %s, }'%json.dumps(e)
def ramp(a,b,T0,sm=False):
    x=f'min(1,max(0,((time+{T0})-{a})/{b-a}))'
    return f'({x}*{x}*(3-2*{x}))' if sm else x
def wpt(x,y): return f'Point((CAM.Angle+({num(x)})*CAM.Size)/{W},(CAM.Aspect+({num(y)})*CAM.Size)/{H})'
FRAME=f'Width=Input{{Value={W}}}, Height=Input{{Value={H}}}, UseFrameFormatSettings=Input{{Value=1}}'
TITLE_PX=min(48,48*980/FW('How far away are other galaxies?',48,'Milker.otf'))
PUNCH_PX=min(50,50*980/FW('Its light left 1.19 billion years ago',50,'Milker.otf'))
def SINE(T,rate,ph): return f'sin({T}*{rate}+{ph})'
NAME_PX=34
PX=1/1080  # Text+ Size unit: Size 1 is roughly a 1080 px font height
def build(k):
    T0=k*SEG; end=T0+SEG; tools=[]; last=['Bg']; n=[0]; add=tools.append
    # CAM is an unconnected Transform used as a data holder: Size = zoom, Angle = MW x px, Aspect = MW y px.
    zs,xs,ys=[],[],[]
    for f in range(0,SEG+5,5):
        z,x,y=cam(T0+f)
        zs.append(f'[{f}]={{{math.exp(z):.7f},Flags={{Linear=true}}}}')
        xs.append(f'[{f}]={{{x:.3f},Flags={{Linear=true}}}}')
        ys.append(f'[{f}]={{{y:.3f},Flags={{Linear=true}}}}')
    for nm,arr in (('CamZ',zs),('CamX',xs),('CamY',ys)):
        add(f'{nm} = BezierSpline {{ SplineColor={{Red=200,Green=200,Blue=200}}, KeyFrames={{{",".join(arr)}}} }},')
    add('CAM = Transform { Inputs={ Size=Input{SourceOp="CamZ",Source="Value"}, Angle=Input{SourceOp="CamX",Source="Value"}, Aspect=Input{SourceOp="CamY",Source="Value"} } },')
    add(f'Bg = Background {{ Inputs={{ {FRAME}, Type=Input{{Value=FuID{{"Gradient"}}}}, Start=Input{{Value={{0.5,1}}}}, End=Input{{Value={{0.5,0}}}}, Gradient=Input{{Value=Gradient{{Colors={{[0]={{0.0,0.0,0.01,1}},[0.45]={{0.005,0.015,0.05,1}},[1]={{0.03,0.08,0.2,1}}}}}}}} }} }},')
    def merge(fg,center=None,size=None,blend=None,angle=None,additive=False):
        n[0]+=1; m=f'Mg{n[0]}'
        I=[f'Background=Input{{SourceOp="{last[0]}",Source="Output"}}',f'Foreground=Input{{SourceOp="{fg}",Source="Output"}}']
        if center: I.append('Center='+expr(center))
        if size: I.append('Size='+expr(size))
        if blend: I.append('Blend='+expr(blend))
        if angle: I.append('Angle='+expr(angle))
        if additive: I.append('Gain=Input{Value=0}')
        add(f'{m} = Merge {{ Inputs={{ {",".join(I)} }} }},'); last[0]=m
    def loader(tag,file):
        fn=f'{ROOT}/assets/cutouts/{file}.png'
        add(f'{tag} = Loader {{ Clips={{Clip{{ID="Clip1",Filename={json.dumps(fn)},FormatID="PNGFormat",StartFrame=-1,LengthSetManually=true,TrimIn=0,TrimOut=0,ExtendFirst=0,ExtendLast=0,Loop=1,AspectMode=0,Depth=0,TimeCode=0,GlobalStart=-2000,GlobalEnd=2000}}}} }},')
    def text(tag,txt,px,font=BODY,rgb=(1,1,1),angle=0,center=None):
        I=[FRAME,'StyledText=Input{Value=%s}'%json.dumps(txt,ensure_ascii=False),f'Font=Input{{Value="{font}"}}','Style=Input{Value="Regular"}',
           f'Red1=Input{{Value={rgb[0]}}}',f'Green1=Input{{Value={rgb[1]}}}',f'Blue1=Input{{Value={rgb[2]}}}']
        I.append('Size='+(expr(px) if isinstance(px,str) else f'Input{{Value={num(px)}}}'))
        if angle: I.append(f'AngleZ=Input{{Value={num(angle)}}}')
        if center: I.append('Center='+(expr(center) if isinstance(center,str) else f'Input{{Value={{{center[0]},{center[1]}}}}}'))
        add(f'{tag} = TextPlus {{ Inputs={{ {",".join(I)} }} }},')
    loader('Stars','stars')
    S0=W/IMG['stars'][0]
    merge('Stars',size=f'{S0:.5f}*(1.28-0.28*(time+{T0})/{TOTAL})')
    live=[]
    for s in ST:
        name,label,dist,t,z,m,ang,R,px=s; a=math.radians(ang); r=R/z
        wx,wy=r*math.cos(a),r*math.sin(a); f0=int(t*FPS)
        if f0-60>=end: continue
        tag=name.split('_')[0].upper(); live.append((s,wx,wy,f0,tag))
        p=ramp(f0,f0+90,T0,True)
        add(f'R{tag} = RectangleMask {{ Inputs={{ MaskWidth=Input{{Value={W}}}, MaskHeight=Input{{Value={H}}}, Center={expr(f"Point((CAM.Angle+({num(wx)})*CAM.Size*0.5*{p})/{W},(CAM.Aspect+({num(wy)})*CAM.Size*0.5*{p})/{H})")}, Width={expr(f"{num(r)}*CAM.Size*{p}/{W}")}, Height=Input{{Value={1.5/W:.6f}}}, Angle=Input{{Value={ang}}} }} }},')
        add(f'L{tag} = Background {{ Inputs={{ {FRAME}, TopLeftRed=Input{{Value={NEON[0]}}}, TopLeftGreen=Input{{Value={NEON[1]}}}, TopLeftBlue=Input{{Value={NEON[2]}}}, EffectMask=Input{{SourceOp="R{tag}",Source="Mask"}} }} }},')
        add(f'E{tag} = EllipseMask {{ Inputs={{ MaskWidth=Input{{Value={W}}}, MaskHeight=Input{{Value={H}}}, Center={expr(f"Point((CAM.Angle+({num(wx)})*CAM.Size*{p})/{W},(CAM.Aspect+({num(wy)})*CAM.Size*{p})/{H})")}, Width=Input{{Value={7/W:.6f}}}, Height=Input{{Value={7/W:.6f}}} }} }},')
        add(f'T{tag} = Background {{ Inputs={{ {FRAME}, TopLeftRed=Input{{Value=1}}, TopLeftGreen=Input{{Value=0.45}}, TopLeftBlue=Input{{Value=0.4}}, EffectMask=Input{{SourceOp="E{tag}",Source="Mask"}} }} }},')
    loader('Imw','mw')
    merge('Imw',center=wpt(0,0),size=f'{MW_PX/IMG["mw"][0]:.5f}*CAM.Size',angle=f'{MW_SPIN}*(time+{T0})/{FPS}')
    for s,wx,wy,f0,tag in live:
        loader('I'+tag,s[0])
        spin,fl,ph=MOVE[s[0]]; z=s[4]; rev=ramp(f0-30,f0+90,T0,True); T=f'((time+{T0})/{FPS})'
        # float gently, and scale up while spinning down as the line reaches the galaxy
        cx=f'{num(wx)}+{num(fl/z)}*{SINE(T,.55,ph)}'; cy=f'{num(wy)}+{num(fl*.8/z)}*{SINE(T,.42,ph+1.4)}'
        merge('I'+tag,center=f'Point((CAM.Angle+({cx})*CAM.Size)/{W},(CAM.Aspect+({cy})*CAM.Size)/{H})',
              size=f'{s[8]/max(IMG[s[0]])/z:.5f}*CAM.Size*(0.55+0.45*{rev})',blend=ramp(f0-30,f0+24,T0),
              angle=f'{spin}*{T}+{140*(1 if spin>0 else -1)}*(1-{rev})')
    # Lines sit above the galaxies so they visibly start at the Milky Way's centre.
    if live:
        keep=last[0]
        add(f'LBase = Background {{ Inputs={{ {FRAME}, TopLeftAlpha=Input{{Value=0}}, TopLeftRed=Input{{Value=0}}, TopLeftGreen=Input{{Value=0}}, TopLeftBlue=Input{{Value=0}} }} }},')
        last[0]='LBase'
        for s,wx,wy,f0,tag in live:
            merge(f'L{tag}',blend=ramp(f0-3,f0+3,T0))
            merge(f'T{tag}',blend=f'{ramp(f0,f0+6,T0)}*(1-{ramp(f0+84,f0+100,T0)})')
        lines=last[0]; last[0]=keep
        for b,bs,g in (('Near',2.5,1.6),('Far',10,1.8)):
            add(f'Glow{b} = Blur {{ Inputs={{ XBlurSize=Input{{Value={bs}}}, Input=Input{{SourceOp="{lines}",Source="Output"}} }} }},')
            add(f'Gain{b} = ColorGain {{ Inputs={{ GainRed=Input{{Value={g}}}, GainGreen=Input{{Value={g*.35:.2f}}}, GainBlue=Input{{Value={g*.35:.2f}}}, Input=Input{{SourceOp="Glow{b}",Source="Output"}} }} }},')
            merge(f'Gain{b}',additive=True)
        merge(lines,additive=True)
    # Labels live in world space, so they shrink with the zoom-out like the galaxies do.
    for s,wx,wy,f0,tag in live:
        name,label,dist,t,z,m,ang,R,px=s; a=math.radians(ang)
        # name position at arrival, pulled inward so it stays inside the frame
        est=FW(label,NAME_PX,'Milker.otf'); sx=m[0]+R*math.cos(a); dx=min(0,1035-(sx+est/2))
        if sx+dx-est/2<45: dx=45+est/2-sx
        text('N'+tag,label,f'{NAME_PX*PX/z:.6f}*CAM.Size',font=DISPLAY,center=wpt(wx+dx/z,wy+(1 if ang>0 else -1)*(px*IMG[name][1]/max(IMG[name])*.42+38)/z))
        nf=f0+{'M77':100,'ANT':115}.get(tag,20)  # M77's label waits until the camera has settled, clear of the title
        merge('N'+tag,blend=ramp(nf,nf+30,T0))
        off=34/z
        text('D'+tag,dist,f'{40*PX/z:.6f}*CAM.Size',angle=ang,center=wpt(wx*.56-math.sin(a)*off,wy*.56+math.cos(a)*off))
        merge('D'+tag,blend=ramp(f0+85,f0+120,T0))
    text('NMW','Milky Way',f'{66*PX:.6f}*CAM.Size',font=DISPLAY,center=wpt(0,MW_PX*.5+40)); merge('NMW')
    # Fixed screen overlays
    text('Title','How far away are other galaxies?',TITLE_PX*PX,font=DISPLAY,center=(.5,1745/H)); merge('Title')
    text('Sub','Measured from the Milky Way',46*PX,rgb=ACCENT,center=(.5,1685/H)); merge('Sub')
    text('Foot','1 light-year = 9.46 trillion km  \u00b7  not to scale',38*PX,center=(.5,215/H)); merge('Foot',blend=ramp(40,90,T0))
    if end>33*FPS:
        text('Here','The Milky Way',42*PX,rgb=ACCENT,center=f'Point((CAM.Angle+45)/{W},(CAM.Aspect+150)/{H})'); merge('Here',blend=ramp(33*FPS,34*FPS,T0))
    if end>35*FPS:
        text('Punch','Its light left 1.19 billion years ago',PUNCH_PX*PX,font=DISPLAY,center=(.5,430/H)); merge('Punch',blend=ramp(int(35*FPS),int(35.5*FPS),T0))
    if end>38.8*FPS:
        add(f'Dark = Background {{ Inputs={{ {FRAME}, TopLeftAlpha=Input{{Value=1}}, TopLeftRed=Input{{Value=0}}, TopLeftGreen=Input{{Value=0}}, TopLeftBlue=Input{{Value=0}} }} }},')
        merge('Dark',blend=ramp(int(38.8*FPS),int(39.9*FPS),T0))
    add(f'MediaOut1 = MediaOut {{ Inputs={{ Index=Input{{Value="0"}}, Input=Input{{SourceOp="{last[0]}",Source="Output"}} }} }},')
    body='\n  '.join(tools)
    return f'''Composition {{
 CurrentTime = 0, RenderRange = {{ 0, 299 }}, GlobalRange = {{ 0, 299 }}, CurrentID = 9,
 Prefs = {{ Comp = {{ FrameFormat = {{ Width={W}, Height={H}, AspectX=1, AspectY=1, Rate={FPS}, GuideRatio=0.5625 }} }} }},
 Tools = ordered() {{
  {body}
 }},
}}
'''
for k in range(NSEG):
    open(f'comps/galaxy_seg{k+1}.comp','w',encoding='utf-8',newline='\n').write(build(k))
print('ok',[os.path.getsize(f'comps/galaxy_seg{k+1}.comp')//1024 for k in range(NSEG)])
