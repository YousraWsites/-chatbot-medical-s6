from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    hashed_password = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    sessions = relationship("Session", back_populates="user")

class Session(Base):
    __tablename__ = "sessions"
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String, default="Nouvelle conversation")
    user_id = Column(Integer, ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User", back_populates="sessions")
    messages = relationship("Message", back_populates="session")

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id"))
    role = Column(String)  # "user" ou "assistant"
    content = Column(Text)
    source = Column(String, nullable=True)  # "doc", "web" ou None (messages "user")
    created_at = Column(DateTime, default=datetime.utcnow)
    session = relationship("Session", back_populates="messages")

class Doctor(Base):
    __tablename__ = "doctors"
    id = Column(Integer, primary_key=True, index=True)
    nom = Column(String)
    specialite = Column(String, index=True)
    creneaux_disponibles = Column(Text)  # créneaux libres séparés par "|", ex: "2026-06-25 09:00|2026-06-25 10:00"
    telegram_chat_id = Column(String, nullable=True, index=True)  # bonus Hermes++ : notif + commandes praticien
    # Détails enrichis affichés dans la page de prise de RDV
    bio = Column(Text, nullable=True)
    hopital = Column(String, nullable=True)
    ville = Column(String, nullable=True)
    langues = Column(String, nullable=True)  # CSV: "Français, Anglais, Arabe"
    tarif_eur = Column(Integer, nullable=True)  # tarif consultation en euros
    duree_min = Column(Integer, nullable=True, default=30)  # durée par défaut

class Appointment(Base):
    __tablename__ = "appointments"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    session_id = Column(Integer, ForeignKey("sessions.id"))
    doctor_id = Column(Integer, ForeignKey("doctors.id"))
    creneau = Column(String)
    statut = Column(String, default="confirmé")  # confirmé, annulé
    motif = Column(Text, nullable=True)  # raison de la consultation (résumé conv ou choix patient)
    type_consultation = Column(String, default="présentiel")  # présentiel | téléconsultation
    notes_patient = Column(Text, nullable=True)  # info à transmettre au praticien
    created_at = Column(DateTime, default=datetime.utcnow)
    user = relationship("User")
    doctor = relationship("Doctor")
