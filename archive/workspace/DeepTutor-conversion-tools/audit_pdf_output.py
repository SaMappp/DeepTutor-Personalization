# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import json,re,hashlib,unicodedata,collections,math,subprocess
import pymupdf as fitz
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parent
V=ROOT/'verification';OUT=ROOT.parent/'Course materials/Computer Programming/英文原版 PDF 课件'
baseline=json.loads((V/'source-baseline.json').read_text(encoding='utf-8'))
manifest=json.loads((ROOT/'conversion-manifest.json').read_text(encoding='utf-8'))
font=ImageFont.truetype(r'C:\Windows\Fonts\arial.ttf',14)
def tokens(s):return collections.Counter(re.findall(r'[a-z0-9_]+',unicodedata.normalize('NFKC',s).casefold()))
selected={1:[6,9,13],2:[8,28,44],3:[4,45],4:[11,23,43],5:[16,31],6:[13,58]}
report=[]
for n,src in enumerate(baseline,1):
 p=next(Path(r['output']) for r in manifest if r['kind']=='ppt' and r['source']==src['source'])
 doc=fitz.open(p);assert len(doc)==src['slides'],(n,len(doc),src['slides'])
 expected=[int(src['size_emu'][k])/12700 for k in ['cx','cy']]
 entries=[];thumbs=[]
 for i,page in enumerate(doc):
  text=page.get_text();st=src['pages'][i]['text'];a,b=tokens(st),tokens(text);missing=a-b;recall=sum((a&b).values())/max(1,sum(a.values()))
  badchars=[hex(ord(c)) for c in text if c=='\ufffd']
  size_ok=all(abs(x-y)<0.6 for x,y in zip([page.rect.width,page.rect.height],expected))
  spans=[span for block in page.get_text('dict')['blocks'] if 'lines' in block for line in block['lines'] for span in line['spans']]
  outbounds=[{'text':s['text'][:80],'bbox':s['bbox']} for s in spans if s['bbox'][0]<-1 or s['bbox'][1]<-1 or s['bbox'][2]>page.rect.width+1 or s['bbox'][3]>page.rect.height+1]
  pix=page.get_pixmap(matrix=fitz.Matrix(0.38,0.38),alpha=False)
  im=Image.frombytes('RGB',[pix.width,pix.height],pix.samples);ink=sum(v<240 for v in im.convert('L').getdata())/(im.width*im.height)
  thumb=Image.new('RGB',(260,172),'#e8edf4');im.thumbnail((256,144));thumb.paste(im,((260-im.width)//2,0));ImageDraw.Draw(thumb).text((8,148),f'Lecture {n:02} | p.{i+1:02}',font=font,fill='#111111');thumbs.append(thumb)
  entries.append({'page':i+1,'chars':len(text),'source_tokens':sum(a.values()),'text_recall':round(recall,4),'missing_tokens':dict(missing),'badchars':badchars,'outbounds':outbounds,'ink_ratio':round(ink,4),'size_ok':size_ok})
  if i+1 in selected[n]:
   dest=V/'rendered'/f'Lecture{n:02}';dest.mkdir(parents=True,exist_ok=True)
   subprocess.run([r'C:\Users\YOUR_NAME\.cache\codex-runtimes\codex-primary-runtime\dependencies\native\poppler\Library\bin\pdftoppm.exe','-f',str(i+1),'-l',str(i+1),'-scale-to','1600','-png','-singlefile',str(p),str(dest/f'page-{i+1}')],check=True,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 cols=5;sheet=Image.new('RGB',(cols*260,math.ceil(len(thumbs)/cols)*172),'white')
 for j,im in enumerate(thumbs):sheet.paste(im,((j%cols)*260,(j//cols)*172))
 sheet.save(V/f'Lecture{n:02}-all-pages.jpg',quality=90)
 assert hashlib.file_digest(Path(src['source']).open('rb'),'sha256').hexdigest()==src['sha256']
 row={'lecture':n,'pdf':str(p),'pages':len(doc),'original_unchanged':True,'representative_pages':selected[n],'min_text_recall':min(x['text_recall'] for x in entries),'fonts':sorted({f[3] for p in doc for f in p.get_fonts()}),'pages_audit':entries}
 report.append(row)
 print(json.dumps({k:v for k,v in row.items() if k not in ['pages_audit','fonts']},ensure_ascii=False),flush=True)
 print('flags',[(x['page'],x['text_recall'],len(x['outbounds']),x['ink_ratio']) for x in entries if x['text_recall']<.97 or x['badchars'] or x['outbounds'] or x['ink_ratio']<.01 or not x['size_ok']],flush=True)
(V/'pdf-audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print('Total pages',sum(x['pages'] for x in report),flush=True)
