# SPDX-License-Identifier: Apache-2.0
# Modified by SaMappp for paged PowerPoint reading; see NOTICE.
"""Bounded, cached Office-to-PDF rendering for the file preview drawer.

LibreOffice is optional. Callers can keep their existing browser/text preview
when it is unavailable or cannot render a particular document.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import tempfile
import threading
import time

MAX_OFFICE_BYTES = 25 * 1024 * 1024
MAX_PREVIEW_PDF_BYTES = 60 * 1024 * 1024
CONVERSION_TIMEOUT_SECONDS = 45
CACHE_TTL_SECONDS = 24 * 60 * 60
MAX_CACHE_FILES = 200
MAX_CACHE_TOTAL_BYTES = 512 * 1024 * 1024
OFFICE_SUFFIXES = frozenset(
    {
        ".docx",
        ".docm",
        ".doc",
        ".pptx",
        ".pptm",
        ".ppt",
        ".xlsx",
        ".xlsm",
        ".xls",
    }
)

_PRESENTATION_FILTERS = {
    ".ppt": (bytes.fromhex("D0CF11E0A1B11AE1"), "MS PowerPoint 97"),
    ".pptx": (bytes.fromhex("504B0304"), "Impress MS PowerPoint 2007 XML"),
}
PRESENTATION_SUFFIXES = frozenset(_PRESENTATION_FILTERS)
_conversion_slots = asyncio.Semaphore(2)
_presentation_slots = threading.BoundedSemaphore(2)


class OfficePreviewError(Exception):
    """Base class for expected preview conversion failures."""


class OfficePreviewUnavailable(OfficePreviewError):
    """LibreOffice is absent on the API host."""


class OfficePreviewTimeout(OfficePreviewError):
    """LibreOffice did not finish within the preview deadline."""


class OfficePreviewInvalid(OfficePreviewError):
    """The source or converted PDF exceeds a bound or has an invalid type."""


class OfficePreviewConversionFailed(OfficePreviewError):
    """LibreOffice failed to produce a usable PDF."""


async def render_office_pdf(data: bytes, filename: str, cache_dir: Path) -> bytes:
    """Render an Office document without blocking the API event loop.

    The cache is private to the caller's data scope; the route must resolve
    and authorize the source before calling this function. An isolated
    LibreOffice profile lets concurrent conversions avoid profile locks.
    """
    suffix = Path(filename).suffix.lower()
    if suffix not in OFFICE_SUFFIXES:
        raise OfficePreviewInvalid("Unsupported Office file type")
    if not data or len(data) > MAX_OFFICE_BYTES:
        raise OfficePreviewInvalid("Office file is empty or too large to preview")
    soffice = _office_executable()
    if not soffice:
        raise OfficePreviewUnavailable("LibreOffice is not installed on the server")

    key = hashlib.sha256(b"office-preview-v1\0" + suffix.encode() + b"\0" + data).hexdigest()
    async with _conversion_slots:
        return await asyncio.to_thread(_render_sync, data, suffix, cache_dir, key, soffice)


def _office_executable() -> str | None:
    from deeptutor.runtime.home import get_runtime_data_root

    configured = os.environ.get("DEEPTUTOR_SOFFICE", "")
    if not configured:
        settings = get_runtime_data_root() / "user/settings/office_preview.json"
        try:
            configured = json.loads(settings.read_text(encoding="utf-8"))["soffice"]
        except (OSError, KeyError, TypeError, ValueError):
            pass
    if isinstance(configured, str) and configured:
        candidate = Path(configured).expanduser()
        if candidate.is_absolute() and candidate.is_file():
            return str(candidate)
    return shutil.which("soffice.com") or shutil.which("soffice")


def render_presentation_pdf(data: bytes, filename: str, cache_dir: Path) -> bytes:
    """Render every source slide, including hidden slides, to one PDF page."""
    from deeptutor.utils.document_validator import DocumentValidator

    suffix = Path(filename).suffix.lower()
    limit = DocumentValidator.MAX_FILE_SIZE
    if suffix not in PRESENTATION_SUFFIXES or not data or len(data) > limit:
        raise OfficePreviewInvalid("Invalid or oversized PowerPoint presentation")
    signature, source_filter = _PRESENTATION_FILTERS[suffix]
    if not data.startswith(signature):
        raise OfficePreviewInvalid("The file does not match its PowerPoint format")
    soffice = _office_executable()
    if not soffice:
        raise OfficePreviewUnavailable("LibreOffice is required for paged PowerPoint reading")
    options = {
        name: {"type": "boolean", "value": value}
        for name, value in {
            "ExportHiddenSlides": "true",
            "ExportNotesPages": "false",
            "ExportOnlyNotesPages": "false",
            "UseLosslessCompression": "true",
            "ReduceImageResolution": "false",
            "UseTaggedPDF": "true",
        }.items()
    }
    key = hashlib.sha256(b"reading-presentation-v2\0" + suffix.encode() + b"\0" + data).hexdigest()
    with _presentation_slots:
        return _render_sync(
            data, suffix, cache_dir, key, soffice,
            convert_to="pdf:impress_pdf_Export:" + json.dumps(options, separators=(",", ":")),
            max_pdf_bytes=limit, timeout=120, source_filter=source_filter,
        )


def _render_sync(
    data: bytes, suffix: str, cache_dir: Path, key: str, soffice: str, *,
    convert_to: str = "pdf", max_pdf_bytes: int = MAX_PREVIEW_PDF_BYTES,
    timeout: int = CONVERSION_TIMEOUT_SECONDS, source_filter: str | None = None,
) -> bytes:
    try:
        cache_dir.mkdir(mode=0o700, parents=True, exist_ok=True)
        cache_available = True
    except OSError:
        cache_available = False
    if cache_available:
        _prune_cache(cache_dir)
    cached = cache_dir / f"{key}.pdf"
    if cache_available and not cached.is_symlink() and cached.is_file():
        try:
            if 0 < cached.stat().st_size <= max_pdf_bytes:
                result = cached.read_bytes()
                if result.startswith(b"%PDF-"):
                    return result
        except OSError:
            pass

    with tempfile.TemporaryDirectory(prefix="dt-office-", ignore_cleanup_errors=True) as workdir:
        work = Path(workdir)
        source = work / f"source{suffix}"
        source.write_bytes(data)
        output_dir = work / "output"
        output_dir.mkdir()
        profile = work / "profile"
        profile.mkdir()
        try:
            process = subprocess.Popen(
                [
                    soffice,
                    f"-env:UserInstallation={profile.as_uri()}",
                    "--headless",
                    *([f"--infilter={source_filter}"] if source_filter else []),
                    "--convert-to",
                    convert_to,
                    "--outdir",
                    str(output_dir),
                    str(source),
                ],
                cwd=work,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                start_new_session=os.name == "posix",
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
            )
        except OSError as exc:
            raise OfficePreviewConversionFailed("Could not start LibreOffice") from exc
        try:
            process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired as exc:
            # `soffice` may launch soffice.bin; kill the whole process group,
            # rather than leaving a converter running after the request ends.
            try:
                if os.name == "posix" and hasattr(os, "killpg"):
                    os.killpg(process.pid, signal.SIGKILL)
                else:
                    process.kill()
            except OSError:
                try:
                    process.kill()
                except OSError:
                    pass
            process.communicate()
            raise OfficePreviewTimeout("Office preview conversion timed out") from exc

        rendered = output_dir / "source.pdf"
        if process.returncode != 0 or not rendered.is_file():
            raise OfficePreviewConversionFailed("LibreOffice could not render this file")
        if rendered.stat().st_size > max_pdf_bytes:
            raise OfficePreviewInvalid("Rendered PDF is too large to preview")
        pdf = rendered.read_bytes()
        if not pdf.startswith(b"%PDF-"):
            raise OfficePreviewConversionFailed("LibreOffice produced an invalid PDF")

    # A failed cache write must not prevent an otherwise valid preview.
    if cache_available:
        temporary: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=cache_dir, prefix=".pending-", suffix=".pdf", delete=False
            ) as tmp:
                temporary = Path(tmp.name)
                tmp.write(pdf)
            os.replace(temporary, cached)
        except OSError:
            pass
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    return pdf


def _prune_cache(cache_dir: Path) -> None:
    """Keep old previews from accumulating indefinitely in a user scope."""
    try:
        files = [entry for entry in cache_dir.iterdir() if entry.suffix == ".pdf"]
        files.sort(
            key=lambda entry: entry.stat().st_mtime if not entry.is_symlink() else 0, reverse=True
        )
        cutoff = time.time() - CACHE_TTL_SECONDS
        retained_bytes = 0
        for index, entry in enumerate(files):
            if entry.is_symlink():
                entry.unlink(missing_ok=True)
                continue
            stat = entry.stat()
            if (
                index >= MAX_CACHE_FILES
                or stat.st_mtime < cutoff
                or retained_bytes + stat.st_size > MAX_CACHE_TOTAL_BYTES
            ):
                entry.unlink(missing_ok=True)
            else:
                retained_bytes += stat.st_size
    except OSError:
        # Cache hygiene is best effort; a bad entry should not block preview.
        pass
