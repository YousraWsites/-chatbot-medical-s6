from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.models import Session as ChatSession, Message, User
from app.routes.auth import get_current_user

router = APIRouter(prefix="/sessions", tags=["sessions"])

class SessionCreate(BaseModel):
    title: Optional[str] = "Nouvelle conversation"

@router.post("/")
def create_session(data: SessionCreate, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = ChatSession(title=data.title, user_id=user.id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return {"id": session.id, "title": session.title, "created_at": session.created_at}

@router.get("/")
def get_sessions(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    sessions = db.query(ChatSession).filter(ChatSession.user_id == user.id).order_by(ChatSession.created_at.desc()).all()
    return [{"id": s.id, "title": s.title, "created_at": s.created_at} for s in sessions]

@router.get("/{session_id}/messages")
def get_messages(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    messages = db.query(Message).filter(Message.session_id == session_id).order_by(Message.created_at).all()
    return [{"role": m.role, "content": m.content, "created_at": m.created_at} for m in messages]

@router.delete("/{session_id}")
def delete_session(session_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.query(ChatSession).filter(ChatSession.id == session_id, ChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    db.query(Message).filter(Message.session_id == session_id).delete()
    db.delete(session)
    db.commit()
    return {"message": "Session deleted"}
