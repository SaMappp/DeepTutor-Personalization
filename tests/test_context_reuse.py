# SPDX-License-Identifier: Apache-2.0
"""Dependency-free cache regressions; all content and identities are synthetic."""
import importlib.util
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / 'overrides/desktop/deeptutor/capabilities/explore_context/reuse.py'
spec = importlib.util.spec_from_file_location('context_reuse_cache', SOURCE)
reuse = importlib.util.module_from_spec(spec)
spec.loader.exec_module(reuse)


def context():
    return SimpleNamespace(session_id='synthetic-session', language='zh', active_capability='chat',
        runtime=SimpleNamespace(workspace=SimpleNamespace(workspace_id='synthetic-workspace')),
        metadata={'source_index': {'at-synthetic': 'alpha'}, 'exploration_message_id': '1',
                  'exploration_lineage': [], 'llm_model': 'synthetic-model'})


class ContextReuseCacheTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.cache = reuse.InvestigationCache(Path(self.tmp.name))

    def test_nearest_ancestor_excludes_sibling(self):
        self.cache.save('key', '1', 'q1', 'ancestor')
        self.cache.save('key', '3', 'q2', 'sibling')
        self.assertEqual(self.cache.load('key', ['1', '2']), ('q1', 'ancestor'))
        self.assertIsNone(self.cache.load('key', ['9']))

    def test_changed_sources_and_identity_invalidate(self):
        key = reuse.cache_key(context())
        for field in ('source', 'session', 'workspace', 'language', 'model'):
            changed = context()
            if field == 'source': changed.metadata['source_index']['at-synthetic'] = 'different'
            if field == 'session': changed.session_id = 'other-session'
            if field == 'workspace': changed.runtime.workspace.workspace_id = 'other-workspace'
            if field == 'language': changed.language = 'en'
            if field == 'model': changed.metadata['llm_model'] = 'other-model'
            self.assertNotEqual(reuse.cache_key(changed), key, field)

    def test_missing_branch_identity_disables_reuse(self):
        changed = context()
        changed.metadata['exploration_lineage'] = None
        self.assertIsNone(reuse.cache_key(changed))
        changed = context()
        changed.metadata['exploration_message_id'] = ''
        self.assertIsNone(reuse.cache_key(changed))

    def test_account_directories_are_isolated(self):
        self.cache.save('key', '1', 'question', 'private summary')
        other = Path(self.tmp.name) / 'other-account'
        other.mkdir()
        self.assertIsNone(reuse.InvestigationCache(other).load('key', ['1']))

    def test_invalid_or_corrupt_cache_falls_back(self):
        self.assertFalse(self.cache.save('key', '1', 'q', ''))
        self.assertFalse(self.cache.save('key', '1', 'q', 'x' * (reuse.MAX_BRIEFING_CHARS + 1)))
        self.cache.path.write_bytes(b'corrupt sqlite test')
        self.assertIsNone(self.cache.load('key', ['1']))
        self.assertFalse(self.cache.save('key', '1', 'q', 'summary'))

    def test_capacity_and_reused_prompt_preserve_scope(self):
        with patch.object(reuse, 'MAX_ENTRIES', 2):
            for i in range(3): self.cache.save('key', str(i), 'question', 'summary')
        self.assertIsNone(self.cache.load('key', ['0']))
        self.assertIsNotNone(self.cache.load('key', ['2']))
        prompt = reuse.reused_briefing('old question', 'old facts', language='zh')
        self.assertIn('历史调查', prompt)
        self.assertIn('read_source', prompt)
        self.assertIn('其他 AI', prompt)


if __name__ == '__main__':
    unittest.main()
