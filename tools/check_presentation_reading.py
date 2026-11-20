# SPDX-License-Identifier: Apache-2.0
"""Real LibreOffice regression using generated slides and a temporary reader."""
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
from importlib.util import module_from_spec, spec_from_file_location
import os
from pathlib import Path
import subprocess
import sys
from tempfile import TemporaryDirectory
from unittest.mock import patch

from pptx import Presentation
from pptx.util import Inches
import pymupdf
from deeptutor.reading.catalog_store import ReadingCatalogStore as LegacyCatalog
from deeptutor.reading.models import ReadingError, ReadingPosition
from deeptutor.reading.store import ReadingStore as LegacyStore

ROOT = Path(__file__).resolve().parents[1]


def overlay(name, layer):
    source = ROOT / "overrides" / layer / (name.replace(".", "/") + ".py")
    spec = spec_from_file_location(name, source)
    module = module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def make_deck(path):
    deck = Presentation()
    for index, keyword in enumerate(["Jade", "Hidden", "Amber"], 1):
        slide = deck.slides.add_slide(deck.slide_layouts[5])
        slide.shapes.title.text = f"Page {index} {keyword}"
        slide.shapes.add_textbox(Inches(1), Inches(3), Inches(8), Inches(2)).text = (
            f"Searchable sentence {index}. Reading imports preserve the original slide layout."
        )
        if index == 2:
            slide._element.set("show", "0")
    deck.save(path)


def main(layer):
    with TemporaryDirectory() as directory:
        work = Path(directory)
        source = work / "Synthetic 课件.pptx"
        make_deck(source)
        digest = sha256(source.read_bytes()).hexdigest()
        legacy_root = work / "legacy"
        old_store = LegacyStore(legacy_root)
        old = old_store.ingest(source)
        assert old.unit == "slide" and old.unit_count == 3
        old_catalog = LegacyCatalog(legacy_root)
        old_catalog.register_manifest(old)
        collection = old_catalog.create_workspace("Synthetic course", [old.material_id])
        old_store.save_position(old.material_id, ReadingPosition(locator=2, percentage=0.53))
        position = old_store.position(old.material_id).to_dict()

        if layer == "desktop":
            overlay("deeptutor.reading.native_ocr", layer)
        service = overlay("deeptutor.services.office_preview", layer)
        catalog_class = overlay("deeptutor.reading.catalog_store", layer).ReadingCatalogStore
        store_module = overlay("deeptutor.reading.store", layer)
        store_class = store_module.ReadingStore
        assert service._office_executable(), "LibreOffice not resolved"
        store = store_class(work / "reader")
        catalog = catalog_class(store.root)
        with patch.object(store_module, "render_presentation_pdf", wraps=service.render_presentation_pdf) as render:
            with ThreadPoolExecutor(2) as pool:
                first = pool.submit(store.ingest, source)
                second = pool.submit(store_class(store.root).ingest, source)
                imported = first.result()
                assert second.result() == imported
            assert render.call_count == 1
        catalog.register_manifest(imported)
        assert imported.render_mode == "pdf" and imported.unit == "page"
        assert imported.unit_count == 3 and imported.material_id == digest[:16]
        assert imported.mime == "application/pdf"
        with pymupdf.open(store.raw_path(imported.material_id)) as reader:
            assert len(reader) == 3
            assert "Hidden" in reader[1].get_text()
            assert "Amber" in reader[2].get_text()
            assert reader[0].rect.width > reader[0].rect.height
        assert "Searchable sentence 2" in store.unit_text(imported.material_id, 2)
        stored_deck = store.root / imported.material_id / "presentation-source" / source.name
        assert sha256(stored_deck.read_bytes()).hexdigest() == digest
        prior = store.manifest(imported.material_id)
        with patch.object(store_module, "render_presentation_pdf", side_effect=AssertionError("Duplicate deck reconverted")):
            assert store.ingest(source) == prior
        assert catalog.find_material_by_content(digest[:16]).material_id == imported.material_id
        store.refresh_document(imported.material_id)
        assert stored_deck.read_bytes() == source.read_bytes()

        subprocess.run([
            service._office_executable(),
            f"-env:UserInstallation={(work / 'ppt-profile').as_uri()}",
            "--headless", "--convert-to", "ppt:MS PowerPoint 97",
            "--outdir", str(work), str(source),
        ], capture_output=True, timeout=120, check=True,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        binary_deck = source.with_suffix(".ppt")
        legacy_format = store.ingest(binary_deck)
        assert legacy_format.unit_count == 3 and legacy_format.render_mode == "pdf"

        upgraded = store_class(legacy_root)
        with patch.object(catalog_class, "enable_presentation_pages", side_effect=OSError("catalog unavailable")):
            try:
                upgraded.ingest(source)
            except OSError:
                pass
            else:
                raise AssertionError("Interrupted update did not surface its error")
        new = upgraded.ingest(source)
        assert new.material_id == old.material_id and new.unit_count == old.unit_count
        assert new.revision == old.revision + 1 and new.title == old.title
        assert upgraded.position(new.material_id).to_dict() == position
        assert upgraded.manifest(new.material_id).render_mode == "pdf"
        assert old_catalog.get_workspace(collection.workspace_id).tabs[0].material.render_mode == "pdf"

        corrupt = work / "Invalid.ppt"
        corrupt.write_bytes(b"This is not a presentation.")
        try:
            store.ingest(corrupt)
        except ReadingError:
            assert not (store.root / sha256(corrupt.read_bytes()).hexdigest()[:16]).exists()
        else:
            raise AssertionError("Invalid deck created a reading record")
        print(f"{layer}: real PPT/PPTX conversion, hidden slide, text, dedupe, legacy upgrade, position and invalid input verified")


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "fixture":
        make_deck(Path(sys.argv[2]))
    else:
        main(sys.argv[1])
