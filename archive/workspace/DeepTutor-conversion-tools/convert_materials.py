# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Safe repeatable presentation conversions; sources are never modified."""
from pathlib import Path
import argparse,base64,hashlib,json,os,subprocess,sys,tempfile,time
ROOT=Path(__file__).resolve().parent
ACADEMIC=ROOT.parent
DEFAULT=ACADEMIC/'Course materials'/'Converted PDFs'
def sha(p):
 with Path(p).open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def pick(kind):
 filt='PowerPoint (*.ppt;*.pptx)|*.ppt;*.pptx' if kind=='ppt' else 'PDF (*.pdf)|*.pdf'
 code="Add-Type -AssemblyName System.Windows.Forms; $d=New-Object System.Windows.Forms.OpenFileDialog; $d.Multiselect=$true; $d.Filter='"+filt+"'; if($d.ShowDialog() -eq 'OK'){[Console]::OutputEncoding=[Text.Encoding]::UTF8; $d.FileNames | ConvertTo-Json -Compress}"
 r=subprocess.run(['powershell.exe','-NoProfile','-STA','-EncodedCommand',base64.b64encode(code.encode('utf-16le')).decode()],capture_output=True,encoding='utf-8',check=True)
 if not r.stdout.strip():return []
 data=json.loads(r.stdout);return [data] if isinstance(data,str) else data
def unique(dest):
 if not dest.exists():return dest
 for i in range(2,10000):
  p=dest.with_name(dest.stem+f'__v{i}'+dest.suffix)
  if not p.exists():return p
 raise RuntimeError('Too many output versions')
def publish(temp,dest):
 # Exclusive creation guarantees that even a concurrent conversion cannot overwrite.
 while True:
  candidate=unique(dest)
  try:
   with candidate.open('xb') as out,Path(temp).open('rb') as src:
    import shutil;shutil.copyfileobj(src,out)
   return candidate
  except FileExistsError:continue

def main():
 ap=argparse.ArgumentParser(description='PPT to searchable PDF; PDF to image-only PPTX backup')
 ap.add_argument('kind',choices=['ppt','pdf']);ap.add_argument('files',nargs='*');ap.add_argument('--outdir',type=Path);ap.add_argument('--resolution',type=int,default=200)
 a=ap.parse_args();files=a.files or pick(a.kind)
 if not files:print('未选择文件，已取消。');return
 out=(a.outdir or (DEFAULT if a.kind=='ppt' else ACADEMIC/'Course materials'/'Image PPTX backup')).resolve();out.mkdir(parents=True,exist_ok=True)
 records=ROOT/'conversion-manifest.json'
 rows=json.loads(records.read_text(encoding='utf-8')) if records.exists() else []
 lock=ROOT/'conversion.lock'
 try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
 except FileExistsError:raise RuntimeError('另一个转换正在运行；请稍后重试。')
 try:
  for filename in files:
   src=Path(filename).resolve(strict=True)
   if src.suffix.lower() not in (('.ppt','.pptx') if a.kind=='ppt' else ('.pdf',)):raise ValueError('不支持的文件：'+str(src))
   digest=sha(src)
   existing=next((r for r in reversed(rows) if r['kind']==a.kind and r['source_sha256']==digest and Path(r['output']).parent==out and Path(r['output']).exists() and sha(r['output'])==r['output_sha256']),None)
   if existing:print('跳过已转换文件：'+existing['output'],flush=True);continue
   with tempfile.TemporaryDirectory(prefix='dt-convert-',dir=ROOT/'runtime',ignore_cleanup_errors=True) as td:
    temp=Path(td)
    if a.kind=='ppt':
     profile=(temp/'lo-profile').as_uri()
     options={k:{'type':'boolean','value':v} for k,v in {'UseLosslessCompression':'true','ReduceImageResolution':'false','UseTaggedPDF':'true','ExportNotesPages':'false','ExportOnlyNotesPages':'false','ExportHiddenSlides':'true'}.items()}
     cmd=[str(ROOT/'LibreOffice/program/soffice.com'),'-env:UserInstallation='+profile,'--headless','--nologo','--nodefault','--norestore','--convert-to','pdf:impress_pdf_Export:'+json.dumps(options,separators=(',',':')),'--outdir',str(temp),str(src)]
     made=temp/(src.stem+'.pdf');suffix='.pdf'
    else:
     made=temp/(src.stem+'__image_slides.pptx');suffix='.pptx'
     cmd=[str(ROOT/'.venv-pdf2pptx/Scripts/pdf2pptx.exe'),str(src),'--output',str(made),'--resolution',str(a.resolution),'--quiet']
    print('正在转换：'+src.name,flush=True)
    r=subprocess.run(cmd,capture_output=True,encoding='utf-8',errors='replace',timeout=600)
    if r.returncode or not made.exists():raise RuntimeError('转换失败：'+r.stdout+'\n'+r.stderr)
    target=out/(src.stem+('' if a.kind=='ppt' else '__image_slides')+suffix)
    dest=publish(made,target)
   assert sha(src)==digest,'原文件发生了变化'
   row={'kind':a.kind,'source':str(src),'source_sha256':digest,'output':str(dest),'output_sha256':sha(dest),'time':time.strftime('%Y-%m-%d %H:%M:%S'),'engine':'LibreOffice 26.8.2' if a.kind=='ppt' else 'pdf2pptx 1.0.5','image_only':a.kind=='pdf'}
   rows.append(row);records.write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf-8');print('已保存：'+str(dest),flush=True)
 finally:os.close(fd);lock.unlink()
if __name__=='__main__':
 (ROOT/'runtime').mkdir(exist_ok=True)
 try:main()
 except Exception as e:print('错误：'+str(e),file=sys.stderr);sys.exit(1)
