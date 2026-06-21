import os

import streamlit as st
import requests

try:
    API_URL = st.secrets["API_URL"]
except (KeyError, FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
    API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Chatbot Médical", page_icon="🏥", layout="wide")

# ── Auth helpers ──────────────────────────────────────────────
def api_register(username, email, password):
    r = requests.post(f"{API_URL}/auth/register", json={"username": username, "email": email, "password": password})
    return r

def api_login(username, password):
    r = requests.post(f"{API_URL}/auth/login", data={"username": username, "password": password})
    return r

def api_get_sessions(token):
    r = requests.get(f"{API_URL}/sessions/", headers={"Authorization": f"Bearer {token}"})
    return r.json()

def api_create_session(token, title="Nouvelle conversation"):
    r = requests.post(f"{API_URL}/sessions/", json={"title": title}, headers={"Authorization": f"Bearer {token}"})
    return r.json()

def api_get_messages(token, session_id):
    r = requests.get(f"{API_URL}/sessions/{session_id}/messages", headers={"Authorization": f"Bearer {token}"})
    return r.json()

def api_chat(token, session_id, question):
    r = requests.post(f"{API_URL}/chat/", json={"session_id": session_id, "question": question}, headers={"Authorization": f"Bearer {token}"})
    return r.json()

def api_delete_session(token, session_id):
    requests.delete(f"{API_URL}/sessions/{session_id}", headers={"Authorization": f"Bearer {token}"})

# ── Session state init ────────────────────────────────────────
if "token" not in st.session_state:
    st.session_state.token = None
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "page" not in st.session_state:
    st.session_state.page = "login"

# ── Pages ─────────────────────────────────────────────────────
def page_login():
    st.title("Chatbot Médical")
    st.subheader("Connexion")
    tab_login, tab_register = st.tabs(["Se connecter", "Créer un compte"])

    with tab_login:
        username = st.text_input("Nom d'utilisateur", key="login_user")
        password = st.text_input("Mot de passe", type="password", key="login_pass")
        if st.button("Se connecter", use_container_width=True):
            r = api_login(username, password)
            if r.status_code == 200:
                st.session_state.token = r.json()["access_token"]
                st.session_state.page = "chat"
                st.rerun()
            else:
                st.error("Identifiants incorrects")

    with tab_register:
        new_user = st.text_input("Nom d'utilisateur", key="reg_user")
        new_email = st.text_input("Email", key="reg_email")
        new_pass = st.text_input("Mot de passe", type="password", key="reg_pass")
        if st.button("Créer le compte", use_container_width=True):
            r = api_register(new_user, new_email, new_pass)
            if r.status_code == 200:
                st.success("Compte créé ! Connecte-toi.")
            else:
                st.error(r.json().get("detail", "Erreur"))

def page_chat():
    token = st.session_state.token

    # Sidebar : liste des sessions
    with st.sidebar:
        st.title("Conversations")
        if st.button("+ Nouvelle conversation", use_container_width=True):
            s = api_create_session(token)
            st.session_state.current_session_id = s["id"]
            st.rerun()

        sessions = api_get_sessions(token)
        for s in sessions:
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(s["title"], key=f"s_{s['id']}", use_container_width=True):
                    st.session_state.current_session_id = s["id"]
                    st.rerun()
            with col2:
                if st.button("🗑", key=f"del_{s['id']}"):
                    api_delete_session(token, s["id"])
                    if st.session_state.current_session_id == s["id"]:
                        st.session_state.current_session_id = None
                    st.rerun()

        st.divider()
        if st.button("Se déconnecter"):
            st.session_state.token = None
            st.session_state.current_session_id = None
            st.session_state.page = "login"
            st.rerun()

    # Zone de chat
    st.title("Chatbot Médical")
    st.caption("Assistant informatif uniquement — ne remplace pas un médecin.")

    if st.session_state.current_session_id is None:
        st.info("Crée une nouvelle conversation dans le menu à gauche.")
        return

    # Afficher les messages
    messages = api_get_messages(token, st.session_state.current_session_id)
    for msg in messages:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    # Input
    question = st.chat_input("Posez votre question médicale...")
    if question:
        with st.chat_message("user"):
            st.write(question)
        with st.chat_message("assistant"):
            with st.spinner("Recherche en cours..."):
                result = api_chat(token, st.session_state.current_session_id, question)
                answer = result.get("answer", "Erreur lors de la génération.")
            st.write(answer)
        st.rerun()

# ── Router ────────────────────────────────────────────────────
if st.session_state.token is None:
    page_login()
else:
    page_chat()
