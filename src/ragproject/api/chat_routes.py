"""HTTP routes for multi-round chat.

A thin layer over :class:`ChatService`: validate input, call the service,
serialize the result. No chat logic lives here -- that is all in
``ragproject.core.chat``.
"""

import json
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from ragproject.api.deps import get_chat_service, get_session_documents
from ragproject.api.file_loading import load_upload
from ragproject.core.chat import (
    ChatService,
    ConversationNotFound,
    SessionDocumentStore,
    StreamEnd,
    StreamStart,
    StreamStatus,
    StreamToken,
)

Service = Annotated[ChatService, Depends(get_chat_service)]
SessionDocs = Annotated[SessionDocumentStore, Depends(get_session_documents)]

router = APIRouter(prefix="/conversations", tags=["chat"])


class CreateConversationRequest(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=255)


class ConversationResponse(BaseModel):
    id: str
    title: str


class ConversationsResponse(BaseModel):
    conversations: list[ConversationResponse]


class MessageRequest(BaseModel):
    question: str = Field(min_length=1)


class Source(BaseModel):
    text: str
    score: float
    document: str | None = None  # originating document name, if known


class MessageResponse(BaseModel):
    answer: str
    standalone_question: str
    sources: list[Source]
    timings_ms: dict[str, float]


class TurnResponse(BaseModel):
    question: str
    answer: str


class HistoryResponse(BaseModel):
    conversation_id: str
    turns: list[TurnResponse]


class UploadDocumentResponse(BaseModel):
    filename: str
    chunks: int


class SessionDocumentsResponse(BaseModel):
    conversation_id: str
    documents: list[str]


@router.post("", response_model=ConversationResponse)
def create_conversation(
    request: CreateConversationRequest, service: Service
) -> ConversationResponse:
    conversation = service.start(request.title)
    return ConversationResponse(id=conversation.id, title=conversation.title)


@router.get("", response_model=ConversationsResponse)
def list_conversations(service: Service) -> ConversationsResponse:
    conversations = service.list_conversations()
    return ConversationsResponse(
        conversations=[ConversationResponse(id=c.id, title=c.title) for c in conversations]
    )


@router.post("/{conversation_id}/messages", response_model=MessageResponse)
def post_message(
    conversation_id: str, request: MessageRequest, service: Service
) -> MessageResponse:
    try:
        result = service.reply(conversation_id, request.question)
    except ConversationNotFound:
        raise HTTPException(status_code=404, detail="Conversation not found") from None
    return MessageResponse(
        answer=result.answer,
        standalone_question=result.standalone_question,
        sources=[
            Source(
                text=hit.metadata.get("text", ""),
                score=hit.score,
                document=hit.metadata.get("source"),
            )
            for hit in result.hits
        ],
        timings_ms=result.timings_ms,
    )


def _sse(event: str, data: dict[str, object]) -> str:
    """Format one Server-Sent Event frame."""
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


@router.post("/{conversation_id}/messages/stream")
def stream_message(
    conversation_id: str, request: MessageRequest, service: Service
) -> StreamingResponse:
    # Validate existence up front so a missing conversation is a real 404,
    # before the streaming response (and its 200 status) has begun.
    if service.get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")

    def event_stream() -> Iterator[str]:
        for event in service.reply_stream(conversation_id, request.question):
            if isinstance(event, StreamStatus):
                yield _sse("status", {"phase": event.phase})
            elif isinstance(event, StreamStart):
                sources = [
                    Source(
                        text=hit.metadata.get("text", ""),
                        score=hit.score,
                        document=hit.metadata.get("source"),
                    )
                    for hit in event.hits
                ]
                yield _sse(
                    "sources",
                    {
                        "standalone_question": event.standalone_question,
                        "sources": [source.model_dump() for source in sources],
                    },
                )
            elif isinstance(event, StreamToken):
                yield _sse("token", {"text": event.text})
            elif isinstance(event, StreamEnd):
                yield _sse("done", {"answer": event.answer, "timings_ms": event.timings_ms})

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/{conversation_id}/messages", response_model=HistoryResponse)
def get_messages(conversation_id: str, service: Service) -> HistoryResponse:
    if service.get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    turns = service.get_history(conversation_id)
    return HistoryResponse(
        conversation_id=conversation_id,
        turns=[TurnResponse(question=turn.question, answer=turn.answer) for turn in turns],
    )


@router.post("/{conversation_id}/documents", response_model=UploadDocumentResponse)
def upload_document(
    conversation_id: str,
    service: Service,
    session_documents: SessionDocs,
    file: UploadFile,
) -> UploadDocumentResponse:
    if service.get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    text = load_upload(file)
    chunk_ids = session_documents.add(conversation_id, file.filename or "upload", text)
    return UploadDocumentResponse(filename=file.filename or "upload", chunks=len(chunk_ids))


@router.get("/{conversation_id}/documents", response_model=SessionDocumentsResponse)
def list_session_documents(
    conversation_id: str, service: Service, session_documents: SessionDocs
) -> SessionDocumentsResponse:
    if service.get_conversation(conversation_id) is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return SessionDocumentsResponse(
        conversation_id=conversation_id,
        documents=session_documents.documents(conversation_id),
    )
