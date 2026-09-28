from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.orchestrator import AgentOrchestrator
from app.ai.schemas import ChatHistoryMessage, ChatMessageRequest, ChatResponse, ChatSessionResponse
from app.chat.models import ChatMessage, ChatSession
from app.core.database import get_db
from app.core.errors import APIError
from app.core.security import current_user
from app.db.user import User

router = APIRouter(prefix="/chat", tags=["Chat"])


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
def create_session(db: Session = Depends(get_db), user: User = Depends(current_user)):
    session = ChatSession(user_id=user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"session_id": session.id, "title": session.title, "created_at": session.created_at}


def _owned_session(db: Session, user_id: UUID, session_id: UUID) -> ChatSession:
    session = db.scalar(
        select(ChatSession).where(ChatSession.id == session_id, ChatSession.user_id == user_id)
    )
    if session is None:
        raise APIError(404, "chat_session_not_found", "That chat session was not found.")
    return session


@router.post("/sessions/{session_id}/messages", response_model=ChatResponse)
def send_message(
    session_id: UUID,
    request: ChatMessageRequest,
    db: Session = Depends(get_db),
    user: User = Depends(current_user),
):
    _owned_session(db, user.id, session_id)
    history_rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
        .limit(12)
    ).all()
    history = [{"role": row.role, "content": row.content} for row in reversed(history_rows)]
    user_message = ChatMessage(session_id=session_id, role="user", content=request.message)
    db.add(user_message)
    db.flush()
    response = AgentOrchestrator(db, user.id).run(request.message, history=history)
    assistant_message = ChatMessage(
        session_id=session_id,
        role="assistant",
        content=response.answer_text,
        structured_answer=response.model_dump(mode="json"),
        tool_calls=[call.model_dump(mode="json") for call in response.tool_calls],
    )
    db.add(assistant_message)
    session = _owned_session(db, user.id, session_id)
    if session.title is None:
        session.title = request.message[:157] + ("..." if len(request.message) > 157 else "")
    db.commit()
    return response


@router.get("/sessions/{session_id}/messages", response_model=list[ChatHistoryMessage])
def list_messages(session_id: UUID, db: Session = Depends(get_db), user: User = Depends(current_user)):
    _owned_session(db, user.id, session_id)
    rows = db.scalars(
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at, ChatMessage.id)
    ).all()
    result = []
    for row in rows:
        structured = None
        if row.structured_answer:
            try:
                structured = ChatResponse.model_validate(row.structured_answer)
            except ValueError:
                structured = None
        result.append(
            ChatHistoryMessage(
                id=row.id,
                role=row.role,
                content=row.content,
                structured_answer=structured,
                created_at=row.created_at,
            )
        )
    return result
