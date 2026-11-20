# SPDX-License-Identifier: Apache-2.0
"""Upgrade legacy slide records from byte-matching originals in the same workspace."""
import argparse
import datetime
from hashlib import sha256
import json
from pathlib import Path
import shutil
import sqlite3

from deeptutor.reading.catalog_store import ReadingCatalogStore
from deeptutor.reading.store import ReadingStore

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace-data", type=Path, required=True)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--backup-dir", type=Path, help="Private directory for an offline backup")
    args = parser.parse_args()
    if args.apply and args.backup_dir is None:
        parser.error("--apply requires --backup-dir; stop the target runtime before migration")
    scope = args.workspace_data.resolve(strict=True)
    reader = scope / "user/workspace/reading"
    db = reader / "_catalog.sqlite3"
    if not db.is_file():
        raise SystemExit("No reading catalog under this workspace data root")
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as conn:
        rows = conn.execute(
            """SELECT DISTINCT content_id FROM reading_materials WHERE render_mode='text'
               AND (lower(filename) LIKE '%.pptx' OR lower(filename) LIKE '%.ppt')"""
        ).fetchall()
    expected = {content_id for (content_id,) in rows}
    originals = {}
    for candidate in (scope / "knowledge_bases").rglob("*"):
        if candidate.suffix.lower() not in {".ppt", ".pptx"} or not candidate.is_file():
            continue
        if not candidate.resolve().is_relative_to(scope) or "raw" not in candidate.relative_to(scope).parts:
            continue
        content_id = sha256(candidate.read_bytes()).hexdigest()[:16]
        if content_id in expected:
            originals.setdefault(content_id, candidate)
    print(json.dumps({"legacy": len(expected), "exact_originals": len(originals), "apply": args.apply}))
    if not args.apply or not originals:
        return
    stamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup = args.backup_dir.resolve() / f"legacy-{stamp}"
    if backup.is_relative_to(scope):
        raise SystemExit("Choose a backup directory outside the target data root")
    backup.mkdir(parents=True)
    with sqlite3.connect(db.as_uri() + "?mode=ro", uri=True) as src, sqlite3.connect(backup / db.name) as dest:
        src.backup(dest)
    store = ReadingStore(reader)
    catalog = ReadingCatalogStore(reader)
    collections_before = {
        row.workspace_id: (row.active_material_id, [tab.material.material_id for tab in row.tabs])
        for row in catalog.list_workspaces(limit=500)
    }
    succeeded = 0
    for content_id, original in originals.items():
        content_dir = reader / content_id
        if content_dir.resolve().parent != reader.resolve() or not content_dir.is_dir():
            continue
        shutil.copytree(content_dir, backup / content_id)
        old = store.manifest(content_id)
        updated = store.ingest(original)
        assert updated.material_id == content_id
        assert updated.unit_count == old.unit_count and updated.render_mode == "pdf"
        assert store.manifest(content_id).render_mode == "pdf"
        # Positions, notes, highlights and bookmarks must survive byte-for-byte.
        for name in ("positions", "annotations", "bookmarks", "position.json", "annotations.json"):
            saved = backup / content_id / name
            files = [saved] if saved.is_file() else list(saved.rglob("*"))
            for file in files:
                if file.is_file():
                    relative = file.relative_to(backup / content_id)
                    assert file.read_bytes() == (content_dir / relative).read_bytes(), relative
        succeeded += 1
        print(json.dumps({"updated": succeeded, "pages": updated.unit_count}), flush=True)
    collections_after = {
        row.workspace_id: (row.active_material_id, [tab.material.material_id for tab in row.tabs])
        for row in catalog.list_workspaces(limit=500)
    }
    assert collections_before == collections_after
    print(json.dumps({"upgraded": succeeded, "unmatched": len(expected - originals.keys()), "collections_preserved": True}))


if __name__ == "__main__":
    main()
