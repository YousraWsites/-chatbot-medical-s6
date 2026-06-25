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
    for col, ddl in [
        ("telegram_chat_id", "VARCHAR"),
        ("bio", "TEXT"),
        ("hopital", "VARCHAR"),
        ("ville", "VARCHAR"),
        ("langues", "VARCHAR"),
        ("tarif_eur", "INTEGER"),
        ("duree_min", "INTEGER"),
    ]:
        if col not in doc_cols:
            conn.execute(text(f"ALTER TABLE doctors ADD COLUMN {col} {ddl}"))
            conn.commit()
    appt_cols = [row[1] for row in conn.execute(text("PRAGMA table_info(appointments)"))]
    for col, ddl in [
        ("motif", "TEXT"),
        ("type_consultation", "VARCHAR DEFAULT 'présentiel'"),
        ("notes_patient", "TEXT"),
    ]:
        if col not in appt_cols:
            conn.execute(text(f"ALTER TABLE appointments ADD COLUMN {col} {ddl}"))
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
     "creneaux_disponibles": "2026-06-25 09:00|2026-06-25 10:30|2026-06-26 14:00",
     "bio": "Endocrinologue spécialisée dans la prise en charge du diabète de type 1 et 2. Diplômée de la faculté de médecine de Marseille (2009), elle a exercé 8 ans au CHU Timone avant de rejoindre la clinique Saint-Jean.",
     "hopital": "Clinique Saint-Jean", "ville": "Marseille",
     "langues": "Français, Arabe, Anglais",
     "tarif_eur": 60, "duree_min": 30},
    {"nom": "Dr. Karim Lefebvre", "specialite": "neurologue",
     "creneaux_disponibles": "2026-06-24 11:00|2026-06-25 16:00",
     "bio": "Neurologue, spécialisé dans les maladies neurodégénératives (Alzheimer, Parkinson). Praticien hospitalier au CHU de Lille, il participe à l'unité de consultation mémoire et au programme de recherche France-Alzheimer.",
     "hopital": "CHU de Lille - Hôpital Roger Salengro", "ville": "Lille",
     "langues": "Français, Anglais",
     "tarif_eur": 70, "duree_min": 45},
    {"nom": "Dr. Sophie Marchand", "specialite": "pneumologue",
     "creneaux_disponibles": "2026-06-24 09:30|2026-06-26 10:00",
     "bio": "Pneumologue expérimentée en oncologie thoracique. Membre de la Société de Pneumologie de Langue Française, elle anime également des consultations de sevrage tabagique.",
     "hopital": "Hôpital Européen Georges-Pompidou", "ville": "Paris 15e",
     "langues": "Français, Anglais, Espagnol",
     "tarif_eur": 75, "duree_min": 30},
    {"nom": "Dr. Yacine Boudraa", "specialite": "oncologue",
     "creneaux_disponibles": "2026-06-25 15:00|2026-06-27 09:00",
     "bio": "Oncologue médical, expert en cancers thoraciques. Coordinateur du parcours patient au Centre Léon Bérard, il participe à plusieurs essais cliniques en immunothérapie.",
     "hopital": "Centre Léon Bérard", "ville": "Lyon",
     "langues": "Français, Anglais, Arabe",
     "tarif_eur": 80, "duree_min": 45},
    {"nom": "Dr. Claire Petit", "specialite": "généraliste",
     "creneaux_disponibles": "2026-06-23 08:30|2026-06-23 17:00|2026-06-24 13:00",
     "bio": "Médecin généraliste, exerce en cabinet de groupe depuis 12 ans. Sensibilisée à la prévention, elle est le premier interlocuteur pour orienter vers la bonne spécialité.",
     "hopital": "Cabinet médical Saint-Michel", "ville": "Toulouse",
     "langues": "Français, Anglais",
     "tarif_eur": 30, "duree_min": 20},
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
        else:
            # Backfill : enrichit les médecins existants avec bio/hopital/etc. si manquant.
            by_name = {d["nom"]: d for d in SEED_DOCTORS}
            for doc in db.query(Doctor).all():
                seed = by_name.get(doc.nom)
                if not seed:
                    continue
                for col in ("bio", "hopital", "ville", "langues", "tarif_eur", "duree_min"):
                    if getattr(doc, col, None) is None:
                        setattr(doc, col, seed.get(col))
            db.commit()
        # Bonus Hermes++ : associe les 2 médecins de démo à leur groupe Telegram.
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
