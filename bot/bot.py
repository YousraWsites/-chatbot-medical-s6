"""Hermes Bot — polling Telegram pour les commandes entrantes du praticien.

Tourne en boucle infinie, lit getUpdates en long-polling, dispatche les messages
des groupes associés à un médecin (Doctor.telegram_chat_id) vers une mini-API
en SQL direct + LLM (Gemini via le service rag).

Commandes supportées :
  /aide                  → liste des commandes
  /rdv_aujourdhui        → liste des RDV du médecin pour aujourd'hui
  /rdv_demain            → liste des RDV du médecin pour demain
  /rdv                   → tous les RDV à venir du médecin

Tout message en langage naturel est passé à Gemini qui répond en utilisant le
contexte du médecin (nom, spécialité, créneaux). C'est volontairement minimaliste
— l'objectif est de démontrer le pattern agent côté praticien, pas de remplacer
Doctolib.
"""
import os
import sys
import time
import logging
import requests
from datetime import date, timedelta

# On importe les modèles SQLAlchemy depuis le backend (volume monté).
sys.path.insert(0, "/app/backend")
from app.database import SessionLocal
from app.models.models import Doctor, Appointment, User
from app.services.rag import _call_llm

logging.basicConfig(level=logging.INFO, format="[bot] %(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("hermes-bot")

TOKEN = os.environ["TELEGRAM_BOT_TOKEN"]
API = f"https://api.telegram.org/bot{TOKEN}"


def send(chat_id, text, parse_mode="Markdown"):
    try:
        r = requests.post(f"{API}/sendMessage", json={
            "chat_id": chat_id, "text": text, "parse_mode": parse_mode,
        }, timeout=10)
        r.raise_for_status()
    except Exception as e:
        log.warning("send failed: %s", e)


def cmd_aide(doctor):
    return (
        f"👋 Bonjour *{doctor.nom}* !\n\n"
        "Je suis *Hermes*, votre assistant de gestion de rendez-vous MediGuide.\n\n"
        "*Commandes disponibles :*\n"
        "• `/aide` — affiche ce message\n"
        "• `/rdv_aujourdhui` — vos rendez-vous du jour\n"
        "• `/rdv_demain` — vos rendez-vous de demain\n"
        "• `/rdv` — tous vos rendez-vous à venir\n\n"
        "Vous pouvez aussi me poser des questions en langage naturel "
        "(ex: « combien de patients cette semaine ? »)."
    )


def _format_rdv_list(rows):
    if not rows:
        return "_Aucun rendez-vous._"
    lines = []
    for appt, user in rows:
        name = user.username if user else f"#{appt.user_id}"
        lines.append(f"• *{appt.creneau}* — `{name}` _(session #{appt.session_id}, {appt.statut})_")
    return "\n".join(lines)


def _rdv_for_day(db, doctor, target_day: date):
    prefix = target_day.strftime("%Y-%m-%d")
    rows = (
        db.query(Appointment, User)
        .outerjoin(User, User.id == Appointment.user_id)
        .filter(Appointment.doctor_id == doctor.id)
        .filter(Appointment.creneau.startswith(prefix))
        .order_by(Appointment.creneau)
        .all()
    )
    return rows


def cmd_rdv_aujourdhui(db, doctor):
    rows = _rdv_for_day(db, doctor, date.today())
    return f"📅 *RDV aujourd'hui* ({date.today():%d/%m/%Y})\n{_format_rdv_list(rows)}"


def cmd_rdv_demain(db, doctor):
    d = date.today() + timedelta(days=1)
    rows = _rdv_for_day(db, doctor, d)
    return f"📅 *RDV demain* ({d:%d/%m/%Y})\n{_format_rdv_list(rows)}"


def cmd_rdv_all(db, doctor):
    today = date.today().strftime("%Y-%m-%d")
    rows = (
        db.query(Appointment, User)
        .outerjoin(User, User.id == Appointment.user_id)
        .filter(Appointment.doctor_id == doctor.id)
        .filter(Appointment.creneau >= today)
        .order_by(Appointment.creneau)
        .all()
    )
    return f"📅 *Vos RDV à venir*\n{_format_rdv_list(rows)}"


def cmd_natural(db, doctor, message):
    """Toute question en langage naturel : on passe à Gemini avec le contexte du médecin."""
    today = date.today().strftime("%Y-%m-%d")
    rows = (
        db.query(Appointment, User)
        .outerjoin(User, User.id == Appointment.user_id)
        .filter(Appointment.doctor_id == doctor.id)
        .filter(Appointment.creneau >= today)
        .order_by(Appointment.creneau)
        .limit(20)
        .all()
    )
    rdv_str = _format_rdv_list(rows)
    prompt = f"""Tu es Hermes, l'assistant de gestion de RDV du Dr. {doctor.nom} ({doctor.specialite}).
Le praticien te pose une question via Telegram. Réponds de manière concise et professionnelle.

Contexte — RDV à venir du Dr. {doctor.nom} :
{rdv_str}

Date du jour : {today}

Question du praticien : {message}

Réponse (max 5 lignes, format Markdown Telegram) :"""
    try:
        return _call_llm(prompt).strip()
    except Exception as e:
        log.warning("LLM error: %s", e)
        return "⚠️ Je n'arrive pas à analyser votre demande pour le moment. Réessayez ou tapez `/aide`."


def handle_message(db, msg):
    chat = msg.get("chat", {})
    chat_id = str(chat.get("id"))
    text = (msg.get("text") or "").strip()
    if not text:
        return

    doctor = db.query(Doctor).filter(Doctor.telegram_chat_id == chat_id).first()
    if not doctor:
        log.info("message from unknown chat %s, ignored", chat_id)
        return

    log.info("from %s (%s): %s", doctor.nom, chat_id, text[:80])

    # Strip @bot_username s'il est mentionné
    text_lower = text.lower().split("@")[0].strip()

    if text_lower in ("/start", "/aide", "/help"):
        send(chat_id, cmd_aide(doctor))
    elif text_lower in ("/rdv_aujourdhui", "/rdv_today", "/today"):
        send(chat_id, cmd_rdv_aujourdhui(db, doctor))
    elif text_lower in ("/rdv_demain", "/rdv_tomorrow", "/tomorrow"):
        send(chat_id, cmd_rdv_demain(db, doctor))
    elif text_lower in ("/rdv", "/rdvs", "/list"):
        send(chat_id, cmd_rdv_all(db, doctor))
    elif text.startswith("/"):
        send(chat_id, "Commande inconnue. Tapez `/aide` pour la liste.")
    else:
        send(chat_id, cmd_natural(db, doctor, text))


def main():
    log.info("Hermes Bot started, polling...")
    offset = None
    while True:
        try:
            params = {"timeout": 30}
            if offset is not None:
                params["offset"] = offset
            r = requests.get(f"{API}/getUpdates", params=params, timeout=40)
            data = r.json()
            if not data.get("ok"):
                log.warning("getUpdates not ok: %s", data)
                time.sleep(5)
                continue
            for upd in data.get("result", []):
                offset = upd["update_id"] + 1
                msg = upd.get("message") or upd.get("edited_message")
                if msg:
                    db = SessionLocal()
                    try:
                        handle_message(db, msg)
                    except Exception:
                        log.exception("handle_message failed")
                    finally:
                        db.close()
        except requests.exceptions.RequestException as e:
            log.warning("network error: %s", e)
            time.sleep(5)
        except Exception:
            log.exception("loop error")
            time.sleep(5)


if __name__ == "__main__":
    main()
