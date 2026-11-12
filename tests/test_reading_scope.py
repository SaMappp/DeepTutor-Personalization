# SPDX-License-Identifier: Apache-2.0
"""Portable regression tests for whole-document versus single-page intent."""
import importlib.util
from pathlib import Path
import unittest

SOURCE = Path(__file__).resolve().parents[1] / 'overrides/desktop/deeptutor/reading/page_scope.py'
spec = importlib.util.spec_from_file_location('reading_page_scope', SOURCE)
scope_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope_module)
resolve = scope_module.resolve_page_scope


class ReadingScopeTests(unittest.TestCase):
    def test_complete_tasks_read_document(self):
        for text in [
            '按照这份作业的要求，生成Part A的答案.txt文件',
            '生成这份作业的完整答案',
            '允许读取 Part A 全部页',
            '我现在在第1页，请完成Part A的答案',
            '我只在第1页和第10页发了消息，请读取整个PDF文件',
            '阅读器仍限制为第1页是为什么，我已将完整的pdf文件放到资料库',
            '总结全文', '解答这份试卷', '读取整份作业',
            'Complete Part A answers', 'Solve this homework',
            'Read the entire PDF', 'Find the final question',
        ]:
            with self.subTest(text=text):
                result = resolve(text, {'locator': 10}, 21)
                self.assertEqual(result['mode'], 'document')
                self.assertEqual(result['pages'], list(range(1, 22)))

    def test_explicit_page_tasks_stay_bounded(self):
        for text, expected in [
            ('讲解当前页', [10]), ('只讲解第2页', [2]),
            ('不要全书总结，只讲解当前页', [10]),
            ('解答第2页的所有题', [2]), ('讲解第3至5页', [3, 4, 5]),
            ('只搜索当前页的函数名', [10]), ('Explain page 3', [3]),
            ('只读第二页', [2]), ('帮我解释这个概念', [10]),
        ]:
            with self.subTest(text=text):
                self.assertEqual(resolve(text, {'locator': 10}, 21)['pages'], expected)

    def test_continuation_inherits_user_task_only(self):
        history = [
            {'role': 'user', 'content': '生成 Part A 的答案'},
            {'role': 'assistant', 'content': '只能看到第1页，请重新上传文件'},
        ]
        self.assertEqual(resolve('继续按原要求', {'locator': 10}, 21, history)['mode'], 'document')
        self.assertEqual(resolve('只讲解当前页', {'locator': 10}, 21, history)['pages'], [10])
        self.assertEqual(resolve('继续', {'locator': 10}, 21, history[1:])['pages'], [10])
        history.append({'role': 'user', 'content': '讲解第2页'})
        self.assertEqual(resolve('继续', {'locator': 10}, 21, history)['pages'], [10])

    def test_invalid_pages_fail_honestly(self):
        for text in ['讲解第22页', '讲解第0页', '讲解第5至2页']:
            with self.assertRaises(ValueError):
                resolve(text, {'locator': 1}, 21)


if __name__ == '__main__':
    unittest.main()
