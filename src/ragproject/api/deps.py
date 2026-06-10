"""Dependency wiring for the API.

:func:`get_pipeline` builds the application's :class:`RagPipeline`. For now it
uses the offline fakes so the service runs with no external dependencies; real
provider-backed implementations replace them in a later phase. Tests override
this dependency to inject a pipeline pre-loaded with known data.
"""

from functools import lru_cache

from ragproject.core.embeddings import FakeEmbedder
from ragproject.core.generation import FakeLLM
from ragproject.core.pipeline import RagPipeline
from ragproject.core.retrieval import Retriever
from ragproject.core.vectorstore import InMemoryVectorStore


@lru_cache(maxsize=1)
def get_pipeline() -> RagPipeline:
    """Return the process-wide pipeline (built once, then cached)."""
    retriever = Retriever(FakeEmbedder(), InMemoryVectorStore())
    return RagPipeline(retriever, FakeLLM())
