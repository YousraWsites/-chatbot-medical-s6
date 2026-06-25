import os

import streamlit as st
import requests

try:
    API_URL = st.secrets["API_URL"]
except (KeyError, FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
    API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="MediGuide — Assistant santé", page_icon="🏥", layout="wide")

# Palette MediGuide — identique au site landing pour cohérence visuelle bout-en-bout.
TEAL_900 = "#134e4a"
TEAL_700 = "#0f766e"
TEAL_500 = "#14b8a6"
TEAL_100 = "#ccfbf1"
TEAL_50 = "#f0fdfa"

st.markdown(f"""
<style>
.stApp {{
    background: {TEAL_50};
}}
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {TEAL_700} 0%, {TEAL_900} 100%);
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
    color: {TEAL_900};
}}
.stTabs [data-baseweb="tab"] {{
    font-weight: 600;
}}
.stTabs [aria-selected="true"] {{
    color: {TEAL_700} !important;
}}
/* Streamlit primary button : on force la palette teal MediGuide (sinon rouge par défaut) */
.stButton button[kind="primary"],
button[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] button {{
    background: linear-gradient(135deg, {TEAL_700} 0%, {TEAL_500} 100%) !important;
    border: none !important;
    color: white !important;
    box-shadow: 0 8px 22px rgba(15, 118, 110, 0.18) !important;
}}
.stButton button[kind="primary"]:hover,
button[data-testid="stBaseButton-primary"]:hover {{
    filter: brightness(1.06);
}}
.med-banner {{
    background: white;
    border-left: 4px solid {TEAL_500};
    border-radius: 8px;
    padding: 12px 18px;
    margin-bottom: 18px;
    color: {TEAL_900};
    font-size: 0.92rem;
}}
.med-hero {{
    text-align: center;
    padding: 30px 0 6px 0;
}}
.med-hero .hero-badge {{
    display: inline-block;
    background: white;
    color: {TEAL_700};
    border: 1px solid {TEAL_100};
    padding: 4px 12px;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
    margin-bottom: 14px;
}}
.med-hero h1 {{
    font-size: 2.2rem;
    margin-bottom: 4px;
    color: {TEAL_700};
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
.source-doc {{ background: {TEAL_100}; color: {TEAL_700}; }}
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

def api_list_appointments(token):
    r = requests.get(f"{API_URL}/hermes/appointments", headers={"Authorization": f"Bearer {token}"})
    return r.json() if r.status_code == 200 else []

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
        <div class="hero-badge">🇫🇷 Sources officielles HAS &amp; INCa</div>
        <h1>🏥 MediGuide</h1>
        <p>Votre assistant santé virtuel — informatif, sourcé, traçable.</p>
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
        st.markdown("### 🏥 MediGuide")
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

        # Mes rendez-vous (n'apparaît que si au moins un RDV pris)
        appts = api_list_appointments(token)
        if appts:
            st.divider()
            st.markdown("### 📅 Mes rendez-vous")
            for a in appts:
                st.markdown(
                    f"**{a['doctor_nom']}**  \n"
                    f"_{a['doctor_specialite']}_  \n"
                    f"🗓 {a['creneau']} — _{a['statut']}_"
                )

        st.divider()
        if st.button("Se déconnecter"):
            st.session_state.token = None
            st.session_state.current_session_id = None
            st.session_state.page = "login"
            st.rerun()

    # Zone de chat
    st.title("🏥 MediGuide")
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

    # Hermes : n'apparaît qu'après au moins un échange complet (1 user + 1 assistant)
    # pour avoir un vrai contexte clinique à analyser, pas un bouton vide en haut de page.
    render_hermes_section(token, st.session_state.current_session_id, len(messages))


def render_hermes_section(token, session_id, message_count: int):
    if message_count < 2:
        return

    st.divider()
    st.caption("💡 Tu peux maintenant demander une orientation vers un spécialiste à partir de cette conversation.")
    if st.button("🩺 Trouver un spécialiste pour cette consultation"):
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
                    st.success(
                        f"✅ Rendez-vous confirmé avec {doctor['nom']} le {creneau}. "
                        f"Tu peux le retrouver dans **📅 Mes rendez-vous** dans le menu à gauche."
                    )
                    del st.session_state.hermes_result
                    st.rerun()
                else:
                    st.error(r.json().get("detail", "Erreur lors de la réservation."))

# ── Router ────────────────────────────────────────────────────
if st.session_state.token is None:
    page_login()
else:
    page_chat()
