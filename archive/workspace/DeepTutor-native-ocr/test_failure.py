# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import json
import sys
import time
import pymupdf

ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'test-source'))
sys.path.insert(1,r'C:\Users\YOUR_NAME\AppData\Local\Open DeepTutor\runtimes\1.7.1-f7aed0744-x64\core')
from deeptutor.reading import ReadingStore,ReadingError
from deeptutor.reading import native_ocr

native_ocr.CONFIG=ROOT/'verification'/'test-config.json'
store=ReadingStore(ROOT/'verification'/'reading')
path=ROOT/'verification'/'空白扫描_失败重试.pdf'
if not path.exists():
    doc=pymupdf.open();p=doc.new_page(width=461,height=615)
    pix=pymupdf.Pixmap(pymupdf.csRGB,pymupdf.IRect(0,0,800,1100),False);pix.clear_with(255)
    p.insert_image(p.rect,pixmap=pix);doc.save(path)
material=store.ingest(path)
errors=[]
for n in range(2):
    try:
        native_ocr.ensure_page(store,material.material_id,1)
        raise AssertionError('Blank result was wrongly accepted')
    except ReadingError as exc:
        errors.append(str(exc))
assert len(errors)==2 and native_ocr.cached_text(store,material.material_id,1) is None
assert native_ocr.question_scope('在当前页搜索函数',{'locator':2},349)['pages']==[2]
summary={'failure_not_empty_success':True,'retry_performs_new_attempt':True,'error_messages':errors,
         'current_page_search_stays_single_page':True}
(ROOT/'verification'/'failure-tests.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=False),flush=True)
