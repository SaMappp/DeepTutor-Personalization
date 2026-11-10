# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""Offline Chinese OCR shared by the GUI and the resumable PDF pipeline."""
from pathlib import Path
import hashlib
import importlib.metadata
import json
import os
import sys

ROOT = Path(__file__).resolve().parent
TOOLS = ROOT.parent
RUNTIME = TOOLS / 'ocr' / 'runtime'
sys.path.insert(0, str(RUNTIME))
PARAMETERS = {'dpi': 300, 'detection_max_side': 1536, 'detection_limit_type': 'max',
              'angle_classifier': False, 'text_score': 0.35,
              'onnx_intra_threads': 1, 'onnx_inter_threads': 1}
_ENGINE = None


def file_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(block)
    return h.hexdigest()


def descriptor():
    models = RUNTIME / 'rapidocr_onnxruntime' / 'models'
    required = ['ch_PP-OCRv3_det_infer.onnx', 'ch_PP-OCRv3_rec_infer.onnx']
    for name in required:
        if not (models / name).is_file():
            raise RuntimeError('本地 OCR 模型缺失：' + str(models / name))
    import pymupdf
    value = {'engine': 'RapidOCR', 'version': importlib.metadata.version('rapidocr-onnxruntime'), 'parameters': PARAMETERS,
             'models': {name: file_hash(models / name) for name in required},
             'onnxruntime': importlib.metadata.version('onnxruntime'),
             'pymupdf': str(pymupdf.version[:2]), 'text_layer_version': 2,
             'font_sha256': file_hash(Path(os.environ.get('WINDIR', r'C:\Windows')) / 'Fonts' / 'msyh.ttc')}
    value['id'] = hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()
    return value


def initialize():
    global _ENGINE
    if _ENGINE is not None:
        return
    os.environ.setdefault('OMP_NUM_THREADS', '1')
    import onnxruntime as ort
    original = ort.SessionOptions

    def options():
        obj = original()
        obj.intra_op_num_threads = 1
        obj.inter_op_num_threads = 1
        return obj

    ort.SessionOptions = options
    import cv2
    cv2.setNumThreads(1)
    from rapidocr_onnxruntime import RapidOCR
    _ENGINE = RapidOCR(det_model_path=None, det_limit_side_len=1536,
                       det_limit_type='max', use_angle_cls=False, text_score=0.35)


def recognize(source, page_number):
    import pymupdf
    import numpy as np
    initialize()
    with pymupdf.open(source) as document:
        pix = document[page_number - 1].get_pixmap(dpi=300, colorspace=pymupdf.csRGB, alpha=False)
        array = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, 3)
        rows, timings = _ENGINE(array[:, :, ::-1].copy())
        return {'page': page_number, 'width': pix.width, 'height': pix.height,
                'rows': rows or [], 'times': timings}
