# SPDX-License-Identifier: AGPL-3.0-or-later
# Modified by SaMappp for native reading; see NOTICE and docs/CHANGE_INVENTORY.md.
"""Resolve reading task scope without treating the viewport as file permission."""
import re

NUMBER = r'[0-9零〇一二两三四五六七八九十百千]+'
CURRENT = r'当前页|这一页|这页|本页|this page|current page'


def chinese_number(value):
    if value.isdigit():
        return int(value)
    digits = dict(zip('零〇一二两三四五六七八九', [0, 0, 1, 2, 2, 3, 4, 5, 6, 7, 8, 9]))
    total = current = 0
    for ch in value:
        if ch in digits:
            current = digits[ch]
        elif ch in '十百千':
            total += (current or 1) * {'十': 10, '百': 100, '千': 1000}[ch]
            current = 0
        else:
            raise ValueError(value)
    return total + current


def _clean(text):
    return re.sub(r'(?:不要|不必|无需|不需要|不用)[^，。；;!?！？\n]*', '', text)


def _document_intent(text):
    text = _clean(text)
    if re.search(
        r'全书|全文|整本|整份|整个(?:\s*(?:PDF|文件|文档|作业|试卷))|所有页|全部页|跨页|'
        r'完整(?:的)?\s*(?:PDF|文件|文档|作业|试卷)|'
        r'\b(?:whole|entire)\s+(?:book|document|file|pdf|assignment|homework)|\ball pages\b', text, re.I
    ):
        return 'whole_document'
    section = re.search(r'(?<![a-z])(?:part|section)\s*[a-z0-9]+(?![a-z0-9])|第' + NUMBER + r'部分', text, re.I)
    if section and re.search(r'答案|作答|解答|完成|做完|全部|完整|answers?|solve|complete', text, re.I):
        return 'section_task'
    if re.search(r'作业|试卷|assignment|homework', text, re.I) and re.search(r'答案|解答|做完|完成|answers?|solve|complete', text, re.I):
        return 'assignment_task'
    if re.search(r'完整答案|全部题|所有题|每道题|all (?:questions|answers)|every question', text, re.I):
        return 'all_questions'
    if re.search(r'查找|检索|搜索|在哪[一几]?页|\b(?:search|find|locate)\b|where.*(?:book|document)', text, re.I):
        return 'document_search'
    return None


def resolve_page_scope(question, viewport, count, history=()):
    """Explicit single-page work stays bounded; whole/section work may cross pages.

    Scope controls *new OCR*, not access to existing text in the open file.
    Only user turns can supply a continued task, never assistant claims or PDF text.
    """
    if count < 1:
        raise ValueError('PDF 没有可读取页面。')
    text = _clean(str(question or ''))
    current = int(viewport.get('locator') or 1)
    pages = set()
    for match in re.finditer(r'第?\s*(' + NUMBER + r')\s*(?:[-—–至到]\s*第?\s*(' + NUMBER + r'))?\s*页', text):
        a = chinese_number(match[1]); b = chinese_number(match[2]) if match[2] else a
        if not 1 <= a <= b <= count:
            raise ValueError(f'PDF 物理页码范围无效，本文件共 {count} 页。')
        pages.update(range(a, b + 1))
    for match in re.finditer(r'\b(?:pages?|p\.)\s*(\d+)(?:\s*[-–]\s*(\d+))?', text, re.I):
        a = int(match[1]); b = int(match[2] or a)
        if not 1 <= a <= b <= count:
            raise ValueError(f'PDF 物理页码范围无效，本文件共 {count} 页。')
        pages.update(range(a, b + 1))

    def single(reason):
        selected = sorted(pages) if pages else [current]
        if not all(1 <= p <= count for p in selected):
            raise ValueError(f'当前 PDF 页码无效，本文件共 {count} 页。')
        return {'mode': 'pages', 'pages': selected, 'reason': reason}

    bounded = re.search(r'(?:只(?:需要|需)?|仅(?:需)?|就)(?:要)?\s*(?:你|帮我|为我|给我|请|对)?\s*(?:讲解|解释|解答|回答|读取|阅读|读|看|处理|分析|总结|搜索|检索|查找)?\s*(?:PDF\s*)?(?:' + CURRENT + r'|第?\s*' + NUMBER + r'\s*(?:[-—–至到]\s*第?\s*' + NUMBER + r')?\s*页)', text, re.I)
    if bounded:
        return single('explicit_page_only')
    intent = _document_intent(text)
    if intent in {'whole_document', 'section_task', 'assignment_task'}:
        return {'mode': 'document', 'pages': list(range(1, count + 1)), 'reason': intent}
    if pages or re.search(CURRENT, text, re.I):
        return single('requested_pages')
    if intent:
        return {'mode': 'document', 'pages': list(range(1, count + 1)), 'reason': intent}
    if re.search(r'继续|按(?:照)?(?:原|之前|上次).{0,8}(?:要求|任务)|接着|\bcontinue\b|\bgo ahead\b', text, re.I):
        for row in reversed(list(history)[-20:]):
            if row.get('role') != 'user' or not isinstance(row.get('content'), str):
                continue
            prior = row['content']
            if _document_intent(prior) and not re.search(r'(?:只|仅).{0,8}(?:' + CURRENT + ')', _clean(prior), re.I):
                return {'mode': 'document', 'pages': list(range(1, count + 1)), 'reason': 'continued_document_task'}
            # An intervening explicit page task replaces an older document task.
            if re.search(CURRENT, prior, re.I) or re.search(r'第\s*' + NUMBER + r'\s*页', prior):
                break
    return single('viewport_default')
