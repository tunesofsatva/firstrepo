# Stage 2: mashups -> first song only, re-home by that song's language, dedupe, popularity cut for Tamil/Kannada/Malayalam
import json,re,collections
F=json.load(open('final.json'))
SEP=re.compile(r'\s+(?:x|X|vs\.?|Vs\.?|VS)\s+|/')
key=lambda s: re.sub(r'[^a-z0-9]','',s.lower())
# Full-name exceptions (checked before splitting)
FULL={"it's my life x rock this party":"It's My Life (Bon Jovi)","it's my life":"It's My Life (Dr. Alban)",
      '24k breathing':'24K Magic','24k kanye gwen daft':'24K Magic','24k magic $igns':'24K Magic','diary milk x jumma chumma':'Jumma Chumma'}
# First-song name -> (canonical name, category); category None = keep where it is; name None = drop
C={}
def m(cat,*pairs):
    for p in pairs:
        a,b=(p if isinstance(p,tuple) else (p,p)); C[key(a)]=(b,cat)
m('English',('Fein','FE!N'),('FE!N','FE!N'),('Girls Just Wanna Have Fun','Girls Just Want To Have Fun'),('Its Tricky',"It's Tricky"),
  ('Lady','Lady (Hear Me Tonight)'),('Lady Hear Me Tonight','Lady (Hear Me Tonight)'),('Livin On A Prayer',"Livin' On A Prayer"),
  ('Dtmf','DtMF'),'Dance Monkey','Levitating','Hotline Bling',('Hymn For the Weekend','Hymn For The Weekend'),
  ('Let the Music Play','Let The Music Play'),'Losing It','Pepas','Right Now',('Sexy & I Know It','Sexy And I Know It'),
  ('Still Dre','Still D.R.E.'),'Without Me',('APT','APT.'),'Boasty','Victory Lap',('Yeah','Yeah!'),'Not Like Us','Run It Up',
  'Watermelon Sugar','Stay')
m('OldHindi',('Cheez Badi','Tu Cheez Badi Hai Mast Mast'),('Choli','Choli Ke Peeche'),('Urvashi','Urvashi Urvashi'),'Tamma Tamma')
m('NewHindi',('Aahun','Aahun Aahun (Love Aaj Kal)'),('Bhaag DK','Bhaag D.K. Bose'),'Chaleya',('Kamariya','Kamariya (Mitron)'),
  ('Lutt le Gaya','Lutt Le Gaya'),('Nashe Si Chadh Gayi','Nashe Si Chadh'),('Pichle Saat Dinon Mein','Pichle Saat Dino Mein'),
  ('Tere Pyar Mein','Tere Pyaar Mein'),('Yaa Ali 2.0','Ya Ali'))
m('Tamil',('Kolaveri Di','Why This Kolaveri Di'),'Manasilaayo')
# Dropped: slow/romantic originals that were only here as mashups, unclear or non-pop first halves
for d in ['Night Changes','Stay Sexy','Anchor Point','Kya Hua Tera Wada','Pardesi','Tujhe Yaad Kiya','Woh Lamhe','Abcdefu','Dil Diya Gallan',
          'Dil Tu Jaan Tu','Hai Jamalo','Love Sick','Majnuna','Maya','Raat Bhar','Rang De','Ranjha','Shayad','Tu Chahiye','By My Side','Jiggle']:
    C[key(d)]=(None,None)

ORDER=list(F.keys())
out={c:{} for c in ORDER}; log=[]
for c in ORDER:
    for name,vs in F[c]:
        n=FULL.get(name.lower())
        if not n: n=SEP.split(name)[0].strip() if SEP.search(name) else name
        cat=c
        if key(n) in C:
            nn,cc=C[key(n)]
            if nn is None: log.append(('drop',c,name)); continue
            n=nn; cat=cc or c
        if n!=name or cat!=c: log.append(('map',c,name,n,cat))
        out[cat].setdefault(key(n),[n,[]])[1].extend(vs)
json.dump(log,open('stage2_log.json','w'))
POP=json.load(open('popular.json')) if __import__('os').path.exists('popular.json') else {}
# Same song present as a dub in another list: keep only its original-language entry
XDROP={('Tamil','Kissik'),('Tamil','Lejjavathiye'),('Tamil','Thayya Thayya'),('Telugu','Rowdy Baby (Telugu)'),('Telugu','Daddy Mummy'),
       ('NewHindi','Daavudi (Devara)'),('NewHindi','Oo Antava'),('NewHindi','Oo Bolega Ya Oo Oo Bolega (Pushpa)'),('NewHindi','Chuttamalle'),
       ('NewHindi','Daddy Mummy'),('NewHindi','Sauda Khara Khara'),('OldHindi','Humma Humma'),('OldHindi','Muqabla'),('OldHindi','Angel Eyes')}
XK={(c,key(n)) for c,n in XDROP}
final={}
for c in ORDER:
    for c2,k in XK:
        if c2==c and k not in out[c]: print('WARN xdrop miss',c,k)
    rows=[r for kk,r in out[c].items() if (c,kk) not in XK]
    if c in POP:
        keep={key(x) for x in POP[c]}
        missing=keep-{key(r[0]) for r in rows}
        if missing: print('WARN not found in',c,missing)
        rows=[r for r in rows if key(r[0]) in keep]
    final[c]=sorted(rows,key=lambda r:r[0].lower())
json.dump(final,open('final2.json','w'))
if __name__=='__main__':
    import sys
    for c in ORDER: print(c,len(final[c]))
    for c in sys.argv[1:]:
        print('==',c); print(' ; '.join(f"{r[0]}[{sum(t['plays'] for t in r[1])}]" for r in final[c]))
