import re,urllib.request,json,html,sys,os
UA={'User-Agent':'Mozilla/5.0'}
def get(u): return urllib.request.urlopen(urllib.request.Request(u,headers=UA),timeout=45).read()
out=sys.argv[1]; rec={}
for i in sys.argv[2:]:
    eso=i.startswith('eso')
    page=('https://www.eso.org/public/images/' if eso else 'https://esahubble.org/images/')+i+'/'
    try:
        h=html.unescape(get(page).decode('utf8','ignore'))
        title=re.search(r'<title>(.*?)</title>',h,re.S).group(1).split('|')[0].strip()
        c=re.search(r'<div class="credit">(.*?)</div>',h,re.S)
        cred=re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',c.group(1))).strip() if c else None
        if not cred:
            t=re.sub(r'\s+',' ',re.sub(r'<[^>]+>',' ',h)); m=re.search(r'Credit:\s*(.{3,160}?)\s*(?:Usage of|About the Image)',t); cred=m.group(1) if m else None
        host='https://www.eso.org/public/archives/images/' if eso else 'https://esahubble.org/media/archives/images/'
        data=None
        for v in ['screen','large']:
            try: data=get(f'{host}{v}/{i}.jpg');break
            except Exception as e: err=e
        if data is None: raise err
        open(os.path.join(out,i+'.jpg'),'wb').write(data)
        rec[i]=dict(title=title,credit=cred,page=page,bytes=len(data),licence='CC BY 4.0');print(i,len(data)//1024,'KB',title[:50],'|',cred)
    except Exception as e: print('ERR',i,e)
old=json.load(open(os.path.join(out,'assets.json'))) if os.path.exists(os.path.join(out,'assets.json')) else {}
old.update(rec); json.dump(old,open(os.path.join(out,'assets.json'),'w'),indent=1)
