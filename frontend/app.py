import os
from datetime import datetime

import streamlit as st
import requests

try:
    API_URL = st.secrets["API_URL"]
except (KeyError, FileNotFoundError, st.errors.StreamlitSecretNotFoundError):
    API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="MediGuide — Assistant santé", page_icon="🏥", layout="wide",
                   initial_sidebar_state="auto")

# Palette MediGuide
TEAL_900 = "#134e4a"
TEAL_700 = "#0f766e"
TEAL_500 = "#14b8a6"
TEAL_100 = "#ccfbf1"
TEAL_50 = "#f0fdfa"

st.markdown(f"""
<style>
.stApp {{ background: {TEAL_50}; }}
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, {TEAL_700} 0%, {TEAL_900} 100%);
}}
section[data-testid="stSidebar"] * {{ color: #ecfdf5 !important; }}
section[data-testid="stSidebar"] button {{
    background: rgba(255,255,255,0.12) !important;
    border: 1px solid rgba(255,255,255,0.3) !important;
}}
section[data-testid="stSidebar"] button p {{ color: #ecfdf5 !important; }}
h1, h2, h3 {{ color: {TEAL_900}; }}
.stTabs [data-baseweb="tab"] {{ font-weight: 600; }}
.stTabs [aria-selected="true"] {{ color: {TEAL_700} !important; }}
/* Bouton primary teal (sinon rouge par défaut) */
.stButton button[kind="primary"],
button[data-testid="stBaseButton-primary"],
[data-testid="stFormSubmitButton"] button {{
    background: linear-gradient(135deg, {TEAL_700} 0%, {TEAL_500} 100%) !important;
    border: none !important; color: white !important;
    box-shadow: 0 8px 22px rgba(15, 118, 110, 0.18) !important;
}}
.med-banner {{
    background: white; border-left: 4px solid {TEAL_500};
    border-radius: 8px; padding: 12px 18px; margin-bottom: 18px;
    color: {TEAL_900}; font-size: 0.92rem;
}}
.med-hero {{ text-align: center; padding: 30px 0 6px 0; }}
.med-hero .hero-badge {{
    display: inline-block; background: white; color: {TEAL_700};
    border: 1px solid {TEAL_100}; padding: 4px 12px; border-radius: 999px;
    font-size: 0.8rem; font-weight: 600; margin-bottom: 14px;
}}
.med-hero h1 {{ font-size: 2.2rem; margin-bottom: 4px; color: {TEAL_700}; }}
.med-hero p {{ color: #555; }}
div[data-testid="stChatMessage"] {{ border-radius: 14px; padding: 4px 8px; }}
.source-badge {{
    display: inline-block; border-radius: 999px; padding: 3px 12px;
    margin-bottom: 8px; font-size: 0.78rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.02em;
}}
.source-doc {{ background: {TEAL_100}; color: {TEAL_700}; }}
.source-web {{ background: #e0e7ff; color: #4338ca; }}

/* === Cartes médecin riches pour la prise de RDV === */
.doc-card {{
    background: white; border-radius: 14px; padding: 18px 20px;
    border: 1px solid #e5e7eb; box-shadow: 0 1px 3px rgba(15,23,42,0.06);
    margin-bottom: 14px;
}}
.doc-card .nom {{
    font-weight: 700; font-size: 1.08rem; color: {TEAL_900}; margin-bottom: 2px;
}}
.doc-card .specialite {{
    display: inline-block; background: {TEAL_100}; color: {TEAL_700};
    padding: 2px 10px; border-radius: 999px; font-size: 0.78rem;
    font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em;
}}
.doc-card .hopital {{ color: #475569; font-size: 0.92rem; margin: 8px 0 2px; }}
.doc-card .meta {{ color: #64748b; font-size: 0.85rem; }}
.doc-card .bio {{
    color: #334155; font-size: 0.9rem; line-height: 1.5; margin-top: 10px;
    padding-top: 10px; border-top: 1px solid #f1f5f9;
}}

/* === Carte récap RDV (style "ticket") === */
.rdv-ticket {{
    background: white; border-radius: 16px; padding: 22px 24px;
    border: 1px solid #e5e7eb; box-shadow: 0 6px 18px rgba(15,118,110,0.10);
    margin-bottom: 16px; position: relative; overflow: hidden;
}}
.rdv-ticket::before {{
    content: ""; position: absolute; left: 0; top: 0; bottom: 0; width: 6px;
    background: linear-gradient(180deg, {TEAL_700}, {TEAL_500});
}}
.rdv-ticket.cancelled::before {{ background: #ef4444; }}
.rdv-ticket.cancelled {{ opacity: 0.7; }}
.rdv-ticket h4 {{
    margin: 0 0 6px; color: {TEAL_900}; font-size: 1.05rem; font-weight: 700;
}}
.rdv-ticket .when {{
    font-size: 1.3rem; font-weight: 800; color: {TEAL_700};
    margin: 8px 0; letter-spacing: -0.02em;
}}
.rdv-ticket .badge-status {{
    display: inline-block; padding: 3px 10px; border-radius: 999px;
    font-size: 0.72rem; font-weight: 700; text-transform: uppercase;
    letter-spacing: 0.04em;
}}
.rdv-ticket .badge-status.confirm {{ background: {TEAL_100}; color: {TEAL_700}; }}
.rdv-ticket .badge-status.cancel {{ background: #fee2e2; color: #b91c1c; }}
.rdv-ticket .meta-row {{
    display: flex; gap: 18px; margin-top: 12px; flex-wrap: wrap;
    color: #475569; font-size: 0.88rem;
}}
.rdv-ticket .motif {{
    margin-top: 12px; padding: 10px 12px; background: {TEAL_50};
    border-radius: 8px; font-size: 0.88rem; color: #334155;
    border-left: 3px solid {TEAL_500};
}}

/* === Responsive mobile === */
@media (max-width: 768px) {{
    .med-hero h1 {{ font-size: 1.6rem; }}
    .doc-card {{ padding: 14px 14px; }}
    .rdv-ticket {{ padding: 18px 18px; }}
    .rdv-ticket .when {{ font-size: 1.1rem; }}
    .rdv-ticket .meta-row {{ gap: 10px; font-size: 0.82rem; }}
    /* Sidebar plus compacte sur mobile */
    section[data-testid="stSidebar"] {{ width: min(280px, 85vw) !important; }}
    /* Évite que la zone de chat soit trop étroite */
    .block-container {{ padding-left: 1rem !important; padding-right: 1rem !important; }}
    /* Header bandeau alerte plus compact */
    .med-banner {{ font-size: 0.85rem; padding: 10px 14px; }}
}}
@media (max-width: 480px) {{
    .stTitle, .block-container h1 {{ font-size: 1.4rem !important; }}
    .med-hero h1 {{ font-size: 1.3rem; }}
}}
</style>
""", unsafe_allow_html=True)


def render_source_badge(source: str):
    if source == "doc":
        st.markdown('<span class="source-badge source-doc">📄 Documents officiels (HAS/INCa)</span>', unsafe_allow_html=True)
    else:
        st.markdown('<span class="source-badge source-web">🌐 Recherche web</span>', unsafe_allow_html=True)


# ── Auth helpers ──────────────────────────────────────────────
def api_register(username, email, password):
    return requests.post(f"{API_URL}/auth/register", json={"username": username, "email": email, "password": password})

def api_login(username, password):
    return requests.post(f"{API_URL}/auth/login", data={"username": username, "password": password})

def api_get_sessions(token):
    return requests.get(f"{API_URL}/sessions/", headers={"Authorization": f"Bearer {token}"}).json()

def api_create_session(token, title="Nouvelle conversation"):
    return requests.post(f"{API_URL}/sessions/", json={"title": title}, headers={"Authorization": f"Bearer {token}"}).json()

def api_get_messages(token, session_id):
    return requests.get(f"{API_URL}/sessions/{session_id}/messages", headers={"Authorization": f"Bearer {token}"}).json()

def api_chat(token, session_id, question):
    return requests.post(f"{API_URL}/chat/", json={"session_id": session_id, "question": question}, headers={"Authorization": f"Bearer {token}"}).json()

def api_delete_session(token, session_id):
    requests.delete(f"{API_URL}/sessions/{session_id}", headers={"Authorization": f"Bearer {token}"})

def api_hermes_recommend(token, session_id):
    return requests.post(f"{API_URL}/hermes/recommend", json={"session_id": session_id}, headers={"Authorization": f"Bearer {token}"})

def api_hermes_book(token, payload):
    return requests.post(f"{API_URL}/hermes/book", json=payload, headers={"Authorization": f"Bearer {token}"})

def api_list_appointments(token):
    r = requests.get(f"{API_URL}/hermes/appointments", headers={"Authorization": f"Bearer {token}"})
    return r.json() if r.status_code == 200 else []

def api_cancel_appointment(token, appointment_id):
    return requests.post(f"{API_URL}/hermes/appointments/{appointment_id}/cancel",
                         headers={"Authorization": f"Bearer {token}"})


# ── Session state init ────────────────────────────────────────
for key, default in [
    ("token", None),
    ("current_session_id", None),
    ("page", "login"),
    ("hermes_result", None),
    ("booking_doctor", None),       # doctor dict en cours de booking
    ("booking_creneau", None),
]:
    if key not in st.session_state:
        st.session_state[key] = default


# ===================================================================
# PAGE LOGIN
# ===================================================================
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
            u = st.text_input("Nom d'utilisateur", key="login_user")
            p = st.text_input("Mot de passe", type="password", key="login_pass")
            if st.button("Se connecter", use_container_width=True, type="primary"):
                r = api_login(u, p)
                if r.status_code == 200:
                    st.session_state.token = r.json()["access_token"]
                    st.session_state.page = "chat"
                    st.rerun()
                else:
                    st.error("Identifiants incorrects")
        with tab_register:
            nu = st.text_input("Nom d'utilisateur", key="reg_user")
            ne = st.text_input("Email", key="reg_email")
            np_ = st.text_input("Mot de passe", type="password", key="reg_pass")
            if st.button("Créer le compte", use_container_width=True, type="primary"):
                r = api_register(nu, ne, np_)
                if r.status_code == 200:
                    st.success("Compte créé ! Connecte-toi.")
                else:
                    st.error(r.json().get("detail", "Erreur"))


# ===================================================================
# SIDEBAR commune (chat / rdv / mes-rdv)
# ===================================================================
def render_sidebar(token, appts_count):
    with st.sidebar:
        st.markdown("### 🏥 MediGuide")

        # Navigation principale
        st.caption("Navigation")
        if st.button("💬 Chat médical", use_container_width=True,
                     type=("primary" if st.session_state.page == "chat" else "secondary")):
            st.session_state.page = "chat"
            st.rerun()
        rdv_label = f"📅 Mes rendez-vous ({appts_count})" if appts_count else "📅 Mes rendez-vous"
        if st.button(rdv_label, use_container_width=True,
                     type=("primary" if st.session_state.page == "mes_rdv" else "secondary")):
            st.session_state.page = "mes_rdv"
            st.rerun()

        st.divider()
        st.caption("Conversations")
        if st.button("+ Nouvelle conversation", use_container_width=True):
            s = api_create_session(token)
            st.session_state.current_session_id = s["id"]
            st.session_state.page = "chat"
            st.session_state.hermes_result = None
            st.rerun()

        sessions = api_get_sessions(token)
        for s in sessions:
            col1, col2 = st.columns([4, 1])
            with col1:
                if st.button(s["title"], key=f"s_{s['id']}", use_container_width=True):
                    st.session_state.current_session_id = s["id"]
                    st.session_state.page = "chat"
                    st.session_state.hermes_result = None
                    st.rerun()
            with col2:
                if st.button("🗑", key=f"del_{s['id']}"):
                    api_delete_session(token, s["id"])
                    if st.session_state.current_session_id == s["id"]:
                        st.session_state.current_session_id = None
                    st.rerun()

        st.divider()
        if st.button("Se déconnecter", use_container_width=True):
            for k in ("token", "current_session_id", "hermes_result", "booking_doctor", "booking_creneau"):
                st.session_state[k] = None
            st.session_state.page = "login"
            st.rerun()


# ===================================================================
# PAGE CHAT
# ===================================================================
def page_chat():
    token = st.session_state.token
    appts = api_list_appointments(token)
    render_sidebar(token, len([a for a in appts if a.get("statut") == "confirmé"]))

    st.title("🏥 MediGuide")
    st.markdown("""
    <div class="med-banner">
        ⚠️ Cet assistant est <strong>informatif uniquement</strong> — il ne remplace pas un avis médical.
        En cas d'urgence, contactez le <strong>15 (SAMU)</strong> ou rendez-vous aux urgences.
    </div>
    """, unsafe_allow_html=True)

    if st.session_state.current_session_id is None:
        st.info("👈 Crée une nouvelle conversation dans le menu à gauche pour commencer.")
        return

    messages = api_get_messages(token, st.session_state.current_session_id)
    for msg in messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "assistant" and msg.get("source"):
                render_source_badge(msg["source"])
            st.write(msg["content"])

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

    # Hermes après ≥ 2 messages
    if len(messages) >= 2:
        st.divider()
        st.caption("💡 Vous pouvez demander une orientation vers un spécialiste à partir de cette conversation.")
        if st.button("🩺 Trouver un spécialiste pour cette consultation"):
            with st.spinner("Hermes analyse la conversation..."):
                r = api_hermes_recommend(token, st.session_state.current_session_id)
            if r.status_code == 200:
                st.session_state.hermes_result = r.json()
                st.session_state.page = "rdv_select"
                st.rerun()
            else:
                st.warning(r.json().get("detail", "Impossible de recommander un spécialiste."))


# ===================================================================
# PAGE RDV — étape 1 : sélection médecin + créneau
# ===================================================================
def page_rdv_select():
    token = st.session_state.token
    appts = api_list_appointments(token)
    render_sidebar(token, len([a for a in appts if a.get("statut") == "confirmé"]))

    result = st.session_state.hermes_result
    if not result:
        st.warning("Aucune recommandation en cours. Retournez sur le chat pour en demander une.")
        if st.button("← Retour au chat"):
            st.session_state.page = "chat"
            st.rerun()
        return

    if st.button("← Retour au chat"):
        st.session_state.page = "chat"
        st.rerun()

    st.title("📋 Prise de rendez-vous")
    st.markdown(f"""
    <div class="med-banner">
        🤖 <strong>Hermes recommande&nbsp;: {result['specialite'].capitalize()}</strong><br>
        <span style="color:#475569;">{result['justification']}</span>
    </div>
    """, unsafe_allow_html=True)

    doctors = result.get("doctors", [])
    if not doctors:
        st.info("Aucun médecin disponible pour cette spécialité pour le moment.")
        return

    st.subheader("Choisissez un praticien")
    for d in doctors:
        with st.container():
            st.markdown(f"""
            <div class="doc-card">
                <div class="nom">{d['nom']}</div>
                <span class="specialite">{d['specialite']}</span>
                <div class="hopital">🏥 {d.get('hopital') or '—'}{', ' + d['ville'] if d.get('ville') else ''}</div>
                <div class="meta">
                    💬 {', '.join(d.get('langues') or []) or 'Français'}
                    &nbsp;·&nbsp; ⏱ {d.get('duree_min') or 30} min
                    &nbsp;·&nbsp; 💶 {d.get('tarif_eur') or '—'} €
                </div>
                {f'<div class="bio">{d["bio"]}</div>' if d.get('bio') else ''}
            </div>
            """, unsafe_allow_html=True)

            if not d.get("creneaux"):
                st.caption("Aucun créneau disponible pour ce praticien.")
                continue

            col1, col2 = st.columns([3, 1])
            with col1:
                slot = st.selectbox("Créneau disponible", d["creneaux"], key=f"slot_{d['id']}")
            with col2:
                st.write("")  # spacing
                if st.button("Choisir ce créneau", key=f"choose_{d['id']}", type="primary",
                             use_container_width=True):
                    st.session_state.booking_doctor = d
                    st.session_state.booking_creneau = slot
                    st.session_state.page = "rdv_confirm"
                    st.rerun()


# ===================================================================
# PAGE RDV — étape 2 : confirmation détaillée
# ===================================================================
def page_rdv_confirm():
    token = st.session_state.token
    appts = api_list_appointments(token)
    render_sidebar(token, len([a for a in appts if a.get("statut") == "confirmé"]))

    d = st.session_state.booking_doctor
    creneau = st.session_state.booking_creneau
    if not d or not creneau:
        st.warning("Aucune réservation en cours.")
        if st.button("← Retour"):
            st.session_state.page = "chat"
            st.rerun()
        return

    if st.button("← Choisir un autre créneau"):
        st.session_state.page = "rdv_select"
        st.rerun()

    st.title("✅ Confirmer le rendez-vous")
    st.caption("Vérifiez les informations puis confirmez. Vous recevrez un récapitulatif à l'écran et la notification sera transmise au praticien.")

    # Récap visuel
    st.markdown(f"""
    <div class="rdv-ticket">
        <h4>{d['nom']} <span class="badge-status confirm">À confirmer</span></h4>
        <div class="when">📅 {creneau}</div>
        <div class="meta-row">
            <span>🏥 {d.get('hopital') or '—'}{', ' + d['ville'] if d.get('ville') else ''}</span>
            <span>⏱ {d.get('duree_min') or 30} min</span>
            <span>💶 {d.get('tarif_eur') or '—'} €</span>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Formulaire détails
    st.subheader("Détails de la consultation")
    suggested = (st.session_state.hermes_result or {}).get("suggested_motif", "")
    motif = st.text_area(
        "Motif de la consultation",
        value=suggested,
        help="Décrivez en une phrase pourquoi vous consultez. Pré-rempli à partir de votre conversation.",
        height=80,
    )
    col1, col2 = st.columns(2)
    with col1:
        type_cs = st.radio(
            "Type de consultation",
            ["présentiel", "téléconsultation"],
            horizontal=True,
            key="type_consult_radio",
        )
    with col2:
        notes = st.text_input(
            "Note pour le praticien (optionnel)",
            placeholder="Ex : prendre carte vitale, antécédents…",
        )

    st.markdown("---")
    col_back, col_confirm = st.columns([1, 2])
    with col_back:
        if st.button("Annuler", use_container_width=True):
            st.session_state.booking_doctor = None
            st.session_state.booking_creneau = None
            st.session_state.page = "rdv_select"
            st.rerun()
    with col_confirm:
        if st.button("🎯 Confirmer le rendez-vous", use_container_width=True, type="primary"):
            r = api_hermes_book(token, {
                "session_id": st.session_state.current_session_id,
                "doctor_id": d["id"],
                "creneau": creneau,
                "motif": motif,
                "type_consultation": type_cs,
                "notes_patient": notes,
            })
            if r.status_code == 200:
                st.session_state.booking_doctor = None
                st.session_state.booking_creneau = None
                st.session_state.hermes_result = None
                st.session_state.page = "mes_rdv"
                st.success("✅ Rendez-vous confirmé ! Le praticien a été notifié.")
                st.rerun()
            else:
                st.error(r.json().get("detail", "Erreur lors de la réservation."))


# ===================================================================
# PAGE MES RDV — liste enrichie avec annulation
# ===================================================================
def page_mes_rdv():
    token = st.session_state.token
    appts = api_list_appointments(token)
    render_sidebar(token, len([a for a in appts if a.get("statut") == "confirmé"]))

    st.title("📅 Mes rendez-vous")
    if not appts:
        st.info("Vous n'avez aucun rendez-vous pour le moment. Lancez une conversation pour qu'Hermes vous oriente vers un spécialiste.")
        if st.button("← Aller au chat"):
            st.session_state.page = "chat"
            st.rerun()
        return

    confirmed = [a for a in appts if a.get("statut") == "confirmé"]
    cancelled = [a for a in appts if a.get("statut") == "annulé"]

    if confirmed:
        st.subheader(f"À venir ({len(confirmed)})")
        for a in confirmed:
            _render_appointment_card(token, a, cancellable=True)

    if cancelled:
        with st.expander(f"Rendez-vous annulés ({len(cancelled)})", expanded=False):
            for a in cancelled:
                _render_appointment_card(token, a, cancellable=False)


def _render_appointment_card(token, a, cancellable=True):
    d = a.get("doctor") or {}
    cls = "rdv-ticket" + (" cancelled" if a.get("statut") == "annulé" else "")
    badge_cls = "cancel" if a.get("statut") == "annulé" else "confirm"
    motif_html = ""
    if a.get("motif"):
        motif_html = f'<div class="motif"><strong>Motif&nbsp;:</strong> {a["motif"]}</div>'
    notes_html = ""
    if a.get("notes_patient"):
        notes_html = f'<div class="motif"><strong>Notes au praticien&nbsp;:</strong> {a["notes_patient"]}</div>'

    st.markdown(f"""
    <div class="{cls}">
        <h4>{d.get('nom','?')} <span class="badge-status {badge_cls}">{a.get('statut','?')}</span></h4>
        <div class="when">📅 {a.get('creneau','?')}</div>
        <div class="meta-row">
            <span>🩺 {d.get('specialite','?')}</span>
            <span>🏥 {d.get('hopital','—')}{', ' + d['ville'] if d.get('ville') else ''}</span>
            <span>⏱ {d.get('duree_min') or 30} min</span>
            <span>💻 {a.get('type_consultation') or 'présentiel'}</span>
        </div>
        {motif_html}
        {notes_html}
    </div>
    """, unsafe_allow_html=True)

    if cancellable:
        col1, col2 = st.columns([3, 1])
        with col2:
            if st.button("Annuler", key=f"cancel_{a['id']}", use_container_width=True):
                r = api_cancel_appointment(token, a["id"])
                if r.status_code == 200:
                    st.success(f"Rendez-vous du {a['creneau']} annulé. Le créneau a été libéré et le praticien notifié.")
                    st.rerun()
                else:
                    st.error(r.json().get("detail", "Erreur lors de l'annulation."))


# ===================================================================
# Router
# ===================================================================
if st.session_state.token is None:
    page_login()
else:
    page = st.session_state.page
    if page == "chat":
        page_chat()
    elif page == "rdv_select":
        page_rdv_select()
    elif page == "rdv_confirm":
        page_rdv_confirm()
    elif page == "mes_rdv":
        page_mes_rdv()
    else:
        st.session_state.page = "chat"
        page_chat()
