from pathlib import Path

import pytest

from ragproject.core.loaders import load_text

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_text_reads_content() -> None:
    text = load_text(FIXTURES / "sample.txt")
    assert "Hello, RAG world." in text
    assert "testing loaders" in text


def test_load_text_missing_file_raises() -> None:
    with pytest.raises(FileNotFoundError):
        load_text(FIXTURES / "does_not_exist.txt")


def test_load_text_unsupported_extension_raises(tmp_path: Path) -> None:
    bad = tmp_path / "data.csv"
    bad.write_text("a,b,c")
    with pytest.raises(ValueError):
        load_text(bad)
