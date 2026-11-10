# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import argparse
import json
from pipeline import process_pdf, DEFAULT_OUTPUT
from deeptutor_client import DeepTutorClient, DESKTOP


def main():
    parser = argparse.ArgumentParser(description='本地 PDF 教材 OCR 与 DeepTutor 导入工具')
    parser.add_argument('files', nargs='*')
    parser.add_argument('--pages', default='', help='PDF 物理页码；留空全书，例如 1-10,20')
    parser.add_argument('--output', default=str(DEFAULT_OUTPUT))
    parser.add_argument('--workers', type=int, default=2)
    parser.add_argument('--base', default=DESKTOP)
    parser.add_argument('--workspace')
    parser.add_argument('--collection')
    parser.add_argument('--list-targets', action='store_true')
    args = parser.parse_args()
    client = DeepTutorClient(args.base)
    try:
        if args.list_targets:
            for workspace in client.workspaces():
                print(json.dumps({'workspace':workspace,
                    'collections':client.collections(workspace['workspace_id'])},ensure_ascii=False))
            return
        if bool(args.workspace) != bool(args.collection):
            parser.error('--workspace 和 --collection 必须一起指定')
        for file in args.files:
            result = process_pdf(file, args.pages, output_root=args.output, workers=args.workers)
            if args.workspace:
                client.import_pdf(result,args.workspace,args.collection)
    finally:
        client.close()


if __name__ == '__main__':
    main()
