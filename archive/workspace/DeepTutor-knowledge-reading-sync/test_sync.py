# SPDX-License-Identifier: Apache-2.0
# Historical local customization; publication paths sanitized. Review docs before running.
from pathlib import Path
import importlib.util,tempfile,unittest,sys,sqlite3
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from deeptutor.reading.catalog_store import ReadingCatalogStore
from deeptutor.reading.store import ReadingStore
from deeptutor.reading.models import ReadingPosition
spec=importlib.util.spec_from_file_location('local_kb_sync',Path(__file__).parent/'patch/knowledge_sync.py');sync=importlib.util.module_from_spec(spec);spec.loader.exec_module(sync)
class SyncTests(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.root=Path(self.temp.name);self.kb=self.root/'knowledge/中文 KB';self.raw=self.kb/'raw';self.raw.mkdir(parents=True);self.catalog=ReadingCatalogStore(self.root/'reader')
 def tearDown(self):self.temp.cleanup()
 def source(self,name,text):
  p=self.raw/name;p.parent.mkdir(exist_ok=True,parents=True);p.write_text(text,encoding='utf-8');return p
 def run_sync(self):return sync._sync_kb(self.kb,catalog=self.catalog,force=True)
 def test_add_dedupe_and_original_bytes(self):
  p=self.source('chapter one.md','# Test chapter\n\nA parameter is a placeholder. 实参是调用值。');raw=p.read_bytes();a=self.run_sync();b=self.run_sync()
  self.assertEqual(a['added'],1);self.assertEqual(b['added'],0);self.assertEqual(b['reused'],1);self.assertFalse(b['failed']);self.assertEqual(len(self.catalog.list_materials()),1);self.assertEqual(p.read_bytes(),raw)
 def test_changed_same_filename_is_additive(self):
  p=self.source('notes.txt','First edition\nOriginal notes.');a=self.run_sync();p.write_text('Second edition\nChanged notes.',encoding='utf-8');b=self.run_sync();self.assertEqual(b['added'],1);self.assertEqual(len(self.catalog.get_workspace(a['collection_id']).tabs),2)
 def test_reuse_existing_collection_preserve_progress_and_title(self):
  p=self.source('a.md','# Alpha\nOriginal alpha.');q=self.source('b.md','# Beta\nOriginal beta.');store=ReadingStore(self.catalog.root);ids=[]
  for src in [p,q]:m=store.ingest(src);self.catalog.register_manifest(m);ids.append(m.material_id)
  collection=self.catalog.create_workspace('My existing lessons',ids);store.save_position(ids[0],ReadingPosition(locator=1,percentage=.55));before=store.position(ids[0]).to_dict();row=self.run_sync()
  self.assertEqual(row['collection_id'],collection.workspace_id);self.assertEqual(self.catalog.get_workspace(collection.workspace_id).title,'My existing lessons');self.assertEqual(store.position(ids[0]).to_dict(),before);self.assertEqual(len(self.catalog.list_workspaces()),1)
 def test_independent_reading_roots(self):
  self.source('a.txt','Source A');a=self.run_sync();other=ReadingCatalogStore(self.root/'another-reader');self.assertEqual(len(other.list_materials()),0);b=sync._sync_kb(self.kb,catalog=other);self.assertNotEqual(a['collection_id'],b['collection_id']);self.assertEqual(len(other.list_materials()),1)
 def test_failure_recovers_and_does_not_lose_other_sources(self):
  self.source('empty.txt','');self.source('ok.txt','Readable source');a=self.run_sync();self.assertEqual(a['added'],1);self.assertEqual(len(a['failed']),1);self.source('empty.txt','Now readable');b=self.run_sync();self.assertEqual(b['added'],1);self.assertFalse(b['failed'])
 def test_concurrent_calls_do_not_duplicate_collections(self):
  self.source('a.txt','Concurrent document')
  with ThreadPoolExecutor(max_workers=4) as pool:rows=list(pool.map(lambda _:self.run_sync(),range(4)))
  self.assertEqual(len(self.catalog.list_workspaces()),1);self.assertEqual(len(self.catalog.list_materials()),1);self.assertFalse(any(r['failed'] for r in rows))
 def test_no_ocr_or_model_side_effects(self):
  self.source('chapter.md','# No OCR\nText-native chapter.')
  with patch('subprocess.Popen',side_effect=AssertionError('No workers allowed')):row=self.run_sync()
  self.assertFalse(row['failed'])
if __name__=='__main__':unittest.main(verbosity=2)
