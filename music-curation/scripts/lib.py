import json,re
T=json.load(open('tracks.json'))
def base(title):
    s=re.sub(r'\(.*?\)|\[.*?\]','',title)
    s=re.sub(r'(?i)\b(full video|lyrical video|video song|official video|4k).*','',s)
    return re.sub(r'[^a-z0-9]','',s.lower())
def short(t): return ','.join(sorted({p.split(' / ')[-1][:16] for p in t['playlists']}))[:60]
def uniq(tracks):
    d={}
    for t in tracks:
        b=base(t['title']) or t['title']
        d.setdefault(b,[]).append(t)
    return d
