from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.database import get_db
from app.models.models import Session as ChatSession, Message, User
from app.routes.auth import get_current_user
from app.services.hermes import recommend_specialist, list_available_doctors, book_appointment

router = APIRouter(prefix="/hermes", tags=["hermes"])


class RecommendRequest(BaseModel):
    session_id: int


class BookRequest(BaseModel):
    session_id: int
    doctor_id: int
    creneau: str


@router.post("/recommend")
def recommend(data: RecommendRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    session = db.query(ChatSession).filter(ChatSession.id == data.session_id, ChatSession.user_id == user.id).first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    history = db.query(Message).filter(Message.session_id == data.session_id).order_by(Message.created_at).all()
    history_list = [{"role": m.role, "content": m.content} for m in history]
    if not history_list:
        raise HTTPException(status_code=400, detail="Pas encore de conversation à analyser")

    result = recommend_specialist(history_list)
    doctors = list_available_doctors(db, result["specialite"])
    result["doctors"] = [
        {"id": d.id, "nom": d.nom, "specialite": d.specialite,
         "creneaux": [c for c in d.creneaux_disponibles.split("|") if c]}
        for d in doctors
    ]
    return result


@router.post("/book")
def book(data: BookRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        appointment = book_appointment(db, user.id, data.session_id, data.doctor_id, data.creneau)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    return {"id": appointment.id, "doctor_id": appointment.doctor_id, "creneau": appointment.creneau,
            "statut": appointment.statut}
