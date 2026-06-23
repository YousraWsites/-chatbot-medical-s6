import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from app.database import engine, SessionLocal
from app.models.models import Base, Doctor
from app.routes import auth, sessions, chat, hermes
from app.services.rag import build_vectorstore, CHROMA_DIR

Base.metadata.create_all(bind=engine)

# Migration légère : la colonne "source" a été ajoutée après la création initiale
# de la table messages (bases existantes en local/prod à mettre à niveau).
with engine.connect() as conn:
    columns = [row[1] for row in conn.execute(text("PRAGMA table_info(messages)"))]
    if "source" not in columns:
        conn.execute(text("ALTER TABLE messages ADD COLUMN source VARCHAR"))
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
    finally:
        db.close()


@app.get("/")
def root():
    return {"message": "Chatbot Médical API is running"}
