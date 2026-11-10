# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import faulthandler
faulthandler.dump_traceback_later(25)
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
import asyncio
import json
import os
import sys
import time
import pymupdf

ROOT=Path(__file__).resolve().parent
VERIFY=ROOT/'verification'
CORE=Path(r'C:\Users\YOUR_NAME\AppData\Local\Open DeepTutor\runtimes\1.7.1-f7aed0744-x64\core')
sys.path.insert(0,str(ROOT/'test-source'))
sys.path.insert(1,str(CORE))
from deeptutor.reading import ReadingStore
from deeptutor.reading import native_ocr
from deeptutor.core.context import UnifiedContext
from deeptutor.runtime.stream_bus import StreamBus
from deeptutor.capabilities.reading.capability import ReadingCapability
from deeptutor.capabilities.reading.tools import ReadMaterialTool,SearchMaterialTool,BINDING_KWARG,MATERIAL_KWARG


def log_rows():
    path=VERIFY/'logs'/'page-ocr.jsonl'
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines()] if path.exists() else []


def create_fixture(name):
    path=VERIFY/name
    if path.exists():return path
    original=Path(r'authorized-source.pdf')
    document=pymupdf.open();p=document.new_page(width=461.2,height=615)
    for n in range(12):
        p.insert_text((35,70+n*34),f'第{n+1}项：函数与极限需要结合定义、运算法则、条件和例题逐步理解。',fontname='china-s',fontsize=10)
    p.add_text_annot((40,40),'原有批注必须保留')
    with pymupdf.open(original) as source:
        for n in [12,29]:
            page=document.new_page(width=source[n].rect.width,height=source[n].rect.height)
            # Completely image-only, so import must not rely on existing notes or image markers.
            page.insert_image(page.rect,pixmap=source[n].get_pixmap(dpi=180,alpha=False))
    document.set_metadata({'title':name,'subject':'native-demand-ocr-fixture-v1'})
    document.set_toc([[1,'原生文字',1],[1,'映射与函数（扫描）',2],[1,'数列极限（扫描）',3]])
    document.save(path,deflate=True)
    return path


async def run():
    faulthandler.cancel_dump_traceback_later()
    VERIFY.mkdir(exist_ok=True)
    config=json.loads((ROOT/'configuration.json').read_text(encoding='utf-8'))
    config.update(cache_root=str(VERIFY/'cache'),root=str(VERIFY))
    (VERIFY/'test-config.json').write_text(json.dumps(config),encoding='utf-8')
    native_ocr.CONFIG=VERIFY/'test-config.json';native_ocr._configuration=None
    store=ReadingStore(VERIFY/'reading')
    source=create_fixture('原生按需OCR验证 混合.pdf')
    before_hash=native_ocr.file_hash(source)
    before_log=len(log_rows())
    material=store.ingest(source)
    assert not any(r['action']=='ocr_start' for r in log_rows()[before_log:])
    assert material.unit_count==3
    raw=store.raw_path(material.material_id)
    assert native_ocr.file_hash(raw)==before_hash
    reports=[]
    async def turn(question,locator):
        context=UnifiedContext(user_message=question,session_id='native-verification',language='zh',
            metadata={'reading_material_id':material.material_id,'reading_viewport':{'locator':locator}})
        bus=StreamBus();beg=time.monotonic()
        with patch('deeptutor.reading.ReadingStore',return_value=store):
            block=await ReadingCapability().pre_loop(context,bus)
        return context,block,bus,round(time.monotonic()-beg,3)
    initial=len(log_rows());context,block,bus,t=await turn('讲解当前页',1)
    assert 'native_pdf_page_context'==block.name and '原生文字' not in context.user_message
    assert not [r for r in log_rows()[initial:] if r['action']=='ocr_start']
    reports.append({'case':'原生文字页零 OCR','seconds':t,'passed':True})
    initial=len(log_rows());context,block,bus,t=await turn('讲解第 2 页',1)
    calls=[r for r in log_rows()[initial:] if r['action']=='ocr_start']
    assert len(calls)==1 and calls[0]['page']==2
    assert '映射与函数' in block.content and '<page number="3"' not in block.content
    assert any('正在本机识别 PDF 第 2 页' in e.content for e in bus._history)
    reports.append({'case':'扫描混合文件仅指定页 OCR','seconds':t,'calls':calls,'passed':True})
    initial=len(log_rows());context2,block2,bus2,t2=await turn('再讲解第2页',1)
    assert not [r for r in log_rows()[initial:] if r['action']=='ocr_start']
    assert any(r['action']=='cache_hit' for r in log_rows()[initial:])
    reports.append({'case':'同页缓存命中','seconds':t2,'passed':True})
    with patch.object(ReadMaterialTool,'_store',return_value=store):
        binding=context2.extension('reading')['tool_binding']
        answer=await ReadMaterialTool().execute(**{MATERIAL_KWARG:material.material_id,BINDING_KWARG:binding,'locators':'1-3'})
        assert not answer.success
    assert not any(r.get('page')==3 and r['action']=='ocr_start' for r in log_rows()[initial:])
    reports.append({'case':'工具不能扩大单页 OCR 范围','passed':True})
    initial=len(log_rows());result=await asyncio.to_thread(native_ocr.ensure_page,store,material.material_id,3)
    assert result['mode']=='ocr' and '极限' in result['text']
    assert [r['page'] for r in log_rows()[initial:] if r['action']=='ocr_start']==[3]
    reports.append({'case':'混合 PDF 按页面分别处理','seconds':result['seconds'],'passed':True})
    other=create_fixture('不同文件 同页码.pdf');other_material=store.ingest(other)
    initial=len(log_rows())
    results=await asyncio.gather(*[asyncio.to_thread(native_ocr.ensure_page,store,other_material.material_id,2) for _ in range(3)])
    calls=[r for r in log_rows()[initial:] if r['action']=='ocr_start']
    assert len(calls)==1 and calls[0]['source_sha256']!=before_hash
    assert sum(r['mode']=='ocr' for r in results)==1
    reports.append({'case':'新文件不串缓存，同页并发只识别一次','calls':calls,'passed':True})
    # Pure scan import must succeed immediately without any OCR calls.
    pure=VERIFY/'纯扫描 无文字.pdf'
    if not pure.exists():
        with pymupdf.open(source) as d:
            p=pymupdf.open();p.insert_pdf(d,from_page=1,to_page=2);p.save(pure)
    initial=len(log_rows());started=time.monotonic();pure_material=store.ingest(pure)
    assert pure_material.unit_count==2
    assert not [r for r in log_rows()[initial:] if r['action']=='ocr_start']
    reports.append({'case':'纯扫描原入口立即导入，零 OCR','seconds':round(time.monotonic()-started,3),'passed':True})
    with pymupdf.open(source) as a,pymupdf.open(raw) as b:
        assert a.get_toc()==b.get_toc()
        assert all(a[n].get_pixmap(dpi=96).samples==b[n].get_pixmap(dpi=96).samples for n in range(len(a)))
    assert native_ocr.file_hash(source)==before_hash
    reports.append({'case':'原件哈希、目录、批注和显示保留','passed':True})
    assert native_ocr.question_scope('不要全书总结，只讲解当前页',{'locator':2},3)['pages']==[2]
    assert native_ocr.question_scope('讲解第二页',{'locator':1},3)['pages']==[2]
    assert native_ocr.question_scope('全书总结',{'locator':1},3)['mode']=='document'
    reports.append({'case':'明确页码、当前页与跨页意图区分','passed':True})
    summary={'tests':reports,'passed':len(reports),'mixed_fixture':str(source),
             'first_page_ocr_seconds':t,'cache_hit_seconds':t2,'material_id':material.material_id}
    (VERIFY/'native-tests.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False),flush=True)


if __name__=='__main__':asyncio.run(run())
