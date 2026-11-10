# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import json,zipfile,xml.etree.ElementTree as E,posixpath,subprocess,hashlib
ROOT=Path(__file__).resolve().parent
source=Path(json.loads((ROOT/'verification/source-baseline.json').read_text(encoding='utf-8'))[1]['source'])
ns={'p':'http://schemas.openxmlformats.org/presentationml/2006/main','a':'http://schemas.openxmlformats.org/drawingml/2006/main'}
E.register_namespace('p',ns['p']);E.register_namespace('a',ns['a'])
with zipfile.ZipFile(source) as z:
 pres=E.fromstring(z.read('ppt/presentation.xml'));rels={r.attrib['Id']:posixpath.normpath('ppt/'+r.attrib['Target']) for r in E.fromstring(z.read('ppt/_rels/presentation.xml.rels'))};name=rels[pres.findall('p:sldIdLst/p:sldId',ns)[64].attrib['{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id']]
 tree=E.fromstring(z.read(name));top=1325880;left=548640;right=11643054;bottom=9098280;scale=(6350000-top)/(bottom-top);width=12192000;offset=(width-(right-left)*scale)/2
 count=0
 for sp in tree.findall('.//p:sp',ns):
  x=sp.find('p:spPr/a:xfrm',ns)
  if x is None:continue
  off=x.find('a:off',ns);ext=x.find('a:ext',ns)
  if int(off.attrib['y'])<top:continue
  off.set('x',str(round(offset+(int(off.attrib['x'])-left)*scale)));off.set('y',str(round(top+(int(off.attrib['y'])-top)*scale)))
  for k in ['cx','cy']:ext.set(k,str(round(int(ext.attrib[k])*scale)))
  for el in sp.iter():
   for k in ['sz','lIns','rIns','tIns','bIns','marL','marR','indent']:
    if k in el.attrib:el.set(k,str(round(int(el.attrib[k])*scale)))
   if el.tag.endswith('}spcPts') and 'val' in el.attrib:el.set('val',str(round(int(el.attrib['val'])*scale)))
  count+=1
 temp=ROOT/'verification/修复用临时副本';temp.mkdir(exist_ok=True)
 dest=temp/(source.stem+'__阅读修正版_仅第65页.pptx')
 with zipfile.ZipFile(dest,'w',zipfile.ZIP_DEFLATED) as out:
  for item in z.infolist():out.writestr(item,E.tostring(tree,encoding='utf-8',xml_declaration=True) if item.filename==name else z.read(item.filename))
 print('Only slide65 scaled to fit canvas; shapes',count,'scale',scale,flush=True)
subprocess.run([str(ROOT/'.venv/Scripts/python.exe'),str(ROOT/'convert_materials.py'),'ppt',str(dest),'--outdir',str(ROOT.parent/'Course materials/Computer Programming/英文原版 PDF 课件')],check=True)
(ROOT/'verification/slide65-repair.json').write_text(json.dumps({'original':str(source),'temporary_copy':str(dest),'changed_xml_entry':name,'slide':65,'shape_count':count,'scale':scale,'reason':'Original slide has the sum and pow helper cards outside its canvas; only the card grid is scaled uniformly into the same-size page. Original source and faithful PDF retained.'},ensure_ascii=False,indent=2),encoding='utf-8')
