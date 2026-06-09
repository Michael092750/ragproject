# ragproject

A modular, testable Retrieval-Augmented Generation (RAG) system.

## Development

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
pytest
```

## Quality checks

```powershell
ruff check .
mypy src
pytest
```
