# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Small integration checks; reuse existing full-book OCR rather than rerun it."""
from pathlib import Path
import json
import threading
import time
import pymupdf
from pypdf import PdfReader
import engine
import pipeline

ROOT = Path(__file__).resolve().parent
VERIFY = ROOT/'verification'
FIXTURES = VERIFY/'fixtures'
OUTPUT = VERIFY/'outputs'
CACHE = VERIFY/'cache'


def build_fixtures():
    FIXTURES.mkdir(parents=True,exist_ok=True)
    text = FIXTURES/'已有文字层 中文 空格.pdf'
    if not text.exists():
        doc = pymupdf.open(); page = doc.new_page(width=461.2,height=615)
        sentence = '函数与极限是高等数学的重要内容，连续函数的性质需要结合定义和定理条件进行分析。'
        for i in range(12):
            page.insert_text((35,80+i*32),sentence,fontname='china-s',fontsize=9)
        page.add_text_annot((35,45),'保留原有批注')
        doc.set_toc([[1,'测试目录',1]]);doc.save(text)
    source = Path(json.loads((ROOT/'current-book.json').read_text(encoding='utf-8'))['source'])
    scan = FIXTURES/'扫描页 中文教材.pdf'
    if not scan.exists():
        with pymupdf.open(source) as original:
            doc = pymupdf.open();doc.insert_pdf(original,from_page=12,to_page=12)
            doc.set_toc([[1,'扫描目录',1]]);doc.save(scan)
    mixed = FIXTURES/'混合 页面 示例.pdf'
    if not mixed.exists():
        doc=pymupdf.open()
        with pymupdf.open(text) as digital, pymupdf.open(scan) as image:
            doc.insert_pdf(digital);doc.insert_pdf(image);doc.insert_pdf(digital)
        doc.set_toc([[1,'文字页',1],[1,'扫描页',2],[1,'文字页',3]]);doc.save(mixed)
    resume = FIXTURES/'断点恢复 两张扫描.pdf'
    if not resume.exists():
        with pymupdf.open(source) as original:
            doc=pymupdf.open();doc.insert_pdf(original,from_page=12,to_page=12)
            doc.insert_pdf(original,from_page=29,to_page=29);doc.save(resume)
    watermark = FIXTURES/'页码水印与笔记.pdf'
    if not watermark.exists():
        doc=pymupdf.open()
        with pymupdf.open(scan) as image:
            for i in range(5):
                doc.insert_pdf(image)
                doc[-1].insert_text((150,300),'WATERMARK',fontsize=24)
                doc[-1].insert_text((230,590),str(i+1),fontsize=10)
        doc.save(watermark)
    return text,scan,mixed,resume,watermark


def run():
    VERIFY.mkdir(exist_ok=True)
    cases=[]
    text,scan,mixed,resume,watermark=build_fixtures()
    hashes={str(p):engine.file_hash(p) for p in [text,scan,mixed,resume,watermark]}
    def record(name,**kw):
        cases.append({'case':name,'passed':True,**kw});print('PASS',name,flush=True)
    def process(path,expression='',**kw):
        return pipeline.process_pdf(path,expression,output_root=OUTPUT,cache_root=CACHE,
                                    log=lambda msg:print(msg,flush=True),**kw)
    with pymupdf.open(watermark) as doc:
        artifacts=pipeline.repeated_artifacts(doc)
        assert all(pipeline.classify(p,artifacts)['action']=='ocr' for p in doc)
    record('页码、重复水印、少量笔记不会被判定为完整正文')
    digital=process(text)
    assert digital['ocr_executed']==0 and digital['validation']['visual_pages_identical']==1
    assert digital['output_sha256']==hashes[str(text)]
    record('已有文字层直接复用且不执行 OCR')
    scanned=process(scan,workers=1)
    assert scanned['ocr_executed']==1
    assert '函数与极限' in pipeline.meaningful(pymupdf.open(scanned['output'])[0].get_text())
    record('扫描教材真实本地 OCR、正文搜索与页面保留')
    blended=process(mixed,workers=2)
    assert blended['ocr_executed']==1 and blended['validation']['ocr_pages']==[2]
    assert blended['validation']['visual_pages_identical']==3
    record('混合 PDF 仅扫描页 OCR',ocr_pages=blended['validation']['ocr_pages'])
    again=process(mixed,workers=2)
    assert again['reused_output'] and again['output_sha256']==blended['output_sha256']
    record('重复处理复用完整输出，无新 OCR')
    partial=process(mixed,'2')
    assert partial['partial'] and partial['range']=='2' and partial['cache_hits']==1 and partial['ocr_executed']==0
    assert 'OCR部分' in Path(partial['output']).name
    assert len(pymupdf.open(partial['output']))==3
    record('物理页码范围与部分结果标记，保留全书页序')
    stop=threading.Event()
    def interrupted(path,number):
        raw=engine.recognize(path,number);stop.set();return raw
    try:
        process(resume,stop=stop,recognizer=interrupted)
        raise AssertionError('Expected pause')
    except pipeline.Paused:
        pass
    resumed=process(resume,workers=1)
    assert resumed['cache_hits']==1 and resumed['ocr_executed']==1
    record('暂停后续作：已完成页不重跑',cache_hits=resumed['cache_hits'])
    desc=engine.descriptor(); source_hash=hashes[str(scan)]
    entry=pipeline.cache_directory(CACHE,source_hash,desc['id'])/'pages'/'0001.json'
    assert pipeline.cache_page(entry,source_hash,desc['id'],1)
    assert pipeline.cache_page(entry,'0'*64,desc['id'],1) is None
    assert pipeline.cache_page(entry,source_hash,'0'*64,1) is None
    assert pipeline.cache_page(entry,source_hash,desc['id'],2) is None
    record('缓存隔离：不同源内容、页码和引擎参数不误用')
    value=json.loads(entry.read_text(encoding='utf-8'));value['rows'][0][1]='损坏缓存'
    damaged=VERIFY/'damaged-cache.json';pipeline.atomic_json(damaged,value)
    assert pipeline.cache_page(damaged,source_hash,desc['id'],1) is None
    record('缓存内容哈希检测损坏')
    with pipeline.source_lock(CACHE,source_hash):
        try:
            with pipeline.source_lock(CACHE,source_hash):
                raise AssertionError('Expected lock rejection')
        except RuntimeError:
            pass
    record('同一源文件并发保护')
    for bad in ['0','3-2','1-9999','a','1,,2']:
        try:
            pipeline.parse_pages(bad,3);raise AssertionError(bad)
        except ValueError:
            pass
    record('无效页码范围拒绝')
    for path,old_hash in hashes.items():
        assert engine.file_hash(path)==old_hash
    record('所有测试原件哈希未改变')
    # Exercise a persisted failed page, then resume without rerunning its valid neighbour.
    failcache=VERIFY/'failure-cache'
    first_raw=engine.recognize(str(resume),1)
    def fail_second(path,number):
        if number==2:
            raise RuntimeError('故障注入：测试失败页重试')
        return first_raw
    try:
        pipeline.process_pdf(resume,output_root=OUTPUT,cache_root=failcache,
                             recognizer=fail_second,log=print)
        raise AssertionError('Expected failure')
    except RuntimeError as exc:
        assert '失败页' in str(exc)
    retried=pipeline.process_pdf(resume,output_root=OUTPUT,cache_root=failcache,workers=1,log=print)
    assert retried['cache_hits']==1 and retried['ocr_executed']==1
    record('失败页有记录且重试仅补失败页',fault_injection=True)
    # Re-selecting an output returns to its known original and cache.
    reselected=process(blended['output'])
    assert reselected['reused_output'] and reselected['output_sha256']==blended['output_sha256']
    record('重新选择已生成版本复用原件与缓存')
    summary={'passed':len(cases),'cases':cases,'fixtures_original_sha256':hashes,
             'mixed_result':blended,'text_result':digital,'scanned_result':scanned,
             'partial_result':partial,'resume_result':resumed}
    pipeline.atomic_json(VERIFY/'integration-results.json',summary)
    print(json.dumps({'passed':len(cases),'report':str(VERIFY/'integration-results.json')},ensure_ascii=False),flush=True)


if __name__=='__main__':
    run()
