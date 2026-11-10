# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Page classification, content-addressed OCR cache, safe output and verification."""
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from contextlib import contextmanager
from pathlib import Path
import hashlib
import json
import msvcrt
import os
import re
import shutil
import time
import uuid
import ctypes
import pymupdf
import engine

ROOT = Path(__file__).resolve().parent
ACADEMIC = ROOT.parent.parent
DEFAULT_OUTPUT = ACADEMIC / 'Course materials' / 'PDF教材自动处理输出'
DEFAULT_CACHE = ROOT / 'cache'
DETECTOR_VERSION = 2


class Paused(Exception):
    pass


def atomic_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.parent / ('.tmp-' + uuid.uuid4().hex[:12])
    try:
        temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


@contextmanager
def source_lock(cache_root, source_hash):
    path = Path(cache_root) / 'locks' / (source_hash + '.lock')
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('a+b') as stream:
        stream.seek(0, 2)
        if stream.tell() == 0:
            stream.write(b'0')
            stream.flush()
        stream.seek(0)
        try:
            msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
        except OSError:
            raise RuntimeError('另一个工具任务正在处理同一份 PDF，请等待或继续该任务。') from None
        try:
            yield
        finally:
            stream.seek(0)
            msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)


def parse_pages(expression, count):
    expression = expression.strip().replace('，', ',').replace('–', '-').replace('－', '-')
    if not expression or expression.lower() in ['all', '全部']:
        return list(range(1, count + 1))
    result = set()
    for part in expression.split(','):
        match = re.fullmatch(r'\s*(\d+)\s*(?:-\s*(\d+))?\s*', part)
        if not match:
            raise ValueError('页码格式应为 1-10,15,20-25；留空表示全书。')
        first = int(match[1]); last = int(match[2] or match[1])
        if not 1 <= first <= last <= count:
            raise ValueError(f'PDF 共 {count} 页，页码范围无效：{part}')
        result.update(range(first, last + 1))
    return sorted(result)


def compact_pages(pages):
    parts = []
    for number in pages:
        if parts and number == parts[-1][-1] + 1:
            parts[-1].append(number)
        else:
            parts.append([number])
    return ','.join(str(p[0]) if len(p) == 1 else f'{p[0]}-{p[-1]}' for p in parts)


def meaningful(text):
    text = re.sub(r'\[(?:图片|Image|image)\s*\d+(?::[^\]]*)?\]', '', text)
    return ''.join(re.findall(r'[A-Za-z\u3400-\u9fff]', text))


def repeated_artifacts(document):
    counts = Counter()
    for page in document:
        lines = {re.sub(r'\s+', '', x) for x in page.get_text().splitlines()}
        counts.update(x for x in lines if 0 < len(x) <= 80)
    threshold = max(5, int(len(document) * 0.6 + 0.99))
    return {text for text, count in counts.items() if count >= threshold}


def classify(page, artifacts=frozenset()):
    bounds = page.rect
    body = pymupdf.Rect(bounds.x0 + bounds.width * .05, bounds.y0 + bounds.height * .08,
                        bounds.x1 - bounds.width * .05, bounds.y1 - bounds.height * .08)
    total = 0; body_chars = 0; long_lines = 0; ys = []
    for block in page.get_text('dict')['blocks']:
        if block['type'] != 0:
            continue
        for line in block['lines']:
            text = ''.join(span['text'] for span in line['spans'])
            if re.sub(r'\s+', '', text) in artifacts:
                continue
            chars = len(meaningful(text))
            total += chars
            rect = pymupdf.Rect(line['bbox'])
            center = (rect.tl + rect.br) / 2
            if body.contains(center):
                body_chars += chars
                if chars >= 8 and rect.width >= bounds.width * .12:
                    long_lines += 1
                    ys.append(center.y)
    coverage = 0.0
    for item in page.get_image_info():
        rect = pymupdf.Rect(item['bbox']) & bounds
        coverage = max(coverage, rect.get_area() / max(bounds.get_area(), 1))
    spread = (max(ys) - min(ys)) / bounds.height if len(ys) > 1 else 0
    sufficient = total >= 200 and body_chars >= 140 and long_lines >= 4 and spread >= .20
    if sufficient:
        action = 'reuse_text'; reason = '正文量、长文本行和页面分布足够，复用已有文字层'
    elif coverage >= .45:
        action = 'ocr'; reason = '大面积扫描图且正文文字不足；页码、少量笔记不视为正文'
    elif total < 30 and len(page.get_drawings()) > 80:
        action = 'ocr'; reason = '存在大量矢量轮廓但缺少可提取正文'
    elif coverage >= .15 and body_chars < 60:
        action = 'ocr'; reason = '图像页缺少可提取正文，尝试本地 OCR'
    elif total:
        action = 'reuse_text'; reason = '原生短文字页，保留已有文字'
    else:
        action = 'blank'; reason = '空白或无正文的非扫描页，原样保留'
    return {'action': action, 'reason': reason, 'meaningful_chars': total,
            'body_chars': body_chars, 'long_lines': long_lines,
            'image_coverage': round(coverage, 4), 'text_vertical_spread': round(spread, 4)}


def cache_page(path, source_hash, engine_id, number):
    try:
        data = json.loads(Path(path).read_text(encoding='utf-8'))
        if (data.get('source_sha256') != source_hash or data.get('engine_id') != engine_id
                or data.get('page') != number or data.get('status') != 'ok'):
            return None
        content = {k:v for k,v in data.items() if k != 'result_sha256'}
        if data.get('result_sha256') != hashlib.sha256(json.dumps(content, sort_keys=True).encode()).hexdigest():
            return None
        validate_rows(data)
        return data
    except (OSError, ValueError, TypeError, KeyError):
        return None


def validate_rows(data):
    if not data['width'] > 0 or not data['height'] > 0 or not isinstance(data['rows'], list):
        raise ValueError('OCR 缓存尺寸或内容无效')
    for box, text, score in data['rows']:
        if len(box) != 4 or not isinstance(text, str):
            raise ValueError('OCR 缓存文本框无效')
        if not 0 <= float(score) <= 1:
            raise ValueError('OCR 缓存置信度无效')


def save_page(path, raw, source_hash, engine_id):
    validate_rows(raw)
    data = {**raw, 'source_sha256': source_hash, 'engine_id': engine_id, 'status': 'ok'}
    data['result_sha256'] = hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()
    atomic_json(path, data)
    return data


def migrate_legacy(source_hash, descriptor, destination, log):
    provenance_path = ROOT / 'legacy-provenance.json'
    if not provenance_path.exists():
        return 0
    value = json.loads(provenance_path.read_text(encoding='utf-8'))
    if value['source_sha256'] != source_hash or value['engine_id'] != descriptor['id']:
        return 0
    if value.get('running'):
        completed = Path(value['completion_report'])
        finished = False
        if completed.exists():
            try:
                report = json.loads(completed.read_text(encoding='utf-8'))
                finished = report.get('source_sha256') == source_hash and report.get('pages') == value['page_count']
            except (ValueError, OSError):
                pass
        active = False
        if value.get('pid'):
            kernel = ctypes.WinDLL('kernel32', use_last_error=True)
            kernel.OpenProcess.restype = ctypes.c_void_p
            handle = kernel.OpenProcess(0x1000, False, int(value['pid']))
            if handle:
                status = ctypes.c_ulong()
                kernel.GetExitCodeProcess(ctypes.c_void_p(handle), ctypes.byref(status))
                kernel.CloseHandle(ctypes.c_void_p(handle))
                active = status.value == 259
        if not finished and (active or not value.get('pid')):
            raise RuntimeError('这本教材原有的全书 OCR 正在运行。为避免重复处理，请等原任务完成后重试；现有缓存不会丢失。')
    count = 0
    for old in Path(value['cache_directory']).glob('*.json'):
        try:
            raw = json.loads(old.read_text(encoding='utf-8'))
            target = destination / f"{raw['page']:04}.json"
            if cache_page(target, source_hash, descriptor['id'], raw['page']):
                continue
            # Import only the exact source, engine/model signatures and parameters attested here.
            raw = {key: raw[key] for key in ['page', 'width', 'height', 'rows', 'times']}
            save_page(target, raw, source_hash, descriptor['id']); count += 1
        except (OSError, KeyError, ValueError, TypeError):
            continue
    if count:
        log(f'已迁移本书之前完成的 {count} 页 OCR 缓存，无需重新识别。')
    return count


def insert_layer(page, data, font):
    page.wrap_contents()
    page.insert_font(fontname='TextbookOCR', fontbuffer=font.buffer)
    shape = page.new_shape()
    sx = page.rect.width / data['width']; sy = page.rect.height / data['height']
    for box, text, confidence in data['rows']:
        text = text.strip()
        if not text:
            continue
        x0 = min(p[0] for p in box) * sx; x1 = max(p[0] for p in box) * sx
        y0 = min(p[1] for p in box) * sy; y1 = max(p[1] for p in box) * sy
        height = max(y1 - y0, 1)
        size = height / (font.ascender - font.descender)
        point = pymupdf.Point(x0, y0 + font.ascender * size)
        advance = max(font.text_length(text, fontsize=size), .01)
        shape.insert_text(point, text, fontname='TextbookOCR', fontsize=size, render_mode=3,
                          morph=(point, pymupdf.Matrix(max(x1-x0, .01) / advance, 1)))
    shape.commit(overlay=True)


def normalized(text):
    return re.sub(r'\s+', '', text)


def process_pdf(source, page_expression='', output_root=DEFAULT_OUTPUT, cache_root=DEFAULT_CACHE,
                workers=2, log=print, progress=lambda done,total: None, stop=None,
                recognizer=None):
    source = Path(source).resolve(strict=True)
    if source.suffix.lower() != '.pdf':
        raise ValueError('只能处理 PDF 文件。')
    source_hash = engine.file_hash(source)
    index_path = Path(cache_root) / 'outputs' / (source_hash + '.json')
    if index_path.exists():
        try:
            known = json.loads(index_path.read_text(encoding='utf-8'))
            original = Path(known['source']).resolve()
            if original != source and original.is_file() and engine.file_hash(original) == known['source_sha256']:
                log('所选文件是已生成的阅读版，复用其原件与缓存继续处理。')
                return process_pdf(original, page_expression, output_root, cache_root, workers,
                                   log, progress, stop, recognizer)
        except (OSError, ValueError, KeyError):
            pass
    desc = engine.descriptor()
    job_root = cache_directory(cache_root, source_hash, desc['id'])
    pages_root = job_root / 'pages'
    with source_lock(cache_root, source_hash):
        job_root.mkdir(parents=True, exist_ok=True)
        atomic_json(job_root / 'source.json', {'path': str(source), 'sha256': source_hash, 'engine': desc})
        migrate_legacy(source_hash, desc, pages_root, log)
        with pymupdf.open(source) as document:
            if document.is_encrypted and not document.authenticate(''):
                raise ValueError('PDF 已加密，请先提供可直接打开的副本。')
            count = len(document)
            selected = parse_pages(page_expression, count)
            artifacts = repeated_artifacts(document)
            decisions = {n: classify(document[n-1], artifacts) for n in selected}
        plan = {'source_sha256': source_hash, 'detector_version': DETECTOR_VERSION,
                'engine_id': desc['id'], 'selected_pages': selected}
        run_id = hashlib.sha256(json.dumps(plan, sort_keys=True).encode()).hexdigest()
        manifest_path = job_root / ('run-' + run_id + '.json')
        if manifest_path.exists():
            previous = json.loads(manifest_path.read_text(encoding='utf-8'))
            old = Path(previous.get('output', ''))
            if previous.get('state') == 'complete' and old.is_file() and engine.file_hash(old) == previous.get('output_sha256'):
                log('输出已存在且哈希验证通过，直接复用：' + str(old))
                register_output(cache_root, previous, manifest_path)
                progress(len(selected), len(selected))
                return {**previous, 'reused_output': True}
        manifest = {**plan, 'run_id': run_id, 'source': str(source), 'source_pages': count,
                    'range': compact_pages(selected), 'partial': len(selected) != count,
                    'state': 'processing', 'decisions': decisions, 'failures': {},
                    'cache_hits': 0, 'ocr_executed': 0}
        def persist():
            atomic_json(manifest_path, manifest)
        persist()
        needs_ocr = [n for n in selected if decisions[n]['action'] == 'ocr']
        ready = len(selected) - len(needs_ocr)
        pending = []
        for n in needs_ocr:
            cached = cache_page(pages_root / f'{n:04}.json', source_hash, desc['id'], n)
            if cached is not None:
                manifest['cache_hits'] += 1; ready += 1
            else:
                pending.append(n)
        log(f'共 {count} 页；本次 PDF 物理页码 {compact_pages(selected)}。已有文字/空白页 {len(selected)-len(needs_ocr)}，OCR 缓存命中 {manifest["cache_hits"]}，待识别 {len(pending)}。')
        progress(ready, len(selected)); persist()
        def accept(number, raw):
            nonlocal ready
            save_page(pages_root / f'{number:04}.json', raw, source_hash, desc['id'])
            manifest['ocr_executed'] += 1; ready += 1
            log(f'第 {number} 页识别完成（{sum(len(r[1]) for r in raw["rows"])} 字符）')
            progress(ready, len(selected)); persist()
        def failure(number, exc):
            manifest['failures'][str(number)] = {'error': str(exc), 'time': time.time()}
            log(f'第 {number} 页失败：{exc}；重新运行会仅重试失败/未完成页。'); persist()
        if pending:
            if recognizer is not None:
                for n in pending:
                    if stop is not None and stop.is_set():
                        break
                    try:
                        accept(n, recognizer(str(source), n))
                    except Exception as exc:
                        failure(n, exc)
            else:
                # Bounded scheduling avoids a queue of hundreds of running pages on pause.
                with ProcessPoolExecutor(max_workers=max(1, min(workers, 4))) as pool:
                    queue = iter(pending); futures = {}
                    def fill():
                        while len(futures) < max(1, min(workers, 4)) and not (stop is not None and stop.is_set()):
                            n = next(queue, None)
                            if n is None:
                                break
                            futures[pool.submit(engine.recognize, str(source), n)] = n
                    fill()
                    while futures:
                        future = next(as_completed(futures))
                        number = futures.pop(future)
                        try:
                            accept(number, future.result())
                        except Exception as exc:
                            failure(number, exc)
                        fill()
        if stop is not None and stop.is_set():
            manifest['state'] = 'paused'; persist()
            raise Paused('已暂停，已完成页面已保存；再次开始会自动续作。')
        if manifest['failures']:
            manifest['state'] = 'failed'; persist()
            raise RuntimeError('存在失败页，未发布不完整结果。错误记录：' + str(manifest_path))
        for n in needs_ocr:
            if cache_page(pages_root / f'{n:04}.json', source_hash, desc['id'], n) is None:
                raise RuntimeError(f'第 {n} 页缓存校验失败，请重试。')
        destination = Path(output_root).resolve() / (source.stem[:32] + '_' + source_hash[:8])
        destination.mkdir(parents=True, exist_ok=True)
        range_label = 'OCR可搜索版' if not manifest['partial'] else 'OCR部分_第' + (compact_pages(selected)[:35].replace(',', '_')) + '页'
        path = destination / (source.stem[:32] + '_' + range_label + '_' + run_id[:8] + '.pdf')
        if path.exists():
            base = path; version = 2
            while path.exists():
                path = base.with_stem(base.stem + f'_v{version}'); version += 1
        temporary = destination / ('.processing-' + uuid.uuid4().hex + '.pdf')
        try:
            if not needs_ocr:
                shutil.copyfile(source, temporary)
            else:
                with pymupdf.open(source) as document:
                    font = pymupdf.Font(fontfile=str(Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Fonts' / 'msyh.ttc'))
                    for n in needs_ocr:
                        raw = cache_page(pages_root / f'{n:04}.json', source_hash, desc['id'], n)
                        insert_layer(document[n-1], raw, font)
                    meta = dict(document.metadata)
                    meta['subject'] = '本地 OCR。已处理 PDF 物理页码：' + compact_pages(selected) + ('；其他页面保持原样，未宣称已 OCR。' if manifest['partial'] else '（全书）。') + '公式请核对原图。'
                    document.set_metadata(meta); document.subset_fonts()
                    document.save(temporary, garbage=4, deflate=True)
            log('正在逐页验证页数、原件哈希、页面显示和文字提取……')
            validation = validate(source, temporary, needs_ocr, pages_root, source_hash, desc['id'])
            if engine.file_hash(source) != source_hash:
                raise RuntimeError('处理期间源文件发生改变，停止发布；请重新选择文件。')
            # The final name is tool-owned and was confirmed absent; never overwrite the source.
            os.rename(temporary, path)
            manifest.update(state='complete', output=str(path), output_sha256=engine.file_hash(path),
                            validation=validation, completed_at=time.time(), reused_output=False)
            persist()
            register_output(cache_root, manifest, manifest_path)
            atomic_json(path.with_suffix('.处理记录.json'), manifest)
            write_note(path, manifest)
            log('已保存：' + str(path))
            return manifest
        finally:
            temporary.unlink(missing_ok=True)


def register_output(cache_root, manifest, manifest_path):
    atomic_json(Path(cache_root) / 'outputs' / (manifest['output_sha256'] + '.json'),
                {k:manifest[k] for k in ['source','source_sha256','output','output_sha256']} |
                {'manifest_path': str(manifest_path)})


def cache_directory(cache_root, source_hash, engine_id):
    # Full digests remain in every entry and are checked on read. Short directory
    # components keep Windows paths below MAX_PATH without changing OS settings.
    return Path(cache_root) / source_hash[:32] / engine_id[:24]


def validate(source, output, ocr_pages, cache_root, source_hash, engine_id):
    with pymupdf.open(source) as a, pymupdf.open(output) as b:
        if len(a) != len(b) or a.get_toc() != b.get_toc():
            raise RuntimeError('输出页数或目录与原件不一致。')
        chars = 0; zero_ocr_pages = []; identity = 0; all_text = []
        for n in range(1, len(a)+1):
            p, q = a[n-1], b[n-1]
            if p.rect != q.rect or p.rotation != q.rotation:
                raise RuntimeError(f'第 {n} 页尺寸或旋转改变。')
            if sum(1 for _ in p.annots()) != sum(1 for _ in q.annots()):
                raise RuntimeError(f'第 {n} 页原批注数量改变。')
            if p.get_pixmap(dpi=96, alpha=False).samples != q.get_pixmap(dpi=96, alpha=False).samples:
                raise RuntimeError(f'第 {n} 页可见内容改变，未发布结果。')
            identity += 1
            text = q.get_text(); chars += len(text.strip()); all_text.append(text)
            if n in ocr_pages:
                raw = cache_page(Path(cache_root)/f'{n:04}.json', source_hash, engine_id, n)
                if not raw['rows']:
                    zero_ocr_pages.append(n)
                expected = [r[1].strip() for r in raw['rows'] if len(meaningful(r[1])) >= 6]
                if any(meaningful(line) not in meaningful(text) for line in expected):
                    raise RuntimeError(f'第 {n} 页的 OCR 文字层无法完整提取。')
        return {'pages': len(a), 'visual_pages_identical': identity,
                'source_hash_unchanged': engine.file_hash(source) == source_hash,
                'output_text_chars': chars, 'ocr_pages': ocr_pages,
                'ocr_no_text_pages': zero_ocr_pages, 'bookmarks_annotations_preserved': True}


def write_note(path, manifest):
    text = f'''# PDF 教材处理说明

原件保留，输出共 {manifest['source_pages']} 页，页序、图像、公式原图和原有 PDF 笔记均保留。
本次已检查/处理的 PDF 物理页码：{manifest['range']}（{'部分范围，其他页保持原样' if manifest['partial'] else '全书'}）。物理页码从 PDF 第一页开始计数，可能不同于书内印刷页码。

已有足够正文的页面复用原文字层；扫描页使用本地中文 OCR 添加不可见文字层。教材不上传外部 OCR 服务。

公式、上下标和手写批注可能识别有误，文字层不是逐式校对版。抄题和核对公式请看保留的原图。

已逐页验证页面显示，{manifest['validation']['visual_pages_identical']} 页在 96 dpi 下与原件像素一致；原件哈希未改变。没有识别出文字的 OCR 页：{manifest['validation']['ocr_no_text_pages']}（可能为空白、插图或识别失败，需要按原图判断）。

旁边的 `.处理记录.json` 保存页级判断、缓存命中、处理范围及验证结果。导入后的记录另存为 `.DeepTutor导入.json`。
'''
    path.with_suffix('.使用说明.md').write_text(text, encoding='utf-8')
