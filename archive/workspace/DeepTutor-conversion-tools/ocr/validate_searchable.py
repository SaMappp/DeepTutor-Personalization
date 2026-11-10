# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
from collections import Counter
import hashlib
import json
import re
import time
import pymupdf
from pypdf import PdfReader
from make_searchable_rapid import SOURCE, OUTPUT, WORK, OUTDIR, CACHE, digest


def normalized(text):
    return re.sub(r'\s+', '', text)


def main():
    report = json.loads((WORK / 'processing-report.json').read_text(encoding='utf-8'))
    assert digest(SOURCE) == report['source_sha256']
    source = pymupdf.open(SOURCE)
    result = pymupdf.open(OUTPUT)
    assert len(source) == len(result) == 349
    assert source.get_toc() == result.get_toc()
    rows = []
    for index in range(len(source)):
        a, b = source[index], result[index]
        assert tuple(a.rect) == tuple(b.rect), index + 1
        assert a.rotation == b.rotation, index + 1
        before = a.get_pixmap(dpi=96, alpha=False)
        after = b.get_pixmap(dpi=96, alpha=False)
        exact = before.samples == after.samples
        if not exact:
            before.save(WORK / f'visual-difference-before-{index+1:03}.png')
            after.save(WORK / f'visual-difference-after-{index+1:03}.png')
        assert exact, f'Visible page changed: {index+1}'
        rows.append({'page': index + 1, 'source_chars': len(a.get_text().strip()),
                     'output_chars': len(b.get_text().strip()), 'pixels_identical': exact,
                     'source_annotations': sum(1 for _ in a.annots()),
                     'output_annotations': sum(1 for _ in b.annots())})
        assert rows[-1]['source_annotations'] == rows[-1]['output_annotations']
        if (index + 1) % 50 == 0:
            print('visual_pages_verified', index + 1, flush=True)
    probes = {13: ['函数与极限', '映射与函数'],
              30: ['收敛数列的性质', '极限的唯一性'],
              150: ['函数图像的描绘', '渐近线'],
              280: ['伯努利方程', '通解']}
    reader = PdfReader(str(OUTPUT))
    probe_results = []
    for number, phrases in probes.items():
        py_text = normalized(reader.pages[number - 1].extract_text() or '')
        mupdf_text = normalized(result[number - 1].get_text())
        for phrase in phrases:
            found = phrase in py_text and phrase in mupdf_text
            assert found, (number, phrase)
            probe_results.append({'page': number, 'phrase': phrase, 'both_extractors_found': found})
        result[number - 1].get_pixmap(dpi=144).save(WORK / f'final-page-{number:03}.png')
    # Exercise the actual installed DeepTutor reader parser without changing its stores.
    from deeptutor.reading.extract import extract_material
    extraction = extract_material(OUTPUT)
    assert len(extraction.units) == len(result)
    assert all(phrase in normalized(extraction.units[n - 1]) for n, phrases in probes.items() for phrase in phrases)
    summary = {'pages': len(result), 'original_sha256_unchanged': digest(SOURCE) == report['source_sha256'],
               'source_sha256': report['source_sha256'], 'output_sha256': digest(OUTPUT),
               'visual_pages_identical': sum(r['pixels_identical'] for r in rows),
               'bookmarks_preserved': True, 'annotations_preserved': True,
               'source_text_chars': sum(r['source_chars'] for r in rows),
               'output_text_chars': sum(r['output_chars'] for r in rows),
               'output_pages_with_text': sum(r['output_chars'] > 0 for r in rows),
               'output_pages_without_text': [r['page'] for r in rows if r['output_chars'] == 0],
               'sparse_pages_under_100_chars': [r for r in rows if r['output_chars'] < 100],
               'output_bytes': OUTPUT.stat().st_size,
               'deeptutor_extractor': extraction.extractor,
               'deeptutor_unit_count': len(extraction.units),
               'probes': probe_results, 'pages_detail': rows,
               'limitation': 'Chinese prose is searchable. Mathematical OCR has observed symbol and layout errors; verify formulas against the unchanged original page images.'}
    OUTDIR.mkdir(parents=True, exist_ok=True)
    (OUTDIR / 'OCR验证报告.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k != 'pages_detail'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
