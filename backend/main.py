from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.database import engine
from app.models.models import Base
from app.routes import auth, sessions, chat

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

@app.get("/")
def root():
    return {"message": "Chatbot Médical API is running"}
