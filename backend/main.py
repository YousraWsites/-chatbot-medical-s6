import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models.models import Base, Doctor
from app.routes import auth, sessions, chat, hermes
from app.services.rag import build_vectorstore, CHROMA_DIR

Base.metadata.create_all(bind=engine)

# Migrations légères pour aligner les bases SQLite déjà déployées sur le schéma actuel.
with engine.connect() as conn:
    msg_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(messages)"))]
    if "source" not in msg_cols:
        conn.execute(text("ALTER TABLE messages ADD COLUMN source VARCHAR"))
        conn.commit()
    doc_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(doctors)"))]
    if "telegram_chat_id" not in doc_cols:
        conn.execute(text("ALTER TABLE doctors ADD COLUMN telegram_chat_id VARCHAR"))
        conn.commit()

app = FastAPI(title="Chatbot Médical API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(hermes.router)

SEED_DOCTORS = [
    {"nom": "Dr. Amel Benyahia", "specialite": "endocrinologue",
     "creneaux_disponibles": "2026-06-25 09:00|2026-06-25 10:30|2026-06-26 14:00"},
    {"nom": "Dr. Karim Lefebvre", "specialite": "neurologue",
     "creneaux_disponibles": "2026-06-24 11:00|2026-06-25 16:00"},
    {"nom": "Dr. Sophie Marchand", "specialite": "pneumologue",
     "creneaux_disponibles": "2026-06-24 09:30|2026-06-26 10:00"},
    {"nom": "Dr. Yacine Boudraa", "specialite": "oncologue",
     "creneaux_disponibles": "2026-06-25 15:00|2026-06-27 09:00"},
    {"nom": "Dr. Claire Petit", "specialite": "généraliste",
     "creneaux_disponibles": "2026-06-23 08:30|2026-06-23 17:00|2026-06-24 13:00"},
]


@app.on_event("startup")
def startup_build_index():
    # En prod (Render), le disque est éphémère : on réindexe si chroma_db a disparu.
    if not os.path.exists(CHROMA_DIR):
        build_vectorstore()


@app.on_event("startup")
def startup_seed_doctors():
    db = SessionLocal()
    try:
        if db.query(Doctor).count() == 0:
            db.add_all(Doctor(**d) for d in SEED_DOCTORS)
            db.commit()
        # Bonus Hermes++ : associe les 2 médecins de démo à leur groupe Telegram.
        # Idempotent : si la valeur env existe et n'est pas déjà set en DB, on l'attribue.
        tg_neuro = os.getenv("TELEGRAM_CHAT_NEURO")
        tg_endo = os.getenv("TELEGRAM_CHAT_ENDO")
        if tg_neuro:
            d = db.query(Doctor).filter(Doctor.nom == "Dr. Karim Lefebvre").first()
            if d and d.telegram_chat_id != tg_neuro:
                d.telegram_chat_id = tg_neuro
        if tg_endo:
            d = db.query(Doctor).filter(Doctor.nom == "Dr. Amel Benyahia").first()
            if d and d.telegram_chat_id != tg_endo:
                d.telegram_chat_id = tg_endo
        db.commit()
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "Chatbot Médical API is running"}
