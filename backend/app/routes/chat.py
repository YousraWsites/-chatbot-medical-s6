from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.models import Session as ChatSession, Message, User
from app.routes.auth import get_current_user
from app.services.rag import get_rag_response

router = APIRouter(prefix="/chat", tags=["chat"])

class ChatRequest(BaseModel):
    session_id: int
    question: str

@router.post("/")
def chat(data: ChatRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.query(ChatSession).filter(ChatSession.id == data.session_id, ChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    # Sauvegarder le message utilisateur
    user_msg = Message(session_id=data.session_id, role="user", content=data.question)
    db.add(user_msg)
    db.commit()

    # Récupérer l'historique
    history = db.query(Message).filter(Message.session_id == data.session_id).order_by(Message.created_at).all()
    history_list = [{"role": m.role, "content": m.content} for m in history]

    # Appeler le RAG
    answer = get_rag_response(data.question, history_list)

    # Sauvegarder la réponse
    bot_msg = Message(session_id=data.session_id, role="assistant", content=answer)
    db.add(bot_msg)
    db.commit()

    return {"answer": answer}
