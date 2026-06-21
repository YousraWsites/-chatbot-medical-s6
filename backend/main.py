import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.models.models import Base
from app.routes import auth, sessions, chat
from app.services.rag import build_vectorstore, CHROMA_DIR

Base.metadata.create_all(bind=engine)

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


@app.on_event("startup")
def startup_build_index():
    # En prod (Render), le disque est éphémère : on réindexe si chroma_db a disparu.
    if not os.path.exists(CHROMA_DIR):
        build_vectorstore()


@app.get("/")
def root():
    return {"message": "Chatbot Médical API is running"}
