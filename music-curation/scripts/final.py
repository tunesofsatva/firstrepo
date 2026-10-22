import json,re
from names import disp
C=json.load(open('cats.json'))
RENAME={}; DROP=set(); MOVE={}
try:
    exec(open('overrides.py').read())
except FileNotFoundError: pass
ORDER=['English','OldHindi','NewHindi','Punjabi','Tamil','Telugu','Kannada','Malayalam']
res={c:{} for c in ORDER}
for c in ORDER:
    for k,v in C.get(c,{}).items():
        t=v[0]; d=disp(t['title'],eng=(c=='English')); d=RENAME.get(d.lower(),d)
        if not d or d.lower() in DROP or (c.lower()+'|'+d.lower()) in DROP: continue
        cc=MOVE.get(c.lower()+'|'+d.lower(), MOVE.get(d.lower(),c) if c=='NewHindi' or d.lower().startswith('annange') else c)
        key=re.sub(r'[^a-z0-9]','',d.lower())
        if key in res[cc]: res[cc][key][1].extend(v); continue
        res[cc][key]=[d,list(v)]
final={c:sorted(res[c].values(),key=lambda r:r[0].lower()) for c in ORDER}
json.dump(final,open('final.json','w'))
if __name__=='__main__':
    import sys
    for c in (sys.argv[1:] or ORDER):
        print(f'== {c} ({len(final[c])})'); print(' ; '.join(r[0] for r in final[c]))
