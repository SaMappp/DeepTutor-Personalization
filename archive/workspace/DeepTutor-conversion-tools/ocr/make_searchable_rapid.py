# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Local Chinese OCR, invisible positioned text, and unchanged original pages."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import argparse
import hashlib
import json
import os
import sys
import time

os.environ.setdefault('OMP_NUM_THREADS', '1')
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / 'runtime'))
import pymupdf
import numpy as np

ACADEMIC = ROOT.parent.parent
SOURCE = Path(r'authorized-source.pdf')
OUTDIR = ACADEMIC / 'Course materials' / 'Calculus' / 'OCR可搜索教材'
OUTPUT = OUTDIR / '高等数学（上册）天津大学_OCR可搜索版.pdf'
WORK = ACADEMIC / 'tmp' / 'pdfs' / 'calculus-ocr'
CACHE = WORK / 'rapid-pages'
FONT_PATH = Path(r'C:\Windows\Fonts\msyh.ttc')
SAMPLES = [12, 29, 149, 279]
ENGINE = None


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def initialize():
    global ENGINE
    import onnxruntime as ort
    original_options = ort.SessionOptions

    def options():
        opts = original_options()
        opts.intra_op_num_threads = 1
        opts.inter_op_num_threads = 1
        return opts

    ort.SessionOptions = options
    import cv2
    cv2.setNumThreads(1)
    from rapidocr_onnxruntime import RapidOCR
    ENGINE = RapidOCR(det_model_path=None, det_limit_side_len=1536,
                      det_limit_type='max', use_angle_cls=False, text_score=0.35)


def recognize(index):
    started = time.monotonic()
    path = CACHE / f'{index + 1:04}.json'
    if path.exists():
        row = json.loads(path.read_text(encoding='utf-8'))
        return {k: row[k] for k in ['page', 'chars', 'line_count']} | {'cached': True}
    with pymupdf.open(SOURCE) as document:
        page = document[index]
        pix = page.get_pixmap(dpi=300, colorspace=pymupdf.csRGB, alpha=False)
        array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        rows, timing = ENGINE(array[:, :, ::-1].copy())
        rows = rows or []
        row = {'page': index + 1, 'width': pix.width, 'height': pix.height,
               'rows': rows, 'times': timing,
               'chars': sum(len(r[1]) for r in rows), 'line_count': len(rows),
               'seconds': round(time.monotonic() - started, 2)}
    path.write_text(json.dumps(row, ensure_ascii=False), encoding='utf-8')
    return {k: row[k] for k in ['page', 'chars', 'line_count', 'seconds']} | {'cached': False}


def add_text(page, data, font):
    page.wrap_contents()
    page.insert_font(fontname='OCRText', fontbuffer=font.buffer)
    shape = page.new_shape()
    sx = page.rect.width / data['width']
    sy = page.rect.height / data['height']
    for box, text, confidence in data['rows']:
        text = text.strip()
        if not text:
            continue
        x0 = min(p[0] for p in box) * sx
        y0 = min(p[1] for p in box) * sy
        x1 = max(p[0] for p in box) * sx
        y1 = max(p[1] for p in box) * sy
        height = max(y1 - y0, 1)
        fontsize = height / (font.ascender - font.descender)
        point = pymupdf.Point(x0, y0 + font.ascender * fontsize)
        width = max(font.text_length(text, fontsize=fontsize), 0.01)
        matrix = pymupdf.Matrix(max(x1 - x0, 0.01) / width, 1)
        shape.insert_text(point, text, fontname='OCRText', fontsize=fontsize,
                          render_mode=3, morph=(point, matrix))
    shape.commit(overlay=True)


def assemble(indices, output, sample):
    font = pymupdf.Font(fontfile=str(FONT_PATH))
    with pymupdf.open(SOURCE) as original:
        target = pymupdf.open() if sample else original
        if sample:
            for index in indices:
                target.insert_pdf(original, from_page=index, to_page=index, annots=True)
        for i, index in enumerate(indices):
            data = json.loads((CACHE / f'{index + 1:04}.json').read_text(encoding='utf-8'))
            add_text(target[i if sample else index], data, font)
        meta = dict(target.metadata)
        meta['title'] = '高等数学（上册）天津大学 · OCR可搜索版'
        meta['keywords'] = (meta.get('keywords') or '') + '; searchable OCR; original pages preserved'
        target.set_metadata(meta)
        target.subset_fonts()
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            raise FileExistsError(output)
        target.save(output, garbage=4, deflate=True)
        if sample:
            target.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', action='store_true')
    parser.add_argument('--workers', type=int, default=6)
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    # Reuse the manually reviewed pilot results.
    for n in SAMPLES:
        pilot = ROOT / f'rapid-sample-{n+1:03}.json'
        cache = CACHE / f'{n+1:04}.json'
        if pilot.exists() and not cache.exists():
            data = json.loads(pilot.read_text(encoding='utf-8'))
            with pymupdf.open(SOURCE) as source:
                pix = source[n].get_pixmap(dpi=300, alpha=False)
            data.update(width=pix.width, height=pix.height,
                        chars=sum(len(r[1]) for r in data['rows']), line_count=len(data['rows']))
            cache.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
    with pymupdf.open(SOURCE) as original:
        indices = SAMPLES if args.sample else list(range(len(original)))
    source_hash = digest(SOURCE)
    started = time.monotonic()
    rows = []
    with ProcessPoolExecutor(max_workers=args.workers, initializer=initialize) as pool:
        futures = [pool.submit(recognize, index) for index in indices]
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            if args.sample or len(rows) % 5 == 0 or len(rows) == len(indices):
                print(json.dumps({'done': len(rows), 'total': len(indices), **row}), flush=True)
    output = WORK / 'sample-rapid.pdf' if args.sample else OUTPUT
    assemble(indices, output, args.sample)
    assert digest(SOURCE) == source_hash
    report = {'source': str(SOURCE), 'source_sha256': source_hash,
              'output': str(output), 'pages': len(indices),
              'seconds': round(time.monotonic() - started, 2),
              'engine': 'RapidOCR 1.2.3 / Chinese PP-OCRv3 / ONNX Runtime CPU',
              'dpi': 300, 'detection_max_side': 1536, 'original_preserved': True,
              'page_results': sorted(rows, key=lambda r: r['page'])}
    (WORK / ('sample-rapid-report.json' if args.sample else 'processing-report.json')).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k!='page_results'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
