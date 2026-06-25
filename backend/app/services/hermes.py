"""
Hermes — orchestrateur léger inspiré du concept multi-agents (modèle orchestrateur
+ sous-agents spécialisés), recodé en natif dans le backend FastAPI plutôt qu'en
installant la plateforme Hermes Agent (Nous Research), pensée pour des canaux
type Telegram/Discord/CLI et pas pour un chat web embarqué en iframe.

Rôle : après le diagnostic informatif du chatbot RAG, router le patient vers le
bon spécialiste et lui proposer un créneau de rendez-vous.

Sous-agents :
- recommend_specialist()  -> détermine la spécialité à partir de la conversation
- list_available_doctors() -> sous-agent "annuaire"
- book_appointment()       -> sous-agent "réservation"
"""
import os
import requests
from dotenv import load_dotenv
from sqlalchemy.orm import Session
from app.models.models import Doctor, Appointment

load_dotenv()

SPECIALITES = [
    "endocrinologue",   # diabète
    "neurologue",       # Alzheimer
    "pneumologue",      # cancer du poumon
    "oncologue",        # cancer
    "généraliste",      # par défaut / cas non spécifique
]

# Hermes (Nous Research) en priorité ; le tier gratuit OpenRouter est partagé entre
# tous les utilisateurs et peut être temporairement saturé (429) -> fallback automatique.
ORCHESTRATOR_MODELS = [
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "openai/gpt-oss-20b:free",
]


def _call_orchestrator(prompt: str) -> str:
    # Si OpenRouter n'est pas configuré (ex: prod Amana en mode Gemini),
    # on tombe sur le LLM principal (cf. LLM_PROVIDER dans rag.py).
    if not os.getenv("OPENROUTER_API_KEY"):
        from app.services.rag import _call_llm
        return _call_llm(prompt).strip()

    last_error = None
    for model in ORCHESTRATOR_MODELS:
        try:
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={"Authorization": f"Bearer {os.getenv('OPENROUTER_API_KEY')}"},
                json={"model": model, "messages": [{"role": "user", "content": prompt}]},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:
            last_error = e
            continue
    raise last_error


def recommend_specialist(history: list) -> dict:
    """Sous-agent 1 : lit la conversation et détermine la spécialité médicale adaptée."""
    conversation = "\n".join(f"{m['role']}: {m['content']}" for m in history[-10:])
    prompt = f"""Tu es un agent d'orientation médicale. À partir de cette conversation entre un
patient et un chatbot informatif, détermine quelle spécialité de médecin consulter.

Spécialités possibles : {", ".join(SPECIALITES)}

Conversation :
{conversation}

Réponds STRICTEMENT au format suivant (2 lignes) :
SPECIALITE: <une des spécialités ci-dessus>
JUSTIFICATION: <une phrase courte expliquant pourquoi>"""

    raw = _call_orchestrator(prompt)
    specialite, justification = "généraliste", "Profil non spécifique, consultation générale recommandée."
    for line in raw.splitlines():
        if line.upper().startswith("SPECIALITE:"):
            value = line.split(":", 1)[1].strip().lower()
            specialite = value if value in SPECIALITES else "généraliste"
        elif line.upper().startswith("JUSTIFICATION:"):
            justification = line.split(":", 1)[1].strip()

    return {"specialite": specialite, "justification": justification}


def list_available_doctors(db: Session, specialite: str) -> list[Doctor]:
    """Sous-agent 2 : annuaire des médecins disponibles pour la spécialité donnée."""
    return db.query(Doctor).filter(Doctor.specialite == specialite).all()


def book_appointment(db: Session, user_id: int, session_id: int, doctor_id: int, creneau: str) -> Appointment:
    """Sous-agent 3 : réserve un créneau et le retire de la liste des disponibilités du médecin.

    Bonus Hermes++ : si le médecin a un telegram_chat_id, notifie son groupe Telegram.
    """
    doctor = db.query(Doctor).filter(Doctor.id == doctor_id).first()
    if not doctor:
        raise ValueError("Médecin introuvable")

    creneaux = [c for c in doctor.creneaux_disponibles.split("|") if c]
    if creneau not in creneaux:
        raise ValueError("Ce créneau n'est plus disponible")

    creneaux.remove(creneau)
    doctor.creneaux_disponibles = "|".join(creneaux)

    appointment = Appointment(
        user_id=user_id, session_id=session_id, doctor_id=doctor_id, creneau=creneau, statut="confirmé"
    )
    db.add(appointment)
    db.commit()
    db.refresh(appointment)

    # Notif Telegram au praticien (bonus, dégrade silencieusement si pas configuré).
    if doctor.telegram_chat_id:
        from app.services.telegram import send
        from app.models.models import User
        patient = db.query(User).filter(User.id == user_id).first()
        patient_name = patient.username if patient else f"#{user_id}"
        send(
            doctor.telegram_chat_id,
            f"📅 *Nouveau rendez-vous*\n"
            f"Patient : `{patient_name}`\n"
            f"Créneau : *{creneau}*\n"
            f"Session #{session_id} — Statut : {appointment.statut}",
        )

    return appointment
