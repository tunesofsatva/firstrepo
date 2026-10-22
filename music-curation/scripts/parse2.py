import sys, json, xml.etree.ElementTree as ET
root=ET.parse(sys.argv[1]).getroot()
tracks={}
for e in root.find('COLLECTION'):
    loc=e.find('LOCATION'); info=e.find('INFO'); t=e.find('TEMPO'); al=e.find('ALBUM')
    g=lambda el,k: (el.get(k,'') if el is not None else '')
    key=g(loc,'VOLUME')+g(loc,'DIR')+g(loc,'FILE')
    tracks[key]=dict(title=e.get('TITLE',''),artist=e.get('ARTIST',''),genre=g(info,'GENRE'),mix=g(info,'MIX'),
      comment=g(info,'COMMENT'),tags=g(info,'RATING'),release=g(info,'RELEASE_DATE'),
      plays=int(g(info,'PLAYCOUNT') or 0),ranking=int(g(info,'RANKING') or 0),bpm=round(float(g(t,'BPM') or 0),1),
      album=g(al,'TITLE'),dir=g(loc,'DIR'),file=g(loc,'FILE'),key=key,playlists=[])
def walk(n,path):
    for c in n.findall('NODE'):
        p=c.find('PLAYLIST'); sub=c.find('SUBNODES'); name=path+[c.get('NAME','')]
        if p is not None:
            for en in p.findall('ENTRY'):
                k=en.find('PRIMARYKEY').get('KEY')
                if k in tracks: tracks[k]['playlists'].append(' / '.join(name[1:]))
        if sub is not None: walk(sub,name)
walk(root.find('PLAYLISTS'),[])
json.dump(list(tracks.values()),open('tracks.json','w'))
print(len(tracks), sum(1 for t in tracks.values() if t['playlists']))
