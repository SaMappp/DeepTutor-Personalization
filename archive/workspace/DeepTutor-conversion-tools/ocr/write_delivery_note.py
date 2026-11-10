# SPDX-License-Identifier: AGPL-3.0-or-later
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import json
from make_searchable_rapid import SOURCE, OUTPUT, OUTDIR


def main():
    validation = json.loads((OUTDIR / 'OCR验证报告.json').read_text(encoding='utf-8'))
    imported = json.loads((OUTDIR / 'DeepTutor导入记录.json').read_text(encoding='utf-8'))
    text = f'''# 高等数学教材 OCR 阅读版说明

已生成保留原页面的可搜索 PDF，共 {validation['pages']} 页。原件未修改。

- 阅读版：`{OUTPUT.name}`
- 文字层：约 {validation['output_text_chars']:,} 个字符，{validation['output_pages_with_text']} 页包含可提取文字。
- 页面显示：逐页以 96 dpi 对照，{validation['visual_pages_identical']} 页像素一致；书签和原有 PDF 批注保留。
- DeepTutor：已加入桌面版 Calculus 工作区的「{imported['collection_title']}」阅读组，原材料继续保留。
- 阅读位置：OCR 版沿用原件的 PDF 第 {imported['new_material_position']['locator']} 页。PDF 页码包含封面、目录等，与书内印刷页码可能不同。

[打开 DeepTutor 阅读组]({imported['url']})，选择名称带「OCR可搜索版」的标签。已打开旧页面时，刷新后可见新标签。

## 识别质量和使用边界

此版适合正文搜索、选中文字、定位段落以及辅助解释。识别采用本地中文 OCR，教材未上传至外部 OCR 服务。

抽查发现数学符号仍有识别误差：如 x/α、v/u、0/O、上下标、极限、分式和多行公式。文字层并非经过逐式人工校对的公式文本。提问、抄题或引用公式时，以页面上的原图为准；必要时把对应题目截图交给支持看图的模型核对。

原来的扫描图像、笔记和公式外观均保留，不会因为文字层识别有误而改写页面上的公式。

## 验证记录

- `OCR验证报告.json`：原文件与输出校验值、逐页文字量、像素对照、跨解析器抽查结果。
- `DeepTutor导入记录.json`：实际导入材料、工作区、阅读组、段落提取验证与阅读位置。
- 原件：`{SOURCE}`
'''
    (OUTDIR / '阅读版使用说明.md').write_text(text, encoding='utf-8')
    print(str(OUTDIR / '阅读版使用说明.md'), flush=True)


if __name__ == '__main__':
    main()
