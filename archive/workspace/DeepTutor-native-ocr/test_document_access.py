# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local validation/deployment script; configure your runtime paths before use.
"""Exercise the real reading capability/tools with synthetic PDFs and zero OCR."""
from pathlib import Path
from unittest.mock import patch
import asyncio
import json
import sys
import tempfile

import pymupdf

ROOT = Path(__file__).resolve().parent
CORE = Path(r'C:\Users\YOUR_NAME\AppData\Local\Open DeepTutor\runtimes\1.7.1-f7aed0744-x64\core')
sys.path.insert(0, str(ROOT / 'test-source'))
sys.path.insert(1, str(CORE))
from deeptutor.reading import ReadingStore, native_ocr
from deeptutor.reading.store import MAX_READ_CHARS
from deeptutor.core.context import UnifiedContext
from deeptutor.runtime.stream_bus import StreamBus
from deeptutor.capabilities.reading.capability import ReadingCapability
from deeptutor.capabilities.reading.tools import ReadMaterialTool, BINDING_KWARG, MATERIAL_KWARG


async def run():
    results = []
    with tempfile.TemporaryDirectory(prefix='document-access-', dir=ROOT / 'verification/full-document-fix') as temp:
        folder = Path(temp)
        config = json.loads((ROOT / 'configuration.json').read_text(encoding='utf-8'))
        config.update(root=str(folder), cache_root=str(folder/'cache'), shared_cache_root=str(folder/'shared'))
        cfg = folder/'configuration.json'; cfg.write_text(json.dumps(config), encoding='utf-8')
        native_ocr.CONFIG = cfg; native_ocr._configuration = None
        store = ReadingStore(folder/'reading')
        source = folder/'synthetic-assignment.pdf'
        doc = pymupdf.open()
        for page in range(1, 22):
            p = doc.new_page()
            for row in range(8):
                p.insert_text((40, 70+row*32), f'PAGE_{page:02}_UNIQUE_EVIDENCE row {row} complete assignment reading regression', fontsize=11)
        doc.save(source); doc.close()
        material = store.ingest(source)

        async def prepare(text, locator=10, history=()):
            ctx = UnifiedContext(user_message=text, session_id='scope-regression', language='zh',
                conversation_history=list(history), metadata={'reading_material_id':material.material_id,'reading_viewport':{'locator':locator}})
            stream = StreamBus()
            with patch('deeptutor.reading.ReadingStore', return_value=store):
                block = await ReadingCapability().pre_loop(ctx, stream)
            return ctx, block, stream

        with patch.object(native_ocr.subprocess, 'run', side_effect=AssertionError('Unexpected OCR subprocess')):
            ctx, block, bus = await prepare('按照这份作业的要求，生成Part A的答案.txt文件')
            binding = ctx.extension('reading')['tool_binding']
            assert binding['native_ocr_scope']['mode'] == 'document'
            assert all(f'PAGE_{page:02}_UNIQUE_EVIDENCE' in block.content for page in range(1, 22))
            results.append({'case':'section task receives all 21 native-text pages from viewport 10', 'passed':True})
            ctx, block, _ = await prepare('阅读器仍限制为第1页是为什么，我已上传完整的PDF文件')
            assert 'PAGE_10_UNIQUE_EVIDENCE' in block.content and 'PAGE_21_UNIQUE_EVIDENCE' in block.content
            results.append({'case':'diagnostic mentions of page 1 do not hide the full PDF', 'passed':True})
            ctx, block, _ = await prepare('讲解当前页', 10)
            assert 'PAGE_10_UNIQUE_EVIDENCE' in block.content and 'PAGE_01_UNIQUE_EVIDENCE' not in block.content
            with patch.object(ReadMaterialTool, '_store', return_value=store):
                response = await ReadMaterialTool().execute(**{MATERIAL_KWARG:material.material_id,
                    BINDING_KWARG:ctx.extension('reading')['tool_binding'], 'locators':'2-8'})
            assert response.success and 'PAGE_02_UNIQUE_EVIDENCE' in response.content and 'PAGE_08_UNIQUE_EVIDENCE' in response.content
            results.append({'case':'native text outside seed pages can be read without OCR or a permission error', 'passed':True})
            ctx, block, _ = await prepare('继续按原要求', 10, [{'role':'user','content':'生成Part A的答案'}, {'role':'assistant','content':'只能看到第1页'}])
            assert 'PAGE_21_UNIQUE_EVIDENCE' in block.content
            results.append({'case':'continued task overrides stale assistant access claims', 'passed':True})

        # Synthetic image-only pages: no OCR subprocess is executed by this suite.
        mixed = folder/'mixed.pdf'; doc = pymupdf.open(source)
        subset = pymupdf.open(); subset.insert_pdf(doc, from_page=0, to_page=0)
        for n in [1, 2]:
            p = subset.new_page(); p.insert_image(p.rect, pixmap=doc[n].get_pixmap(dpi=90))
        subset.save(mixed); subset.close(); doc.close()
        scan_material = store.ingest(mixed)
        ctx = UnifiedContext(user_message='生成整份作业答案', metadata={'reading_material_id':scan_material.material_id,'reading_viewport':{'locator':1}})
        bus = StreamBus()
        with patch('deeptutor.reading.ReadingStore', return_value=store), patch.object(native_ocr.subprocess, 'run', side_effect=AssertionError('Eager OCR')):
            block = await ReadingCapability().pre_loop(ctx, bus)
        assert block.content.count('text_source="not_read"') == 2
        results.append({'case':'cross-page preparation does not eagerly OCR unopened scan pages', 'passed':True})
        only_one = {'material_id':scan_material.material_id, 'mode':'pages', 'pages':[1]}
        with patch.object(native_ocr, 'ensure_page') as ensure:
            with patch.object(ReadMaterialTool, '_store', return_value=store):
                response = await ReadMaterialTool().execute(**{MATERIAL_KWARG:scan_material.material_id,
                    BINDING_KWARG:{'native_ocr_scope':only_one}, 'locators':'2-3'})
            assert not response.success and ensure.call_count == 0
        results.append({'case':'single-page task cannot start OCR on unrelated scan pages', 'passed':True})
        calls=[]
        def fake_recognizer(store, mid, page):
            calls.append(page)
            return {'page':page,'mode':'ocr','text':'recognized synthetic page evidence','seconds':.1}
        with patch.object(native_ocr, 'ensure_page', side_effect=fake_recognizer):
            read = await native_ocr.prepare_tool_pages(store, scan_material.material_id, [2],
                ctx.extension('reading')['tool_binding']['native_ocr_scope'], bus)
        assert read == [2] and calls == [2]
        assert any('第 2 页本机识别完成' in event.content for event in bus._history)
        results.append({'case':'authorized cross-page read prepares only requested page and emits progress', 'passed':True})
        with patch.object(native_ocr, 'cached_text', return_value='previous verified cache'), patch.object(native_ocr, 'ensure_page', return_value={'page':2,'mode':'cache','text':'previous verified cache','seconds':0}) as ensure:
            assert await native_ocr.prepare_tool_pages(store, scan_material.material_id, [2], only_one) == [2]
            assert ensure.call_count == 1
        results.append({'case':'existing scan cache outside seed pages remains readable without new OCR', 'passed':True})
        with patch.object(native_ocr, 'ensure_page', return_value={'page':1,'mode':'native','text':'x'*(MAX_READ_CHARS+1),'seconds':0}) as ensure:
            read = await native_ocr.prepare_tool_pages(store, material.material_id, [1,2,3], {'material_id':material.material_id,'mode':'document','pages':[1,2,3]})
            assert read == [1] and ensure.call_count == 1
        results.append({'case':'context budget stops before processing pages that cannot enter this batch', 'passed':True})
    report = {'passed':len(results),'tests':results,'real_ocr_subprocesses':0}
    (ROOT/'verification/full-document-fix/regression-results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False))


if __name__ == '__main__':
    asyncio.run(run())
