import os

import streamlit as st
import requests

try:
    API_URL = st.secrets["API_URL"]
except (KeyError, FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
    API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Chatbot Médical", page_icon="🏥", layout="wide")

TEAL = "#0f766e"
TEAL_LIGHT = "#14b8a6"
BG_SOFT = "#f0fdfa"

st.markdown(f"""
<style>
.stApp {{
    background: {BG_SOFT};
}}
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {TEAL} 0%, #134e4a 100%);
}}
section[data-testid="stSidebar"] * {{
    color: #ecfdf5 !important;
}}
section[data-testid="stSidebar"] button {{
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
}}
section[data-testid="stSidebar"] button p {{
    color: #ecfdf5 !important;
}}
h1, h2, h3 {{
    color: #134e4a;
}}
.stTabs [data-baseweb="tab"] {{
    font-weight: 600;
}}
.stTabs [aria-selected="true"] {{
    color: {TEAL} !important;
}}
.med-banner {{
    background: white;
    border-left: 4px solid {TEAL_LIGHT};
    border-radius: 8px;
    padding: 12px 18px;
    margin-bottom: 18px;
    color: #134e4a;
    font-size: 0.92rem;
}}
.med-hero {{
    text-align: center;
    padding: 30px 0 6px 0;
}}
.med-hero h1 {{
    font-size: 2.2rem;
    margin-bottom: 4px;
    color: {TEAL};
}}
.med-hero p {{
    color: #555;
}}
div[data-testid="stChatMessage"] {{
    border-radius: 14px;
    padding: 4px 8px;
}}
.source-badge {{
    display: inline-block;
    border-radius: 999px;
    padding: 3px 12px;
    margin-bottom: 8px;
    font-size: 0.78rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.02em;
}}
.source-doc {{ background: #ccfbf1; color: #0f766e; }}
.source-web {{ background: #e0e7ff; color: #4338ca; }}
</style>
""", unsafe_allow_html=True)


def render_source_badge(source: str):
    if source == "doc":
        st.markdown('<span class="source-badge source-doc">📄 Documents officiels (HAS/INCa)</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="source-badge source-web">🌐 Recherche web</span>', unsafe_allow_html=True)

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

def api_hermes_recommend(token, session_id):
    r = requests.post(f"{API_URL}/hermes/recommend", json={"session_id": session_id}, headers={"Authorization": f"Bearer {token}"})
    return r

def api_hermes_book(token, session_id, doctor_id, creneau):
    r = requests.post(f"{API_URL}/hermes/book", json={"session_id": session_id, "doctor_id": doctor_id, "creneau": creneau}, headers={"Authorization": f"Bearer {token}"})
    return r

# ── Session state init ────────────────────────────────────────
if "token" not in st.session_state:
    st.session_state.token = None
if "current_session_id" not in st.session_state:
    st.session_state.current_session_id = None
if "page" not in st.session_state:
    st.session_state.page = "login"

# ── Pages ─────────────────────────────────────────────────────
def page_login():
    st.markdown("""
    <div class="med-hero">
        <h1>🏥 Chatbot Médical</h1>
        <p>Assistant informatif basé sur des sources officielles (HAS, INCa)</p>
    </div>
    """, unsafe_allow_html=True)

    _, center, _ = st.columns([1, 1.3, 1])
    with center:
        tab_login, tab_register = st.tabs(["Se connecter", "Créer un compte"])

        with tab_login:
            username = st.text_input("Nom d'utilisateur", key="login_user")
            password = st.text_input("Mot de passe", type="password", key="login_pass")
            if st.button("Se connecter", use_container_width=True, type="primary"):
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
            if st.button("Créer le compte", use_container_width=True, type="primary"):
                r = api_register(new_user, new_email, new_pass)
                if r.status_code == 200:
                    st.success("Compte créé ! Connecte-toi.")
                else:
                    st.error(r.json().get("detail", "Erreur"))

def page_chat():
    token = st.session_state.token

    # Sidebar : liste des sessions
    with st.sidebar:
        st.markdown("### 🏥 Chatbot Médical")
        st.caption("Conversations")
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
    st.title("🏥 Chatbot Médical")
    st.markdown("""
    <div class="med-banner">
        ⚠️ Cet assistant est <strong>informatif uniquement</strong> — il ne remplace pas un avis médical.
        En cas d'urgence, contactez le 15 (SAMU) ou rendez-vous aux urgences.
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.current_session_id is None:
        st.info("Crée une nouvelle conversation dans le menu à gauche.")
        return

    # Afficher les messages
    messages = api_get_messages(token, st.session_state.current_session_id)
    for msg in messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant" and msg.get("source"):
                render_source_badge(msg["source"])
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
                source = result.get("source")
            if source:
                render_source_badge(source)
            st.write(answer)
        st.rerun()

    render_hermes_section(token, st.session_state.current_session_id)


def render_hermes_section(token, session_id):
    st.divider()
    if st.button("🩺 Voir un spécialiste"):
        with st.spinner("Hermes analyse la conversation..."):
            r = api_hermes_recommend(token, session_id)
        if r.status_code != 200:
            st.warning(r.json().get("detail", "Impossible de recommander un spécialiste pour le moment."))
            return
        st.session_state.hermes_result = r.json()

    result = st.session_state.get("hermes_result")
    if not result:
        return

    st.markdown(f"""
    <div class="med-banner">
        🤖 <strong>Hermes recommande :</strong> {result['specialite'].capitalize()}<br>
        <span style="color:#555;">{result['justification']}</span>
    </div>
    """, unsafe_allow_html=True)

    doctors = result.get("doctors", [])
    if not doctors:
        st.info("Aucun médecin disponible pour cette spécialité pour le moment.")
        return

    for doctor in doctors:
        with st.container(border=True):
            st.write(f"**{doctor['nom']}** — {doctor['specialite']}")
            if not doctor["creneaux"]:
                st.caption("Aucun créneau disponible.")
                continue
            creneau = st.selectbox("Créneau", doctor["creneaux"], key=f"creneau_{doctor['id']}")
            if st.button("Réserver", key=f"book_{doctor['id']}", type="primary"):
                r = api_hermes_book(token, session_id, doctor["id"], creneau)
                if r.status_code == 200:
                    st.success(f"Rendez-vous confirmé avec {doctor['nom']} le {creneau}.")
                    del st.session_state.hermes_result
                    st.rerun()
                else:
                    st.error(r.json().get("detail", "Erreur lors de la réservation."))

# ── Router ────────────────────────────────────────────────────
if st.session_state.token is None:
    page_login()
else:
    page_chat()
