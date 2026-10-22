import json,re,collections
from lib import T, base
def has(t,*subs): return any(s in p for p in t['playlists'] for s in subs)
lang=lambda t: t['genre'].split(' ')[0] if t['genre'] else ''
dance=lambda t: bool(re.search(r'\b(Dance|Sangeet)\b',t['comment']))
upish=lambda t: bool(re.search(r'\b(Dance|Sangeet|Up|Club|Peak)\b',t['comment']))
EXPL=re.compile(r'(?i)fuck|f\*ck|\bfck\b|bitch|\bwap\b|\bculo\b')
def sw(k,lst): return any(k.startswith(x) for x in lst)

ENG_PL=['000 A1 Dance','After Party / English Dance','Commercial All Time OGs','Commercial Dance Mashups',
        'Commercial EDM and Bigroom','Commercial Trap','Dance Retro Pop','9. Disco / 3 Dance Disco']
ENG_G={'Pop & RnB','Hip-Hop','Moombah & Reggaeton','Bigroom','Retro Pop','Disco','Afro & Amapiano','Eurodance','Trap','RnB','Retro Hip-Hop'}
OLD_RE=re.compile(r'\b(50s|60s|70s|80s|90s|90s Nostalgia|00s|00s Memories|Retro)\b')
OLD_FORCE=('kajrare','baazigar','saakisaaki','kyamujhe','dhoommachale','gulabiaankhen','yehdosti','jeenekehain','rockthaparty',
 'deewangi','omshantiom','tucheezbadi','aankhonmeinteri','jahanteri','jaanumerijaan','mindblowing','muqabla','anchorpoint',
 'dheemtadare','ghananghanan','mehbooba','mundiyan','nirma','obetaji','yammayamma','yehshaammastani','olaalduppatte','bumbro',
 'jiyajale','rangbarse','terarangballe','yaarosunlo','bachkerehna','chappachappa','babujizara','bademiyan','chandikidaal',
 'ekdoteen','mynameislakhan','pareehoonmain','radhakaise','khiladi420','badshah','cholikepeeche','cholixtaambdi','dolare',
 'guptgupt','legayi','mastkalander','nimbooda','pardesi','righthere','taal','yehmeradil','zindagimeri','uriuri','staysexy',
 'dildoobaxcon','tumsemilke','beedijalaile','kiyakiya','justchill','eenameena','didi','dhoom','ishqkameena','koimilgaya','kaalDhamaal'.lower())
NEW_FORCE=('marjaani','bhaagdk','kalachasma','tunemaari','chammachamma','tujheaksa','raatbhar','dhatingnaach','abtoforever',
 'badtameez','dilbardilbar','ekladkikodekha','kargayichull','partyallnight','senorita','ikjunoon','dramaqueen','aapkakyahoga',
 'oonchihai','dancepechance','ainvayi','anjaana','charbaj','cutiepie','dancebasanti','dhatteriki','dilkajohaal','dilliwaali',
 'bhootnike','soorajkibaahon','galmitthi','kabhikabhiaditi','kukkad','ogujariya','palat','pappucant','partyonmymind',
 'subahhone','tumeri','twist','ufftera','balampichkari','areypyaar','tammatammaagain','slowmotion','dildhadakne','bytheway',
 'desigirl','desiboyz','aajkiparty','punjabiweddingsong','kashmirmain','phirmilenge','oohlala','pichlesaat','ommangalam',
 'pyarki','characterdheela','yaronemere','ailareaila','dummarodum','saturdaysaturday','ekmainaur','dildance','discodisco',
 'jalwa','laila','sautarah','hookahbar','locha','iskiuski','jaanekyun')
HINDI_DROP=('kesariya','tumhiho','tujaanena','kalhonaaho','bekhayali','kabhijobadal','jobhejithi','buddhusamann','sunnrahahai',
 'tuhimerishab','roobaroo','terahonelaga','pehlibaar','maintenusamjhawa','matujhesalaam','shivatandava','shivtandav',
 'jamalkuduabrar','ghoomar','odhani','dhindhora','dholitaaro','dholitaro','chudi','goriteragaon','rangilomaro','losecontrol',
 'bewafa','onelove','peelings','papakahtehain','gustakhdil','apnabanale','devadeva','loveyouzindagi','phirseudd',
 'iktara','maanmerijaan','mitwa','ikpal','tumkyajaano','tuneKaha'.lower(),'aapkidua','gubbare')
HINDI_DROP_EXACT={'tumse','sham','onelove','voicesindjshead','tunekaha'}
TAMIL_DROP=('unvizhigalil','vazhithunaiye','mundhinamparthe','hasilifisiliye','hosanna','kangalirandal','gulmuharmalare',
 'azhagiye','dhevadhai','enrojaa','ennaikonjam','ivanyaaro','kadhalsadugudu','sundhari','kannanvarum','kannuodu','orumaalai',
 'poovukkul','yedhoondru','uyirinuyire','kuttistory','mangalyam','adiyaekolluthey','unakkumenakkum','kaalakaalamaaga',
 'varahanadhikarai','pudhumalar','chennaisentamizh','kforkabaradakkam','nucleya','bassrani','videobydruminem','notlikus',
 'jalsajalsa','inthadi','champaginifrom','chikituvibe','bulletsongthewarriorr','orukuchiorukulfithe','padichupartehn',
 'loosupennae','illamaiethoehto','mustafaamustafaa','whythiskolaveridid','cocacolabrownu','kalasalakalasala','inkypinkyinkyponkyyou',
 'naatu' ,'jalsa','dharalaprabhu','kaathumela','vainko','evandaenakku','engeyumeppothum','enveetula','kalyanakalavaram',
 'leanermeaner','sangeethcelebration','kasupanam','bachelorroom','theepidikka','aalaporaan','neruppu','annaaththe','adiyemanam',
 'maanaamadurai','23theme','aa23','thetiger','powerhouse','ranagalam','kodanakodi','godblessu','hukum','marana','mastertheblaster',
 'oruvan','muthadachammak')
KEEP_TAMIL_EXACT={'naatusarakku','jalsa'}  # (handled below)
KAN_OTHERS_KEEP=('dilmangemore','shaanetop','hodiombath','enmadbeku','jilkajilkare','hellohello','oneondu','kannanekannane')
PUN_DROP=('sayonee','whythiskolaveri','ghoomar','dilt ujaantu'.replace(' ',''),'kangna' if False else '#')

cats=collections.defaultdict(list)
for t in T:
    L=lang(t); k=base(t['title'])
    if EXPL.search(t['title']+' '+t['artist']): continue
    if not t['title'].strip(): continue
    # Punjabi
    if L=='Punjabi' or (L=='Hindi' and has(t,'Punjabi [Fast]')) or k.startswith(('bolotarara','nananare')):
        if (dance(t) or upish(t) or has(t,'Punjabi [Fast]','Punjabi [Slow]','3 Punjabi','Hip Hop [Slow]','Punjabi Dance')) and not sw(k,PUN_DROP) and 'Warmup' not in ' '.join(t['playlists']):
            if not (L=='Hindi' and not has(t,'Punjabi')) or k.startswith(('bolotarara','nananare')):
                cats['Punjabi'].append(t)
        continue
    # English
    if L in ('English','') and not has(t,'English Dance Tech') and 'Tech House' not in t['genre'] and (has(t,*ENG_PL) or (L=='English' and dance(t) and t['genre'][8:] in ENG_G)):
        if L=='English' or has(t,'Mainstream English','English Dance'):
            cats['English'].append(t); continue
    # Hindi
    if L=='Hindi' or (L=='' and has(t,'b. Mainstream Bollywood')) or has(t,'Hindi Tech'):
        if (has(t,'b. Mainstream Bollywood','Hindi Tech') or dance(t)) and not has(t,'Warmup','10 Jive [Slow]') and not sw(k,HINDI_DROP) and k not in HINDI_DROP_EXACT:
            old = has(t,'Golden Hits','9 Jive') or bool(OLD_RE.search(t['tags']))
            if sw(k,OLD_FORCE): old=True
            if sw(k,NEW_FORCE): old=False
            cats['OldHindi' if old else 'NewHindi'].append(t)
        continue
    if has(t,'Tamil Kuthu','Tamil Non Kuthu') or (L=='Tamil' and dance(t)):
        if not sw(k,TAMIL_DROP) or k in ('naatusarakku',): cats['Tamil'].append(t)
        continue
    if has(t,'Telugu Kuthu','Telugu Non Kuthu') or (L=='Telugu' and dance(t)) or k=='peelings': cats['Telugu'].append(t); continue
    if has(t,'Kannada Kuthu','Kannada Non Kuthu') or (has(t,'Kannada Others') and sw(k,KAN_OTHERS_KEEP)) or (L=='Kannada' and dance(t)): cats['Kannada'].append(t); continue
    if has(t,'Malayalam Dance') or (L=='Malayalam' and dance(t)): cats['Malayalam'].append(t)

out={}
for c,v in cats.items():
    d={}
    for t in v:
        k=base(t['title']) or t['title']
        d.setdefault(k,[]).append(t)
    out[c]={k:sorted(v,key=lambda t:(-t['plays'],-len(t['playlists']))) for k,v in d.items()}
    print(c,len(out[c]))
json.dump(out,open('cats.json','w'))
