"""Document loaders: turn a file on disk into plain text.

Start small: only ``.txt`` is supported here. PDF and DOCX support will be
added as separate, independently tested functions later.
"""

from pathlib import Path

SUPPORTED_EXTENSIONS = {".txt"}


def load_text(path: str | Path) -> str:
    """Read a plain-text file and return its contents as a string.

    Args:
        path: Path to a ``.txt`` file.

    Returns:
        The file's contents, decoded as UTF-8.

    Raises:
        FileNotFoundError: If ``path`` does not point to an existing file.
        ValueError: If the file's extension is not supported.
    """
    p = Path(path)
    if not p.is_file():
        raise FileNotFoundError(f"No such file: {p}")
    if p.suffix.lower() not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported file type {p.suffix!r}; " f"supported: {sorted(SUPPORTED_EXTENSIONS)}"
        )
    return p.read_text(encoding="utf-8")
