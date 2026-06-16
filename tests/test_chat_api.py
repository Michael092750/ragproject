from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient

from ragproject.api.app import app
from ragproject.api.deps import get_chat_service, get_session_documents
from ragproject.core.chat import (
    AlwaysRetrieveRouter,
    ChatService,
    InMemoryConversationStore,
    NoOpQueryRewriter,
    SessionDocuments,
    ThresholdFilter,
)
from ragproject.core.embeddings import FakeEmbedder
from ragproject.core.generation import FakeLLM
from ragproject.core.retrieval import Retriever
from ragproject.core.vectorstore import InMemoryVectorStore


@pytest.fixture
def client() -> Iterator[TestClient]:
    # A fresh, fully in-memory chat service per test via dependency override.
    retriever = Retriever(FakeEmbedder(dim=16), InMemoryVectorStore())
    retriever.index(["the sky is blue"], metadatas=[{"source": "facts.txt"}])
    # Shared between the chat service and the upload route -- same instance.
    session_documents = SessionDocuments(FakeEmbedder(dim=16))
    service = ChatService(
        retriever=retriever,
        router=AlwaysRetrieveRouter(),
        rewriter=NoOpQueryRewriter(),
        llm=FakeLLM(response="Grounded answer [1]."),
        store=InMemoryConversationStore(),
        relevance_filter=ThresholdFilter(),
        session_documents=session_documents,
    )
    app.dependency_overrides[get_chat_service] = lambda: service
    app.dependency_overrides[get_session_documents] = lambda: session_documents
    yield TestClient(app)
    app.dependency_overrides.clear()


def _new_conversation(client: TestClient) -> str:
    conversation_id: str = client.post("/conversations", json={"title": "c"}).json()["id"]
    return conversation_id


def test_create_conversation(client: TestClient) -> None:
    response = client.post("/conversations", json={"title": "My chat"})
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "My chat"
    assert body["id"]


def test_post_message_returns_answer_and_sources(client: TestClient) -> None:
    conversation_id = _new_conversation(client)
    response = client.post(
        f"/conversations/{conversation_id}/messages", json={"question": "the sky is blue"}
    )
    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == "Grounded answer [1]."
    assert body["sources"][0]["text"] == "the sky is blue"
    assert body["sources"][0]["document"] == "facts.txt"
    assert set(body["timings_ms"]) >= {"retrieve", "generate", "total"}


def test_history_round_trips(client: TestClient) -> None:
    conversation_id = _new_conversation(client)
    client.post(f"/conversations/{conversation_id}/messages", json={"question": "the sky is blue"})
    response = client.get(f"/conversations/{conversation_id}/messages")
    assert response.status_code == 200
    turns = response.json()["turns"]
    assert turns[0]["question"] == "the sky is blue"
    assert turns[0]["answer"] == "Grounded answer [1]."


def test_message_to_unknown_conversation_is_404(client: TestClient) -> None:
    response = client.post("/conversations/nope/messages", json={"question": "hi"})
    assert response.status_code == 404


def test_history_of_unknown_conversation_is_404(client: TestClient) -> None:
    assert client.get("/conversations/nope/messages").status_code == 404


def test_message_missing_question_is_422(client: TestClient) -> None:
    conversation_id = _new_conversation(client)
    assert client.post(f"/conversations/{conversation_id}/messages", json={}).status_code == 422


def test_stream_message_returns_sse_events(client: TestClient) -> None:
    conversation_id = _new_conversation(client)
    response = client.post(
        f"/conversations/{conversation_id}/messages/stream",
        json={"question": "the sky is blue"},
    )
    assert response.status_code == 200
    assert "text/event-stream" in response.headers["content-type"]
    body = response.text
    assert "event: status" in body
    assert '"phase": "retrieving"' in body  # semantic phase; UI copy is the frontend's job
    assert "event: sources" in body
    assert "event: token" in body
    assert "event: done" in body
    assert "facts.txt" in body  # document name carried in the sources event
    assert "Grounded answer [1]." in body  # full answer in the done event


def test_stream_message_persists_turn(client: TestClient) -> None:
    conversation_id = _new_conversation(client)
    client.post(
        f"/conversations/{conversation_id}/messages/stream",
        json={"question": "the sky is blue"},
    )
    history = client.get(f"/conversations/{conversation_id}/messages").json()["turns"]
    assert history[0]["answer"] == "Grounded answer [1]."


def test_stream_message_unknown_conversation_is_404(client: TestClient) -> None:
    response = client.post("/conversations/nope/messages/stream", json={"question": "hi"})
    assert response.status_code == 404


def test_list_conversations_returns_created(client: TestClient) -> None:
    client.post("/conversations", json={"title": "first"})
    client.post("/conversations", json={"title": "second"})
    response = client.get("/conversations")
    assert response.status_code == 200
    titles = {c["title"] for c in response.json()["conversations"]}
    assert titles == {"first", "second"}


def test_upload_document_and_list(client: TestClient) -> None:
    conversation_id = _new_conversation(client)
    response = client.post(
        f"/conversations/{conversation_id}/documents",
        files={"file": ("notes.txt", b"the moon is bright tonight", "text/plain")},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["filename"] == "notes.txt"
    assert body["chunks"] >= 1
    listed = client.get(f"/conversations/{conversation_id}/documents").json()
    assert listed["documents"] == ["notes.txt"]


def test_session_document_surfaces_in_chat(client: TestClient) -> None:
    conversation_id = _new_conversation(client)
    client.post(
        f"/conversations/{conversation_id}/documents",
        files={"file": ("notes.txt", b"the moon is bright tonight", "text/plain")},
    )
    response = client.post(
        f"/conversations/{conversation_id}/messages",
        json={"question": "the moon is bright tonight"},
    )
    assert response.status_code == 200
    documents = {source["document"] for source in response.json()["sources"]}
    assert "notes.txt" in documents  # the session upload was retrieved alongside the shared index


def test_upload_to_unknown_conversation_is_404(client: TestClient) -> None:
    response = client.post(
        "/conversations/nope/documents",
        files={"file": ("notes.txt", b"text", "text/plain")},
    )
    assert response.status_code == 404


def test_upload_unsupported_type_is_415(client: TestClient) -> None:
    conversation_id = _new_conversation(client)
    response = client.post(
        f"/conversations/{conversation_id}/documents",
        files={"file": ("data.csv", b"a,b,c", "text/csv")},
    )
    assert response.status_code == 415


def test_list_documents_unknown_conversation_is_404(client: TestClient) -> None:
    assert client.get("/conversations/nope/documents").status_code == 404
