from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.models import Session as ChatSession, Message, User, Doctor, Appointment
from app.routes.auth import get_current_user
from app.services.hermes import recommend_specialist, list_available_doctors, book_appointment

router = APIRouter(prefix="/hermes", tags=["hermes"])


class RecommendRequest(BaseModel):
    session_id: int


class BookRequest(BaseModel):
    session_id: int
    doctor_id: int
    creneau: str
    motif: Optional[str] = None
    type_consultation: Optional[str] = "présentiel"
    notes_patient: Optional[str] = None


def _doctor_payload(d: Doctor) -> dict:
    return {
        "id": d.id, "nom": d.nom, "specialite": d.specialite,
        "creneaux": [c for c in (d.creneaux_disponibles or "").split("|") if c],
        "bio": d.bio, "hopital": d.hopital, "ville": d.ville,
        "langues": [l.strip() for l in (d.langues or "").split(",") if l.strip()],
        "tarif_eur": d.tarif_eur, "duree_min": d.duree_min,
    }


def _appointment_payload(a: Appointment, d: Doctor) -> dict:
    return {
        "id": a.id, "creneau": a.creneau, "statut": a.statut,
        "motif": a.motif, "type_consultation": a.type_consultation,
        "notes_patient": a.notes_patient, "created_at": a.created_at,
        "doctor": {
            "id": d.id, "nom": d.nom, "specialite": d.specialite,
            "hopital": d.hopital, "ville": d.ville,
            "tarif_eur": d.tarif_eur, "duree_min": d.duree_min,
        } if d else None,
    }


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
    result["doctors"] = [_doctor_payload(d) for d in doctors]
    # Pré-rempli du motif (1er message user, tronqué) pour gagner du temps
    result["suggested_motif"] = next(
        (m["content"][:200] for m in history_list if m["role"] == "user"), ""
    )
    return result


@router.post("/book")
def book(data: BookRequest, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    try:
        appointment = book_appointment(
            db, user.id, data.session_id, data.doctor_id, data.creneau,
            motif=data.motif, type_consultation=data.type_consultation,
            notes_patient=data.notes_patient,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    doctor = db.query(Doctor).filter(Doctor.id == data.doctor_id).first()
    return _appointment_payload(appointment, doctor)


@router.get("/appointments")
def list_my_appointments(db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    rows = (
        db.query(Appointment, Doctor)
        .join(Doctor, Doctor.id == Appointment.doctor_id)
        .filter(Appointment.user_id == user.id)
        .order_by(Appointment.creneau.desc())
        .all()
    )
    return [_appointment_payload(a, d) for a, d in rows]


@router.post("/appointments/{appointment_id}/cancel")
def cancel_appointment(appointment_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    appt = db.query(Appointment).filter(
        Appointment.id == appointment_id, Appointment.user_id == user.id
    ).first()
    if not appt:
        raise HTTPException(status_code=404, detail="Rendez-vous introuvable")
    if appt.statut == "annulé":
        raise HTTPException(status_code=400, detail="Rendez-vous déjà annulé")
    appt.statut = "annulé"
    doctor = db.query(Doctor).filter(Doctor.id == appt.doctor_id).first()
    if doctor:
        slots = [c for c in (doctor.creneaux_disponibles or "").split("|") if c]
        if appt.creneau not in slots:
            slots.append(appt.creneau)
            slots.sort()
            doctor.creneaux_disponibles = "|".join(slots)
    db.commit()
    if doctor and doctor.telegram_chat_id:
        from app.services.telegram import send
        patient = db.query(User).filter(User.id == user.id).first()
        send(
            doctor.telegram_chat_id,
            f"❌ *Annulation de rendez-vous*\n"
            f"Patient : `{patient.username if patient else '?'}`\n"
            f"Créneau libéré : *{appt.creneau}*",
        )
    return _appointment_payload(appt, doctor)
