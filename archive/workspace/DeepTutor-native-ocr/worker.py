# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
"""One process, one requested page; no directory scans or automatic book jobs."""
from pathlib import Path
import argparse
import json
import sys
import time

ROOT=Path(__file__).resolve().parent
CFG=json.loads((ROOT/'configuration.json').read_text(encoding='utf-8'))
sys.path.insert(0,CFG['tool_root'])
import engine
import pipeline


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source',required=True)
    parser.add_argument('--page',required=True,type=int)
    parser.add_argument('--source-hash',required=True)
    parser.add_argument('--engine-id',required=True)
    parser.add_argument('--output',required=True)
    args=parser.parse_args()
    if engine.file_hash(args.source)!=args.source_hash:
        raise RuntimeError('原文件内容哈希不匹配，拒绝使用其他文件的缓存。')
    descriptor=engine.descriptor()
    if descriptor['id']!=args.engine_id:
        raise RuntimeError('OCR 模型或关键参数改变，请更新本地按需 OCR 配置后重试。')
    started=time.monotonic()
    raw=engine.recognize(args.source,args.page)
    if len(pipeline.meaningful(''.join(r[1] for r in raw['rows'])))<5:
        raise RuntimeError('本页未识别出可用正文，可能是空白、纯图或低质量扫描；未将空白结果当作读取成功。可再次提问重试。')
    pipeline.save_page(Path(args.output),raw,args.source_hash,args.engine_id)
    print(json.dumps({'page':args.page,'seconds':round(time.monotonic()-started,3),'engine_id':descriptor['id']}),flush=True)


if __name__=='__main__':
    main()
