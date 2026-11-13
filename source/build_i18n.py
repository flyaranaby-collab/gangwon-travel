import json,glob,re
import os; os.chdir(os.path.dirname(os.path.abspath(__file__)))
p='index.html'; s=open(p,encoding='utf-8').read()
d={}
for f in sorted(glob.glob('i18n/*.tsv')):
    for line in open(f,encoding='utf-8').read().splitlines():
        parts=line.split('\t')
        if len(parts)!=4 or not parts[0]: continue
        d[parts[0]]=parts[1:]
extra={}
for k,v in list(d.items()):
    for sep in [' · ']:
        if sep in k and all(sep in x for x in v):
            ks=k.split(sep); vs=[x.split(sep) for x in v]
            if all(len(x)==len(ks) for x in vs):
                for i,kk in enumerate(ks):
                    if kk not in d: extra[kk]=[vs[j][i] for j in range(3)]
    m=re.match(r'^(.+?) \((.+)\)$',k)
    if m and all(re.match(r'^(.+?)[ ]?[（(]',x) for x in v):
        base=m.group(1)
        if base not in d: extra[base]=[re.match(r'^(.+?)[ ]?[（(]',x).group(1) for x in v]
for k,v in extra.items(): d.setdefault(k,v)
blob='const I18N_DICT = '+json.dumps(d,ensure_ascii=False,separators=(',',':'))+';\n'
eng=open('i18n/engine.js',encoding='utf-8').read()
block='<script id="i18n">\n'+blob+eng+'</script>\n'
if '<script id="i18n">' in s:
    s=re.sub(r'<script id="i18n">.*?</script>\n', lambda m: block, s, flags=re.S)
else:
    s=s.replace('<script>\n// ───────── 데이터', block+'<script>\n// ───────── 데이터',1)
    s=s.replace('render();\ninitRuntime();\n</script>','render();\ninitRuntime();\nsetLang(LANG);\n</script>',1)
    s=s.replace('    <div>\n      <div class="kicker">Gangwon-do','    <div class="langbar seg" id="langSeg" role="group" aria-label="Language" data-noi18n><button data-lang="ko">한국어</button><button data-lang="en">EN</button><button data-lang="zh">中文</button><button data-lang="ja">日本語</button></div>\n    <div>\n      <div class="kicker">Gangwon-do',1)
    s=s.replace('\n</style>','\n.langbar { justify-self: end; }\n.hero .langbar button { padding: 5px 12px; font-size: 13px; }\n</style>',1)
open(p,'w',encoding='utf-8').write(s)
print(len(d), 'langbar' in s, 'setLang(LANG)' in s)
