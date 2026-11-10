# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""One-time migration of the already running and verified Tianjin Calculus job."""
from pathlib import Path
import hashlib
import json
import time
import pymupdf
import engine
import pipeline


def main():
    academic = pipeline.ACADEMIC
    folder = academic/'Course materials'/'Calculus'/'OCR可搜索教材'
    report = json.loads((folder/'OCR验证报告.json').read_text(encoding='utf-8'))
    processing = json.loads((academic/'tmp'/'pdfs'/'calculus-ocr'/'processing-report.json').read_text(encoding='utf-8'))
    source = Path(processing['source']); output = Path(processing['output'])
    assert report['visual_pages_identical'] == report['pages'] == 349
    assert engine.file_hash(source) == report['source_sha256']
    assert engine.file_hash(output) == report['output_sha256']
    desc = engine.descriptor()
    provenance = json.loads((pipeline.ROOT/'legacy-provenance.json').read_text(encoding='utf-8'))
    assert provenance['engine_id'] == desc['id']
    assert provenance['source_sha256'] == report['source_sha256']
    provenance['running'] = False
    pipeline.atomic_json(pipeline.ROOT/'legacy-provenance.json',provenance)
    job = pipeline.cache_directory(pipeline.DEFAULT_CACHE, report['source_sha256'], desc['id'])
    count = pipeline.migrate_legacy(report['source_sha256'],desc,job/'pages',print)
    selected = list(range(1,350))
    for n in selected:
        assert pipeline.cache_page(job/'pages'/f'{n:04}.json',report['source_sha256'],desc['id'],n)
    plan = {'source_sha256':report['source_sha256'],'detector_version':pipeline.DETECTOR_VERSION,
            'engine_id':desc['id'],'selected_pages':selected}
    run_id = hashlib.sha256(json.dumps(plan,sort_keys=True).encode()).hexdigest()
    with pymupdf.open(source) as doc:
        artifacts = pipeline.repeated_artifacts(doc)
        decisions = {n:pipeline.classify(doc[n-1],artifacts) for n in selected}
    manifest = {**plan,'run_id':run_id,'source':str(source),'source_pages':349,'range':'1-349',
                'partial':False,'state':'complete','decisions':decisions,'failures':{},
                'cache_hits':349,'ocr_executed':0,'adopted_legacy_pages':349,
                'output':str(output),'output_sha256':report['output_sha256'],
                'validation':{'pages':349,'visual_pages_identical':349,'source_hash_unchanged':True,
                              'output_text_chars':report['output_text_chars'],'ocr_pages':selected,
                              'ocr_no_text_pages':[],'bookmarks_annotations_preserved':True},
                'completed_at':time.time(),'reused_output':True}
    pipeline.atomic_json(job/'source.json',{'path':str(source),'sha256':report['source_sha256'],'engine':desc})
    path = job/('run-'+run_id+'.json')
    pipeline.atomic_json(path,manifest)
    pipeline.atomic_json(output.with_suffix('.处理记录.json'),manifest)
    pipeline.register_output(pipeline.DEFAULT_CACHE,manifest,path)
    pipeline.write_note(output,manifest)
    pipeline.atomic_json(pipeline.ROOT/'current-book.json',manifest)
    pipeline.atomic_json(pipeline.ROOT/'tool-settings.json',{
        'output_root':str(pipeline.DEFAULT_OUTPUT),'workspace_id':'REDACTED_WORKSPACE_ID',
        'collection_id':'REDACTED_WORKSPACE_ID'})
    print(json.dumps({'cache_pages_migrated':count,'ocr_executed':0,'output':str(output)},ensure_ascii=False))


if __name__ == '__main__':
    main()
