# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Add local Tesseract OCR text while retaining the original PDF page objects."""
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path
import argparse
import hashlib
import json
import os
import time

os.environ.setdefault('OMP_THREAD_LIMIT', '1')
os.environ.setdefault('OMP_NUM_THREADS', '1')
import pymupdf

ROOT = Path(__file__).resolve().parent
ACADEMIC = ROOT.parent.parent
SOURCE = Path(r'authorized-source.pdf')
OUTPUT_DIR = ACADEMIC / 'Course materials' / 'Calculus' / 'OCR可搜索教材'
OUTPUT = OUTPUT_DIR / '高等数学（上册）天津大学_OCR可搜索版.pdf'
WORK = ACADEMIC / 'tmp' / 'pdfs' / 'calculus-ocr'
CACHE = WORK / 'text-layers'
SAMPLE_PAGES = [12, 29, 149, 279]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def ocr_page(index):
    started = time.monotonic()
    cached = CACHE / f'{index + 1:04}.pdf'
    if cached.exists():
        with pymupdf.open(cached) as layer:
            text = layer[0].get_text()
        return {'page': index + 1, 'chars': len(text.strip()), 'seconds': 0, 'cached': True}
    with pymupdf.open(SOURCE) as original:
        pixmap = original[index].get_pixmap(dpi=300, colorspace=pymupdf.csRGB, alpha=False)
        encoded = pixmap.pdfocr_tobytes(language='chi_sim+eng', tessdata=str(ROOT / 'tessdata_best'))
    with pymupdf.open(stream=encoded, filetype='pdf') as layer:
        page = layer[0]
        # Keep OCR's Unicode maps and invisible text; discard only the redundant raster.
        for image in list(page.get_images(full=True)):
            page.delete_image(image[0])
        text = page.get_text()
        layer.save(cached, garbage=4, deflate=True)
    (CACHE / f'{index + 1:04}.txt').write_text(text, encoding='utf-8')
    return {'page': index + 1, 'chars': len(text.strip()),
            'seconds': round(time.monotonic() - started, 2), 'cached': False}


def assemble(indices, output, sample=False):
    with pymupdf.open(SOURCE) as original:
        if sample:
            target = pymupdf.open()
            for index in indices:
                target.insert_pdf(original, from_page=index, to_page=index, annots=True, links=True)
        else:
            target = original
        for target_index, source_index in enumerate(indices):
            page = target[target_index if sample else source_index]
            with pymupdf.open(CACHE / f'{source_index + 1:04}.pdf') as layer:
                page.show_pdf_page(page.rect, layer, 0, overlay=True, keep_proportion=False)
        meta = dict(target.metadata)
        meta['title'] = '高等数学（上册）天津大学 · OCR可搜索版'
        meta['keywords'] = (meta.get('keywords') or '') + '; OCR; chi_sim+eng; original appearance preserved'
        target.set_metadata(meta)
        output.parent.mkdir(parents=True, exist_ok=True)
        if output.exists():
            raise FileExistsError(f'Refusing to overwrite: {output}')
        target.save(output, garbage=3, deflate=True)
        if sample:
            target.close()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--sample', action='store_true')
    parser.add_argument('--workers', type=int, default=4)
    args = parser.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    source_hash = sha256(SOURCE)
    with pymupdf.open(SOURCE) as original:
        indices = SAMPLE_PAGES if args.sample else list(range(len(original)))
    rows = []
    started = time.monotonic()
    with ProcessPoolExecutor(max_workers=args.workers) as pool:
        futures = {pool.submit(ocr_page, n): n for n in indices}
        for future in as_completed(futures):
            row = future.result()
            rows.append(row)
            print(json.dumps({'done': len(rows), 'total': len(indices), **row}), flush=True)
    output = WORK / 'sample.pdf' if args.sample else OUTPUT
    assemble(indices, output, args.sample)
    assert sha256(SOURCE) == source_hash, 'Original PDF unexpectedly changed'
    report = {'source': str(SOURCE), 'source_sha256': source_hash, 'output': str(output),
              'pages': len(indices), 'ocr_language': 'chi_sim+eng', 'dpi': 300,
              'seconds': round(time.monotonic() - started, 2),
              'engine': 'PyMuPDF embedded Tesseract, tessdata_best',
              'original_preserved': True, 'page_results': sorted(rows, key=lambda r: r['page'])}
    (WORK / ('sample-report.json' if args.sample else 'processing-report.json')).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k != 'page_results'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
