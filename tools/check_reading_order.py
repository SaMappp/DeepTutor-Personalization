# SPDX-License-Identifier: Apache-2.0
"""Regression for a Windows publish failure that used to reorder a KB batch."""
from importlib.util import module_from_spec, spec_from_file_location
import os
import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import patch

if os.environ.get("DEEPTUTOR_CORE"):
    sys.path.insert(0, os.environ["DEEPTUTOR_CORE"])

from deeptutor.reading import store
from deeptutor.reading.catalog_store import ReadingCatalogStore
from deeptutor.reading.models import ReadingPosition

ROOT = Path(__file__).resolve().parents[1]


def load_patch(name):
    path = ROOT / "overrides/desktop/deeptutor/reading" / f"{name}.py"
    spec = spec_from_file_location(f"reading_order_{name}", path)
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ReadingOrderTests(unittest.TestCase):
    def test_upload_order_retry_and_manual_order_persist(self):
        staged_store = load_patch("store")
        sync = load_patch("knowledge_sync")
        replace = os.replace
        failures = []

        def replace_once(source, dest):
            if isinstance(source, Path) and source.name.endswith(".staging") and not failures:
                failures.append(source)
                error = PermissionError("synthetic Windows sharing conflict")
                error.winerror = 5
                raise error
            replace(source, dest)

        with TemporaryDirectory() as temp:
            root = Path(temp)
            raw = root / "kb" / "raw"
            raw.mkdir(parents=True)
            for name in ["z-first.txt", "a-second.txt", "b-third.txt"]:
                (raw / name).write_text(f"Document {name}", encoding="utf-8")
            reader = root / "reader"
            catalog = ReadingCatalogStore(reader)
            order = ["z-first.txt", "a-second.txt", "b-third.txt"]
            with patch.object(sync, "ReadingStore", staged_store.ReadingStore), patch.object(os, "replace", replace_once):
                result = sync._sync_kb(raw.parent, catalog=catalog, uploaded_paths=order)
            self.assertEqual(len(failures), 1)
            self.assertEqual(result["failed"], [])
            collection_id = result["collection_id"]
            collection = catalog.get_workspace(collection_id)
            self.assertEqual([tab.material.filename for tab in collection.tabs], order)
            first = collection.tabs[0].material.material_id
            position_store = store.ReadingStore(reader)
            position_store.save_position(first, ReadingPosition(locator=1, percentage=.43))
            before = position_store.position(first).to_dict()
            order_ids = [tab.material.material_id for tab in reversed(collection.tabs)]
            catalog.reorder_materials(collection_id, order_ids)
            (raw / "new.txt").write_text("New document", encoding="utf-8")
            sync._sync_kb(raw.parent, catalog=catalog, uploaded_paths=["new.txt"])
            after = ReadingCatalogStore(reader).get_workspace(collection_id)
            self.assertEqual([tab.material.material_id for tab in after.tabs[:-1]], order_ids)
            self.assertEqual(after.tabs[-1].material.filename, "new.txt")
            self.assertEqual(after.active_material_id, collection.active_material_id)
            self.assertEqual(position_store.position(first).to_dict(), before)

    def test_permanent_error_is_not_hidden(self):
        staged_store = load_patch("store")
        error = PermissionError("synthetic permanent filesystem error")
        error.winerror = 1314
        with patch.object(os, "replace", side_effect=error) as rename:
            with self.assertRaises(PermissionError):
                staged_store._publish_ingested_material(Path("stage"), Path("destination"))
            self.assertEqual(rename.call_count, 1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
