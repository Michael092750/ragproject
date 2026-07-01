"""Crash-resilient wrapper around ``ingest_bulk`` for OCR-heavy corpora.

Sustained Docling+RapidOCR runs fragment the native heap over thousands of image
alloc/free cycles until a moderate allocation fails and the process SIGSEGVs --
fatal to a single long ``ingest_bulk`` run. This wrapper instead runs the ingest
in a *subprocess* and, when it dies, relaunches a **fresh** process that resumes
from the manifest (already-ingested files are skipped). A clean heap each time
sidesteps the fragmentation, with no drop in OCR resolution.

Each subprocess processes many files before it recycles, so model-load cost is
amortized. If one document crashes the parser even in a fresh process (no
progress made), it is recorded in the manifest with 0 chunks so the next attempt
moves past it instead of looping forever.

Run with the SAME env as ``ingest_bulk`` (DATABASE_URL for the durable manifest,
VECTOR_BACKEND, RAG_PROVIDER, ...):

    python scripts/ingest_resilient.py <folder>
"""

import hashlib
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from industryiq.api.deps import _build_ingest_state_store
from industryiq.config import get_settings
from industryiq.core.ingestion.models import FileState
from industryiq.core.loaders import SUPPORTED_EXTENSIONS

# Safety cap so a pathological corpus can't loop forever.
_MAX_ATTEMPTS = 60
_HASH_BLOCK = 1 << 20


def _supported_files(root: Path) -> list[Path]:
    """Every ingestable file under ``root``, in the same order ingest_bulk walks."""
    exts = {s.lower() for s in SUPPORTED_EXTENSIONS}
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts)


def _file_hash(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(_HASH_BLOCK), b""):
            digest.update(block)
    return digest.hexdigest()


def main(root: Path) -> None:
    # Only the manifest store -- no models loaded in the supervisor process.
    store = _build_ingest_state_store(get_settings())
    files = _supported_files(root)
    if not files:
        sys.exit(f"no ingestable files under {root}")

    for attempt in range(1, _MAX_ATTEMPTS + 1):
        pending = [p for p in files if store.get_file_state(p.relative_to(root).as_posix()) is None]
        if not pending:
            print(
                f"\nAll {len(files)} files ingested; resilient run complete "
                f"after {attempt - 1} subprocess attempt(s)."
            )
            return

        target = pending[0]  # where this attempt will resume
        print(
            f"\n=== attempt {attempt}: {len(pending)}/{len(files)} pending, "
            f"resuming at {target.relative_to(root).as_posix()} ===",
            flush=True,
        )
        proc = subprocess.run([sys.executable, "-u", "scripts/ingest_bulk.py", str(root)])

        if proc.returncode == 0:
            continue  # clean exit; loop re-checks pending and finishes

        # Crashed (e.g. SIGSEGV from OCR). If the resume target still isn't in the
        # manifest, this subprocess made no progress -> that file crashes even a
        # fresh process. Mark it skipped (0 chunks) so we advance past it.
        src = target.relative_to(root).as_posix()
        if store.get_file_state(src) is None:
            store.upsert_file_state(
                FileState(
                    source=src,
                    size=target.stat().st_size,
                    content_hash=_file_hash(target),
                    chunk_count=0,
                    ingested_at=datetime.now(UTC),
                )
            )
            print(
                f"  !! {src} crashed the parser in a fresh process "
                f"(exit {proc.returncode}); marked skipped (0 chunks).",
                flush=True,
            )
        else:
            print(
                f"  .. subprocess exited {proc.returncode} after making progress; resuming.",
                flush=True,
            )

    still_pending = sum(
        1 for p in files if store.get_file_state(p.relative_to(root).as_posix()) is None
    )
    print(f"\nStopped after {_MAX_ATTEMPTS} attempts; {still_pending} file(s) still pending.")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit("usage: python scripts/ingest_resilient.py <folder>")
    folder = Path(sys.argv[1])
    if not folder.is_dir():
        sys.exit(f"not a folder: {folder}")
    main(folder)
