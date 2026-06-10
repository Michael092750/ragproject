"""FastAPI application: thin HTTP layer over :class:`RagPipeline`.

Routes validate input, call the pipeline, and serialize the result. They contain
no RAG logic of their own -- that all lives in ``ragproject.core``.
"""

from typing import Annotated

from fastapi import Depends, FastAPI
from pydantic import BaseModel, Field

from ragproject.api.deps import get_pipeline
from ragproject.core.pipeline import RagPipeline

Pipeline = Annotated[RagPipeline, Depends(get_pipeline)]


class IngestRequest(BaseModel):
    text: str = Field(min_length=1)
    source: str | None = None


class IngestResponse(BaseModel):
    chunk_ids: list[str]


class QueryRequest(BaseModel):
    question: str = Field(min_length=1)
    k: int = Field(default=5, ge=1)


class Source(BaseModel):
    text: str
    score: float


class QueryResponse(BaseModel):
    answer: str
    sources: list[Source]


app = FastAPI(title="ragproject")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/ingest")
def ingest(request: IngestRequest, pipeline: Pipeline) -> IngestResponse:
    chunk_ids = pipeline.ingest_text(request.text, source=request.source)
    return IngestResponse(chunk_ids=chunk_ids)


@app.post("/query")
def query(request: QueryRequest, pipeline: Pipeline) -> QueryResponse:
    result = pipeline.query(request.question, k=request.k)
    sources = [Source(text=hit.metadata.get("text", ""), score=hit.score) for hit in result.hits]
    return QueryResponse(answer=result.answer, sources=sources)
