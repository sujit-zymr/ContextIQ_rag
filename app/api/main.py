import os
from contextlib import asynccontextmanager
from typing import Annotated
from uuid import UUID

from fastapi import Depends, FastAPI, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
import psycopg

from app.api.auth import get_current_user, router as auth_router
from app.api.documents import router as documents_router
from app.api.schemas import (
    MessageResponse,
    SendMessageRequest,
    SendMessageResponse,
    SessionCreateRequest,
    SessionResponse,
)
from app.conversations.contextualizer import ContextualizationError, resolve_follow_up
from app.database.connection import init_db
from app.database.conversation_repository import (
    activate_session,
    append_message,
    create_session,
    get_messages,
    get_session,
    list_sessions,
)
from app.generation.answerer import AnswerGenerationError, generate_answer
from app.observability import (
    configure_observability,
    flush_observability,
    observation_span,
    set_span_output,
)
from app.retrieval.similarity_search import search_chunks


@asynccontextmanager
async def lifespan(_app):
    configure_observability()
    try:
        init_db()
    except psycopg.OperationalError as exc:
        raise RuntimeError(
            "PostgreSQL is unreachable. Start it with `docker compose up -d postgres` "
            "and verify DATABASE_URL points to the running host and port."
        ) from exc
    try:
        yield
    finally:
        flush_observability()


app = FastAPI(
    title="ContextIQ RAG API",
    version="0.1.0",
    description="Authenticated conversation sessions for the ContextIQ RAG pipeline.",
    lifespan=lifespan,
)


def _allowed_origins() -> list[str]:
    configured = os.getenv("CORS_ALLOWED_ORIGINS", "").strip()
    if configured:
        return [origin.strip() for origin in configured.split(",") if origin.strip()]
    return [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8080",
        "http://localhost:8501",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8501",
    ]


_origins = _allowed_origins()
app.add_middleware(
    CORSMiddleware,
    allow_origins=_origins,
    allow_credentials="*" not in _origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(documents_router)


def _session_response(row, message_count=0):
    return SessionResponse(
        id=row[0], user_id=row[1], title=row[2], status=row[3],
        created_at=row[4], updated_at=row[5], message_count=message_count,
    )


def _message_response(row):
    return MessageResponse(
        id=row[0], session_id=row[1], role=row[2], content=row[3],
        citations=row[4] or [], abstained=row[5], metadata=row[6] or {}, created_at=row[7],
    )


def _require_owned_session(session_id, user_id):
    session = get_session(session_id, user_id)
    if session is None:
        # Return the same response for missing and foreign sessions.
        raise HTTPException(status_code=404, detail="Conversation session not found.")
    return session


@app.get("/healthz", tags=["operations"])
def health_check():
    return {"status": "ok"}


@app.post("/sessions", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
def start_session(
    payload: SessionCreateRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    with observation_span(
        "rag.api.session_create",
        input_value={"user_id": str(user["id"])},
    ) as span:
        row = create_session(user["id"], payload.title.strip() or "New chat")
        set_span_output(span, {"session_id": str(row[0])})
        return _session_response(row)


@app.get("/sessions", response_model=list[SessionResponse])
def sessions(user: Annotated[dict, Depends(get_current_user)]):
    return [_session_response(row, message_count=row[6]) for row in list_sessions(user["id"])]


@app.post("/sessions/{session_id}/activate", response_model=SessionResponse)
def resume_session(
    session_id: UUID,
    user: Annotated[dict, Depends(get_current_user)],
):
    row = activate_session(session_id, user["id"])
    if row is None:
        raise HTTPException(status_code=404, detail="Conversation session not found.")
    return _session_response(row)


@app.get("/sessions/{session_id}/messages", response_model=list[MessageResponse])
def session_messages(
    session_id: UUID,
    user: Annotated[dict, Depends(get_current_user)],
    limit: Annotated[int, Query(ge=1, le=500)] = 100,
):
    _require_owned_session(session_id, user["id"])
    return [_message_response(row) for row in get_messages(session_id, user["id"], limit=limit)]


@app.post("/sessions/{session_id}/messages", response_model=SendMessageResponse)
def send_message(
    session_id: UUID,
    payload: SendMessageRequest,
    user: Annotated[dict, Depends(get_current_user)],
):
    with observation_span(
        "rag.api.message_lifecycle",
        input_value={
            "session_id": str(session_id),
            "user_id": str(user["id"]),
            "top_k": payload.top_k,
        },
        as_type="chain",
    ) as span:
        _require_owned_session(session_id, user["id"])
        if activate_session(session_id, user["id"]) is None:
            raise HTTPException(status_code=404, detail="Conversation session not found.")

        previous_rows = get_messages(session_id, user["id"], limit=12)
        history = [{"role": row[2], "content": row[3]} for row in previous_rows]
        user_row = append_message(
            session_id, user["id"], "user", payload.content.strip(),
            metadata={"message_type": "question"},
        )
        if user_row is None:
            raise HTTPException(status_code=404, detail="Conversation session not found.")

        try:
            resolution = resolve_follow_up(payload.content, history)
        except ContextualizationError as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        if resolution["needs_clarification"]:
            assistant_row = append_message(
                session_id,
                user["id"],
                "assistant",
                resolution["clarification_question"],
                metadata={"needs_clarification": True},
            )
            set_span_output(span, {
                "session_id": str(session_id),
                "needs_clarification": True,
            })
            return SendMessageResponse(
                session_id=session_id,
                user_message=_message_response(user_row),
                assistant_message=_message_response(assistant_row),
                retrieval_query=None,
                needs_clarification=True,
            )

        retrieval_query = resolution["standalone_query"]
        try:
            chunks = search_chunks(retrieval_query, payload.top_k, mode="hybrid")
            generated = generate_answer(retrieval_query, chunks, search_mode="hybrid")
        except (AnswerGenerationError, ContextualizationError) as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

        assistant_row = append_message(
            session_id,
            user["id"],
            "assistant",
            generated["answer"],
            citations=generated["citations"],
            abstained=generated["abstained"],
            metadata={
                "retrieval_query": retrieval_query,
                "needs_clarification": False,
                "answer_reason": generated["reason"],
            },
        )
        set_span_output(span, {
            "session_id": str(session_id),
            "needs_clarification": False,
            "abstained": generated["abstained"],
            "citations_count": len(generated["citations"]),
        })
        return SendMessageResponse(
            session_id=session_id,
            user_message=_message_response(user_row),
            assistant_message=_message_response(assistant_row),
            retrieval_query=retrieval_query,
            needs_clarification=False,
        )
