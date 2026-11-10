# SPDX-License-Identifier: Apache-2.0
# Modified by SaMappp from HKUDS/DeepTutor v1.7.1; see NOTICE and docs/CHANGE_INVENTORY.md.
"""Local, additive KB-to-reader synchronization in the current account/workspace.

No model calls, embeddings, captions, OCR or deletions are performed here.
Knowledge indexes and original source documents are never modified.
"""
from __future__ import annotations

from contextlib import contextmanager
import hashlib
import logging
from pathlib import Path
import sqlite3
import threading
import time

from deeptutor.reading.catalog_store import ReadingCatalogStore
from deeptutor.reading.store import ReadingStore
from deeptutor.utils.document_validator import DocumentValidator

logger = logging.getLogger(__name__)
_GUARD = threading.Lock()
_LOCKS: dict[str, threading.RLock] = {}
_RECENT: dict[str, tuple[float, dict]] = {}


def _lock(root: Path):
    with _GUARD:
        return _LOCKS.setdefault(str(root.resolve()), threading.RLock())


@contextmanager
def _database(root: Path):
    con = sqlite3.connect(root / '_knowledge_sync.sqlite3', timeout=30)
    con.row_factory = sqlite3.Row
    try:
        with con:
            con.executescript('''
                CREATE TABLE IF NOT EXISTS kb_collections (
                    kb_root TEXT PRIMARY KEY, collection_id TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS kb_documents (
                    kb_root TEXT NOT NULL, relative_path TEXT NOT NULL,
                    size INTEGER NOT NULL, mtime_ns INTEGER NOT NULL,
                    content_id TEXT NOT NULL, material_id TEXT NOT NULL,
                    status TEXT NOT NULL, error TEXT NOT NULL DEFAULT '',
                    updated_at REAL NOT NULL,
                    PRIMARY KEY(kb_root, relative_path)
                );
            ''')
            yield con
    finally:
        con.close()


def _permitted() -> bool:
    from deeptutor.multi_user.learning_access import assert_learning_material
    try:
        assert_learning_material('', upload=True)
        return True
    except PermissionError:
        # A restricted learning account cannot gain upload rights through sync.
        return False


def _source_files(raw: Path):
    if not raw.is_dir():
        return []
    root = raw.resolve()
    return sorted((p for p in raw.rglob('*') if p.is_file()
                   and not p.is_symlink() and p.resolve().is_relative_to(root)
                   and not any(s.startswith('.') for s in p.relative_to(raw).parts)
                   and p.suffix.lower() in DocumentValidator.ALLOWED_EXTENSIONS),
                  key=lambda p: p.relative_to(raw).as_posix().casefold())


def _hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()[:16]


def _sync_kb(kb_root: Path, *, catalog: ReadingCatalogStore, force: bool = False) -> dict:
    kb_root = kb_root.resolve()
    raw = kb_root / 'raw'
    paths = _source_files(raw)
    result = {'knowledge_base': kb_root.name, 'collection_id': '', 'added': 0,
              'reused': 0, 'failed': [], 'documents': len(paths)}
    if not paths:
        return result
    store = ReadingStore(catalog.root)
    with _lock(catalog.root), _database(catalog.root) as con:
        key = str(kb_root)
        saved = {r['relative_path']: dict(r) for r in con.execute(
            'SELECT * FROM kb_documents WHERE kb_root=?', (key,))}
        prepared = []
        for path in paths:
            rel = path.relative_to(raw).as_posix()
            st = path.stat()
            prev = saved.get(rel)
            unchanged = bool(prev and prev['size'] == st.st_size
                             and prev['mtime_ns'] == st.st_mtime_ns)
            cid = prev['content_id'] if unchanged and prev['content_id'] else _hash(path)
            prepared.append((path, rel, st, prev, unchanged, cid))
        membership = con.execute('SELECT collection_id FROM kb_collections WHERE kb_root=?', (key,)).fetchone()
        collection = catalog.get_workspace(membership[0]) if membership else None
        if collection is None:
            # Reuse a clearly matching pre-existing collection, preserving its
            # name, active material, sessions, order and every old tab.
            collections = catalog.list_workspaces(limit=500)
            exact = [w for w in collections if w.title in {kb_root.name, '知识中心 · ' + kb_root.name}]
            source_ids = {p[-1] for p in prepared}
            owned_elsewhere = {r[0] for r in con.execute(
                'SELECT collection_id FROM kb_collections WHERE kb_root<>?', (key,))}
            subset = [w for w in collections if w.workspace_id not in owned_elsewhere
                      and len(w.tabs) >= 2
                      and {t.material.material_id for t in w.tabs}.issubset(source_ids)]
            if len(exact) == 1:
                collection = exact[0]
            elif len(subset) == 1:
                collection = subset[0]
        if collection is not None:
            result['collection_id'] = collection.workspace_id
        known = {t.material.material_id for t in collection.tabs} if collection else set()
        for path, rel, st, prev, unchanged, cid in prepared:
            if (unchanged and prev['status'] == 'failed' and not force
                    and time.time() - prev['updated_at'] < 30):
                result['failed'].append({'file': rel, 'error': prev['error']})
                continue
            try:
                if st.st_size > DocumentValidator.MAX_FILE_SIZE:
                    raise ValueError('Document exceeds the reader file-size limit')
                mid = prev['material_id'] if unchanged and prev['material_id'] else cid
                record = catalog.get_material(mid)
                if record is None:
                    manifest = store.ingest(path, filename=path.name)
                    mid = manifest.material_id
                    # Do not rewrite an existing material's user-selected title.
                    if catalog.get_material(mid) is None:
                        catalog.register_manifest(manifest)
                if path.stat().st_mtime_ns != st.st_mtime_ns or path.stat().st_size != st.st_size:
                    raise ValueError('Source changed during synchronization; retry after saving')
                if collection is None:
                    collection = catalog.create_workspace(
                        '知识中心 · ' + kb_root.name, [mid],
                        description='知识中心新增文档自动同步；按内容去重，保留已有阅读批注与进度。删除知识库文件不会自动删除阅读记录。',
                        color='teal')
                    known.add(mid)
                    result['added'] += 1
                    result['collection_id'] = collection.workspace_id
                elif mid not in known:
                    catalog.add_material(collection.workspace_id, mid, make_active=False)
                    known.add(mid)
                    result['added'] += 1
                else:
                    result['reused'] += 1
                con.execute('INSERT OR REPLACE INTO kb_collections VALUES (?,?)',
                            (key, collection.workspace_id))
                con.execute('INSERT OR REPLACE INTO kb_documents VALUES (?,?,?,?,?,?,?,?,?)',
                            (key, rel, st.st_size, st.st_mtime_ns, cid, mid, 'ready', '', time.time()))
            except Exception as exc:
                error = str(exc)[:1000]
                con.execute('INSERT OR REPLACE INTO kb_documents VALUES (?,?,?,?,?,?,?,?,?)',
                            (key, rel, st.st_size, st.st_mtime_ns, cid, '', 'failed', error, time.time()))
                result['failed'].append({'file': rel, 'error': error})
                logger.warning('KB-to-reader sync failed for %s/%s: %s', kb_root.name, rel, error)
    return result


def sync_visible_knowledge(*, force: bool = False) -> dict:
    """Reconcile sources visible in this exact reading/account scope.

    Called off the event loop when entering the reading collection/library.
    It also recovers missed CLI additions, linked-folder syncs and restarts.
    """
    if not _permitted():
        return {'knowledge_bases': [], 'skipped': 'reading uploads are restricted'}
    from deeptutor.multi_user.knowledge_access import list_visible_knowledge_bases, resolve_kb
    catalog = ReadingCatalogStore()
    root_key = str(catalog.root.resolve())
    with _lock(catalog.root):
        previous = _RECENT.get(root_key)
        if not force and previous and time.monotonic() - previous[0] < 2:
            return previous[1]
        results = []
        try:
            entries = list_visible_knowledge_bases()
        except Exception as exc:
            logger.warning('Unable to enumerate knowledge sources for reading sync: %s', exc)
            return {'knowledge_bases': [], 'error': str(exc)[:500]}
        for item in entries:
            try:
                resource = resolve_kb(item['id'])
                results.append(_sync_kb(Path(resource.base_dir) / resource.name,
                                        catalog=catalog, force=force))
            except Exception as exc:
                logger.warning('Unable to sync visible knowledge source %s: %s', item.get('name'), exc)
                results.append({'knowledge_base': item.get('name'), 'error': str(exc)[:500]})
        answer = {'knowledge_bases': results}
        _RECENT[root_key] = (time.monotonic(), answer)
        return answer


def sync_saved_documents(raw_dir: Path | str) -> dict:
    """Upload hook: resolve the actual KB owner, never trust a caller path/id.

    Failure does not undo a successfully saved knowledge upload. The next
    reading visit retries it, and the status endpoint reports any error.
    """
    try:
        from deeptutor.services.workspace.knowledge import workspace_id_for_kb_base_dir
        from deeptutor.services.workspace.context import workspace_context
        raw = Path(raw_dir).resolve()
        if raw.name != 'raw':
            return {'skipped': 'not a local document directory'}
        owner = workspace_id_for_kb_base_dir(raw.parent.parent)
        if owner is None:
            return {'skipped': 'unregistered knowledge storage'}
        with workspace_context(owner):
            if not _permitted():
                return {'skipped': 'reading uploads are restricted'}
            catalog = ReadingCatalogStore()
            with _lock(catalog.root):
                result = _sync_kb(raw.parent, catalog=catalog, force=True)
                _RECENT.pop(str(catalog.root.resolve()), None)
                return result
    except Exception as exc:
        logger.warning('Saved KB documents will be retried by the reader: %s', exc)
        return {'error': str(exc)[:500]}

