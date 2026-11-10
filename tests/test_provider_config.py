# SPDX-License-Identifier: Apache-2.0
import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('provider_config', ROOT / 'tools/provider_config.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ProviderTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.settings = Path(self.temp.name)
        self.catalog = {'services': {'llm': {'active_profile_id': 'original', 'active_model_id': 'original-model'}}}
        (self.settings / 'model_catalog.json').write_text(json.dumps(self.catalog))
        self.config = json.loads((ROOT / 'examples/provider.example.json').read_text())
        self.config['targets'][0]['settings_dir'] = str(self.settings)
        self.env = patch.dict(os.environ, DEEPTUTOR_PROVIDER_API_KEY='unit-test-placeholder')
        self.env.start()
        self.addCleanup(self.env.stop)
        self.writes = []

    def call(self, base, path, payload=None):
        if path.endswith('/runtime'):
            return {'owner_turn_count': 0}
        if payload:
            self.writes.append(payload)
        return {'catalog': self.catalog}

    def test_preflight_performs_no_writes_or_backups(self):
        with patch.object(module, 'call', side_effect=self.call):
            self.assertEqual(module.configure(self.config)['writes'], 0)
        self.assertEqual(self.writes, [])
        self.assertFalse((self.settings / 'backups').exists())

    def test_active_turn_prevents_all_writes(self):
        with patch.object(module, 'call', return_value={'owner_turn_count': 1}):
            with self.assertRaises(RuntimeError):
                module.configure(self.config, True)
        self.assertFalse((self.settings / 'backups').exists())

    def test_apply_preserves_default_and_makes_private_backup(self):
        with patch.object(module, 'call', side_effect=self.call):
            self.assertTrue(module.configure(self.config, True)['default_selection_preserved'])
        self.assertFalse(self.writes[0]['activate'])
        backups = list((self.settings / 'backups').glob('*/model_catalog.json'))
        self.assertEqual(json.loads(backups[0].read_text()), self.catalog)

    def test_replacing_active_default_profile_is_refused(self):
        self.config['profile_id'] = 'original'
        with patch.object(module, 'call', side_effect=self.call), self.assertRaises(ValueError):
            module.configure(self.config, True)
        self.assertEqual(self.writes, [])

    def test_remote_target_and_embedded_credentials_rejected(self):
        for value in ['https://example.com', 'http://example.com:8001', 'http://user:pass@127.0.0.1:8001', 'http://localhost:8001/redirect']:
            with self.subTest(value=value), self.assertRaises(ValueError):
                module.local_url(value)

    def test_redirect_does_not_forward_credentials(self):
        self.assertIsNone(module.NoRedirect().redirect_request(None, None, 302, '', {}, 'https://example.com'))


if __name__ == '__main__':
    unittest.main()
